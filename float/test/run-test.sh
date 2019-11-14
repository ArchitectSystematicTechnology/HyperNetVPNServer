#!/bin/bash

# Find the absolute path to this script's directory
# (so that we can find the 'float' root dir).
bin_dir=$(dirname "$0")
bin_dir=${bin_dir:-.}
bin_dir=$(cd "${bin_dir}" && pwd)
float_dir="${bin_dir}/.."

# Used for all ansible/float invocations.
export ANSIBLE_VAULT_PASSWORD_FILE=".ansible_vault_pw"
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_STDOUT_CALLBACK=actionable

die() {
    echo "ERROR: $*" >&2
    exit 1
}

clean() {
    rm -f group_vars/all/secrets.yml
    rm -f group_vars/all/apt-proxy.yml
    rm -f ansible.log
    rm -fr conf
    stop_vagrant
}

start_vagrant() {
    # Ignore errors on update.
    vagrant box update
    vagrant up ${LIBVIRT:+--provider libvirt} \
        || die "could not start virtual machines"
}

stop_vagrant() {
    pushd $test_dir
    vagrant destroy -f
    popd
}

check_hosts_ready() {
    # Wait at most 30 seconds for the vms to become reachable.
    local i=0
    while [ $i -lt 10 ]; do
        sleep 3
        ansible -v -i config.yml all -m ping && break
        i=$(($i + 1))
    done
    [ $i -eq 10 ] && die "could not reach virtual machines over SSH"
}

setup_ansible_env() {
    test -e create-env.${test_name}.sh \
         || die "there is no setup script for test environment $name"
    ./create-env.${test_name}.sh ${test_dir} \
         ${LIBVIRT:+--libvirt=${LIBVIRT}} \
         ${MITOGEN:+--mitogen=${MITOGEN}} \
         || die "error creating test environment"

    if [ -n "${apt_proxy}" ]; then
        cat > ${test_dir}/group_vars/all/apt-proxy.yml <<EOF
---
apt_proxy: ${apt_proxy}
apt_proxy_enable_https: true
EOF
    fi

    # Install a test dhparam file to save some time.
    mkdir -p ${test_dir}/credentials/x509
    cp ${bin_dir}/dhparam.test ${test_dir}/credentials/x509/dhparam

    # Create a test ansible vault password.
    echo test-passphrase > ${test_dir}/.ansible_vault_pw
}

run_ansible() {
    ../../float run init-credentials \
        || die "failed to run the init-credentials playbook"
    ../../float run site.yml \
        || die "failed to run the site.yml playbook"
}

run_integration_test() {
    local mode="$1"

    # Give the system some time to stabilize.
    sleep ${wait_time}

    # The following is required to make the test output readable.
    ANSIBLE_DISPLAY_FAILED_STDERR=True \
    ANSIBLE_STDOUT_CALLBACK=unixy \
    ../../float run ${bin_dir}/integration-test-${mode}.yml \
        || die "failed to run the integration tests"
}

usage() {
    cat <<EOF
Usage: $0 [<options>] <test-dir>

Executes a Vagrant-based test of the Ansible configuration
contained in 'test-dir'.

Known options:
  --local           Run tests on this machine (exclusive with --docker).
  --docker          Run tests on the cluster using a Docker container.
  --keep            Do not destroy the VMs after running tests.
  --apt-proxy ADDR  Use the specified APT proxy (host:port).
  --wait-time SECS  Wait some time before running tests (default: 30 seconds).
  --help            Print this help message.

Environment variables can also be used to control the runtime setup:

* Setting MITOGEN to the Mitogen source path will configure Ansible to
  use the Mitogen plugin.

* Setting LIBVIRT to a qemu socket path (potentially remote) will
  configure Vagrant to use the libvirt provider instead of the default
  virtualbox one. The special value 'localhost' makes it use the local
  libvirtd.

* The --apt-proxy option can also be passed as the APT_PROXY
  environment variable.

* The MODE variable can be set to either 'local' or 'docker and has
  the same effect as passing the --local or --docker options.

For convenience when integrating with CI systems, if the environment
variable FLOAT_TEST_SSH_PRIVATE_KEY is set, its contents are assumed
to be a SSH private key: the test runner will start a new SSH agent,
and load the key into it.

EOF
}

keep_vms=0
apt_proxy=${APT_PROXY:-}
wait_time=30
mode=${MODE:-local}
while [ $# -gt 0 ]; do
    case "$1" in
        --keep)
            keep_vms=1
            ;;
        --apt-proxy)
            shift
            apt_proxy="$1"
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --wait-time)
            shift
            wait_time="$1"
            ;;
        --local)
            mode=local
            ;;
        --docker)
            mode=docker
            ;;
        -*)
            echo "Unknown option '$1'" >&2
            usage >&2
            exit 2
            ;;
        *)
            break
            ;;
    esac
    shift
done

test_name="$1"
if [ -z "${test_name}" ]; then
    usage >&2
    exit 2
fi
# Small provision for compatibility: drop the test- prefix.
case $test_name in
    test-*)
        test_name=${test_name#test-}
        ;;
esac
test_dir="${PWD}/test-${test_name}"

# Set up our SSH private key if necessary.
if [ -n "${FLOAT_TEST_SSH_PRIVATE_KEY}" ]; then
    eval `ssh-agent -s`
    ( umask 077 ;
      mkdir /tmp/priv-$$ ;
      echo "${FLOAT_TEST_SSH_PRIVATE_KEY}" > /tmp/priv-$$/key ;
      ssh-add /tmp/priv-$$/key ;
      rm -f /tmp/priv-$$/key )
fi

if [ ${keep_vms} -eq 0 ]; then
    trap "stop_vagrant; rm -fr \"$test_dir\"" EXIT SIGINT SIGTERM
fi

setup_ansible_env

pushd $test_dir
clean
start_vagrant
check_hosts_ready
run_ansible
run_integration_test ${mode}
popd

# Execute the env-specific tests, if any.
if [ -e test.${test_name}.sh ]; then
    ./test.${test_name}.sh \
        || die "env-specific test suite failed"
fi

# Set up our SSH private key if necessary.
if [ -n "${FLOAT_TEST_SSH_PRIVATE_KEY}" ]; then
    ssh-agent -k
fi

exit 0
