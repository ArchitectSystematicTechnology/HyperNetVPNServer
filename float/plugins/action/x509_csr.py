# Automatically create X509 CSR for services.
#
# This module creates all the required X509 CSR for a given service.
#
# Tasks use this module to then generate certificates on each host.

import os
import random
from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):
    """Automatically create X509 CSRs for a given service."""

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        # Retrieve action parameters.
        credentials_name = self._task.args['credentials_name']
        domain = self._task.args['domain']
        mode = self._task.args['mode']
        params = self._task.args.get('params', {})
        private_key_path = self._task.args['private_key_path']
        cert_path = self._task.args.get('cert_path')
        ca_cert_path = self._task.args.get('ca_cert_path')
        check_only = self._task.args.get('check', False)
        renew_days = int(self._task.args.get('renew_days', '30'))

        names = []
        ip_addrs = []
        is_client, is_server = False, False
        if mode == 'client':
            is_client = True
            names = ['%s.%s' % (credentials_name, domain)]
        elif mode == 'server':
            is_server = True
            # For each name, use the short version and the FQDN.
            for n in params.get('names', []):
                names.append('%s.%s' % (n, domain))
                names.append(n)
            ip_addrs = params.get('addrs', [])
        else:
          raise Exception('mode must be client or server')

        result = super(ActionModule, self).run(tmp, task_vars)

        names.sort()
        cn = names[0]
        changed = True
        subject = 'CN=' + cn
        if check_only:
            # When the 'check' argument is true, only check the
            # validity of the currently installed certificate.
            changed, reason = self._check_cert(
                task_vars, subject, names, ip_addrs, is_client, is_server,
                renew_days, cert_path, ca_cert_path)
            if changed:
                result['reason'] = reason
        else:
            # When Ansible runs in check mode, generate a valid CSR
            # using a temporary private key that will be deleted when
            # done.
            if self._play_context.check_mode:
                private_key_path = '/tmp/pkey-%x' % random.randint(0, 1<<32)

            self._make_private_key(task_vars, private_key_path)
            csr = self._make_csr(task_vars, subject, names, ip_addrs, private_key_path)
            result['csr'] = csr

            if self._play_context.check_mode:
                self._cmd(task_vars, ['rm', '-f', private_key_path])

        result['changed'] = changed
        return result

    def _cmd(self, task_vars, args, creates=None):
        args = {
            '_raw_params': ' '.join(args),
            'creates': creates,
        }
        return self._execute_module(
            module_name='command',
            module_args=args,
            task_vars=task_vars,
            wrap_async=False)

    def _make_private_key(self, task_vars, private_key_path):
        cmd = ['x509ca', 'gen-key', '--key=' + private_key_path]
        self._cmd(task_vars, cmd, creates=private_key_path)

    def _make_csr(self, task_vars, subject, alt_names, ip_addrs, private_key_path):
        cmd = ['x509ca', 'csr',
               '--key=' + private_key_path,
               '--subject=' + subject]
        for alt in alt_names:
            cmd.append('--alt=' + alt)
        for ip in ip_addrs:
            cmd.append('--ip=' + ip)
        result = self._cmd(task_vars, cmd)
        if result.get('rc', 0) != 0:
            raise Exception('CSR generation failed: cmd="%s", result=%s' % (
                ' '.join(cmd), str(result)))
        return result['stdout']

    def _check_cert(self, task_vars, subject, alt_names, ip_addrs, is_client,
                    is_server, renew_days, cert_path, ca_cert_path):
        # Return true if the certificate needs to be re-created.
        cmd = ['x509ca', 'check',
               '--cert=' + cert_path,
               '--subject=' + subject,
               '--renew-days=%d' % renew_days]
        if is_client:
            cmd.append('--client')
        if is_server:
            cmd.append('--server')
        for alt in alt_names:
            cmd.append('--alt=' + alt)
        for ip in ip_addrs:
            cmd.append('--ip=' + ip)
        if ca_cert_path:
            cmd.append('--ca-cert=' + ca_cert_path)

        result = self._cmd(task_vars, cmd)
        return (result.get('rc', 0) != 0), result['stdout']
