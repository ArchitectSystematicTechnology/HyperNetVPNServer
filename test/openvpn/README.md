Test Docker image that runs an OpenVPN client using the float-pt provider.

Build it with:

    $ docker build -t float-pt-openvpn-test .

Run it with:

    $ docker run --rm -it --sysctl=net.ipv6.conf.all.disable_ipv6=0 --cap-add=NET_ADMIN \
        float-pt-openvpn-test 10.121.20.11

Replace the IP with the one you want to test.


# Notes

The test uses a custom Go binary because we haven't found an easy way to
just run a shell script after openvpn has established a connection. Instead
we talk to the openvpn client over its management connection in order to
detect the CONNECTED state, and then try to ping a remote test IP.

If using vagrant to run test machines with float deployed, the docker
container needs to be able to connect to the vagrant network, otherwise you will
get:

     connect to 10.121.20.11 port 443 failed: Connection refused

One crude way to do that is to insert a FORWARD iptables rule, like the following:

    # iptables -I FORWARD -s 0.0.0.0/0 -d 10.121.20.0/24 -j ACCEPT


