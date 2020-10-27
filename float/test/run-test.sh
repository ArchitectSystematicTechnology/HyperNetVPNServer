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
export ANSIBLE_STDOUT_CALLBACK=unixy

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
    create_env_cmd=$(PATH=$PATH:. command -v create-env.${test_name}.sh)
    test -n "$create_env_cmd" \
         || die "there is no setup script for test environment $name"
    ${create_env_cmd} ${test_dir} \
         --net ${private_network} \
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
    ${float_dir}/float run init-credentials \
        || die "failed to run the init-credentials playbook"
    ${float_dir}/float run site.yml \
        || die "failed to run the site.yml playbook"
}

run_integration_test() {
    local mode="$1"

    # Give the system some time to stabilize.
    sleep ${wait_time}

    # The following is required to make the test output readable.
    ANSIBLE_DISPLAY_FAILED_STDERR=True \
    ANSIBLE_STDOUT_CALLBACK=unixy \
    ${float_dir}/float run ${bin_dir}/integration-test-${mode}.yml \
        || die "failed to run the integration tests"
}

save_logs() {
    local test_dir="$1"
    local out_dir="$2"

    pushd $test_dir
    ANSIBLE_STDOUT_CALLBACK=unixy \
    ${float_dir}/float run --extra-vars "out_dir=$out_dir" \
        ${bin_dir}/save-logs.yml
    popd
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
  --network ADDR    Use the given private network (default: pick one at random
                    in the 10.0.0.0/8 range). ADDR must end in '.0' as the
                    network is always a /24.
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

EOF
}

keep_vms=0
apt_proxy=${APT_PROXY:-}
wait_time=30
mode=${MODE:-local}
private_network="10.$(( 1 + ($RANDOM % 254) )).$(( 1 + ($RANDOM % 254) )).0"
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
        --network)
            private_network="$1"
            ;;
        --save-logs)
            shift
            save_logs="$1"
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

if [ -n "$TEST_DIR" ]; then
    test_dir="${TEST_DIR}"
else
    test_dir="${PWD}/test-${test_name}"
fi

cleanup_cmd=""

if [ -n "${save_logs}" ]; then
    cleanup_cmd="save_logs \"$test_dir\" \"$save_logs\";"
fi

if [ ${keep_vms} -eq 0 ]; then
    cleanup_cmd="${cleanup_cmd} stop_vagrant; rm -fr \"$test_dir\";"
fi

trap "$cleanup_cmd" EXIT SIGINT SIGTERM

setup_ansible_env

pushd $test_dir
clean
start_vagrant
check_hosts_ready
run_ansible
run_integration_test ${mode}
popd

# Execute the env-specific tests, if any.
test_cmd=$(PATH=$PATH:. command -v test.${test_name}.sh)
if [ -n "$test_cmd" ]; then
    export NETWORK=${private_network}
    export TEST_DIR=${test_dir}
    $test_cmd \
        || die "env-specific test suite failed: $test_cmd"
fi

exit 0
