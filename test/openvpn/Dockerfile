FROM golang:latest AS build

COPY ovpnctl.go /build/
RUN cd /build && go build -tags netgo -o ovpnprobe ovpnprobe.go

FROM debian:stable

RUN apt-get update && apt-get install --no-install-recommends -y curl openvpn
COPY --from=build /build/ovpnprobe /ovpnprobe
COPY connect.sh /connect.sh

ENTRYPOINT ["/bin/sh", "/connect.sh"]

