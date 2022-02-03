# Generate a host configuration file for tinc (fetching the public key
# from the remote host), and store the result in an Ansible fact.

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleFileNotFound
from ansible.module_utils._text import to_text


HOST_TEMPLATE = '''
{% for ip in ips %}
Address = {{ ip }}
{% endfor %}
Port = {{ tinc_config.port | default('655') }}
Cipher = {{ tinc_config.cipher | default('aes-128-cbc') }}
Digest = {{ tinc_config.digest | default('sha256') }}
Compression = {{ tinc_config.compression | default('0') }}
PMTU = {{ tinc_config.pmtu | default('1460') }}
Subnet = {{ tinc_host_subnet }}

{{ tinc_host_public_key }}
'''


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

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

    def run(self, tmp=None, task_vars=None):
        overlay = self._task.args['overlay']
        subnet = self._templar.template('{{ ip_%s }}/32' % overlay)

        # Find the overlay configuration by scanning the 'net_overlays'
        # configuration variable, which is a list - it would be simpler with
        # a dictionary.
        net_overlays = self._templar.template('{{ net_overlays|default([]) }}')
        overlay_config = {'name': overlay}
        for n in net_overlays:
            if n['name'] == overlay:
                overlay_config = n
                break

        result = super(ActionModule, self).run(tmp, task_vars)
        
        # Fetch the host public key.
        pubkey = self._cmd(task_vars, [
            '/bin/cat', '/etc/tinc/%s/rsa_key.pub' % overlay])['stdout']
        if not pubkey:
            result['failed'] = True
            result['msg'] = "could not fetch host public key"
            return result

        # Generate the template, adding some custom variables of our own.
        self._templar._available_variables['tinc_host_subnet'] = subnet
        self._templar._available_variables['tinc_host_public_key'] = pubkey
        self._templar._available_variables['tinc_config'] = overlay_config
        data = self._templar.do_template(HOST_TEMPLATE,
                                         preserve_trailing_newlines=True,
                                         escape_backslashes=False)
        
        result['ansible_facts'] = {'tinc_host_config': data}
        result['changed'] = False
        return result
