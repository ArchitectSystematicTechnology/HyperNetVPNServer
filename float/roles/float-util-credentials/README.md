credentials
===

Ansible role that installs all the [service
credentials](../docs/service_mesh.md#mutual-service-authentication) on
the hosts where they're needed. This role works in combination with
the 'x509' action plugin.

Private keys never leave the target host, we create a CSR and sign it
on the Ansible host.

X509 credentials are stored in /etc/credentials/x509 under directories
named after the services. Every service directory contains a copy of
the public CA certificate, so it can be bind-mounted in a container
easily.

Private keys have mode 440, are owned by root and by a dedicated group
named *service*-credentials. When the service is actually installed,
later, maybe by an Ansible role, it can add the service user to this
group.

Use by including this role and setting the *credentials* variable to a
list of entries specifying the desired credentials. This is already
done once system-wide by the *float-credentials* role with the
credentials automagically derived from the service definitions by
*float*.
