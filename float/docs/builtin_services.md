Built-in services
===

The infrastructure provided by *float* includes a number of services
that are not always considered "infrastructure" proper, but provide
what we believe is critical platform-level functionality. In general,
they are meant to discover your services automatically (via their
*services.yml* metadata), and thus be globally useful.

The list might vary but currently includes:

* A [reverse HTTP proxy](http_router.md) that sits in front of all the
  HTTP-based services, and automatically handles request routing,
  caching, and SSL certificates using Letsencrypt.

* A [DNS](../roles/dns/README.md) service meant for public clients, with
  automated generation of the necessary zones, so all you normally
  need to put it in production is a NS delegation. It is easily
  customizable with additional records.

* [Monitoring](../roles/prometheus/README.md), based on Prometheus,
  with automatic collection of your service's *monitoring_endpoints*
  and generic per-service availability alerts.

  There are dashboards at `https://grafana.your_public_domain/` and
  Prometheus itself is accessible at
  `https://monitor.your_public_domain/`.

* A [log collection and analysis](../roles/log-collector/README.md)
  service, using rsyslog and Elasticsearch/Kibana. Collects (and
  anonymizes) all logs, either syslog or stderr, produced by your
  services, with configurable retention policies.

  The Elasticsearch API is available internally at
  `http://log-collector.your_internal_domain:9200/`, and can be
  queried on all machines using the
  [logcat](https://git.autistici.org/ai3/tools/logcat) utility, e.g.:

```shell
$ logcat --from=-48h --iso 'program:auth-server AND "user@example.com"'
...
```

* An [authentication stack](identity_management.md) that allows
  administrators, and eventually users, of your services to
  authenticate with a single system, that supports OTP and hardware
  tokens.

  The necessary bits are available for integration:

  * The SSO public key is on all hosts at */etc/sso/public.key*
  * The SSO login server by default will be located at
    `https://login.your_public_domain/`.

* A backup system that understands application-level metadata and is
  integrated with the automation, allowing for unattended restores and
  single-hosted service moves (TODO).

## Default groups

By default, and in line with its model, float does not care much about
where its builtin services run. It will however expect two host groups
to exist (possibly overlapping):

* the *frontend* group will be used to schedule the user-visible
  services like the HTTP/TCP reverse proxies and DNS. Note that this
  group name is **fixed**: user-visible services *must* run on the
  "frontend" group, as the name is hard-coded in multiple places
  (wherever we need to look up all the user-visible hosts). In the
  default configuration, hosts in the frontend group are the only ones
  that receive traffic from users.

* the *backend* group will be used to run all the other built-in
  services. In the default configuration, backend hosts only receive
  traffic from frontend hosts through the network overlay (VPN).

It is possible to override the *scheduling_group* attribute of the
default services in your own *services.yml* file, for instance to
constrain specific services to dedicated hosts, or whatever other
reason you see fit.
