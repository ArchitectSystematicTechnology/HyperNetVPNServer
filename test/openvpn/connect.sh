#!/bin/sh

api_server=${API_SERVER:-api.float.bitmask.net}

ip=${1}
port=${2:-1194}
api_ip=${3:-${ip}}

# Create a temporary directory with certificates.
tmpdir=$(mktemp -d)
trap "rm -fr ${tmpdir}" EXIT

set -ex

mkdir -p /dev/net
if [ ! -c /dev/net/tun ]; then
    mknod /dev/net/tun c 10 200
fi

/sbin/ip a s
/sbin/ip r s

cd ${tmpdir}
curl -vskL -o cacert.pem --resolve ${api_server}:443:${api_ip} https://${api_server}/ca.crt
curl -vskL -o openvpn.pem --resolve ${api_server}:443:${api_ip} https://${api_server}/3/cert

openvpn --setenv LEAPOPENVPN 1 --nobind --dev tun --client \
	--tls-client --remote-cert-tls server --script-security 1 \
	--tls-version-min 1.2 --cipher AES-256-GCM --keepalive 10 30 \
	--tls-cipher TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384 --auth SHA512 \
	--ca cacert.pem --cert openvpn.pem --key openvpn.pem \
	--persist-key --persist-local-ip \
	--ignore-unknown-option block-outside-dns \
	--verb 3 --remote ${ip} ${port} tcp4

