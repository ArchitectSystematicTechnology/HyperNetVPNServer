dns
===

The infrastructure provides a public (authoritative) DNS
infrastructure, meant to run on front-end servers alongside the public
HTTP routers. Zones for public domains are automatically generated and
populated with records based on the *public_endpoints* (of different
kinds) defined in the service configuration.

The current implementation uses, for legacy reasons, Bind
and [zonetool](https://git.autistici.org/ale/zonetool), a wrapper that
generates DNS zones from YAML files, allowing templating and other
features. In the future we might consider switching
to [Knot](https://knot-dns.cz), which integrates these features.

The DNS configuration lives in */etc/dns*, and, like the public HTTP
router, it is meant to facilitate integration with custom
automation. For this purpose, configuration is split into two
directories:

* */etc/dns/manual* contains manually-maintained zones, including the
  autogenerated public zones. If you need to manually ship DNS
  configurations from your Ansible config, drop them here.
* */etc/dns/auto* (empty by default) is meant for custom automation
  mechanisms - it is separate from the other directory so that it's
  possible for the automation to detect obsolete configs and remove
  them.

A small wrapper script is installed, */usr/sbin/update-dns*, which
will invoke zonetool with the right options and re-generate the DNS
zones for bind. The named daemon must be reloaded manually.

## Custom DNS zones

To install a custom, manually maintained DNS zone, you are going to
need to create a tiny dedicated Ansible role. There are detailed
instructions on how to do so in
[docs/ansible.md](../../docs/ansible.md).

## Further customization

If you need Bind to set up specific zones or delegations, your own
automation can create the following files:

* */etc/bind/named.conf.internal-custom-zones*
* */etc/bind/named.conf.external-custom-zones*

which should contain Bind directives for the internal and external
views respectively.