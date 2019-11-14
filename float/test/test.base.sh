#!/bin/sh

# Test that the 'okserver' works via its public_endpoint.
resp=$(curl --verbose --insecure \
            --resolve ok.example.com:443:192.168.10.10 \
            https://ok.example.com/)
if [ "${resp}" != "OK" ]; then
    echo "ERROR: bad response from ok.example.com" >&2
    exit 1
fi

exit 0
