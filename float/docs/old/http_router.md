Traffic routing
===

While it's probably possible to configure it to do otherwise, *float*
assumes that your services will run on isolated, internal private
networks, so it provides a mechanism to expose them publicly and route
external traffic to the correct backend processes.

To do so, one or more hosts should be dedicated to running the
*frontend* service (usually by setting up a host group and setting the
service *scheduling_group* accordingly). Such hosts will have their
public IP addresses advertised to the world via DNS. The *frontend*
service runs a set of proxies (NGINX and HAproxy) to route requests to
the correct service backends.

# High-level traffic flow

Float uses a basic two-tier model for serving requests, with a reverse
proxy layer between users and the back-end applications. Traffic to
the reverse proxies themselves (hosts running the *frontend* service)
is controlled via DNS: float creates low-TTL DNS records for its
public endpoints. This has all the usual caveats of using DNS for this
purpose, and it isn't really meant as a precise load-balancing layer.

Reliability is then provided by having multiple back-ends for the
application itself: the reverse proxies will find one that works. It
is important to note that, at the moment, float provides *no* accurate
load-balancing whatsoever, just basic round-robin or random-selection:
in NGINX, proper load balancing mechanisms are a paid feature.

# HTTP

The infrastructure provides a way for HTTP-based services to expose
themselves to the public Internet by defining [public
endpoints](configuration.md#global-traffic-routing). This is done via
the so-called *public HTTP router*, which is simply a NGINX
reverse-proxy installation that is automatically configured based on
service metadata.

The clients of this service are users (or generically, external
clients), not other services, which should instead talk directly to
each other.

The public HTTP router will force all incoming requests to HTTPS.

For implementation details, see the
[nginx Ansible role README](../roles/float-infra-nginx/README.md).

## SSL Certificates

The public HTTP router will automatically generate SSL certificates
for the required domain names. It will generate self-signed
certificates on the first install, and then switch to using
Letsencrypt in production environments.

## Cache

A global HTTP cache is available for services that require it. Its
location is */var/cache/nginx*, and it can be configured with the
following variables:

`nginx_cache_keys_mem` is the memory size of the key buffer.

`nginx_cache_fs_size` is the maximum on-disk size of the cache (note
that nginx might use as much as twice what specified here, depending
on expiration policy).

## Controlling incoming HTTP traffic

The public HTTP router offers the possibility to block incoming
requests based on their User-Agent (to ban bots, etc), or based on the
URL they are trying to access. The latter is often required for
regulatory compliance.

There is documentation of this functionality in the README files below
the
[roles/float-infra-nginx/templates/config/block/](../roles/float-infra-nginx/templates/config/block/)
directory.

## Tuning the NGINX configuration

It is possible to configure a number of NGINX tunable parameters,
which might be necessary depending on the incoming traffic. Check out
[roles/float-infra-nginx/defaults/main.yml](../roles/float-infra-nginx/defaults/main.yml) for
specific documentation on them.

# Non-HTTP

It is also possible to route arbitrary TCP traffic from the front-end
hosts to the service backends. In this case, the proxy will not
terminate SSL traffic or otherwise manipulate the request. The
original client IP address will be unavailable to the service.

Define *public_tcp_endpoints* for a service to enable this feature.

Note that there is no functionality for reverse proxying UDP services:
in this scenario you are probably better off scheduling your UDP
service directly on the *frontend* group (or use a different group
altogether and take care of DNS manually).
