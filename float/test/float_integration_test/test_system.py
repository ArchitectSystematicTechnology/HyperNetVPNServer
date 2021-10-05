import json
import time
import unittest
from dns.resolver import Resolver
from float_integration_test import TestBase, ANSIBLE_VARS


UNKNOWN_DOMAIN_MSG = b'You have reached this page because your request could not be properly identified'


class URLTestBase(TestBase):

    def _assert_endpoint_ok(self, public_endpoint_name, auth=False):
        c = self.sso_conversation()
        url = 'https://%s.%s/' % (
            public_endpoint_name, ANSIBLE_VARS['domain_public'][0])
        result = c.request(url, self.frontend_ip())
        self.assertFalse(result.get('error'), f'url={url}')
        self.assertEqual(200, result['status'], f'url={url}')
        self.assertFalse(
            UNKNOWN_DOMAIN_MSG in result['body'],
            f'The server returned the generic "unknown domain" page for {url}')
        self.assertEqual(auth, c.auth_requested)


class TestHTTPRouter(URLTestBase):
    """Basic functionality test for the public HTTP router."""

    def test_nonexisting_domain_returns_default_page(self):
        c = self.sso_conversation()
        result = c.request('https://an.unknown.domain/',
                           self.frontend_ip())
        self.assertFalse(result.get('error'))
        self.assertEqual(200, result['status'])
        self.assertTrue(UNKNOWN_DOMAIN_MSG in result['body'])


class TestDNS(TestBase):

    def setUp(self):
        self.resolver = Resolver(configure=False)
        self.resolver.nameservers = self.all_frontend_ips()

    def test_public_dns_entries_for_services(self):
        frontend_ips = set(self.all_frontend_ips())
        for service in ANSIBLE_VARS['services'].values():
            for pe in service.get('public_endpoints', []):
                if pe.get('skip_dns', False):
                    continue
                name = '%s.%s' % (pe['name'],
                                  ANSIBLE_VARS['domain_public'][0])
                print(f'querying {name}')
                resp = self.resolver.query(name, 'A')
                for record in resp:
                    self.assertTrue(str(record) in frontend_ips)


class TestBuiltinServiceURLs(URLTestBase):
    """Verify that all the public_endpoints are reachable.

    Tests will only run if the corresponding service (from
    services.yml.default) is actually enabled.

    """

    def _assert_endpoint_ok_if_enabled(self, service_name,
                                       public_endpoint_name,
                                       auth=False):
        if service_name not in ANSIBLE_VARS['services']:
            self.skipTest('service %s not enabled' % service_name)
        self._assert_endpoint_ok(public_endpoint_name, auth)

    def test_okserver(self):
        self._assert_endpoint_ok_if_enabled('ok', 'ok')

    def test_admin_dashboard(self):
        self._assert_endpoint_ok_if_enabled('admin-dashboard', 'admin', True)

    def test_monitor(self):
        self._assert_endpoint_ok_if_enabled('prometheus', 'monitor', True)

    def test_alertmanager(self):
        self._assert_endpoint_ok_if_enabled('prometheus', 'alerts', True)

    def test_grafana(self):
        self._assert_endpoint_ok_if_enabled('prometheus', 'grafana', True)

    def test_thanos(self):
        self._assert_endpoint_ok_if_enabled('prometheus', 'thanos', True)

    def test_kibana(self):
        if not ANSIBLE_VARS.get('enable_elasticsearch', True):
            self.skipTest('Elasticsearch is disabled')
        self._assert_endpoint_ok_if_enabled('log-collector', 'logs', True)


def _alert_to_string(metric):
    o = metric['alertname'] + '('
    if 'name' in metric:
        o += metric['name']
    elif 'instance' in metric:
        o += metric['instance']
    elif 'float_service' in metric:
        o += metric['float_service']
    elif 'job' in metric:
        o += metric['job']
    if 'host' in metric:
        o += '@' + metric['host']
    if 'probe' in metric:
        o += 'probe=' + metric['probe']
    if 'target' in metric:
        o += '@' + metric['target']
    o += ')'
    return o


class TestSystem(TestBase):
    """Check functionality at the system level."""

    # Alerts that will be ignored.
    WHITELISTED_ALERTS = ['DiskWillFillIn4Hours']

    def test_no_firing_alerts(self):
        if 'prometheus' not in ANSIBLE_VARS['services']:
            self.skipTest('monitoring not enabled')
        firing_alerts = None
        for i in range(5):
            try:
                firing_alerts = self._get_firing_alerts()
                break
            except ValueError:
                time.sleep(1)
        self.assertFalse(
            firing_alerts is None,
            'Could not load alerts')
        self.assertEqual(
            0, len(firing_alerts),
            'The following alerts are firing: %s' % (
                ', '.join(firing_alerts),))

    def _get_firing_alerts(self):
        c = self.sso_conversation()
        alerts_uri = 'https://monitor.%s/api/v1/query?query=ALERTS' % (
            ANSIBLE_VARS['domain_public'][0],)
        result = c.request(alerts_uri, self.frontend_ip())
        self.assertFalse(
            'error' in result,
            'Request failed with error: %s' % result.get('error'))
        self.assertEqual(200, result['status'])
        response = json.loads(result['body'])
        self.assertEqual('success', response['status'])
        print(json.dumps(response['data'], indent=4))
        firing_alerts = [
            _alert_to_string(x['metric'])
            for x in response['data']['result']
            if (x['metric']['alertstate'] == 'firing' and
                x['metric']['severity'] == 'page' and
                x['metric']['alertname'] not in self.WHITELISTED_ALERTS)
        ]
        return firing_alerts


if __name__ == '__main__':
    unittest.main(verbosity=2)
