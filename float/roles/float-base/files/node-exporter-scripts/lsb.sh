#!/bin/sh

id=$(lsb_release --short --id | tr A-Z a-z)
codename=$(lsb_release --short --codename)
version=0
if [ -e /etc/debian_version ]; then
    version=$(cat /etc/debian_version)
fi
echo "node_lsb_release{id=\"${id}\",codename=\"${codename}\",version=\"${version}\"} 1"

exit 0
