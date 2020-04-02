FROM debian:stable

RUN apt-get update && apt-get install --no-install-recommends -y curl openvpn
COPY connect.sh /connect.sh

ENTRYPOINT ["/bin/sh", "/connect.sh"]

