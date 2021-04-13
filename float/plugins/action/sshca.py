# Automatically sign SSH host keys with a CA.
#
# The SSH CA private key is stored in the configuration repository,
# encrypted with Ansible Vault. For this to work, the
# ANSIBLE_VAULT_PASSWORD_FILE environment variable should be set, so
# that we can simply invoke 'ansible-vault encrypt'.

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile

from ansible.plugins.action import ActionBase


@contextlib.contextmanager
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def vault_encrypt(srcpath, dstpath):
    if os.getenv('ANSIBLE_VAULT_PASSWORD_FILE'):
        subprocess.check_call(
            ['ansible-vault', 'encrypt', '--output=' + dstpath, srcpath])
    else:
        print('Warning: no ANSIBLE_VAULT_PASSWORD_FILE, secrets will be '
              'stored unencrypted!', file=sys.stderr)
        shutil.copy(srcpath, dstpath)


class ActionModule(ActionBase):
    """Sign SSH host keys with a CA."""

    TRANSFERS_FILES = False

    BYPASS_HOST_LOOP = True

    def run(self, tmp=None, task_vars=None):
        ca_private_key_path = self._task.args['ca']
        ca_public_key_path = ca_private_key_path + '.pub'

        result = super(ActionModule, self).run(tmp, task_vars)

        changed = False
        if not os.path.exists(ca_private_key_path):
            with temp_dir() as tmpdir:
                # Generate the SSH CA key if it does not exist.
                tmp_ca_private_key_path = os.path.join(tmpdir, 'cakey')
                subprocess.check_call(
                    ['ssh-keygen', '-t', 'ed25519', '-C' 'ca', '-N', '',
                     '-f', tmp_ca_private_key_path])
                vault_encrypt(tmp_ca_private_key_path, ca_private_key_path)
                shutil.copy(tmp_ca_private_key_path + '.pub', ca_public_key_path)
                changed = True

        result['changed'] = changed
        return result
