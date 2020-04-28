FROM debian:stable

RUN apt-get -q update && env DEBIAN_FRONTEND=noninteractive \
    apt-get install --no-install-recommends -y python3 python3-pip python3-setuptools python3-yaml python3-jinja2 python3-nose

ADD . /src
WORKDIR /src
RUN python3 setup.py install

ENV TEST_CONFIG=/test-config.yml
ENV TEST_PARAMS=/src/float_integration_test/test-params.yml
CMD ["nosetests3", "-v", "float_integration_test"]
