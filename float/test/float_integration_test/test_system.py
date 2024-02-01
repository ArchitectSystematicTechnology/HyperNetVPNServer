import json
import time
import unittest
from dns.resolver import Resolver

from float_integration_test import TestBase, PrometheusTestBase, URLTestBase, \
    ANSIBLE_VARS


class TestHTTPRouter(URLTestBase):
    """Basic functionality test for the public HTTP router."""

    def test_nonexisting_domain_returns_default_page(self):
        c = self.sso_conversation()
        result = c.request('https://an.unknown.domain/',
                           self.frontend_ip())
        self.assertFalse(result.get('error'))
        self.assertEqual(200, result['status'])
        self.assertTrue(self.UNKNOWN_DOMAIN_MSG in result['body'])


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
    services.yml) is actually enabled.

    """

    def assert_endpoint_ok_if_enabled(self, service_name,
                                      public_endpoint_name,
                                      auth=False):
        if service_name not in ANSIBLE_VARS['services']:
            self.skipTest('service %s not enabled' % service_name)
        self.assert_endpoint_ok(public_endpoint_name, auth)

    def test_okserver(self):
        self.assert_endpoint_ok_if_enabled('ok', 'ok')

    def test_service_dashboard(self):
        self.assert_endpoint_ok_if_enabled('service-dashboard', 'service-dashboard', True)

    def test_monitor(self):
        self.assert_endpoint_ok_if_enabled('prometheus', 'monitor', True)

    def test_alertmanager(self):
        self.assert_endpoint_ok_if_enabled('prometheus', 'alerts', True)

    def test_grafana(self):
        self.assert_endpoint_ok_if_enabled('prometheus', 'grafana', True)

    def test_thanos(self):
        self.assert_endpoint_ok_if_enabled('prometheus', 'thanos', True)

    def test_kibana(self):
        if not ANSIBLE_VARS.get('enable_elasticsearch', True):
            self.skipTest('Elasticsearch is disabled')
        self.assert_endpoint_ok_if_enabled('log-collector', 'logs', True)


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


class TestSystem(PrometheusTestBase):
    """Check functionality at the system level."""

    # Alerts that will be ignored.
    WHITELISTED_ALERTS = ['DiskWillFillIn4Hours']

    def test_no_firing_alerts(self):
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
        alerts = self.eval_prometheus_expr('ALERTS')
        print(json.dumps(alerts, indent=4))
        return [
            _alert_to_string(x['metric'])
            for x in alerts
            if (x['metric']['alertstate'] == 'firing' and
                x['metric']['severity'] == 'page' and
                x['metric']['alertname'] not in self.WHITELISTED_ALERTS)
        ]


class TestPrometheusMetrics(PrometheusTestBase):

    def test_all_targets_are_reachable(self):
        result = self.eval_prometheus_expr('up < 1')
        self.assertEqual([], result)

    def test_all_targets_are_being_scraped(self):
        result = self.eval_prometheus_expr('scrape_samples_scraped == 0')
        self.assertEqual([], result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
