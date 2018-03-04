#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasySetActiveServerCommand(sublime_plugin.WindowCommand):
    server_keys = []
    server_on = '>'
    server_off = ' ' * 3
    server_active = ''

    def run(self):
        self.server_active = utils.te_get_setting('te_server_active', 'Offline')
        servers = utils.te_get_setting('te_sql_server')
        self.server_keys = [self.is_active(x) for x in servers.keys()]
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.server_keys, self.on_done), 1)

    def is_active(self, server_key):
        checked = self.server_on if server_key == self.server_active else self.server_off
        return '%s %s' % (checked, server_key)

    def on_done(self, index):
        if index >= 0 and not self.server_keys[index].startswith(self.server_on):
            utils.te_set_setting("te_server_active", self.server_keys[index].strip())


