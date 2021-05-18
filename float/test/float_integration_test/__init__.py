import os
import random
import unittest
import yaml
import jinja2

from .http import Conversation


# Parse the Ansible ai3 configuration file, and read both the
# inventory and the group_vars/all definitions.
#
# The results will be three global dictionaries:
#
# * ANSIBLE_VARS contains all the Ansible variables
# * TEST_PARAMS are the environment-specific testing parameters,
#   loaded by default from the test-params.yml file in this
#   directory.
#
_ansible_config_file = os.getenv('TEST_CONFIG', 'test-config.yml')
with open(_ansible_config_file) as fd:
    ANSIBLE_VARS = yaml.safe_load(fd)

# Read test parameters.
_params_file = os.getenv(
    'TEST_PARAMS', os.path.join(os.path.dirname(__file__), 'test-params.yml'))
with open(_params_file) as fd:
    TEST_PARAMS = yaml.safe_load(fd)


def _ansible_eval(expr):
    """Evaluate a Jinja expr with the Ansible configuration context."""
    # This will fail horribly if the result is not a string.
    while '{{' in expr:
        expr = jinja2.Template(expr).render(ANSIBLE_VARS)
    return expr


def hosts_in_group(group):
    """Return names of hosts in an inventory group."""
    return ANSIBLE_VARS['groups'].get(group, [])


class TestBase(unittest.TestCase):

    # Tell the 'nose' multiprocess runner that it can parallelize
    # individual tests in the TestCase.
    _multiprocess_can_split_ = True

    def frontend_ip(self):
        """Return a random IP for the 'frontend' group."""
        host = random.choice(hosts_in_group('frontend'))
        return ANSIBLE_VARS['hostvars'][host]['ip']

    def sso_conversation(self, sso_username=None, sso_password=None):
        url = _ansible_eval(
            '{{ sso_server_url | default("https://login." + domain_public[0]) }}')
        if not sso_username:
            sso_username = TEST_PARAMS['priv_user']['name']
        if not sso_password:
            sso_password = TEST_PARAMS['priv_user']['password']
        return Conversation(
            sso_username=sso_username,
            sso_password=sso_password,
            login_server=url,
        )
