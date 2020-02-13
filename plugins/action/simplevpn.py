import os
import yaml
from ansible.plugins.action import ActionBase


class EIPConfig:

    def __init__(self, openvpn, locations, gateways, provider):
        self.openvpn = openvpn
        self.locations = locations
        self.gateways = gateways
        self.provider = provider


# def parseConfig(provider_config):
#     with open(provider_config) as conf:
#         config = yaml.load(conf.read())
#     eip = EIPConfig()
#     eip.openvpn.update(yamlListToDict(config['openvpn']))

#     for loc in config['locations']:
#         eip.locations.update(yamlIdListToDict(loc))
#     for gw in config['gateways']:
#         eip.gateways.update(yamlIdListToDict(gw))
#     eip.provider.update(yamlListToDict(config['provider']))
#     return eip


# def yamlListToDict(values):
#     vals = {}
#     for d in values:
#         for k, v in d.items():
#             vals[k] = v
#     return vals


# def yamlIdListToDict(data):
#     _d = {}
#     for identifier, values in data.items():
#         _d[identifier] = yamlListToDict(values)
#     return _d


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
        "gateways": dict((k, {
            "host": "%s.%s" % (v["inventory_hostname"], public_domain),
            "ip_address": v["ip"],
            "location": v.get("location", "Unknown"),
            "capabilities": {
                "adblock": False,
                "filter_dns": False,
                "limited": False,
                "transport": transports,
            },
        }) for k, v in config.gateways),
        "openvpn_configuration": config.openvpn,
    }
        
    # Instead of calling the template here, we just return the
    # 'config' object so that Ansible can use it with its own template
    # module.
    return eip_config


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        # Get task arguments.
        public_domain = self._task.args['domain']
        openvpn = self._task.args['openvpn']
        locations = self._task.args['locations']
        gateways = self._task.args['gateways']
        provider = self._task.args['provider']
        obfs4_state_dir = self._task.args.get('obfs4_state_dir')
        transports = self._task.args.get('transports', [
            ["openvpn", "tcp", "443", {}],
            ["obfs4", "tcp", "23042", {}],
        ])

        config = EIPConfig(openvpn, locations, gateways, provider)
        config = produceEipConfig(config, obfs4_state_dir, public_domain, transports)

        result = super(ActionModule, self).run(tmp, task_vars)
        result.update({
            'changed': False,   # Always nice to return 'changed'.
            'eip_config': eip_config, # Actual result.
        })

        return result
