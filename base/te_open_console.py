#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import tempfile
import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasyOpenConsoleCommand(sublime_plugin.WindowCommand):

    def run(self):
        prefix = 'Console_'
        tf = tempfile.NamedTemporaryFile(mode='w+t', suffix='.sql', prefix=prefix, dir=None, delete=True)
        new_view = sublime.active_window().open_file(tf.name)

        new_view.set_syntax_file(utils.te_get_setting('te_syntax', utils.DEFAULT_SYNTAX))
        new_view.settings().set('tsqleasy_is_here', True)

        new_view.settings().set("word_wrap", False)
        new_view.set_line_endings('unix')
        tf.close()
