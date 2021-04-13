# Automatically create ED25519 credentials for services.

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
    """Generates ED25519 public/private key pair."""

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        pubkey_path = self._task.args['pubkey']
        privkey_path = self._task.args['privkey']

        changed = False
        if not os.path.exists(privkey_path) or not os.path.exists(pubkey_path):
            with temp_dir() as tmpdir:
                tmp_privkey_path = os.path.join(tmpdir, 'secret.key')
                subprocess.check_call(
                    ['ed25519gen',
                     '--outkey=' + tmp_privkey_path,
                     '--output=' + pubkey_path])
                vault_encrypt(tmp_privkey_path, privkey_path)
            changed = True

        result = super(ActionModule, self).run(tmp, task_vars)
        result['changed'] = changed
        return result
