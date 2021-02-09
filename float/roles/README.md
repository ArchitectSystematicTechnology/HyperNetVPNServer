Roles in this directory all share a "float-" prefix to avoid collisions
with user-defined roles. They are roughly grouped into sections:

* *base* for the most low-level functionality, setting up the machines
  and preparing them to run cointainers, along with distributing the
  necessary credentials.

* *infra* for roles meant to configure specific services that are part
  of the wider float "infrastructure" (but with few exceptions run on
  top of the *base* layer, i.e. within containers etc).

* *util* for internal roles that are included by other roles, either to
  expose common functionality to user roles (geoip, mariadb instances),
  or to handle Ansible-related logic shared by multiple roles.


