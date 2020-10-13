Accessing internal services
===

While *float* is primarily focused towards providing **public** access
to services (by way of its reverse HTTP proxy setup), there are
scenarios in which we may want to provide access to internal services,
restricted to a specific group of people (administrators).

There are many reasons why one would want to do this:

* access privileged services not meant for the general public (any
  infrastructural service that has a web UI: monitoring, logging, etc)
* individual service backends may provide status pages or other
  debugging information that is not itself part of the "exposed"
  service
* the desire to provide fully private services, for the consumption of
  admins and other internal services

This document presents an overview of the possible techniques, and
their respective advantages / disadvantages.

We're going to assume that the internal services are running on an
internal (private) network - while it is possible to use *float*
differently, this is the default setup.


# Access technologies

## VPN

The "standard" solution for this scenario: privileged users will set
up a VPN connection to your internal private network (via a gateway
server that is reachable from the Internet). Authentication is handled
by the VPN itself.

This approach has many downsides:

* every user has to run a VPN client
* VPN clients are messy, as you're operating at the IP layer
* DNS setup is problematic: you either run all users' queries through
  a caching resolver on your private network, or you have to make
  public entries (with private IPs) for your private web services
* coming up with a setup that will not interfere with people's other
  activities is non trivial (split networking etc)
* you still need to deal with user authentication at the HTTP layer
  (you don't want your privileged services to just trust the IP
  address, right?)

## Client proxies

Some of the disadvantages of the VPN approach can be mitigated by
running a traffic proxy at the application (HTTP) layer, taking
advantage of the configurability of the proxy lookup logic in browsers
via `proxy.pac`. For instance, you could have something like the
following proxy configuration:

```
if (domain.endswith('example.com')) {
  return 'socks5://localhost:1234';
}
```

to tell browsers to use localhost:1234 for all your \*.example.com
URLs. At that address you would find a SOCKS5 proxy, presumably
forwarding traffic directly into your private network. Some external
authenticated mechanism would be required in order to establish this
proxy connection -- it doesn't have to be HTTP authentication, for
instance a *ssh* connection would be enough (the -D option provides a
quick way to set up a SOCKS proxy).

The advantages:

* completely transparent with respect to normal browser traffic
* "safe" fallback (if the proxy is misconfigured, traffic does not go
  through at all)
* since the proxy is terminated inside your private network, you don't
  need public DNS entries for privileged web services

There is still some minimal setup required on the client (to establish
the proxy connection), but that's a lot easier to manage across
multiple platforms than a VPN client.

Float implements this in testing environments, with the (publicly
accessible) SOCKS5 proxy
[float-debug-proxy](https://git.autistici.org/ai3/tools/float-debug-proxy).

## Authenticated reverse proxy

Another alternative could be to just make everything "public", and put
your privileged web services behind an authenticating reverse
proxy. In this scenario, you would have public DNS records for all
your privileged web services, pointing at the reverse proxy IP. The
reverse proxy would then take care of enforcing authentication, and
pass the user information along to the privileged web service.

This is possibly the least intrusive approach:

* no client is needed
* interacts well with other activities (there is no "special setup",
  users are just browsing normally)
* pretty much the only way to get valid SSL certificates for your
  internal services

However there are downsides too:

* every privileged web service needs public DNS records (and
  certificates, etc. etc.) - this can be automated of course, but it
  makes those services "discoverable", which may not be desired in
  some cases
* it can be difficult to protect complex APIs (i.e. anything that has
  both a web UI and a machine-oriented API, which presumably expect
  different authentication methods)

"ai3/float" currently adopts this approach via the *sso-proxy*.


# Picking the right access technology

In order to chose the "right" access technology for an infrastructure,
one needs to consider exactly what kind of *access* is desired.

In most cases, what one wants is specifically HTTP(S) access to
services using a browser. The focus on the browser is important: in
the encouraged setup for *float*, internal services talk to each other
using mTLS. This poses a big problem, as it is non-trivial to support
both mutually authenticated TLS (which requires a client certificate)
and non-authenticated TLS clients such as a browser.

Browsers technically support client certificates, but the UX is
absolutely terrible, and nowadays client SSL certificates in browsers
are basically unused even by the few historical adopters (banks,
public administrations). Similar issues plague the usage of custom SSL
Certification Authorities in browsers, which would also be required
for interoperability with float's internal service credentials PKI.

In environments with a heterogeneous, non centrally managed client
device pool (which is very rare outside of corporate environments),
there is a fundamental necessity to keep software requirements on the
user's side as simple as possible: excessive customization of the
browser environment is to be avoided.

This pretty much leaves only the *authenticated reverse proxy* option
on the table, as it is the only one that can provide a seamless,
zero-configuration experience for internal web services.
