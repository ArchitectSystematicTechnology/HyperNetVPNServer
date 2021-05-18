Replacing Ansible
===

As *float* only sees Ansible as an implementation detail, so it's fair
to keep track of how we might eventually replace it with something
else (currently undefined).

To do so, it's useful to examine *how* exactly we are using Ansible
and what features we ultimately rely upon. Float has been explicitly
design to minimize the number of these features, to keep the contact
surface between itself and Ansible as small as possible.

* The main code for float, including the scheduling logic, is fully
  contained in the "float.py" Ansible inventory plugin. Its output is
  just a list of variables (global and per-host), which can be easily
  integrated into other systems.

* We use Ansible to copy files in place, eventually using
  templates. This is the fundamental feature of all configuration
  management systems. Most of our file copies are hooked with some
  kind of restart-the-associated-service task.

* We use a lot of verbose Ansible code to run loops over data
  structures (credentials, host / DNS configs, etc), accounting for a
  significant part of code bloat and execution time. This is a
  particularly bad spot for float/Ansible integration, but the
  underlying algorithms are very simple (just nested loops). Some of
  these are slowly being unrolled using functional filters.

* We use a pattern of remote execution + data transfers to sign
  credentials without the private key ever leaving the hosts. This is
  mostly done in Ansible action plugins for speed (x509_ca, sshca),
  but the workflow is similar in all cases: generate private key on
  the host, sign public key on the Ansible host, transfer the results;
  the advantage is that the private key material never moves around.
  This logic represents the vast majority of our custom Python code,
  and it's largely the same functionality repeated for different CA
  models (X509, SSH).

* We maintain a minimal dependency on "discovered" ansible_facts as a
  way to decouple the configuration templates from Ansible itself as
  much as possible.

* There's [still one place where we run a global collection
  pass](https://git.autistici.org/ai3/float/-/issues/86) in order to
  use the results in a subsequent Ansible task: when collecting all
  *tinc* public keys to generate the tinc configuration (every host
  needs all the other peers' public keys). This pattern of accessing
  non-inventory facts about other hosts is quite problematic due to
  the requirement of all the hosts being up (or using a persistent
  cache for facts), and it is highly discouraged. There are probably
  alternative solutions that could be explored (like storing the tinc
  public keys in the repository), on a case-by-case basis.

Also, some float limitations are directly derived from Ansible
characteristics:

* Float requires you to manually write a playbook tying your service
  group to your Ansible role, because it is currently impossible to
  parameterize the *import_role* Ansible directive.

* We can't meaningfully use role dependencies (at least not the way
  the roles are currently written), because Ansible considers
  dependencies to be local to each playbook, so if every role depends
  on *float-base*, it will end up being run as many times as there are
  services.


## Advice for writing Ansible roles for services

If one is running services on float, and wishes to retain some level
of flexibility to switch to other mechanisms in the future, here are
some guidelines that could be followed to maximize that chance:

* Do not use discovered *ansible_facts*, especially not from other
  hosts, but use facts from the host inventory instead. If you need
  information about hosts to be available to service configurations,
  define additional host attributes in the inventory.

* Only use simple Ansible task modules such as "copy", "template",
  "file" and possibly "systemd" to restart containers. If you're using
  a container-based service deployment style, there should be no need
  for anything else. These types of tasks, along with their usually
  minimal logic, should be relatively simple to translate to other
  environments.
