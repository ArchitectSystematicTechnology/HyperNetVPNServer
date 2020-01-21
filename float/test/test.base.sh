#!/bin/sh

# Our target is the .10 IP.
addr=$(echo $NETWORK | sed -e 's/\.[0-9]*$/.10/')

# If we are in a remote libvirt environment, run the
# curl command on the jumphost.
runcmd=
if [ -n "$LIBVIRT" -a "$LIBVIRT" != "localhost" ]; then
    runcmd="ssh $LIBVIRT"
fi

# Test that the 'okserver' works via its public_endpoint.
resp=$(${runcmd} curl --verbose --insecure \
            --resolve ok.example.com:443:${addr} \
            https://ok.example.com/)
if [ "${resp}" != "OK" ]; then
    echo "ERROR: bad response from ok.example.com" >&2
    exit 1
fi

exit 0
