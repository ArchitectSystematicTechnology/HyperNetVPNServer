Test Docker image that runs an OpenVPN client using the float-pt provider.

Build it with:

    $ docker build -t float-pt-openvpn-test .

Run it with:

    $ docker run --rm -it --sysctl=net.ipv6.conf.all.disable_ipv6=0 --cap-add=NET_ADMIN \
        float-pt-openvpn-test 10.121.20.11

Replace the IP with the one you want to test.
