#!/usr/bin/env python
#
# The float.py inventory plugin holds two major purposes: it runs the
# "predictable" scheduling algorithm (that will produce the same
# output for identical configurations), and it generates all the
# Ansible global and host variables that the roles will need.
#
# Its input is the float config.yml file (which points at an Ansible
# inventory in YAML format), see docs/configuration.md in this
# repository for details.
#
# This script is standalone and it is possible to invoke it directly,
# in which case it will simply print a JSON dump of all the generated
# variables, useful for debugging.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import collections
import os
import random
import yaml
from zlib import crc32

from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseFileInventoryPlugin


# Common client credentials that are not attached to a service but will be
# installed on all hosts (i.e. clients for basic infra services).
DEFAULT_SERVICE_CREDENTIALS = [
    {
        'name': 'log-client',
    },
    {
        'name': 'backup-agent',
    },
    {
        'name': 'auth-server',
    },
    {
        'name': 'assetmon-client',
    },
]


class ConfigError(Exception):
    pass


# Convert a string into Python-compatible identifier (suitable for
# Ansible group names).
def _make_identifier(s):
    return s.replace('-', '_')


# Returns the absolute path to a file. If the given path is relative,
# it will be evaluated based on the given path_reference.
def _abspath(path, relative_to='/'):
    if path.startswith('/'):
        return path
    return os.path.abspath(os.path.join(os.path.dirname(relative_to), path))


# Merge two dictionaries, like a.update(b) but applied
# recursively. Only dict values will be merged.
def _merge_dict(a, b):
    for k in b:
        if k in a and isinstance(a[k], dict) and isinstance(b[k], dict):
            _merge_dict(a[k], b[k])
        else:
            a[k] = b[k]
    return a


# Force a YAML value to be a list (in case it's a string).
def _to_list(l):
    if not isinstance(l, list):
        return [l]
    return l


# A version of yaml.safe_load that supports the special 'include'
# top-level attribute and recursively merges included files.
def _read_yaml(path):
    with open(path) as fd:
        data = yaml.safe_load(fd)
    if not data:
        return {}
    if not isinstance(data, dict):
        raise ConfigError('data in %s is not a dictionary' % (path,))
    if 'include' in data:
        # Rebuild the data dictionary by iterative merging.
        base = {}
        for inc in _to_list(data.pop('include')):
            base = _merge_dict(base, _read_yaml(_abspath(inc, relative_to=path)))
        data = _merge_dict(base, data)
    return data


# Read the main configuration file, which points at the other ones as
# well as including some global configuration parameters.
def _read_main_config(path):
    # Default configuration (only useful for tests).
    data = {
        'services_file': 'services.yml',
        'hosts_file': 'hosts.yml',
        'vars_dir': 'group_vars/all',
        'credentials_dir': '.',
    }
    with open(path) as fd:
        data.update(yaml.safe_load(fd))

    # Make all paths in the config absolute paths.
    for k in data:
        if k.endswith('_file') or k.endswith('_dir'):
            data[k] = _abspath(data[k], relative_to=path)

    return data


# Filter a dictionary for members that have the 'enabled' attribute
# not explicitly set to False.
def _filter_enabled(d):
    out = {}
    for k in d:
        v = d[k]
        if v.get('enabled', True):
            out[k] = v
    return out


# Load the configuration and return a dictionary with 'vars',
# 'inventory' and 'services' attributes.
def _load_config(main_config_path):
    config = {}
    config['vars'] = _read_main_config(main_config_path)
    config['services'] = _filter_enabled(
        _read_yaml(config['vars'].pop('services_file')))
    config['inventory'] = _read_yaml(config['vars'].pop('hosts_file'))
    if 'hosts' not in config['inventory']:
        raise ConfigError('no hosts in inventory')
    return config


# Check that the iterable contains unique elements.
def _unique(l):
    l = list(l)
    return len(set(l)) == len(l)


# Verify that invariants in the configuration are not violated.
def _check_config(config):
    # TODO: add meaningful checks like port uniqueness.
    pass


# Return all network overlays that a host is a member of.
def _host_net_overlays(name, inventory):
    return [k[3:] for k in inventory['hosts'][name] if k.startswith('ip_')]


# Return all groups defined for a host.
def _host_groups(name, inventory, assignments=None):
    groups = ['all']
    groups.extend(inventory['hosts'][name].get('groups', []))
    groups.extend(
        ('overlay_' + n) for n in _host_net_overlays(name, inventory))
    if assignments:
        groups.extend(
            _make_identifier(s) for s in assignments.get_by_host(name))
    return groups


# Return all host IP addresses for the specified overlay.
def _host_net_overlay_addrs(name, inventory, overlay):
    if overlay == 'public':
        return inventory['hosts'][name]['public_ips']

    addrs = []
    key = 'ip_' + overlay
    if key in inventory['hosts'][name]:
        addrs.append(inventory['hosts'][name][key])
    return addrs


# Return all host IP addresses, on all interfaces.
def _host_addrs(name, inventory):
    addrs = []
    for ip in inventory['hosts'][name]['ips']:
        addrs.append(ip)
    for k, v in inventory['hosts'][name].items():
        if k.startswith('ip_'):
            addrs.append(v)
    return addrs


def _host_dns_map(name, inventory):
    dns = {}
    dns[name] = inventory['hosts'][name]['ips']
    for k, v in inventory['hosts'][name].items():
        if k.startswith('ip_'):
            dns.setdefault(name + '.' + k[3:], []).append(v)
    return dns


# Return all service-related DNS names for a specific host.
def _host_service_names(name, service_name, inventory, assignments):
    # Use a set for deduplication when hostname == shard_id.
    names = set([
        service_name,
        name + '.' + service_name,
    ])
    if 'shard_id' in inventory['hosts'][name]:
        names.add(inventory['hosts'][name]['shard_id'] + '.' + service_name)
    if assignments.is_master(service_name, name):
        names.add(service_name + '-master')
    return list(names)


# Return host-specific parameters for the X509 service credentials
# associated with a service.
def _service_credential_params(name, service_name, inventory, assignments):
    names = _host_service_names(name, service_name, inventory, assignments)
    names.append('localhost')
    names.append(name)
    addrs = _host_addrs(name, inventory)
    addrs.extend(['127.0.0.1', '::1'])
    return {
        'names': names,
        'addrs': addrs,
    }


# Return the network overlay common to two hosts, or 'public' if none.
def _common_net_overlay(hosta, hostb, inventory):
    a = set(_host_net_overlays(hosta, inventory))
    b = set(_host_net_overlays(hostb, inventory))
    i = a.intersection(b)
    if not i:
        return 'public'
    return sorted(i)[0]


# Build the service discovery DNS map for a service as seen from src_host.
def _service_dns(src_host, service_name, service, inventory, assignments):
    dns = {}
    for hostname in assignments.get_by_service(service_name):
        # Find the overlay in common between source and target host,
        # and use the target IP on that network.
        overlay = _common_net_overlay(src_host, hostname, inventory)
        addrs = _host_net_overlay_addrs(hostname, inventory, overlay)
        for name in _host_service_names(hostname, service_name, inventory, assignments):
            dns.setdefault(name, []).extend(addrs)
    return dns


# Build a fake 'host' service used to point at the common-overlay
# address for each host.
def _hosts_dns(src_host, inventory, assignments):
    dns = {}
    for hostname in inventory['hosts']:
        overlay = _common_net_overlay(src_host, hostname, inventory)
        addrs = _host_net_overlay_addrs(hostname, inventory, overlay)
        dns[hostname + '.host'] = addrs
    return dns


# Build the full service discovery DNS map for host 'name'.
def _host_service_dns_map(name, inventory, services, assignments):
    dns = {}
    for s in assignments.all_services():
        dns.update(_service_dns(name, s, services[s], inventory, assignments))
    dns.update(_hosts_dns(name, inventory, assignments))
    return dns


def _global_dns_map(inventory):
    dns = {}
    for h in inventory['hosts']:
        dns.update(_host_dns_map(h, inventory))
    return dns


# Build a group -> hosts map out of an inventory.
def _build_group_map(inventory, assignments=None):
    group_map = {}
    for h in inventory['hosts']:
        for g in _host_groups(h, inventory, assignments):
            group_map.setdefault(g, []).append(h)
    # Sort all values for consistent output of Ansible loops.
    return dict((k, sorted(v)) for k, v in group_map.items())


# Build the map of public_endpoints and their paths. The result is a
# high-level view of the NGINX configuration, split into a list of
# upstreams, and a list of servers with location -> upstream maps.
#
# This can be computed just from the services dictionary, but this is
# logic we rather didn't have in Jinja templates.
#
# We're only doing this for the HTTP endpoints, as the other types
# (tcp, other) do not have a nested path structure to worry about.
#
# Modifies the service.public_endpoints objects in-place by adding the
# 'float_upstream_name' attribute, referring to the associated
# upstream object.
def _build_public_endpoints_map(services):
    upstreams = {}
    endpoints = {}
    # Since iteration is random, we might encounter a public_endpoint
    # with a subpath before the root (so before the entry in
    # 'endpoints' is created. So we maintain a separate path map.
    path_map = {}
    for service_name, svc in services.items():
        for pe in svc.get('public_endpoints', []):
            # The upstream name combines endpoint name and service to
            # obtain a unique identifier.
            name = pe['name']
            upstream_name = 'be_%s_%s_%s' % (name, pe['port'], service_name)
            upstreams[upstream_name] = {
                'name': upstream_name,
                'service_name': service_name,
                'port': pe['port'],
                'enable_sso_proxy': pe.get('enable_sso_proxy', False),
                'sharded': pe.get('sharded', False),
            }
            pe['float_upstream_name'] = upstream_name
            # Always /-terminate paths, ensure they are set on the
            # public_endpoint object.
            path = pe.get('path', '/').rstrip('/') + '/'
            pe['path'] = path
            if path == '/':
                if name in endpoints:
                    raise Exception(
                        'Multiple definitions for / in public_endpoint %s' % name)
                path_map.setdefault(name, {})['/'] = pe
                endpoints[name] = {
                    'name': name,
                    'sharded': pe.get('sharded', False),
                    'domains': pe.get('domains', []),
                    'autoconfig': pe.get('autoconfig', True),
                    'extra_nginx_config': pe.get('extra_nginx_config'),
                    'float_path_map': path_map[name],
                }
            else:
                if name in path_map and path in path_map[name]:
                    raise Exception(
                        'Multiple definitions for %s in public_endpoint %s' % (
                            path, name))
                path_map.setdefault(name, {})[path] = pe
    return upstreams, endpoints


def _build_public_endpoint_port_map(services):
    endpoints_by_port = {}
    for svc in services.values():
        for pe in svc.get('public_endpoints', []):
            endpoints_by_port[pe['port']] = pe['name']
    return endpoints_by_port


# Build the map of upstreams for 'horizontal' (well-known etc) HTTP
# public endpoints.
#
# Modifies the service.horizontal_endpoints objects in-place by adding
# the 'float_upstream_name' attribute, referring to the associated
# upstream object.
def _build_horizontal_upstreams_map(services):
    upstreams = {}
    for service_name, svc in services.items():
        for ep in svc.get('horizontal_endpoints', []):
            upstream_name = 'be_%s_%s_%s' % (ep['name'], ep['port'], service_name)
            upstreams[upstream_name] = {
                'name': upstream_name,
                'service_name': service_name,
                'port': ep['port'],
                'enable_sso_proxy': False,
                'sharded': False,
            }
            ep['float_upstream_name'] = upstream_name
    return upstreams


# Return autogenerated host-specific variables.
def _host_vars(name, inventory, services, assignments):
    # Set enabled/disabled services for each host, and explode the
    # service credentials for assigned services so that it is easier
    # to iterate on them in the 'credentials' Ansible role.
    hv = {
        'float_enabled_services': [],
        'float_disabled_services': [],
        'float_enabled_containers': [],
        'float_host_service_credentials': [],
        'float_host_overlay_networks': _host_net_overlays(name, inventory),
        'float_host_dns_map': _host_service_dns_map(
            name, inventory, services, assignments),
    }

    # Add default client credentials that are present on all hosts.
    for c in DEFAULT_SERVICE_CREDENTIALS:
        hv['float_host_service_credentials'].append({
            'credentials': c, 'service': 'LOCAL',
            'mode': 'client', 'x509_params': {}})

    # There isn't necessarily a 1:1 mapping between services and
    # systemd units (in some corner cases of hard separation between
    # roles, for instance), so we need to compute the set difference.
    enabled_systemd_units, disabled_systemd_units = set(), set()

    for s in assignments.all_services():
        service_name_var = s.replace('-', '_')
        service_enabled_var = 'float_enable_' + service_name_var
        idx = assignments.find(s, name)
        hv[service_enabled_var] = (idx >= 0)
        if idx >= 0:
            hv['float_instance_index_' + service_name_var] = idx
            hv['float_enabled_services'].append(s)
            for c in services[s].get('containers', []):
                hv['float_enabled_containers'].append(
                    _denormalize_container(s, c))
            for u in services[s].get('systemd_services', []):
                enabled_systemd_units.add(u)
            for c in services[s].get('service_credentials', []):
                if c.get('enable_server', True):
                    params = _service_credential_params(name, s, inventory, assignments)
                    hv['float_host_service_credentials'].append({
                        'credentials': c, 'service': s,
                        'mode': 'server', 'x509_params': params})
                if c.get('enable_client', True):
                    hv['float_host_service_credentials'].append({
                        'credentials': c, 'service': s,
                        'mode': 'client', 'x509_params': {}})
        else:
            hv['float_disabled_services'].append(s)
            for u in services[s].get('systemd_services', []):
                disabled_systemd_units.add(u)

        if services[s].get('master_election'):
            is_master_var = 'float_%s_is_master' % (service_name_var,)
            hv[is_master_var] = assignments.is_master(s, name)

    hv['float_disabled_systemd_units'] = list(
        disabled_systemd_units.difference(enabled_systemd_units))

    return hv


# Return an object that binds together service and container, to
# simplify iteration logic in Ansible templates.
def _denormalize_container(service_name, container):
    return {
        'service': service_name,
        'tag': '%s-%s' % (service_name, container['name']),
        'container': container,
    }


def _service_systemd_units(name, service):
    return [
        'docker-%s-%s.service' % (name, container['name'])
        for container in service.get('containers', [])]


class Assignments(object):
    """Runtime service/host assignment map."""

    def __init__(self, service_hosts_map, service_master_map):
        self._all_services = service_hosts_map.keys()
        self._fwd = service_hosts_map
        self._rev = {}
        for s, hosts in service_hosts_map.items():
            for h in hosts:
                self._rev.setdefault(h, []).append(s)
        self._masters = service_master_map

    def find(self, service, host):
        try:
            return self._fwd.get(service, []).index(host)
        except ValueError:
            return -1

    def is_master(self, service, host):
        return self._masters.get(service) == host

    def get_master(self, service):
        return self._masters.get(service)

    def get_by_host(self, host):
        return self._rev.get(host, [])

    def get_by_service(self, service):
        return self._fwd.get(service, [])

    def all_services(self):
        return self._all_services

    def __str__(self):
        return str(self._fwd)

    @classmethod
    def _available_hosts(cls, service, group_map, service_hosts_map):
        if 'schedule_with' in service:
            return service_hosts_map[service['schedule_with']]
        scheduling_groups = ['all']
        if 'scheduling_group' in service:
            scheduling_groups = [service['scheduling_group']]
        elif 'scheduling_groups' in service:
            scheduling_groups = service['scheduling_groups']
        available_hosts = set()
        for g in scheduling_groups:
            if g not in group_map:
                raise Exception(f'The scheduling_group "{g}" is not defined in inventoy')
            available_hosts.update(group_map[g])
        return list(available_hosts)

    @classmethod
    def schedule(cls, services, inventory):
        """Schedule services on the given host inventory.

        Creates service assignments, with a reproducible (non-random)
        algorithm so that every invocation with the same configuration
        produces the same result.

        """
        service_hosts_map = {}
        service_master_map = {}
        group_map = _build_group_map(inventory)
        host_occupation = collections.defaultdict(int)

        # Iterations should happen over sorted items for reproducible
        # results. The sort function combines the 'scheduling_order'
        # attribute (default -1), the presence of the 'schedule_with'
        # attribute, and the service name.
        def _sort_key(service_name):
            return (services[service_name].get('scheduling_order', -1),
                    1 if 'schedule_with' in services[service_name] else 0,
                    service_name)

        for service_name in sorted(services.keys(), key=_sort_key):
            service = services[service_name]
            available_hosts = cls._available_hosts(service, group_map,
                                                   service_hosts_map)
            num_instances = service.get('num_instances', 'all')
            if num_instances == 'all':
                service_hosts = sorted(available_hosts)
            else:
                service_hosts = sorted(_binpack(
                    available_hosts, host_occupation, num_instances))
            service_hosts_map[service_name] = service_hosts
            for h in service_hosts:
                host_occupation[h] += 1
            if service.get('master_election'):
                if 'master_scheduling_group' in service:
                    available_hosts = set(available_hosts).intersection(
                            set(group_map[service['master_scheduling_group']]))
                if not available_hosts:
                    raise Exception(
                        'Could not run master election for service %s: '
                        'no overlap between available hosts and master_scheduling_group' % (
                            service_name,))
                service_master_map[service_name] =  _master_election(available_hosts)
        return cls(service_hosts_map, service_master_map)


# Return True if any of the services have the 'attr' attribute set.
def _any_attribute_set(services, attr):
    for x in services.values():
        if attr in x:
            return True
    return False


# Pre-process inventory entries, to normalize host variables and
# provide defaults (thus simplifying the jinja template logic).
def _preprocess_inventory(inventory):
    for host in inventory['hosts'].values():
        # Set 'ips' if the legacy variables are set.
        if 'ips' not in host:
            host['ips'] = []
            if 'ip' in host:
                host['ips'].append(host['ip'])
            if 'ip6' in host:
                host['ips'].append(host['ip6'])
        # Same for 'public_ips'.
        if 'public_ips' not in host:
            host['public_ips'] = []
            if 'public_ip' in host:
                host['public_ips'].append(host['public_ip'])
            if 'public_ip6' in host:
                host['public_ips'].append(host['public_ip6'])
        # Default public_ips to ips.
        if not host['public_ips']:
            host['public_ips'] = host['ips']


# Run the scheduler, and return inventory and groups for Ansible.
def run_scheduler(config):
    services = config['services']
    inventory = config['inventory']
    _preprocess_inventory(inventory)
    assignments = Assignments.schedule(services, inventory)

    # Augment all data structures with autogenerated and
    # schedule-related information before feeding them to Ansible.
    for service_name, service in services.items():
        service['name'] = service_name
        service['group_name'] = _make_identifier(service_name)
        service['user'] = f'docker-{service_name}'
        service['hosts'] = assignments.get_by_service(service_name)
        if service.get('master_election'):
            service['master_host'] = assignments.get_master(service_name)
        service.setdefault('systemd_services', []).extend(
            _service_systemd_units(service_name, service))

    for hostname, hostvars in inventory['hosts'].items():
        hostvars.update(_host_vars(
            hostname, inventory, services, assignments))

    # Merge everything into the 'all' group_vars.
    all_vars = inventory.setdefault('group_vars', {}).setdefault('all', {})
    all_vars.update(config['vars'])
    all_vars.update({
        'float_plugin_loaded': True,
        'services': services,
        'float_global_dns_map': _global_dns_map(inventory),
        # The following variables are just used for debugging purposes (dashboards).
        'float_service_assignments': assignments._fwd,
        'float_service_masters': assignments._masters,
        'float_http_endpoints_by_port': _build_public_endpoint_port_map(services),
    })

    # Set the HTTP frontend configuration on the 'frontend' group.
    http_upstreams, http_endpoints = _build_public_endpoints_map(services)
    inventory['group_vars'].setdefault('frontend', {}).update({
        'float_enable_http_frontend': _any_attribute_set(
            services, 'public_endpoints'),
        'float_http_upstreams': http_upstreams,
        'float_http_endpoints': http_endpoints,
    })
    # Merge the upstream map for horizontal endpoints.
    http_upstreams.update(_build_horizontal_upstreams_map(services))

    # Create the group->hosts map that Ansible needs. Create a dynamic
    # net-overlay group with hosts that use network overlays.
    groups = _build_group_map(inventory, assignments)
    groups['net_overlay'] = [
        h for h in inventory['hosts']
        if _host_net_overlays(h, inventory)]

    return inventory, groups


def _predictable_random(args):
    """Returns a predictable RNG based on the given args.

    The sequence of generated numbers will be the same every
    invocation, as long as the arguments are identical.
    """
    # Uses crc32(x) as seed.
    return random.Random(crc32(','.join(args).encode()))


# Randomly pick n among the least-occupied hosts.
def _binpack(hosts, occupation_map, n):
    # Deal with edge cases first.
    if n > len(hosts):
        raise Exception('Can\'t schedule %d instances on %d hosts' % (
            n, len(hosts)))
    if n == len(hosts):
        return hosts

    # Always sort the host list.
    hosts = sorted(hosts)
    rnd = _predictable_random(hosts)
    result = []

    # Iterate over the occupation map in groups of hosts with equal,
    # increasing occupation levels, so that the emptiest hosts come
    # first. Stop the iteration when we have n hosts.
    reverse_occupation_map = {}
    for h in hosts:
        reverse_occupation_map.setdefault(occupation_map[h], []).append(h)
    for v in sorted(reverse_occupation_map.keys()):
        # The shuffle is necessary so we pick random elements if there
        # are more hosts at the current occupation level than we need.
        tmp_hosts = reverse_occupation_map[v]
        py2_shuffle(rnd, tmp_hosts)
        result.extend(tmp_hosts)
        if len(result) >= n:
            return result[:n]
    return result


# Predictably select a host among the given list, based on the
# contents of the list itself.
def _master_election(hosts):
    hosts = sorted(hosts)
    rnd = _predictable_random(hosts)
    return py2_choice(rnd, hosts)


# Entry point for the Ansible inventory plugin.
class InventoryModule(BaseFileInventoryPlugin):

    NAME = 'float'

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache=cache)

        try:
            cfg = _load_config(path)
            _check_config(cfg)
        except ConfigError as e:
            raise AnsibleParserError(str(e))

        float_inventory, groups = run_scheduler(cfg)
        self.to_ansible(inventory, float_inventory, groups)

    # Apply our configuration to the Ansible inventory.
    def to_ansible(self, ansible_inventory, inventory, groups):
        for hostname, hostvars in inventory['hosts'].items():
            ansible_inventory.add_host(hostname)
            for k, v in hostvars.items():
                ansible_inventory.set_variable(hostname, k, v)
        for group_name, hosts in groups.items():
            ansible_inventory.add_group(group_name)
            for hostname in hosts:
                ansible_inventory.add_child(group_name, hostname)
            for k, v in inventory['group_vars'].get(group_name, {}).items():
                ansible_inventory.set_variable(group_name, k, v)


# The 'random' module got a major rewrite between Python 2 and Python
# 3, and the 'choice' and 'shuffle' methods return incompatible
# results. Stick with the obsolete Python 2 version until we have
# migrated all clients, otherwise scheduling results won't be
# reproducible between versions.
def py2_choice(rnd, seq):
    return seq[int(rnd.random() * len(seq))]


def py2_shuffle(rnd, seq):
    for i in reversed(range(1, len(seq))):
        # pick an element in x[:i+1] with which to exchange x[i]
        j = int(rnd.random() * (i+1))
        seq[i], seq[j] = seq[j], seq[i]


if __name__ == '__main__':
    import json
    import sys
    cfg = _load_config(sys.argv[1])
    _check_config(cfg)
    inv, g = run_scheduler(cfg)
    print(json.dumps(inv, indent=4))
