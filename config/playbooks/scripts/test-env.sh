#!/bin/bash
#
# Create a test environment using 'float create-env', then modifying
# it with some leap-specific parameters.
#

usage() {
    cat >&2 <<EOF
Usage: $0 [<options>] <dir>

Create a LEAP test environment using float. The newly created environment will
have all the necessary configuration to test the full LEAP set up, or parts of
it.

The parts to include in the test environment correspond to high-level groups
of services, and are called 'mixins'. You can combine more than one by using
the --mixin option multiple times. Available mixins currently include:

  'web' - the web hosting stack
  'vpn' - email services and account management services

Known options:

  --hosts N         Turn up N virtual machines (default: 2)
  --mixin NAME      Include mixin NAME in the test environment
  --registry HOST   Location of the docker registry
  --registry-password PASSWORD
                    Specify the password for the docker-registry-client user
                    on the specified registry to access the private
                    images
  --mitogen PATH    Location of the Mitogen source code (defaults to the
                    value of the MITOGEN environment variable as a
                    convenience for CI). When set, the generated ansible.cfg
                    will already be configured to use Mitogen's Ansible
                    plugin.
  --libvirt HOST    Configure Vagrant to use libvirt on HOST. If HOST has
                    the special value 'localhost', use the local libvirtd
                    (i.e. qemu://system).

EOF
    exit 2
}

# Get the absolute path of the testbed root directory, the one
# containing this same script.
testbed_root_dir="$(dirname "$0")"
testbed_root_dir="${testbed_root_dir:-.}"
testbed_root_dir="$(cd "$testbed_root_dir/.." && pwd)"

preflight_checks() {
  # Find the float binary.
    float_bin="${testbed_root_dir}/float/float"
    if [ ! -x "$float_bin" ]; then
        echo "The ./float/float binary does not seem to be there. Have you already run 'git submodule init' and 'git submodule update'?" >&2
        exit 1
    fi
    
    # Find required local binaries
    local_binaries="x509ca ed25519gen"
    for binary in $local_binaries; do
      path=$(command -v "$binary")
      if [ -z "$path" ]; then
        echo "Could not find $binary in \$PATH."
        echo "Make sure these commands are available: $local_binaries"
        exit 1
      fi
    done
}

preflight_checks

# Parse command-line options.
docker_registry_password=
services_mixin=common
num_hosts=2
libvirt_host=
# Attempt mitogen autodetection first, e.g. pip install mitogen in an virtual
# environment.
mitogen_path=$(python3 -c 'import ansible_mitogen.plugins.strategy as m; print m.__path__[0]' 2>/dev/null)
if [ -n "$MITOGEN" ]; then
    mitogen_path="$MITOGEN"
fi

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help)
            usage
            ;;
          
        --registry=*)
            docker_registry="${1##*=}"
            ;;
        --registry)
            docker_registry="$2"
            shift
            ;;
        
        --registry-password=*)
            docker_registry_password="${1##*=}"
            ;;
        --registry-password)
            docker_registry_password="$2"
            shift
            ;;

        --mitogen=*)
            mitogen_path="${1#*=}"
            ;;
        --mitogen)
            mitogen_path="$2"
            shift
            ;;

        --mixin=*)
            services_mixin="$services_mixin ${1#*=}"
            ;;
        --mixin)
            services_mixin="$services_mixin $2"
            shift
            ;;

        --hosts=*)
            num_hosts="${1##*=}"
            ;;
        --hosts)
            num_hosts="$2"
            shift
            ;;

        --libvirt=*)
            libvirt_host="${1#*=}"
            ;;
        --libvirt)
            libvirt_host="$2"
            shift
            ;;

        -*)
            echo "Unknown option $1" >&2
            exit 2
            ;;
        *)
            break
            ;;
    esac
    shift
done

# The output directory is the first argument.
if [ $# -lt 1 ]; then
    echo "Not enough arguments" >&2
    usage
fi
dir="$1"
if [ -e "$dir" ]; then
    echo "The output directory ${dir} already exists! Remove it if you want to re-create the test environment." >&2
    exit 1
fi

create_env_opts=
if [ -n "$mitogen_path" ]; then
    if [ ! -d "$mitogen_path" ]; then
        echo "Warning: --mitogen is set, but does not point to a directory, ignoring it" >&2
    else
        create_env_opts="--mitogen $mitogen_path"
    fi
fi
if [ -n "$libvirt_host" ]; then
    create_env_opts="$create_env_opts --libvirt $libvirt_host"
fi
create_env_opts="--domain ${DOMAIN:-float.bitmask.org} ${create_env_opts}"

"$float_bin" create-env --vagrant --num-hosts $num_hosts $create_env_opts "$dir"
if [ $? -gt 0 ]; then
    echo "ERROR, test environment creation incomplete" >&2
    exit 1
fi

# Fix the path to the testbed roles.
sed -e "s,^\\(roles_path.*\\):roles\$,\\1:${testbed_root_dir}/config/roles," -i \
    "${dir}/ansible.cfg"

# Generate the services.yml file (overwriting the one created by float
# create-env).
cat > "${dir}/services.yml" <<EOF
---

include:
  # Change to services.yml.default if you want to enable ES.
  - "${testbed_root_dir}/float/services.yml.no-elasticsearch"
EOF
for mixin in $services_mixin; do
    if [ -e "${testbed_root_dir}/config/services.${mixin}.yml" ]; then
        echo "  - \"${testbed_root_dir}/config/services.${mixin}.yml\"" \
             >> "${dir}/services.yml"
    else
        echo "WARNING: can't find mixin ${testbed_root_dir}/config/services.${mixin}.yml"
    fi
done

# Generate the passwords.yml file (overwriting the one created by
# float create-env).
cat > "${dir}/passwords.yml" <<EOF
---

- include: "${testbed_root_dir}/float/passwords.yml.default"
EOF
for mixin in $services_mixin; do
    if [ -e "${testbed_root_dir}/config/passwords.${mixin}.yml" ]; then
        echo "- include: \"${testbed_root_dir}/config/passwords.${mixin}.yml\"" \
             >> "${dir}/passwords.yml"
    else
        echo "WARNING: can't find mixin ${testbed_root_dir}/config/passwords.${mixin}.yml"
    fi
done

# Generate the site.yml file.
cat > "${dir}/site.yml" <<EOF
---

- import_playbook: "${testbed_root_dir}/float/playbooks/all.yml"
EOF
for mixin in $services_mixin; do
    if [ -e "${testbed_root_dir}/config/playbooks/${mixin}.yml" ]; then
        echo "- import_playbook: \"${testbed_root_dir}/config/playbooks/${mixin}.yml\"" \
             >> "${dir}/site.yml"
    else
        echo "WARNING: can't find mixin ${testbed_root_dir}/config/playbooks/${mixin}.yml"
    fi
done
echo "- import_playbook: \"${testbed_root_dir}/config/playbooks/testdata.yml\"" \
    >> "${dir}/site.yml"

# Disable ES/Kibana by default.
cat > "${dir}/group_vars/all/disable-elasticsearch.yml" <<EOF
---

enable_elasticsearch: false
EOF

# Write the ai3 default configuration (for SSO customization).
cat > "${dir}/group_vars/all/sso.yml" <<EOF
---

enable_keystore: true
sso_server_url: "https://accounts.{{ domain_public[0] }}/sso/"
sso_server_url_path_prefix: "/sso/"
sso_server_account_recovery_url: "/account/recovery"

sso_extra_allowed_services:
  - "[^.]+\\\\.webmail\\\\.investici\\\\.org/$"
  - "^services\\\\.investici\\\\.org/admin/$"
  - "^(imap|accountserver|mailman)\\\\.infra\\\\.investici\\\\.org/$"

sso_allowed_exchanges:
  - src_regexp: "^[^.]+\\\\.webmail\\\\.({{ domain_public | join('|') }})/$"
    dst_regexp: "^imap\\\\.{{ domain | regex_escape }}/$"
  - src_regexp: "^accounts\\\\.({{ domain_public | join('|') }})/$"
    dst_regexp: "^(accountserver|mailman)\\\\.{{ domain | regex_escape }}/$"
  - src_regexp: "^accountadmin\\\\.({{ domain_public | join('|') }})/$"
    dst_regexp: "^(accountserver|mailman)\\\\.{{ domain | regex_escape }}/$"
  - src_regexp: "^services\\\\.({{ domain_public | join('|') }})/admin/$"
    dst_regexp: "^accountserver\\\\.{{ domain | regex_escape }}/$"


EOF

# Set the DKIM selector to be the one used by ai-scripts.
cat > "${dir}/group_vars/all/dkim.yml" <<EOF
---

dkim_selector: stigmate
EOF

# Filesystem space savings
cat > "${dir}/group_vars/all/doublespace.yml" <<EOF
---

es_log_keep_days:
  audit: 2
  logstash: 2
  http: 2
prometheus_tsdb_retention: 2d
mariadb_innodb_log_file_size: 20M
log_collector_retention_days: 2
EOF


# Write the Docker registry configuration, with its secret auth token.
if [ -n "$docker_registry_password" ]; then
    (umask 077 ; cat > "${dir}/group_vars/all/docker.yml" <<EOF
---

docker_registry_url: "https://registry.git.autistici.org"
docker_registry_username: "docker-registry-client"
docker_registry_password: "${docker_registry_password}"

EOF
     )
fi

# Generate an apt proxy configuration if we have apt-cacher-ng
# installed locally. In order to do so, we have to parse the host
# network randomly assigned by 'float create-env'.
net_autodetect=$(awk '$1 == "ip:" {print $2}' < "${dir}/hosts.yml" | head -1 | cut -d. -f1-3)
#if [ -e /usr/sbin/apt-cacher-ng ] || [ -n "$libvirt_host" ]; then
#    # The local host will be reachable at the IP address ${network}.1
#    apt_proxy_ip="${net_autodetect}.1"
#    echo "apt_proxy: ${apt_proxy_ip}:3142" \
#         > "${dir}/group_vars/all/apt_proxy.yml"
#    echo "Auto-configured apt proxy at ${apt_proxy_ip}:3142"
#fi

# Generate an Ansible Vault password for the test environment.
echo testpass > "${dir}/.ansible_vault_pw"

# Install the test DH parameters, which is going to save a lot of time
# during init-credentials.
mkdir -p "${dir}/credentials/x509"
cp "${testbed_root_dir}/float/test/dhparam.test" "${dir}/credentials/x509/dhparam"

# Create a script to run tests.
cat > ${dir}/run-tests <<EOF
#!/bin/sh
set -e
${testbed_root_dir}/float/float run ${testbed_root_dir}/float/test/integration-test-docker.yml
${testbed_root_dir}/float/float run ${testbed_root_dir}/config/playbooks/ai3-test.yml
EOF
chmod a+x ${dir}/run-tests

# Create a script to start a test browser.
cat > ${dir}/test-browser <<EOF
#!/bin/sh
exec ${testbed_root_dir}/test-browser --proxy ${net_autodetect}.10:9051 "\$@"
EOF
chmod a+x ${dir}/test-browser

if [ -n "$libvirt_host" ]; then
    vagrant_up="vagrant up --provider libvirt"
else
    vagrant_up="vagrant up"
fi

# Print a friendly summary to the user.
cat > ${dir}/README.md <<EOF

Your test environment in ${dir} is now set up!

Run the following commands to use it:

    cd ${dir}
    export ANSIBLE_VAULT_PASSWORD_FILE=.ansible_vault_pw
    export ANSIBLE_HOST_KEY_CHECKING=False
    ${testbed_root_dir}/float/float run playbooks/init-credentials
    ${vagrant_up}
    ${testbed_root_dir}/float/float run site.yml

You will then be able to browse the live services on your test
instance by running:

    ${dir}/test-browser https://admin.investici.org/

The default admin account is 'admin' with password 'password'.

To run the test suite, ensure the python-nose package is installed,
and run:

    ${dir}/run-tests

EOF

cat ${dir}/README.md
echo
echo "You can find these instructions at ${dir}/README.md"


exit 0
