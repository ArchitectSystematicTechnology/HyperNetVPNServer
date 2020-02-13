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


def patchObfs4Cert(config, cert):
    for gw in config.gateways:
        for options in config.gateways[gw]['transports']:
            opts = {}
            transport, _, _ = options
            if transport == "obfs4":
                opts['cert'] = cert
                opts['iatMode'] = "0"
            options.append(opts)
    return config


def produceEipConfig(config, obfs4_state_dir):
    if obfs4_state_dir:
        obfs4_cert = open(
            obfs4_state_dir + '/obfs4_cert.txt').read().rstrip()
        config = patchObfs4Cert(config, obfs4_cert)

    # Instead of calling the template here, we just return the
    # 'config' object so that Ansible can use it with its own template
    # module.
    return config


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        # Get task arguments.
        openvpn = self._task.args['openvpn']
        locations = self._task.args['locations']
        gateways = self._task.args['gateways']
        provider = self._task.args['provider']
        obfs4_state_dir = self._task.args.get('obfs4_state_dir')

        config = EIPConfig(openvpn, locations, gateways, provider)
        config = produceEipConfig(config, obfs4_state_dir)

        result = super(ActionModule, self).run(tmp, task_vars)
        result.update({
            'changed': False,   # Always nice to return 'changed'.
            'simplevpn_config': config, # Actual result.
        })

        return result
