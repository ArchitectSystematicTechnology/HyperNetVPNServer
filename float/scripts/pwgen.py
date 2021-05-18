#!/usr/bin/env python3
# pwgen.py
# Creates and provides passwords to Ansible.
#
# See also ansible sources: lib/ansible/parsing/yaml/constructor.py

import argparse
import base64
import binascii
import os
import subprocess
import sys
import yaml


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


# Encrypt/decrypt functions for Ansible Vault.
def ansible_vault_decrypt(src):
    return subprocess.check_output(
        ['ansible-vault', 'decrypt', '--output=-', src])


def ansible_vault_encrypt(data, dst):
    p = subprocess.Popen(
        ['ansible-vault', 'encrypt', '--output=' + dst, '-'],
        encoding='utf-8',
        stdin=subprocess.PIPE)
    p.communicate(data)
    rc = p.wait()
    if rc != 0:
        raise Exception('ansible-vault encrypt error')


# Encrypt/decrypt functions for when there is no Ansible Vault.
def nop_decrypt(src):
    with open(src) as fd:
        return fd.read()


def nop_encrypt(data, dst):
    with open(dst, 'w') as fd:
        fd.write(data)


def generate_simple_password(length=32):
    """Simple password generator.

    The resulting passwords should be alphanumeric, easily
    cut&pastable and usable on the command line.
    """
    n = int(length * 5 / 8)
    return base64.b32encode(os.urandom(n)).decode().rstrip('=')


def generate_binary_secret(length=32):
    """Binary password generator.

    Generates more complex passwords. Unfortunately at the moment the
    result needs to be UTF8-encodable due to Ansible limitations, so
    we can't just grab some random bytes from os.urandom() and we
    base64-encode them instead.

    """
    n = int(length * 3 / 4)
    return base64.b64encode(os.urandom(n)).decode().rstrip('=')


def generate_hex_secret(length=16):
    """Binary password generator (hex-encoded)."""
    return binascii.hexlify(os.urandom(int(length/2))).decode('ascii')


def generate_tsig_key():
    """Create TSIG keys to use with Bind version 9.

    The result is a dictionary with the attributes 'algo', 'public'
    and 'private'.

    """
    # This looks weird, actually.
    private = base64.b64encode(os.urandom(64)).decode()
    return {
        'algo': 'HMAC-SHA512',
        'private': private,
        'public': private[-32:],
    }


def generate_rsa_key(bits):
    """Create a RSA private key of the specified size.

    The result is a PEM-encoded string.
    """
    return subprocess.check_output(
        ['openssl', 'genrsa', str(bits)],
        encoding='ascii')


def generate_password(entry):
    ptype = entry.get('type', 'simple')
    if ptype == 'simple':
        return generate_simple_password(length=int(entry.get('length', 32)))
    if ptype == 'binary':
        return generate_binary_secret(length=int(entry.get('length', 32)))
    if ptype == 'hex':
        return generate_hex_secret(length=int(entry.get('length', 32)))
    if ptype == 'tsig':
        return generate_tsig_key()
    if ptype == 'rsakey':
        return generate_rsa_key(bits=int(entry.get('bits', 2048)))
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

    decrypt, encrypt = (ansible_vault_decrypt,
                        ansible_vault_encrypt)
    if not os.getenv('ANSIBLE_VAULT_PASSWORD_FILE'):
        print('Warning: ANSIBLE_VAULT_PASSWORD_FILE is unset, bypassing Ansible Vault',
              file=sys.stderr)
        decrypt, encrypt = (nop_decrypt, nop_encrypt)

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
