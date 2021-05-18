auth-server
===

Ansible role that installs the primary [authentication
service](https://git.autistici.org/id/auth). Required by any service
that needs low-level authentication functionality.

By default auth-server comes with no service-specific configuration,
other roles will install files in the directories below
*/etc/auth-server/*.
