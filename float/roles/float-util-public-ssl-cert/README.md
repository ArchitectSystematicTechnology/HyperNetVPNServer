public-ssl-cert
===

This role ensures that a SSL certificate for the specified public
domain exists. On the first run of Ansible, it will simply install a
self-signed certificate. It is expected that ACME (not configured by
this role!) will eventually replace it with a valid certificate.
