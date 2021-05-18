base
=====

Set up the base Debian system, including the SSH daemon
and its associated config, and various common packages.

## Configuration

Check the [float configuration reference](../docs/reference.md) for
further details on global configuration variables.

## Experimental features

* `enable_fail2ban` (default: *True*): install *fail2ban* on all
  hosts, without configuring any jails. The idea is that services
  might configure their own jails, and float provides standardized
  mechanisms for log-tailing (via journald) and banning (via the
  *firewall-ipset* action provided by the *firewall* package).

* `enable_osquery` (default: *False*): when True, install *osquery*
  on all hosts. There is currently no analysis component, so this
  isn't very useful yet.

## Notes

### Third-party package repositories

This role installs the APT source at *deb.autistici.org*, as it's
required by some packages.
