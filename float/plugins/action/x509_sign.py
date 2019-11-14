# Sign X509 CSR
#
# This module signs a given X509 CSR.

import contextlib
import os
import shutil
import subprocess
import tempfile

from ansible.plugins.action import ActionBase
from ansible.module_utils._text import to_bytes


@contextlib.contextmanager
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def vault_decrypt(srcpath, dstpath):
    subprocess.check_call(
        ['ansible-vault', 'decrypt', '--output=' + dstpath, srcpath])


class ActionModule(ActionBase):
    """Sign a X509 CSR for a given service."""

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        # Retrieve action parameters.
        csr = self._task.args['csr']
        ca_cert_path = self._task.args['ca_cert_path']
        ca_key_path = self._task.args['ca_key_path']
        mode = self._task.args['mode']

        is_client, is_server = False, False
        if mode == 'client':
          is_client = True
        elif mode == 'server':
          is_server = True
        else:
          raise Exception('mode must be client or server')

        with temp_dir() as tmp_dir:
            tmp_ca_key_path = os.path.join(tmp_dir, 'ca_private_key.pem')
            vault_decrypt(ca_key_path, tmp_ca_key_path)
            signed_csr = self._sign_csr(csr, ca_cert_path, tmp_ca_key_path, is_client, is_server)

        result = super(ActionModule, self).run(tmp, task_vars)

        result['changed'] = True
        result['cert'] = signed_csr
        return result

    def _sign_csr(self, csr, ca_cert_path, ca_key_path, is_client, is_server):
        cmd = ['x509ca', 'sign',
               '--ca-cert=' + ca_cert_path,
               '--ca-key=' + ca_key_path]
        if is_client:
            cmd.append('--client')
        if is_server:
            cmd.append('--server')

        pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = pipe.communicate(to_bytes(csr))
        if pipe.returncode != 0:
            raise Exception('error: %s' % (stderr, ))
        return stdout

