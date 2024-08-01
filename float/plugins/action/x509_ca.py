# Automatically create X509 service CA.

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

    TRANSFERS_FILES = False

    BYPASS_HOST_LOOP = True

    def run(self, tmp=None, task_vars=None):
        ca_cert_path = self._task.args['ca_cert_path']
        ca_key_path = self._task.args['ca_key_path']
        ca_subject = self._task.args.get('ca_subject', 'O=Service CA')

        result = super(ActionModule, self).run(tmp, task_vars)

        if (os.path.exists(ca_key_path)
            and os.path.exists(ca_cert_path)):
            changed = False
        else:
            changed = True
            with temp_dir() as tmp_dir:
                tmp_ca_key_path = os.path.join(tmp_dir, 'ca_private_key.pem')
                subprocess.check_call([
                    'x509ca', 'init', '--subject=' + ca_subject,
                    '--ca-cert=' + ca_cert_path, '--ca-key=' + tmp_ca_key_path])
                vault_encrypt(tmp_ca_key_path, ca_key_path)

        result['changed'] = changed
        return result
