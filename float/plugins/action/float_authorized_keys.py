# Prepare a SSH authorized_keys file content using float 'admins'.

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        admins = self._templar.template('{{ admins }}')
        authorized_keys = []

        # For each SSH key, add a comment with the owner's username.
        for entry in admins:
            username = entry['name']
            if 'ssh_keys' not in entry:
                continue
            for key in entry['ssh_keys']:
                key_without_comment = ' '.join(key.split()[:2])
                key_with_comment = f'{key_without_comment} {username}\n'
                authorized_keys.append(key_with_comment)

        result = super(ActionModule, self).run(tmp, task_vars)
        result['ansible_facts'] = {'float_authorized_keys': ''.join(authorized_keys)}
        result['changed'] = False
        return result
