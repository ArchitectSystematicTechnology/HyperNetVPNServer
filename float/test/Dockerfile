FROM debian:stable

RUN apt-get -q update && env DEBIAN_FRONTEND=noninteractive \
    apt-get install --no-install-recommends -y python python-pip python-setuptools python-yaml python-nose

ADD . /src
WORKDIR /src
RUN python setup.py install

ENV TEST_CONFIG=/test-config.yml
ENV TEST_PARAMS=/src/float_integration_test/test-params.yml
CMD ["nosetests", "-v", "float_integration_test"]
