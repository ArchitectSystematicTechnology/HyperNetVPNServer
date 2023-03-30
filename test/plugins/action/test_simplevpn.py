import unittest
from os import path
from pathlib import Path

from plugins.action import simplevpn

public_domain = "test.com"
provider_description = "testing your floats"
provider_api_uri = "https://testing-float.com"
ca_cert_uri = "https://testing-float.com/cert.pem"
ca_public_crt = path.join(Path(__file__).parent.resolve(), "cert.pem")


class TestSimpleVpn(unittest.TestCase):

    def test_produce_provider_config(self):
        expected = {
            "api_uri": provider_api_uri,
            "api_version": "3",
            "ca_cert_fingerprint": "SHA256: b3ba134cdb0451d3addff3b2b42fc97393b7e5ee8261cd9317e0d4d975446508",
            "ca_cert_uri": ca_cert_uri,
            "default_language": "en",
            "description": {
                "en": provider_description,
            },
            "domain": "%s" % (public_domain),
            "enrollment_policy": "open",
            "languages": [
                "en",
            ],
            "name": {
                "en": provider_description,
            },
            "service": {
                "allow_anonymous": True,
                "allow_free": True,
                "allow_limited_bandwidth": False,
                "allow_paid": False,
                "allow_registration": False,
                "allow_unlimited_bandwidth": True,
                "bandwidth_limit": 102400,
                "default_service_level": 1,
                "levels": {
                    "1": {
                        "description": "Please donate.",
                        "name": "free",
                    },
                },
            },
            "services": [
                "openvpn",
            ],
        }
        actual = simplevpn.produce_provider_config(
            public_domain, provider_description, provider_api_uri, ca_cert_uri, ca_public_crt)

        self.assertEqual(expected, actual)

    def test_produce_eip_config(self):
        gateways = [{
            "inventory_hostname": "gateway1",
            "ip": "10.10.10.1",
            "ips": ["10.10.10.1"],
            "public_ips": ["10.10.10.1"],
        },
            {
            "inventory_hostname": "gateway2",
            "ip": "10.10.10.2",
            "ips": ["10.10.10.2"],
            "public_ips": ["10.10.10.2"],
        }]

        locations = {"Amsterdam": {"country_code": "NL",
                                   "hemisphere": "N",
                                   "name": "Amsterdam",
                                   "timezone": "+2"},
                     "Seattle": {"country_code": "US",
                                 "hemisphere": "N",
                                 "name": "Seattle",
                                 "timezone": "-7"}}
        openvpn_configuration = {"auth": "SHA512",
                                 "cipher": "AES-256-GCM",
                                 "data-ciphers": "AES-256-GCM",
                                 "dev": "tun",
                                 "float": "",
                                 "keepalive": "10 30",
                                 "key-direction": "1",
                                 "nobind": True,
                                 "persist-key": True,
                                 "rcvbuf": "0",
                                 "sndbuf": "0",
                                 "tls-cipher": "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384",
                                 "tls-version-min": "1.2",
                                 "verb": "3"}

        transports = [{"ports": ["53", "80", "1194"],
                       "protocols": ["tcp", "udp"],
                       "type": "openvpn"},
                      {"ports": ["443"], "protocols": ["tcp"], "type": "obfs4"}]
        config = simplevpn.EIPConfig(
            openvpn_configuration, locations, gateways)

        expected = {
            "gateways": [{"capabilities": {"adblock": False,
                                           "filter_dns": False,
                                           "limited": False,
                                           "transport": [{"ports": ["53", "80", "1194"],
                                                          "protocols": ["tcp", "udp"],
                                                          "type": "openvpn"},
                                                         {"ports": ["443"],
                                                          "protocols": ["tcp"],
                                                          "type": "obfs4"}]},
                          "host": "gateway1.test.com",
                          "ip_address": "10.10.10.1",
                          "location": "Unknown"},
                         {"capabilities": {"adblock": False,
                                           "filter_dns": False,
                                           "limited": False,
                                           "transport": [{"ports": ["53", "80", "1194"],
                                                          "protocols": ["tcp", "udp"],
                                                          "type": "openvpn"},
                                                         {"ports": ["443"],
                                                          "protocols": ["tcp"],
                                                          "type": "obfs4"}]},
                          "host": "gateway2.test.com",
                          "ip_address": "10.10.10.2",
                          "location": "Unknown"}
                         ],
            "locations": {"Amsterdam": {"country_code": "NL",
                                        "hemisphere": "N",
                                        "name": "Amsterdam",
                                        "timezone": "+2"},
                          "Seattle": {"country_code": "US",
                                      "hemisphere": "N",
                                      "name": "Seattle",
                                      "timezone": "-7"}},
            "openvpn_configuration": {"auth": "SHA512",
                                      "cipher": "AES-256-GCM",
                                      "data-ciphers": "AES-256-GCM",
                                      "dev": "tun",
                                      "float": "",
                                      "keepalive": "10 30",
                                      "key-direction": "1",
                                      "nobind": True,
                                      "persist-key": True,
                                      "rcvbuf": "0",
                                      "sndbuf": "0",
                                      "tls-cipher": "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384",
                                      "tls-version-min": "1.2",
                                      "verb": "3"},
            "serial": 3,
            "version": 3
        }

        actual = simplevpn.produce_eip_config(
            config, None, public_domain, transports
        )

        self.assertEqual(expected, actual)


if __name__ == "__main__":

    unittest.main()
