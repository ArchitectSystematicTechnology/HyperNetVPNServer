prometheus
===

This role sets up monitoring and alerting
using [Prometheus](https://prometheus.io). It will scrape all
*monitoring_endpoints* defined in your services.yml file, as well as a
number of host-level metrics for every host in the Ansible inventory.

It also includes [Grafana](https://grafana.com) for dashboards.

Note that the Alertmanager web interface is currently not provided (it
is no longer packaged with Debian), so in order to add and manipulate
silences one should use "amtool" inside the container, i.e.:

```shell
$ in-container prometheus-alertmanager amtool alert
```

On the read path, [Thanos](https://thanos.io) is used to merge results from
multiple Prometheus instances.

## Alert delivery

The only supported mechanism for alert delivery right now is
email. The alertmanager performs its own SMTP delivery. You're
encouraged to use an external SMTP service for this purpose, to ensure
that you're not trying to deliver alerts over the same email
infrastructure you are monitoring.

Email delivery can be configured through the following variables:

* `alert_email` is the address that should receive email alerts
* `alertmanager_smtp_from` is the sender address to use for alert
  emails
* `alertmanager_smtp_smarthost` is the server to use for outbound SMTP
* `alertmanager_smtp_require_tls` should be set to *true* if the
  server requires TLS
* `alertmanager_smtp_auth_username` and
  `alertmanager_smtp_auth_password` are the credentials for
  authentication
* `alertmanager_smtp_hello` is the hostname to use in the HELO SMTP
  header sent to the server (default: *localhost*)

If *alert_email* is left empty, alertmanager won't deliver any alerts
but it will still be active and functional (via *amtool*).

## Customizing alerts

A few alerting rules are provided by default
in
[roles/prometheus/files/rules/](roles/prometheus/files/rules/). This
includes:

* host-level alerts (high CPU usage, disk full, network errors...)
* service failures (systemd services down, or crash-looping)
* HTTP errors on *public_endpoints*

To add your own alerts, you may want to create your own Ansible role
with the necessary rule and alert files, and schedule it to execute on
hosts in the *prometheus* group. For instance, in your playbook (if
the Ansible role is called *site-alerts*):

```yaml
- hosts: prometheus
  roles:
    - site-alerts
```

The alertmanager configuration expects some common labels to be set on
your alerts in order to apply its inhibition hierarchy (and make
alerting less noisy):

* `severity` should be set to one of *warn* (no notification) or
  *page*
* `scope` should be one of *host* (for prober-based alerts),
  *instance* (for all other targets), or *global*.

## Monitoring external targets

It is possible to extend Prometheus to scrape external targets, by
adding them to the *prometheus_external_targets* configuration
variable.

Each entry in that list should have the following attributes:

* `name` maps to the Prometheus job_name
* `scheme` can be *http* (default) or *https*
* `metrics_path` (default /metrics)
* `targets` is the list of host:port targets to scrape

## Scraping external Prometheus instances

In is possible to federate (scrape) external Prometheus instances
by defining a list of targets (usually on port 9090) in the
*prometheus_federated_targets* configuration variable.

Scraping a federated Prometheus instance is similar to scraping an
external target, but it uses the */federate* endpoint and preserves
remote labels.

## Creating Grafana dashboards

Since we potentially run more than one instance of Grafana for
reliability purposes, it is not possible to create and save new
dashboards via the Grafana UI: the results will only be saved locally
in the instance you happen to talk to.

Instead, one should drop the dashboard JSON files in the
*/etc/grafana/dashboards/* directory, preferably using a custom
Ansible role as mentioned above.

## Extending metrics storage retention

Float supports so-called long term storage (lts) for Prometheus metrics via
federation.

The `prometheus-lts` service provides such functionality; it will **scrape**
all Prometheus instances via federation. For queries, the service also runs a
`thanos sidecar` instance to make long term metrics available.

Although the service is not active by default, it can be deployed by including
`playbooks/prometheus-lts.yml` in `site.yml` and the corresponding
`services.prometheus-lts.yml` in `services.yml`.
