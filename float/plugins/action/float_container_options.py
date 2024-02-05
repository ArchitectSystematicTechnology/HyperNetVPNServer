from ansible.plugins.action import ActionBase


TMPFS_FLAGS = 'tmpfs-mode=01777'
DEFAULT_TMPFS_SIZE = '64M'


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    # Options to set the container environment.
    def _environment_options(self, service, container):
        service_name = service['name']
        hostname = self._templar.template('{{ inventory_hostname }}')
        domain = self._templar.template('{{ domain }}')

        env = {
            'FLOAT_SERVICE': f'{service_name}.{domain}',
            'FLOAT_INSTANCE_NAME': f'{hostname}.{service_name}.{domain}',
            'FLOAT_CONTAINER_IMAGE': container['image'],
            'FLOAT_CONTAINER_NAME': f'{service_name}-{container["name"]}',
        }
        if 'env' in container:
            env.update(container['env'])

        options = []
        for key, value in sorted(env.items()):
            options.append(f'--env={key}={value}')
        return options

    # Options for volumes (tmpfs, bind mounts).
    def _mount_options(self, service, container):
        options = []
        add_tmpfs = True

        def _bind(src, dst):
            options.append(f'--mount=type=bind,source={src},destination={dst}')

        def _tmpfs(dst, flags=None):
            opt = f'--mount=type=tmpfs,destination={dst},{TMPFS_FLAGS}'
            if flags:
                opt += f',{flags}'
            options.append(opt)

        if container.get('readonly', True):
            options.append('--read-only')
            add_tmpfs = False

        for vol in container.get('volumes', []):
            for src, dst in sorted(vol.items()):
                if dst == '/tmp':
                    add_tmpfs = False
                if src == 'tmpfs':
                    _tmpfs(dst, f'tmpfs-size={DEFAULT_TMPFS_SIZE}')
                elif src.startswith('tmpfs/'):
                    sz = src[6:]
                    _tmpfs(dst, f'tmpfs-size={sz}')
                else:
                    _bind(src, dst)
        _tmpfs('/run', 'tmpfs-size=16M,exec=true,notmpcopyup')
        _bind('/dev/log', '/dev/log')
        _bind('/etc/credentials/system', '/etc/ssl/certs')
        if add_tmpfs:
            _tmpfs('/tmp', f'tmpfs-size={DEFAULT_TMPFS_SIZE},notmpcopyup')

        for creds in service.get('service_credentials', []):
            creds_name = creds['name']
            ca_tag = creds.get('ca_tag', 'x509')
            creds_path = f'/etc/credentials/{ca_tag}/{creds_name}'
            _bind(creds_path, creds_path)

        return options

    # Network options (ports).
    def _network_options(self, container):
        options = ['--network=host']
        ports = []
        if 'ports' in container:
            ports = container['ports']
        elif 'port' in container:
            ports = [container['port']]
        for port in sorted(ports):
            options.append(f'--expose={port}')
        return options

    def run(self, tmp=None, task_vars=None):
        service = self._task.args['service']
        container = self._task.args['container']

        options = []

        options.extend(self._environment_options(service, container))
        options.extend(self._mount_options(service, container))
        options.extend(self._network_options(container))

        is_root = container.get('root')
        if container.get('drop_capabilities', not is_root):
            options.append('--security-opt=no-new-privileges')
            options.append('--cap-drop=all')

        if 'docker_options' in container:
            options.extend(container['docker_options'].split())

        result = super().run(tmp, task_vars)
        result['options'] = options
        result['changed'] = False
        return result
