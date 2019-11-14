prometheus
===

This role sets up monitoring and alerting
using [Prometheus](https://prometheus.io). It will scrape all
*monitoring_targets* defined in your services.yml file, as well as a
number of host-level metrics for every host in the Ansible inventory.

It also includes [Grafana](https://grafana.com) for dashboards.

Note that the Alertmanager web interface is currently not provided (it
is no longer packaged with Debian), so in order to add and manipulate
silences one should use "amtool" inside the container, i.e.:

```shell
$ in-container prometheus-alertmanager amtool alert
```

## Customizing alerts

A few alerting rules are provided by default
in
[rules/prometheus/files/rules/](rules/prometheus/files/rules/). This
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

## Creating Grafana dashboards

Since we potentially run more than one instance of Grafana for
reliability purposes, it is not possible to create and save new
dashboards via the Grafana UI: the results will only be saved locally
in the instance you happen to talk to.

Instead, one should drop the dashboard JSON files in the
*/etc/grafana/dashboards/* directory, preferably using a custom
Ansible role as mentioned above.
