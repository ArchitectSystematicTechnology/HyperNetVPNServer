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
  management systems. Most of our file copies are hooked into some
  sort of restart-the-associated-service loop.

* We use a lot of verbose Ansible code to run loops over data
  structures (credentials, host / DNS configs, etc), accounting for a
  significant part of code bloat and execution time. This is a
  particularly bad spot for float/Ansible integration, but the
  underlying algorithms are very simple (just nested loops).

* We use a pattern of remote execution + data transfers to sign
  credentials without the private key ever leaving the hosts. This is
  mostly done in Ansible action plugins for speed (x509_ca, sshca),
  but the workflow is similar in all cases: generate private key on
  the host, sign public key on the Ansible host, transfer the results;
  the advantage is that the private key material never moves around.

* Some services require us to refer to other host's IP addresses
  rather than just by name, so we access other host's metadata
  variables (facts, which are part of the inventory).

* In a couple of places we run a global collection pass in order to
  use the results in a subsequent Ansible task: for instance when
  collecting all *tinc* public keys to generate the tinc configuration
  (every host needs all the other peers' public keys). This pattern of
  accessing non-inventory facts about other hosts is quite problematic
  due to the requirement of all the hosts being up (or using a
  persistent cache for facts), and it is highly discouraged. There are
  probably alternative solutions that could be explored (like storing
  the tinc public keys in the repository), on a case-by-case basis.
