import json
import os
import random
import unittest
from urllib.parse import urlencode
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
        return ANSIBLE_VARS['hostvars'][host]['ips'][0]

    def all_frontend_ips(self):
        """Return all IPs in the 'frontend' group."""
        return [ANSIBLE_VARS['hostvars'][x]['ips'][0]
                for x in hosts_in_group('frontend')]

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


class PrometheusTestBase(TestBase):

    def setUp(self):
        super().setUp()
        if 'prometheus' not in ANSIBLE_VARS['services']:
            self.skipTest('monitoring not enabled')
        self.prometheus_url = 'https://monitor.%s' % (
            ANSIBLE_VARS['domain_public'][0],)

    def eval_prometheus_expr(self, expr):
        c = self.sso_conversation()
        uri = '%s/api/v1/query?%s' % (
            self.prometheus_url, urlencode({'query': expr}))
        resp = c.request(uri, self.frontend_ip())
        self.assertFalse(
            'error' in resp,
            'Request failed with error: %s' % resp.get('error'))
        self.assertEqual(200, resp['status'])
        result = json.loads(resp['body'])
        self.assertEqual('success', result['status'],
                         'Prometheus error: %s' % json.dumps(result))
        return result['data']['result']


class URLTestBase(TestBase):

    UNKNOWN_DOMAIN_MSG = b'You have reached this page because your request could not be properly identified'

    def assert_endpoint_ok(self, public_endpoint_name, auth=False):
        c = self.sso_conversation()
        url = 'https://%s.%s/' % (
            public_endpoint_name, ANSIBLE_VARS['domain_public'][0])
        result = c.request(url, self.frontend_ip())
        self.assertFalse(result.get('error'), f'url={url}')
        self.assertEqual(200, result['status'], f'url={url}')
        self.assertFalse(
            self.UNKNOWN_DOMAIN_MSG in result['body'],
            f'The server returned the generic "unknown domain" page for {url}')
        self.assertEqual(auth, c.auth_requested)
