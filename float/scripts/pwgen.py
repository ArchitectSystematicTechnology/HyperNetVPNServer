#!/usr/bin/env python3
# pwgen.py
# Creates and provides passwords to Ansible.
#
# See also ansible sources: lib/ansible/parsing/yaml/constructor.py

from __future__ import print_function

import argparse
import base64
import binascii
import os
import random
import shutil
import six
import subprocess
import string
import sys
import tempfile
import yaml

# six.ensure_str does not seem to be in Debian stretch.
try:
    ensure_str = six.ensure_str
except:
    def ensure_str(x):
        if isinstance(x, unicode):
            return x.encode('utf-8')
        return x


# Possible exit codes for this program.
EXIT_NOTHING_TO_DO = 0
EXIT_CHANGED = 1
EXIT_ERROR = 2


# Returns the absolute path to a file. If the given path is relative,
# it will be evaluated based on the given path_reference.
def _abspath(path, relative_to='/'):
    if path.startswith('/'):
        return path
    return os.path.abspath(os.path.join(os.path.dirname(relative_to), path))


# A version of yaml.safe_load that supports the special 'include'
# top-level attribute and recursively merges included files.
def _read_yaml(path):
    with open(path) as fd:
        data = yaml.safe_load(fd)
    if not isinstance(data, list):
        raise Exception('data in %s is not a list' % (path,))
    # Find elements that include other files.
    out = []
    for entry in data:
        if 'include' in entry:
            out.extend(_read_yaml(_abspath(entry['include'], path)))
        else:
            out.append(entry)
    return out


def decrypt(src):
    return subprocess.check_output(
        ['ansible-vault', 'decrypt', '--output=-', src])


def encrypt(data, dst):
    p = subprocess.Popen(
        ['ansible-vault', 'encrypt', '--output=' + dst, '-'],
        stdin=subprocess.PIPE)
    p.communicate(data.encode())
    rc = p.wait()
    if rc != 0:
        raise Exception('ansible-vault encrypt error')


def generate_simple_password(length=32):
    """Simple password generator.

    The resulting passwords should be alphanumeric, easily
    cut&pastable and usable on the command line.
    """
    n = int(length * 5 / 8)
    return ensure_str(
        base64.b32encode(os.urandom(n)).rstrip('='.encode()))


def generate_binary_secret(length=32):
    """Binary password generator.

    Generates more complex passwords. Unfortunately at the moment the
    result needs to be UTF8-encodable due to Ansible limitations, so
    we can't just grab some random bytes from os.urandom() and we
    base64-encode them instead.

    """
    n = int(length * 3 / 4)
    return ensure_str(
        base64.b64encode(os.urandom(n)).rstrip('='.encode()))


def generate_hex_secret(length=16):
    """Binary password generator (hex-encoded)."""
    return ensure_str(
        binascii.hexlify(os.urandom(int(length/2))))


def _dnssec_keygen():
    """Older bind versions use dnssec-keygen to generate TSIG keys.

    dnssec-keygen outputs the random base name it has chosen for
    its output files. We need to provide a zone name, but it
    doesn't matter what the value is.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        base = subprocess.check_output([
            '/usr/sbin/dnssec-keygen', '-a', 'HMAC-SHA512', '-b', '512',
            '-n', 'USER', '-K', tmp_dir, 'pwgen',
        ]).strip()
        base = base.decode()
        result = {'algo': 'HMAC-SHA512'}
        with open(os.path.join(tmp_dir, base + '.key')) as fd:
            result['public'] = fd.read().split()[7]
        with open(os.path.join(tmp_dir, base + '.private')) as fd:
            for line in fd.readlines():
                if line.startswith('Key: '):
                    result['private'] = line.split()[1]
        return result
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _tsig_keygen():
    """In newer versions, the utility to generate TSIG keys is not
    dnssec-keygen anymore, but tsig-keygen.
    """
    base = subprocess.check_output([
        '/usr/sbin/tsig-keygen', '-a', 'HMAC-SHA512', 'pwgen'
    ]).strip().split()
    result = {'algo': 'HMAC-SHA512'}
    result['private'] = base[6].decode()[1:-2]
    result['public'] = result['private'][-32:]
    return result


def generate_tsig_key():
    """Create TSIG keys to use with Bind version 9.

    The result is a dictionary with the attributes 'algo', 'public'
    and 'private'.

    """
    if os.path.exists("/usr/sbin/tsig-keygen"):
        result = _tsig_keygen()
    else:
        result = _dnssec_keygen()
    if not result.get('public') or not result.get('private'):
        raise Exception('Could not parse dnssec-keygen output')
    return result


def generate_rsa_key(bits):
    """Create a RSA private key of the specified size.

    The result is a PEM-encoded string.
    """
    return ensure_str(
        subprocess.check_output(['openssl', 'genrsa', str(bits)]))


def generate_password(entry):
    ptype = entry.get('type', 'simple')
    if ptype == 'simple':
        return generate_simple_password(length=int(entry.get('length', 32)))
    elif ptype == 'binary':
        return generate_binary_secret(length=int(entry.get('length', 32)))
    elif ptype == 'hex':
        return generate_hex_secret(length=int(entry.get('length', 32)))
    elif ptype == 'tsig':
        return generate_tsig_key()
    elif ptype == 'rsakey':
        return generate_rsa_key(bits=int(entry.get('bits', 2048)))
    else:
        raise Exception('Unknown password type "%s"' % ptype)


def main():
    parser = argparse.ArgumentParser(description='''
Autogenerate secrets for use with Ansible.

Secrets are encrypted with Ansible Vault, so the
ANSIBLE_VAULT_PASSWORD_FILE environment variable must be defined.
''')
    parser.add_argument(
        '--vars', metavar='FILE', dest='vars_file',
        help='Output vars file')
    parser.add_argument(
        'password_file',
        help='Secrets metadata')
    args = parser.parse_args()

    if not os.getenv('ANSIBLE_VAULT_PASSWORD_FILE'):
        raise Exception("You need to set ANSIBLE_VAULT_PASSWORD_FILE")

    passwords = {}

    if os.path.exists(args.vars_file):
        passwords.update(yaml.safe_load(decrypt(args.vars_file)))

    changed = False

    for entry in _read_yaml(args.password_file):
        name = entry['name']
        if name not in passwords:
            print("Generating password for '%s'" % name, file=sys.stderr)
            passwords[name] = generate_password(entry)
            changed = True

    if changed:
        encrypt(yaml.dump(passwords), args.vars_file)
        return EXIT_CHANGED

    return EXIT_NOTHING_TO_DO


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print("Error: %s" % str(e), file=sys.stderr)
        sys.exit(EXIT_ERROR)

