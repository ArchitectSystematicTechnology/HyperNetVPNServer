Autogeneration of public SSL certificates
===

The *float* platform will manage the creation and renewal of SSL
certificates for all the public endpoints it knows about, with no
interaction required from the operator. It does so using Letsencrypt
and the ACME protocol.

Since Letsencrypt certificates are usually short-lived, renewal must
not require operator intervention (it would be required too often), so
we cannot drive the process via Ansible like we do for the internal
X509 PKI. Instead, certificate management must be an online (live)
service, meeting the following requirements:

* it should examine the current certificates and figure out when they
  are about to expire and should be renewed;
* it should use the ACME protocol to create or renew certificates,
  including handling the ACME verification challenges;
* it must propagate the new certificates to all front-end hosts so
  that the TLS-terminating routers (nginx, haproxy) can pick them up.

Furthermore, all the above has to be done with a minimal and properly
defined set of permissions and dependencies.

This is one of the most complex parts of the infrastructure so we try
to document it carefully.

# Introduction: lifecycle of a public SSL certificate

It's easier to set up services if all the SSL certificates they need
are already available, which is definitely the case for our
nginx/haproxy traffic router front-ends. So, in order to keep our
configuration simple, and to make everything work on the first Ansible
run, *float* guarantees that all the required public SSL certificate
files will always exist.

What happens is that the actual contents of the certificate change
over the lifetime of a cluster. The exact details depend on whether we
are considering a *testing* or *production* environment, where the
difference has to do with whether the hosts are reachable over the
public Internet.

For each public SSL certificate:

* at first, if no certificate exists on the hosts, a self-signed
  certificate is created by Ansible and installed. In this state, the
  service is clearly still insecure, but the daemons can start and
  it's possible to view websites in a browser (with warnings).

* then, the *acme* service takes over management of the certificate,
  and, depending on the configuration:

  * in *production* environments, it tries to create a valid SSL
    certificate using ACME. If it succeeds, the self-signed
    certificate is replaced with a valid one.

  * in *testing* environments, where the ACME validation challenges
    can't be satisfied (because the hosts can't be reached from the
    ACME validation servers), it simply creates another self-signed
    certificate instead of talking to Letsencrypt to get one.

  in either case, the certificate is then renewed automatically by
  the *acme* service whenever it is about to expire.


# The ACME service

The service is split into multiple agents, each performing a specific
role. Let's see in detail what they are.

## *acmeserver*

The first part of the service is basically a cron job, that
periodically checks all known certificates (we get the list via
Ansible), and eventually attempts to create or renew them.

This role is fulfilled by the
[acmeserver](https://git.autistici.org/ai3/acmeserver) daemon. We run
a single instance of it, because downtime is not particularly
critical, and it saves us from implementing locking.

To obtain a new certificate (unless it's a self-signed one), we need
to satisfy an ACME challenge. The acme service supports two challenge
types: *http-01* and *dns-01*.

Once the certificate has been obtained, it will be pushed to all
frontends using the *replds* service (see below).

## *http-01* challenges

To reply to a *http-01* challenge we need to serve a token at a
well-known URL (over plain HTTP) on all the domains requested in the
certificate.

The *acmeserver* can respond to these requests, and all requests for
the */.well-known/acme-challenge/* prefix on all domains to be
forwarded to it by NGINX.

## *dns-01* challenges

In the *dns-01* case, the Letsencrypt servers will make a DNS request
for a specific TXT record in our DNS. To do this, *acmeserver* talks
directly to all the *bind* processes running on the front-end hosts,
and modifies the zones using a TSIG-authenticated request.

## *replds*

The file replication component of the service is
[replds](https://git.autistici.org/ai3/replds), a small daemon that
replicates data across multiple identical nodes (the front-end hosts).

The replds service is a multi-instance systemd service, the instance
used by the acme service is called *replds@acme*.

This component is provided by the *acme-storage* Ansible role.

## Reloading services

Certificates written by replds are then read by the various front-end
services (so at least NGINX in the default *float*
configuration). There is unfortunately no explicit communication
between replds and nginx (replds itself lacks a notification
mechanism, mostly because it does not have transactions and we can't
know when a set of certificate and private key will both be ready), so
the services are reloaded by cron jobs, that check if certificates
used by each service have changed since the last execution. An example
of such a script can be found in
[../nginx/files/acme-reload-nginx](acme-reload-nginx).

The execution interval of these cron jobs ultimately controls the
propagation delay for new certificates.

## Notes

Note that the overall process is safe mostly due to the idempotency of
ACME operations, and the low urgency of the task: if we fail to obtain
a valid certificate, or are interrupted midway through the process, we
can simply start over on the next attempt. In line with this approach,
the *acmeserver* and *replds* daemons do not keep any state
themselves, besides the certificate files that are stored on the
filesystem. This introduces the possibility that an unclean acmeserver
restart during a dns-01 validation process might leave stranded TXT
records in the DNS server, but the process is rare enough that this
seems harmless.

# Adding custom certificates

For some services, you may need to generate public certificates that
are not described in *float* service metadata. In this case, you're
going to need a custom Ansible role, running on hosts in the *acme*
group, to ship a custom acmeserver configuration snippet in
*/etc/acme/certs.d*.
