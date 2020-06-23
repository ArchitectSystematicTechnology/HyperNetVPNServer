jacoelho.stunnel
=========

An ansible role that installs stunnel4 on Ubuntu.

Tested on ubuntu 14.04 (Trusty)

Role Variables
--------------

Each stunnel configuration is mapped to a variable (see `defaults/main.yml`)

To pin a specific stunnel version:

    stunnel_version: ""

Sample configuration:


    stunnel_cert: /etc/ssl/certs/ssl-cert-snakeoil.pem
    stunnel_key: /etc/ssl/private/ssl-cert-snakeoil.key
    stunnel_client: "yes"
    stunnel_services:
      - name: proxy
        connect: "1.2.3.4:2000"
        accept: "3000"

Dependencies
------------

None.

Example Playbook
----------------

    - hosts: servers
      roles:
        - { role: jacoelho.stunnel }

License
-------

BSD

Author Information
------------------

This role was created in 2015 by [José Coelho](https://github.com/jacoelho)
