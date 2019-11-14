#!/bin/sh

set -e

../float create-env --vagrant --num-hosts 2 --domain example.com --net 192.168.10.0 "$@"

cat > "$1/services.yml" <<EOF
---

include:
  - "../../services.yml.no-elasticsearch"

ok:
  scheduling_group: backend
  containers:
    - name: http
      image: registry.git.autistici.org/ai3/docker/okserver:latest
      port: 3100
      env:
        PORT: 3100
      resources:
        ram: 1g
        cpu: 0.5
  public_endpoints:
    - name: ok
      port: 3100
      scheme: http

EOF

cat > "$1/passwords.yml" <<EOF
---

- include: ../../passwords.yml.default

EOF

cat > "$1/group_vars/all/disable-elasticsearch.yml" <<EOF
---

enable_elasticsearch: false
EOF

exit 0
