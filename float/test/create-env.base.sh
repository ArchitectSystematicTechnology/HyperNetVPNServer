#!/bin/sh

set -e

../float create-env --vagrant --num-hosts 1 --domain example.com "$@"

cat > "$1/services.yml" <<EOF
---

frontend:
  scheduling_group: frontend
  service_credentials:
    - name: nginx
      enable_server: false
    - name: ssoproxy
      enable_server: false
    - name: replds-acme
  systemd_services:
    - nginx.service
    - sso-proxy.service
    - bind9.service
    - replds@acme.service
  ports:
    - 5005

ok:
  scheduling_group: all
  num_instances: 1
  containers:
    - name: http
      image: registry.git.autistici.org/ai3/docker/okserver:latest
      port: 3100
      env:
        PORT: 3100
  public_endpoints:
    - name: ok
      port: 3100
      scheme: http

EOF

cat > "$1/passwords.yml" <<EOF
- name: ssoproxy_session_auth_key
  description: sso-proxy cookie authentication key
  type: binary
  length: 64
- name: ssoproxy_session_enc_key
  description: sso-proxy cookie encryption key
  type: binary
  length: 32
- name: dnssec_nsec3_salt
  description: Salt used by dnssec-signzone for NSEC3 replies (public,
    recommended to be rotated occasionally)
  type: binary
  length: 32
EOF

exit 0
