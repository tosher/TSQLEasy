#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import os.path
import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasyOpenLocalObjectCommand(sublime_plugin.TextCommand):
    proc_dirs = []
    filename = ''
    filename_abs_path = ''

    def run(self, view):
        path = os.path.dirname(os.path.abspath(self.view.file_name()))
        position = self.view.sel()[0].begin()
        word_cursor = self.view.substr(self.view.word(position)).strip('\n').strip()
        self.filename = '%s.sql' % word_cursor
        if self.is_path(path):
            self.get_proc(path)
        else:
            sublime.status_message('File [%s] does not exists in dir [%s]' % (self.filename, path))
            self.on_select()

    def on_select(self):
        self.proc_dirs = list(utils.te_get_setting('te_procedure_path'))
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.proc_dirs, self.on_done), 1)

    def on_done(self, dir_index):
        path = self.proc_dirs[dir_index]
        if self.is_path(path):
            self.get_proc(path)
        else:
            sublime.status_message('File [%s] does not exists in dir [%s]' % (self.filename, path))
            print('File [%s] does not exists in dir [%s]' % (self.filename, path))

    def is_path(self, path):
        self.filename_abs_path = '%s\\%s' % (path, self.filename)
        if path and os.path.isfile(self.filename_abs_path):
            return True
        else:
            return False

    def get_proc(self, path):
        sublime.active_window().open_file(self.filename_abs_path)
        self.view.set_syntax_file(utils.te_get_setting('te_syntax', utils.DEFAULT_SYNTAX))
        self.view.settings().set('tsqleasy_is_here', True)
