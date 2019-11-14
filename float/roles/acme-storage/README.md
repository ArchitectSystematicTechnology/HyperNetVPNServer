Role that provides public credentials on the local filesystem, below
/etc/credentials/public.

It does also provide the *replds* service which stores and
synchronizes the public credentials themselves. The *acmeserver*
service talks to it to store the certificates upon renewal. It is a
fully meshed, gossip-based eventually consistent system. Since there
is a non-zero replication delay on average, each node needs to
implement its own local reload mechanism for the associated daemons.

This Ansible role is included as a dependency from roles that need
access to /etc/credentials/public.
