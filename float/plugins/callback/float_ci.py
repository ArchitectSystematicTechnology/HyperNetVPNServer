# Original source at https://github.com/systemli/ansible-drift/raw/master/callback_plugins/actionable.py
# (c) 2015, Andrew Gaffney <andrew@agaffney.org>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    callback: actionable
    type: stdout
    short_description: shows only items that need attention
    description:
      - Use this callback when you dont care about OK nor Skipped.
      - This callback suppresses any non Failed or Changed status.
    version_added: "2.1"
    extends_documentation_fragment:
      - default_callback
    requirements:
      - set as stdout callback in configuration
'''

import collections
import time

from ansible.plugins.callback.default import CallbackModule as CallbackModule_default


def timestamp(self):
    if self.current is not None:
        self.stats[self.current]['time'] = time.time() - self.stats[self.current]['time']


class CallbackModule(CallbackModule_default):

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'ci'

    def __init__(self):
        self.super_ref = super(CallbackModule, self)
        self.super_ref.__init__()
        self.last_play = None
        self.last_task = None
        self.shown_play = False
        self.shown_title = False
        self.anything_shown = False

        self.stats = collections.OrderedDict()
        self.current = None

    # This comes from profile_tasks.py
    def _record_task(self, task):
        """
        Logs the start of each task
        """
        timestamp(self)

        # Record the start time of the current task
        self.current = task._uuid
        self.stats[self.current] = {'time': time.time(), 'name': task.get_name()}
        if self._display.verbosity >= 2:
            self.stats[self.current]['path'] = task.get_path()

    # This comes from debug.py
    def _dump_results(self, result, indent=None, sort_keys=True, keep_invocation=False):
        '''Return the text to output for a result.'''

        # Enable JSON identation
        result['_ansible_verbose_always'] = True

        save = {}
        for key in ['stdout', 'stdout_lines', 'stderr', 'stderr_lines', 'msg', 'module_stdout', 'module_stderr']:
            if key in result:
                save[key] = result.pop(key)

        output = CallbackModule_default._dump_results(self, result)

        for key in ['stdout', 'stderr', 'msg', 'module_stdout', 'module_stderr']:
            if key in save and save[key]:
                output += '\n\n%s:\n\n%s\n' % (key.upper(), save[key])

        for key, value in save.items():
            result[key] = value

        return output

    def v2_playbook_on_play_start(self, play):
        self._play = play
        self.last_play = play
        self.shown_play = False

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.last_task = task
        self.shown_title = False
        self._record_task(task)

    def v2_playbook_on_handler_task_start(self, task):
        self.super_ref.v2_playbook_on_handler_task_start(task)
        self.shown_title = True
        self._record_task(task)

    def display_task_banner(self):
        if not self.shown_play:
            self.super_ref.v2_playbook_on_play_start(self.last_play)
            self.shown_play = True
        if not self.shown_title:
            self.super_ref.v2_playbook_on_task_start(self.last_task, None)
            self.shown_title = True
        self.anything_shown = True

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if ignore_errors:
            return
        self.display_task_banner()
        self.super_ref.v2_runner_on_failed(result, ignore_errors)

    def v2_runner_on_ok(self, result):
        pass

    def v2_runner_on_unreachable(self, result):
        self.display_task_banner()
        self.super_ref.v2_runner_on_unreachable(result)

    def v2_runner_on_skipped(self, result):
        pass

    def v2_playbook_on_no_hosts_matched(self):
        pass

    def v2_playbook_on_include(self, included_file):
        pass

    def v2_playbook_on_stats(self, stats):
        if self.anything_shown:
            self.super_ref.v2_playbook_on_stats(stats)

        self._display.display("Task timings:")

        timestamp(self)

        # Sort the tasks
        results = sorted(
            self.stats.items(),
            key=lambda x: x[1]['time'],
            reverse=True,
        )

        # Display the top tasks
        results = results[:30]

        # Print the timings
        for uuid, result in results:
            msg = u"{0:-<{2}}{1:->9}".format(result['name'] + u' ', u' {0:.02f}s'.format(result['time']), self._display.columns - 9)
            if 'path' in result:
                msg += u"\n{0:-<{1}}".format(result['path'] + u' ', self._display.columns)
            self._display.display(msg)

    def v2_on_file_diff(self, result):
        if 'diff' in result._result and result._result['diff'] and result._result.get('changed', False):
            diff = self._get_diff(result._result['diff'])
            if diff:
                self.display_task_banner()
                self._display.display(diff)

    def v2_runner_item_on_ok(self, result):
        pass

    def v2_runner_item_on_skipped(self, result):
        pass

    def v2_runner_item_on_failed(self, result):
        self.display_task_banner()
        self.super_ref.v2_runner_item_on_failed(result)

    def _print_task_banner(self, task):
        task_banner = U"TASK [%s]" % task.get_name().strip()
        self._display.banner(task_banner)
        self._last_task_banner = self.last_task._uuid
