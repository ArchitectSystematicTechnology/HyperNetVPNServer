net-overlay
===========

This role allows you to create VPNs (also called *overlay networks*
sometimes) easily, on demand, just by setting a few parameters on host
variables in the configuration file.

To create a new overlay, just set an attribute named *ip_* + the
overlay name containing the unique IP address for the host, in the
host variables of each node of the private network.

Then add the overlay to the global variable *net_overlays*, which
lists all the known private networks. For instance:

```yaml
hosts:
  host1:
    ip: 1.2.3.4
    ip_vpn1: 2.3.4.5
  host2:
    ip: 1.2.3.5
    ip_vpn1: 2.3.4.6

group_vars:
  all:
    net_overlay_backend: tinc
    net_overlays:
      - { name: vpn1 }
```

The above configuration snippet sets up a network named *vpn1* between
the two hosts (by default it uses a /24 network - this is currently
not configurable). The only network overlay backend currently available
is *tinc*, so there's actually no need to explicitly specify it.

The inventory plugin will automatically generate a group containing
*host1* and *host2*, named *overlay-vpn1*.

## Overlay configuration

The *net_overlay* configuration variable must contain a list of all
your configured network overlays, each a dictionary with the following
attributes:

`name` is the only mandatory attribute, the name of the overlay network.

`port` is the port used by the transport layer. If you define more
than one overlay network, the ports **must** be different! The default
value is 655, which is the default *tinc* port.

`cipher`, `digest`, `compression` and `pmtu` are *tinc*-specific
attributes that have sensible defaults. If you wish to modify them,
check out the *tinc.conf(5)* man page for the possible values and
their meaning.
