#!/usr/bin/env python
#
# Check if a port is available, and also check that the configuration
# is free of port conflicts (i.e. more than one service claims the
# specified port).
#

from __future__ import print_function

import os, sys
sys.path.append(
    os.path.join(
        os.path.dirname(__file__),
        '../plugins/inventory'))

import six
import float as float_plugin


if __name__ == '__main__':
    import json, sys
    if len(sys.argv) < 2:
        print('Usage: port-check.py <config> [<port>]')
        sys.exit(2)

    cfg = float_plugin._load_config(sys.argv[1])
    float_plugin._check_config(cfg)
    services = cfg['services']

    used_ports = set()
    port_map = {}
    def _record(port, name):
        used_ports.add(port)
        port_map.setdefault(port, set()).add(name)

    for name, svc in six.iteritems(services):
        for port in svc.get('ports', []):
            _record(port, name)
        for container in svc.get('containers', []):
            if 'port' in container:
                _record(container['port'], name)
            for port in container.get('ports', []):
                _record(port, name)
        for pe in svc.get('public_endpoints', []):
            _record(pe['port'], name)

    if len(sys.argv) == 2:
        # Find ports with > 1 service
        conflicts = [
            (k, v) for k, v in six.iteritems(port_map)  if len(v) > 1]

        if conflicts:
            print('Warning: there are port conflicts:')
            for port, services in conflicts:
                print('port %d: services=%s' % (port, ', '.join(services)))

    else:
        port = int(sys.argv[2])
        if port in used_ports:
            print('port %d is NOT available (service=%s)' % (
                port, ', '.join(port_map[port])))
        else:
            print('port %d is available' % port)
