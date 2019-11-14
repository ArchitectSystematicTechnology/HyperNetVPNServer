credentials
===

Ansible role that installs all the [service
credentials](../docs/service_mesh.md#mutual-service-authentication) on
the hosts where they're needed.

Private keys never leave the target host, we create a CSR and sign it
on the Ansible host.
