#!/usr/bin/env python3
#
# Read a hosts.yml float inventory, and manage a VM group derived by it.
# This tool is meant to replace "vagrant up" in a CI pipeline.
#

import argparse
import json
import os
import re
import shlex
import subprocess
import yaml


# The Vagrant "insecure" SSH key that is used to log onto the VMs.
INSECURE_PRIVATE_KEY = '''-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzI
w+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoP
kcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2
hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NO
Td0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcW
yLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQIBIwKCAQEA4iqWPJXtzZA68mKd
ELs4jJsdyky+ewdZeNds5tjcnHU5zUYE25K+ffJED9qUWICcLZDc81TGWjHyAqD1
Bw7XpgUwFgeUJwUlzQurAv+/ySnxiwuaGJfhFM1CaQHzfXphgVml+fZUvnJUTvzf
TK2Lg6EdbUE9TarUlBf/xPfuEhMSlIE5keb/Zz3/LUlRg8yDqz5w+QWVJ4utnKnK
iqwZN0mwpwU7YSyJhlT4YV1F3n4YjLswM5wJs2oqm0jssQu/BT0tyEXNDYBLEF4A
sClaWuSJ2kjq7KhrrYXzagqhnSei9ODYFShJu8UWVec3Ihb5ZXlzO6vdNQ1J9Xsf
4m+2ywKBgQD6qFxx/Rv9CNN96l/4rb14HKirC2o/orApiHmHDsURs5rUKDx0f9iP
cXN7S1uePXuJRK/5hsubaOCx3Owd2u9gD6Oq0CsMkE4CUSiJcYrMANtx54cGH7Rk
EjFZxK8xAv1ldELEyxrFqkbE4BKd8QOt414qjvTGyAK+OLD3M2QdCQKBgQDtx8pN
CAxR7yhHbIWT1AH66+XWN8bXq7l3RO/ukeaci98JfkbkxURZhtxV/HHuvUhnPLdX
3TwygPBYZFNo4pzVEhzWoTtnEtrFueKxyc3+LjZpuo+mBlQ6ORtfgkr9gBVphXZG
YEzkCD3lVdl8L4cw9BVpKrJCs1c5taGjDgdInQKBgHm/fVvv96bJxc9x1tffXAcj
3OVdUN0UgXNCSaf/3A/phbeBQe9xS+3mpc4r6qvx+iy69mNBeNZ0xOitIjpjBo2+
dBEjSBwLk5q5tJqHmy/jKMJL4n9ROlx93XS+njxgibTvU6Fp9w+NOFD/HvxB3Tcz
6+jJF85D5BNAG3DBMKBjAoGBAOAxZvgsKN+JuENXsST7F89Tck2iTcQIT8g5rwWC
P9Vt74yboe2kDT531w8+egz7nAmRBKNM751U/95P9t88EDacDI/Z2OwnuFQHCPDF
llYOUI+SpLJ6/vURRbHSnnn8a/XG+nzedGH5JGqEJNQsz+xT2axM0/W/CRknmGaJ
kda/AoGANWrLCz708y7VYgAtW2Uf1DPOIYMdvo6fxIB5i9ZfISgcJ/bbCUkFrhoH
+vq/5CIWxCPp0f85R4qxxQ5ihxJ0YDQT9Jpx4TMss4PSavPaBH3RXow5Ohe+bYoQ
NE5OgEXk2wVfZczCZpigBKbKZHNYcelXtTt/nP3rsCuGcM4h53s=
-----END RSA PRIVATE KEY-----
'''


def parse_inventory(path, host_attrs):
    with open(path) as fd:
        inventory = yaml.safe_load(fd)

    hosts = [{'ip': v['ansible_host'], 'name': k}
             for k, v in inventory['hosts'].items()]
    for h in hosts:
        h.update(host_attrs)

    # We know that the network is a /24.
    net = re.sub(r'\.[0-9]+$', '.0/24', hosts[0]['ip'])
    return {
        'network': net,
        'hosts': hosts,
    }


def do_request(url, ssh_gw, payload):
    data = json.dumps(payload)
    cmd = "curl -s -X POST -H 'Content-Type: application/json' -d %s %s" % (
        shlex.quote(data), url)
    if ssh_gw:
        cmd = "ssh %s %s" % (ssh_gw, shlex.quote(cmd))

    output = subprocess.check_output(cmd, shell=True)
    try:
        return json.loads(output)
    except json.decoder.JSONDecodeError:
        print(f'server error: {output}')
        raise


def install_ssh_key():
    # Install the SSH key as Vagrant would do, for compatibility.
    key_path = os.path.join(
        os.getenv('HOME'), '.vagrant.d', 'insecure_private_key')
    if os.path.exists(key_path):
        return
    os.makedirs(os.path.dirname(key_path), mode=0o700, exist_ok=True)
    with open(key_path, 'w') as fd:
        fd.write(INSECURE_PRIVATE_KEY)
    os.chmod(key_path, 0o600)


def main():
    ci_job_id = os.getenv('CI_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--url', metavar='URL', default='http://127.0.0.1:4949',
        help='URL of the vmine API server')
    parser.add_argument(
        '--ssh', metavar='USER@HOST',
        help='proxy the vmine API request through SSH')
    parser.add_argument(
        '--state-file', metavar='FILE',
        default=f'.vmine_group-{ci_job_id}' if ci_job_id else '.vmine_group',
        help='state file to store the vmine group ID')
    parser.add_argument(
        '--inventory', metavar='FILE', default='hosts.yml',
        help='float host inventory')
    parser.add_argument(
        '--image', metavar='NAME',
        help='base image to use for the VMs')
    parser.add_argument(
        '--ram', type=int,
        help='memory reservation for the VMs')
    parser.add_argument(
        '--ttl', metavar='DURATION', default='1h',
        help='TTL for the virtual machines')
    parser.add_argument(
        'cmd',
        choices=['up', 'down'])
    args = parser.parse_args()

    if args.cmd == 'up':
        host_attrs = {}
        if args.ram:
            host_attrs['ram'] = args.ram
        if args.image:
            host_attrs['image'] = args.image
        req = parse_inventory(args.inventory, host_attrs)
        req['ttl'] = args.ttl

        print('creating VM group...')
        resp = do_request(args.url + '/api/create-group', args.ssh, req)
        group_id = resp['group_id']
        with open(args.state_file, 'w') as fd:
            fd.write(group_id)
        print(f'created VM group {group_id}')

        install_ssh_key()

    elif args.cmd == 'down':
        try:
            with open(args.state_file) as fd:
                group_id = fd.read().strip()
        except FileNotFoundError:
            print('state file not found, exiting')
            return
        print(f'stopping VM group {group_id}...')
        do_request(args.url + '/api/stop-group', args.ssh,
                   {'group_id': group_id})
        os.remove(args.state_file)


if __name__ == '__main__':
    main()
