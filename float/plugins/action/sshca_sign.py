# Automatically sign SSH host keys with a CA.
#
# The SSH CA private key is stored in the configuration repository,
# encrypted with Ansible Vault. For this to work, the
# ANSIBLE_VAULT_PASSWORD_FILE environment variable should be set, so
# that we can simply invoke 'ansible-vault decrypt'.

import base64
import contextlib
import os
import re
import shutil
import subprocess
import tempfile
import time

from ansible.plugins.action import ActionBase


@contextlib.contextmanager
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def vault_decrypt(srcpath, dstpath):
    if os.getenv('ANSIBLE_VAULT_PASSWORD_FILE'):
        subprocess.check_call(
            ['ansible-vault', 'decrypt', '--output=' + dstpath, srcpath])
    else:
        shutil.copy(srcpath, dstpath)


class ActionModule(ActionBase):
    """Sign SSH host keys with a CA.

    Will fetch the remote host key and copy back the signed
    certificate, in a single action (for simplicity). Uses a local
    temporary directory to do the signing.
    """

    TRANSFERS_FILES = True

    def run(self, tmp=None, task_vars=None):
        hostname = self._templar.template('{{inventory_hostname}}')
        fqdn = self._templar.template('{{inventory_hostname}}.{{domain}}')

        ca_private_key_path = self._task.args['ca']
        pubkey_path = self._task.args['pubkey']
        principals = self._task.args.get('principals', [fqdn])
        validity = self._task.args.get('validity', '52w')
        renew_days = int(self._task.args.get('renew_days', '60'))
        cert_path = re.sub(r'\.pub$', '-cert.pub', pubkey_path)

        result = super(ActionModule, self).run(tmp, task_vars)

        # TODO: Support check_mode properly. Right now we simply
        # return with changed: false, because we are unable to run the
        # 'ssh-keygen' command remotely to obtain the expiration time.
        if self._play_context.check_mode:
            result['changed'] = False
            return result

        changed = False
        if self._needs_renewal(task_vars, cert_path, renew_days):
            with temp_dir() as tmpdir:
                # Decrypt the SSH CA key into the temporary directory.
                tmp_ca_private_key_path = os.path.join(tmpdir, 'cakey')
                vault_decrypt(ca_private_key_path, tmp_ca_private_key_path)

                tmp_pubkey_path = os.path.join(tmpdir, 'host.pub')
                tmp_cert_path = os.path.join(tmpdir, 'host-cert.pub')
                self._fetch_pubkey(task_vars, pubkey_path, tmp_pubkey_path)

                subprocess.check_call(
                    ['ssh-keygen', '-h', '-s', tmp_ca_private_key_path,
                     '-I', 'host-' + hostname, '-n', ','.join(principals),
                     '-V', '+' + validity, tmp_pubkey_path])

                self._store_cert(tmp, task_vars, tmp_cert_path, cert_path)

                changed = True

        result['changed'] = changed
        return result

    def _needs_renewal(self, task_vars, cert_path, renew_days):
        # Check if the certificate exists.
        result = self._execute_module(
            module_name='stat',
            module_args={'path': cert_path},
            task_vars=task_vars,
            wrap_async=False)
        if not result['stat']['exists']:
            return True

        # Check the expiration date.
        result = self._execute_module(
            module_name='command',
            module_args={
                '_raw_params': "ssh-keygen -L -f %s | awk '/Valid:/ {print $5}'" % cert_path,
                '_uses_shell': True,
            },
            task_vars=task_vars,
            wrap_async=False)
        if result['rc'] != 0:
            return True
        expiration = time.mktime(
            time.strptime(result['stdout'].strip(), '%Y-%m-%dT%H:%M:%S'))
        warn_deadline = time.time() + (86400 * renew_days)
        return expiration < warn_deadline

    def _fetch_pubkey(self, task_vars, pubkey_path, local_path):
        result = self._execute_module(
            module_name='slurp',
            module_args={
                'src': pubkey_path,
            },
            task_vars=task_vars,
            wrap_async=False)
        with open(local_path, 'w') as fd:
            fd.write(base64.b64decode(result['content']).decode('utf-8'))

    def _store_cert(self, tmp, task_vars, local_path, cert_path):
        # From Ansible 2.5 we should use 'self._connection._shell.tmpdir' instead of 'tmp'.
        if tmp is None:
            tmp = self._make_tmp_path()
        tmp_src = self._connection._shell.join_path(tmp, 'source')

        remote_path = self._transfer_file(local_path, tmp_src)
        self._fixup_perms2((tmp, remote_path))
        self._execute_module(
            module_name='copy',
            module_args={
                'src': remote_path,
                'dest': cert_path,
                'owner': 'root',
                'group': 'root',
                'mode': 0o600,
            },
            task_vars=task_vars)
