Service mesh
============

The *service mesh* is a fancy name for the layer of glue that allows
services to find and talk to each other. Ours offers the following
features:

* The ability to set up *overlay* networks to isolate
  service-to-service traffic from the public Internet.
* Services find each other with DNS A / AAAA lookups, so the client
  must know the target port. As a consequence, each service must use a
  globally unique port. This also implies that it's impossible to
  schedule more than one instance of a service on each host.
* DNS views are used to provide topology-aware service resolution, so
  that hosts sharing a network overlay will route service requests
  over that network.
* Connections between services are direct, not mediated by proxies, so
  there is no global load balancing and clients are expected to keep
  track of the state of backends and implement retry policies.
* Services can securely authenticate each other by using credentials
  automatically provided by the service mesh.

# Naming

Services are identified by their *name*, an alphanumeric string (it
can also include a dash '-' character).

All DNS entries are served under an internal domain *domain*.

Every host has its own view of the DNS map. The specific IP addresses
associated with a target service instance will depend on whether the
source and target host share any network overlays, which will be used
in preference to the public IP address of the backend host.

## Locating service backends

The access patterns to backends of a distributed service vary
depending on the service itself: for instance, with services that are
replicated for high-availability, the client usually does not care
which backend it talks to. In other cases, such as with *partitioned*
services, clients need to identify individual backends.

We provide three ways of discovering the IP address of service
backends. The port must be known and fixed at the application level.

Note that in all cases, the DNS map returns the *configured* state of
the services, regardless of their health. It is up to the client to
keep track of the availability status of the individual backends.

### All backends

The DNS name for *service.domain* results in a response containing the
IP addresses of all configured backends for *service*.

```
$ getent hosts myservice.mydomain
1.2.3.4
2.3.4.5
3.4.5.6
```

Note that due to limitations of the DNS protocol, not all backends may
be discovered this way. It is however expected that a sufficient
number of them will be returned in the DNS response to make high
availability applications possible. If you need the full list of
instances, it is best to obtain it at configuration time via Ansible.

### Individual backends

Each service instance has a name that identifies it specifically,
obtained by prepending the (short) host name to the service name:

```
$ getent hosts host1.myservice.mydomain
1.2.3.4
```

This is the hostname that the instance should use to advertise itself
to its peers, if the service requires it.

### Shards

Backends can also have permanent *shard* identifiers, that identify a
specific backend host, and that do not change on reschedules. These
are useful when a service is partitioned across multiple backends and
the hosts have state or data associated with it. A shard identifier is
an alphanumeric literal, specific to the host.

```
$ getent hosts shard1.myservice.mydomain
1.2.3.4
```

### Master-elected services

When a service uses *master election*, an instance is automatically
picked at configuration time to be the *master* of the service. This
instance will be discoverable along with the other instances when
resolving the service name. In addition, the special DNS name
*service-master.domain* will point at it:

```
$ getent hosts myservice-master.mydomain
2.3.4.5
```

## Configuring distributed services in Ansible

The same kind of service discovery described above is available in
Ansible roles, using the dynamically generated group variables:

```
{% for hostname in groups['myservice'] %}
...
{% endfor %}
```

Similarly, individual backends are identified by their
*inventory_hostname*, e.g. in an example service configuration file:

```yaml
advertised_url: https://{{ inventory_hostname }}.myservice.{{ domain }}:1234/
```

# Mutual Service Authentication

Service communication should be encrypted, and communicating services
should authenticate each other. The standard way to do this is with
TLS as the transport layer. The service mesh provides its own *service
PKI* to automatically generate X509 credentials for all services.

The X509 certificates are deployed on the host filesystem, and access
to them is controlled via UNIX permissions (using a dedicated
group). This provides an attestation of UNIX identity across the whole
infrastructure.

Each service, in *services.yml*, can define multiple credentials, each
with its own name and attributes: this can be useful for complex
services with multiple processes, but in most cases there will be just
a single credential, with the same name as the service. When multiple
credentials are used, all server certificates will have the same DNS
names (those associated with the service), so it's unusual to have
multiple server credentials in a service specification.

Credentials are saved below `/etc/credentials/x509/<name>`, with
the following structure:

```
    /etc/credentials/x509/<name>/
      +-- ca.pem                   CA certificate for the service PKI
      +-- client/
      |   +-- cert.pem             Client certificate
      |   \-- private_key.pem      Client private key
      \-- server/
          +-- cert.pem             Server certificate
          \-- private_key.pem      Server private key
```

Private keys are stored unencrypted, and are only readable by the
`<name>-credentials` group. The user that the service runs as must be
a member of this group.

Server certificates will include all the names and IP addresses that
service backends are reachable as. This includes:

* *service_name.domain*
* *service_name*
* *hostname.service_name.domain*
* *hostname.service_name*
* *shard.service_name.domain* (if present)
* *fqdn*
* localhost
* all public IP addresses of the host
* all IP addresses of the host on its network overlays

The purpose is to pass server name validation on the largest number of
clients possible, without forcing a specific implementation.

Client certificates have the following names, note that it is using
the credentials name, not the service name:

* *name.domain*
* *name*

The service configuration for credentials is described in the
[configuration](configuration.md#credentials) page. Using multiple
client credentials for a single service might allow ACL separation in
complex services.

Most legacy services should be able to implement CA-based client
certificate validation, which at least protects the transport from
unprivileged observers. But some clients can validate the client
certificate CN, which implements a form of distributed UNIX permission
check (the client had access to a specific certificate), and is
therefore preferable.

# Network overlays

It is possible to define internal networks that span multiple hosts,
called *overlays*, which can then be used for service-to-service
traffic, ignoring the details of the actual underlying public network
topology.

For now, only a single IPv4 address can be assigned to a host on each
private network. In the future, it should be possible to assign an
entire subnet, so that individual IPs will be available to services.

The current implementation uses [tinc](https://www.tinc-vpn.org/) and
sets up a fully connected mesh.

See the [configuration](configuration.md#host-variables) page for
details on the host configuration required to enable network overlays.

When the client and server hosts are on the same private network, the
DNS-based service discovery will return the server's address on that
private network, ensuring that service-to-service communication goes
over the VPN.

# Usage

## Server implementation

Servers should use TLS 1.2, and they should require clients to provide
a certificate and validate that it is signed by the CA.  Since
credentials are ECDSA certificates, servers should at least support
the ECDHE\_ECDSA\_WITH\_AES\_128\_GCM\_SHA256 cipher suite.

For authenticating the client, servers can look at the client
certificate subject, and apply ACLs based on it.

A reference HTTPS server implementation for Go is provided in the
[git.autistici.org/ai3/go-common/serverutil](https://git.autistici.org/ai3/go-common/blob/master/serverutil/) package.

HTTP servers should apply backpressure (when they detect overload) by
returning responses with HTTP status 429.

## Client implementation

Since the infrastructure provides little in terms of traffic control,
clients should be smart and well-behaved, they should expect failures
and handle them gracefully. At the very least this implies:

* Clients should use DNS to fetch the backend(s). The results should
  be refreshed periodically to detect new and expired backends. This
  is important, so that you don't need to restart all the clients when
  a service is rescheduled. Implementing a load balancing policy with
  the returned addresses is left to the client.

* All outbound requests must have deadlines, and handle timeout
  errors, so that a failure to reach a backend does not cause requests
  to pile up indefinitely.

* Clients should retry failed requests as many times as necessary,
  within the deadline, using exponential back-off. Retriable failures
  should include transport-level errors and backpressure errors at the
  application level.

### Go

A reference HTTP(S) client implementation for Go is provided in the
[git.autistici.org/ai3/go-common/clientutil](https://git.autistici.org/ai3/go-common/blob/master/clientutil/) package.

### Python

A relatively robust Python HTTPS client could be something as simple
as this (using the [requests](http://python-requests.org/)
and [backoff](https://pypi.python.org/pypi/backoff) packages):

```python
import backoff
import requests

class StatusError(Exception):
    def __init__(self, code):
        self.code = code
        super(StatusError, self).__init__('HTTP status %d' % code)

class RetriableStatusError(StatusError):
    pass

@backoff.on_exception(backoff.expo,
                      (requests.exceptions.Timeout,
                       requests.exceptions.ConnectionError,
                       RetriableStatusError),
                      max_tries=10)
def json_request(self, uri, data, ssl_cert, ssl_key, ssl_ca, timeout=10):
    session = requests.Session()
    session.cert = (ssl_cert, ssl_key)
    session.verify = ssl_ca
    session.timeout = timeout
    req = session.prepare_request(requests.Request(
        'POST',
        uri,
        data=json.dumps(data),
        headers={'Content-Type': 'application/json'},
    ))
    resp = session.send(req)
    if resp.status_code == 429 or resp.status_code >= 500:
        raise RetriableStatusError(resp.status_code)
    elif resp.status_code != 200:
        raise StatusError(resp.status_code)
    return resp.json()
```

## Static host entries

The current implementation defers control of the contents of
/etc/hosts to the *float* automation. Sometimes (often in testing) you
might need to manually place static entries there. For this, you can
set the Ansible variable *static_host_entries* to a list of
dictionaries, one for each entry, having the *host* and *addr*
attributes.
