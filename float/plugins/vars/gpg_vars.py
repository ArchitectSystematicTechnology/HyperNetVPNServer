from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    vars: gpg_vars
    version_added: "2.4"
    short_description: Loads GPG-encrypted group_vars and host_vars
    description:
        - Loads GPG-encrypted YAML vars into corresponding groups/hosts in group_vars/ and host_vars/ directories.
        - Files are restricted by extension to .yml.gpg.
        - Hidden (starting with '.') and backup (ending with '~') files and directories are ignored.
        - Only applies to inventory sources that are existing paths.
    notes:
        - It takes the place of the previously hardcoded group_vars/host_vars loading.
'''

import os
import subprocess
import yaml
from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_bytes, to_native, to_text
from ansible.plugins.vars import BaseVarsPlugin
from ansible.inventory.host import Host
from ansible.inventory.group import Group
from ansible.utils.vars import combine_vars

FOUND = {}
CACHE = {}
GPG = os.getenv('GPG', 'gpg')


def _decrypt(path):
    return subprocess.check_output([GPG, '-d', path])


class VarsModule(BaseVarsPlugin):

    def _cached_load(self, path):
        if path in CACHE:
            return CACHE[path]
        self._display.display('loading GPG vars from %s' % path)
        data = yaml.load(_decrypt(path))
        CACHE[path] = data
        return data

    def get_vars(self, loader, path, entities, cache=True):
        ''' parses the inventory file '''

        if not isinstance(entities, list):
            entities = [entities]

        super(VarsModule, self).get_vars(loader, path, entities)

        data = {}
        for entity in entities:
            if isinstance(entity, Host):
                subdir = 'host_vars'
            elif isinstance(entity, Group):
                subdir = 'group_vars'
            else:
                raise AnsibleParserError("Supplied entity must be Host or Group, got %s instead" % (type(entity)))

            # avoid 'chroot' type inventory hostnames /path/to/chroot
            if not entity.name.startswith(os.path.sep):
                try:
                    found_files = []
                    # load vars
                    opath = os.path.realpath(os.path.join(self._basedir, subdir))
                    key = '%s.%s' % (entity.name, opath)
                    if cache and key in FOUND:
                        found_files = FOUND[key]
                    else:
                        b_opath = to_bytes(opath)
                        # no need to do much if path does not exist for basedir
                        if os.path.exists(b_opath):
                            if os.path.isdir(b_opath):
                                self._display.debug("\tprocessing dir %s" % opath)
                                found_files = self._find_vars_files(opath, entity.name)
                                FOUND[key] = found_files
                            else:
                                self._display.warning("Found %s that is not a directory, skipping: %s" % (subdir, opath))

                    for found in found_files:
                        # TODO: use the loader?
                        new_data = self._cached_load(found)
                        if new_data:  # ignore empty files
                            data = combine_vars(data, new_data)

                except Exception as e:
                    raise AnsibleParserError(to_native(e))
        return data

    def _find_vars_files(self, path, name):
        """ Find {group,host}_vars files """

        b_path = to_bytes(os.path.join(path, name))
        found = []

        # first look for w/o extensions
        if os.path.isdir(b_path):
            found.extend(self._get_dir_files(to_text(b_path)))
        else:
            b_path += to_bytes('.yml.gpg')
            if os.path.exists(b_path):
                found.append(b_path)
        return found

    def _get_dir_files(self, path):

        found = []
        for spath in sorted(os.listdir(path)):
            if not spath.startswith(u'.') and not spath.endswith(u'~'):  # skip hidden and backups

                full_spath = os.path.join(path, spath)

                if os.path.isdir(full_spath):
                    found.extend(self._get_dir_files(full_spath))
                elif os.path.isfile(full_spath) and spath.endswith('.yml.gpg'):
                    # only consider files with valid extensions or no extension
                    found.append(full_spath)

        return found
