base
=====

Set up the base Debian system, including the SSH daemon
and its associated config, and various common packages.

## Configuration

Some global configuration options in Ansible control aspects of the
setup shared across all servers:

* `admins`: a list of dictionaries containing the authentication
  details for administrators. These control SSH logins and admin-level
  SSO-enabled applications on the web. Every dictionary can have the
  following attributes:
  * `name`: name of the user
  * `password`: the encrypted version of the password
  * `ssh_keys`: a list of public SSH keys for this user (each one
    should be a string in the standard SSH public key format)
  * `totp_secret`: the TOTP secret (enables 2FA)

* `apt_proxy`: if set, a *host:port* pair pointing at an HTTP proxy for
  Debian packages. Recommended for test environments, as it improves
  performance quite dramatically.

* `enable_fail2ban` (default: *False*): if set to True, fail2ban is
  installed and configured to look for failed SSH logins.

* `enable_ssh` (default: *True*): whether to take over the SSH
  configuration and set up a SSH CA for host-based authentication.

* `enable_osquery` (default: *False*): when True, install *osquery*
  on all hosts

* `mail_relay`: a dictionary of attributes configuring outbound email
  over (authenticated) SMTP. Useful when you do not intend on running
  your own mail service. Available attributes:
  * `root_user`: the address to send root email to
  * `server` and `port`: address of the SMTP server to use
  * `user` and `password`: authentication parameters for SMTP

## Notes

### Third-party package repositories

This role installs the APT source at *deb.autistici.org*, as it's
required by some packages.

### SSH setup

When *enable_ssh* is true (the default), this role will manage the SSH
configuration of the hosts.

In the current setup, all users should log in as root using SSH public
key authentication. Users as such do not exist on the hosts. This is
probably due to change at some point, to increase auditability (though
the SSH server logs the key name used for logins).
