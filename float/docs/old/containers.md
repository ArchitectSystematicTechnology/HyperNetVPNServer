Guidelines on container structure for *float*
===

There are many ways to design service architecture, and *float* tries
to support as many as possible, though with its reverse proxy layer it
is obviously oriented towards request-based services.

To understand how the float capabilities map to architecture choices
and trade-offs, we're going to examine some of the float core concepts
and how they map to the trade-offs involved in an example scenario.

Nothing here is particularly novel, and furthermore (these being just
*guidelines*) this document represents just a specific point of view
on these issues, among many other equally valid ones.

## Core concepts

Float lets you define *services*, which are composed of *containers*,
which in turn contain one or more *processes*. We're going to ignore
"naked" systemd services installed via Ansible here, as they work
analogously to a simpler version of containers for the purpose of this
discussion.

Services are the fundamental *unit of scheduling*: each instance of a
service is assigned to a specific host, meaning that all of its
containers are scheduled together on that host.

They provide a name by which other services on your infrastructure can
find the instances (their IP addresses) that constitute it, via
float's service discovery mechanism.

Finally, services offer high-level features such as monitoring
aggregation etc, that allow you to look at the instances as a
meaningful aggregate.

Containers, on the other hand, are the lowest-level observable feature
in float: this is what float restarts when the configuration changes,
for instance, and it can know such things as "is this container
crashing often" etc.

How to map these abstractions to your architecture is your decision,
it has of course to first suit the specific problem you are solving.

## An example

Let's consider as an example a fairly typical two-layer service that
uses Apache + PHP to serve a website, ignoring an eventual MySQL for
now. This is a request-based service so some of the considerations
that we're going to make will be specific to this perspective.

There are three major possibilities for representing such a service
within float:

1. a float service "apache" and another float service "php", which may
   potentially be scheduled on different hosts, and that talk to each
   other over the service boundary: apache finds php endpoints using
   float's service discovery mechanism (i.e. DNS);
2. a single float service "web", with apache and php bundled together
   as a single unit of deployment, where apache talks to php inside
   the service boundary (i.e. it connects to localhost). This scenario
   can be further split into two:
   1. the float service "web" consists of an apache container and a
      separate php container, each runs independently of the other,
      they talk to each other either over the network (on localhost),
      or via an explicitly shared mechanism on the host (for instance
      a shared /run/web/sockets directory);
   2. the float service "web" consists of a single container that
      bundles together apache and php, maybe here they talk to each
      other via a /run/web/sockets directory that is completely 
      internal to the container itself.

Obviously the first problem to solve is that abstractions must make
sense to you and to the specific problem you're solving. Here the
"apache" and "php" components were pretty obvious choices for the
two-layer service we were considering.

The second thing to consider in terms of *float* architecture is what
we want the *request flow* to be: how, specifically, each component in
our service stack is supposed to talk to the following one as the
request flows downstream through the layers. Including float's reverse
proxy layer in the picture, the conceptual flow is quite simple:

```
reverse proxy
    |
    V 
  apache
    |
    V
   php
```

These components may be scheduled on different hosts (or not), so one
thing to consider is what the latency at each step will be. Generally,
as you move downwards the service stack, there is also a fan-out
factor to consider: consider a PHP script making multiple MySQL
requests, for instance.

The choice of representation depends on a number of different criteria
and decisions, of which we'll name a few:

* A good question to consider is "what kind of actions do you want to
  take in order to scale your service"? Maybe you run a datacenter,
  servers are just bare compute capacity for you, and can just add new
  ones when apache or php look busy, independently, in which case
  you'd go towards scenario #1. Or perhaps your service is
  data-partitioned, and to add a new server means moving some of your
  data to it, in which case it would makes sense to co-locate apache
  and php with the data, which makes scenario #2 look more suitable.
* If your service is distributed among hosts in different locations,
  you might like scenario #2 more as it contains the latency to the
  reverse proxy -> apache hop.
* For scenario #2, to decide amongst its two variants, another good
  question is "how do you like to build your containers"? This is a
  release engineering topic that depends on your CI, on what your
  upstreams look like, etc.

In terms of container bundling (#2.1 vs #2.2 above), we like our
containers do to "one thing", for whatever definition of "thing" you
find useful (provide a service, for example), so we run an init daemon
inside our containers to differentiate between important processes,
that control the lifecycle of the container itself, and non-important
ones that can simply be restarted whenever they fail.

For instance, let's consider a hypothetical mailing list service: this
has at least two major inbound APIs, a SMTP entry point for message
submission, and an HTTP API for mailing list management. These are
implemented by separate processes. We also want to run, say, a
Prometheus exporter, yet another separate process: but we don't
particularly care about its fate as long as it is running, and anyway
monitoring will tell us if it's not running, so this process is "less
important" than the first two.  We would have these three processes in
a single container, with the first two marked as "important" (i.e. the
container will terminate when they exit, signaling a failure to float
through systemd and monitoring), while the exporter would be marked as
not-important and simply silently restarted whenever it fails.
