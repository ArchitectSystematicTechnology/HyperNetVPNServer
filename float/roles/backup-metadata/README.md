backup-metadata
===

Ansible role that installs the metadata service for the [backup
system](https://git.autistici.org/ai3/tools/tabacco).

It's just a simple REST API backed by a SQLite database. The server
does not run in a container simply because the binary is already
present on all hosts (it is also the backup *client*), and it's just
simpler this way.
