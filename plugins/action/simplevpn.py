import hashlib
import os
import yaml
import tempfile
from OpenSSL import crypto
from ipaddress import ip_address, IPv4Address, IPv6Address
from ansible.plugins.action import ActionBase

def ipv4(str):
  try:
    return type(ip_address(str)) == IPv4Address
  except ValueError:
    return False

def ipv6(str):
  try:
    return type(ip_address(str)) == IPv6Address
  except ValueError:
    return False

def first_ipv4(list):
  try:
    return [i for i in list if ipv4(i)][0]
  except IndexError:
    return None

def first_ipv6(list):
  try:
    return [i for i in list if ipv6(i)][0]
  except IndexError:
    return None

def get_fingerprint(cert_data):
    cert_contents = open(cert_data).read()
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_contents)
    return cert.digest('sha256').replace(b':', b'').lower().decode('ascii')

class EIPConfig:

    def __init__(self, openvpn, locations, gateways):
        self.openvpn = openvpn
        self.locations = locations
        self.gateways = gateways

def patch_obfs4_cert(transports, cert):
    for t in transports:
        if t['type'] == "obfs4":
            t.setdefault('options', {})
            t['options']['cert'] = cert
            t['options']['iatMode'] = "0"
    return transports


def no_nulls(d):
    if isinstance(d, dict):
        return dict(
            (k, no_nulls(v))
            for k, v in d.items() if v is not None)
    elif isinstance(d, list):
        return [no_nulls(x) for x in d if x]
    else:
        return d


def produce_eip_config(config, obfs4_state_dir, public_domain, transports):
    if obfs4_state_dir:
        obfs4_cert = open(
            obfs4_state_dir + '/obfs4_cert.txt').read().rstrip()
        transports = patch_obfs4_cert(transports, obfs4_cert)

    # Build the JSON data structure that needs to end up in eip-service.json.
    eip_config = {
        "serial": 3,
        "version": 3,
        "locations": config.locations,
        "gateways": [{
            "host": "%s.%s" % (v["inventory_hostname"], public_domain),
            "ip_address": first_ipv4(v.get("ips")),
            "ip_address6": first_ipv6(v.get("ips")),
            "location": v.get("location", "Unknown"),
            "bucket": v.get("bucket", ""),
            "capabilities": {
                "adblock": False,
                "filter_dns": False,
                "limited": False,
                "transport": transports,
            },
        } for v in config.gateways],
        "openvpn_configuration": config.openvpn,
    }

    # Instead of calling the template here, we just return the
    # 'config' object so that Ansible can use it with its own template
    # module.
    return no_nulls(eip_config)


def produce_provider_config(public_domain, provider_description, provider_api_uri, ca_cert_uri, ca_public_crt):
    ca_fp = get_fingerprint(ca_public_crt)

    # Build the JSON data structure that needs to end up in provider.json.
    provider_config = {
        "api_uri": provider_api_uri,
        "api_version": "3",
        "ca_cert_fingerprint": "SHA256: " + ca_fp,
        "ca_cert_uri": ca_cert_uri,
        "default_language": "en",
        "description": {
            "en": provider_description
        },
        "domain": "%s" % (public_domain),
        "enrollment_policy": "open",
        "languages": [
            "en"
        ],
        "name": {
            "en": provider_description
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
                    "name": "free"
                }
            },
        },
        "services": [
            "openvpn"
        ]
    }

    # Instead of calling the template here, we just return the
    # 'config' object so that Ansible can use it with its own template
    # module.
    return no_nulls(provider_config)

class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        # Get EIP config task arguments.
        obfs4_state_dir = self._task.args.get('obfs4_state_dir')
        locations = self._task.args['locations']
        public_domain = self._task.args['domain']
        provider_description = self._task.args['provider_description']
        transports = self._task.args.get('transports', [
            dict(type="openvpn", protocols=["tcp", "udp"], ports=["53","80", "1194"]),
            dict(type="obfs4", protocols=["tcp"], ports=["443"]),
            dict(type="obfs4", protocols=["kcp"], ports=["4431"]),
        ])
        gateways = self._task.args['gateways']
        openvpn = self._task.args['openvpn']

        # Get provider config task elements
        provider_api_uri = self._task.args['provider_api_uri']
        ca_cert_uri = self._task.args['ca_cert_uri']
        ca_public_crt = self._task.args['ca_public_crt']

        config = EIPConfig(openvpn, locations, gateways)
        eip_config = produce_eip_config(config, obfs4_state_dir, public_domain, transports)
        provider_config = produce_provider_config(public_domain, provider_description, provider_api_uri, ca_cert_uri, ca_public_crt)

        result = super(ActionModule, self).run(tmp, task_vars)
        result.update({
            'changed': False,   # Always nice to return 'changed'.
            'eip_config': eip_config, # Actual result.
            'provider_config': provider_config, # Actual result.
        })

        return result
