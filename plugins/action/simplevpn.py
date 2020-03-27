import hashlib
import os
import yaml
import tempfile
from OpenSSL import crypto
from ansible.plugins.action import ActionBase


def get_fingerprint(cert_data):
    cert_contents = open(cert_data).read()
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_contents)
    return cert.digest('sha256').replace(b':', b'').lower().decode('ascii')

class EIPConfig:

    def __init__(self, openvpn, locations, gateways):
        self.openvpn = openvpn
        self.locations = locations
        self.gateways = gateways

def patchObfs4Cert(transports, cert):
    # Build a new list since we can't modify tuples in place.
    out = []
    for tr, proto, port, options in transports:
        if tr == "obfs4":
            options['cert'] = cert
            options['iatMode'] = "0"
        out.append((tr, proto, port, options))
    return out


def produceEipConfig(config, obfs4_state_dir, public_domain, transports):
    if obfs4_state_dir:
        obfs4_cert = open(
            obfs4_state_dir + '/obfs4_cert.txt').read().rstrip()
        transports = patchObfs4Cert(transports, obfs4_cert)

    # Build the JSON data structure that needs to end up in eip-service.json.
    eip_config = {
        "serial": 3,
        "version": 3,
        "locations": config.locations,
        "gateways": dict((x["host"], x) for x in [
            {
                "host": "%s.%s" % (v["inventory_hostname"], public_domain),
                "ip_address": v["ip"],
                "location": v.get("location", "Unknown"),
                "capabilities": {
                    "adblock": False,
                    "filter_dns": False,
                    "limited": False,
                    "transport": transports,
                },
            } for v in config.gateways]),
        "openvpn_configuration": config.openvpn,
    }
        
    # Instead of calling the template here, we just return the
    # 'config' object so that Ansible can use it with its own template
    # module.
    return eip_config


def produceProviderConfig(public_domain, provider_api_uri, ca_cert_uri, ca_public_crt):
    ca_fp = get_fingerprint(ca_public_crt)

    # Build the JSON data structure that needs to end up in provider.json.
    provider_config = {
        "api_url": provider_api_uri,
        "api_version": "3",
        "ca_cert_fingerprint": "SHA256: " + ca_fp,
        "ca_cert_uri": ca_cert_uri,
        "default_language": "en",
        "description": {
            "en": "LEAP Provider"
        },
        "domain": "%s" % (public_domain),
        "enrollment_policy": "open",
        "languages": [
            "en"
        ],
        "name": {
            "en": "LEAP Provider"
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
    return provider_config

class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        # Get EIP config task arguments.
        obfs4_state_dir = self._task.args.get('obfs4_state_dir')
        locations = self._task.args['locations']
        public_domain = self._task.args['domain']
        transports = self._task.args.get('transports', [
            ["openvpn", "tcp", "443", {}],
            ["obfs4", "tcp", "23042", {}],
        ])
        gateways = self._task.args['gateways']
        openvpn = self._task.args['openvpn']

        # Get provider config task elements
        provider_api_uri = self._task.args['provider_api_uri']
        ca_cert_uri = self._task.args['ca_cert_uri']
        ca_public_crt = self._task.args['ca_public_crt']

        config = EIPConfig(openvpn, locations, gateways)
        eip_config = produceEipConfig(config, obfs4_state_dir, public_domain, transports)
        provider_config = produceProviderConfig(public_domain, provider_api_uri, ca_cert_uri, ca_public_crt)

        result = super(ActionModule, self).run(tmp, task_vars)
        result.update({
            'changed': False,   # Always nice to return 'changed'.
            'eip_config': eip_config, # Actual result.
            'provider_config': provider_config, # Actual result.
        })

        return result
