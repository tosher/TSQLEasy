#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import os.path
import tempfile
import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasyOpenServerObjectCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        position = self.view.sel()[0].begin()
        word_region = self.view.word(position)
        word_cursor = self.view.substr(word_region).strip('\n').strip()

        chars_before_region = sublime.Region(word_region.a - 1, word_region.a)
        chars_before = self.view.substr(chars_before_region).strip()

        if chars_before == u'.':
            while not chars_before.startswith((' ', '\n')):
                chars_before_region = sublime.Region(chars_before_region.a - 1, chars_before_region.b)
                chars_before = self.view.substr(chars_before_region)
            chars_before = chars_before.strip()

        if chars_before:
            word_cursor = ''.join([chars_before, word_cursor])

        sqlreq = "exec sp_helptext @objname = ?"
        sqlcon = utils.te_get_connection()
        if sqlcon.sqlconnection is not None:
            sqlcon.dbexec(sqlreq, [word_cursor])
            text = ''
            if sqlcon.sqldataset:
                text = ''.join([row.Text for row in sqlcon.sqldataset])
                # if pythonver < 3:
                #     text = text.encode('utf-8')

            sqlcon.dbdisconnect()
            if text:
                prefix = '%s_tmp_' % word_cursor
                with tempfile.NamedTemporaryFile(mode='w+t', suffix='.sql', prefix=prefix, dir=None, delete=True) as tf:

                    tf.write(text.replace('\r', ''))
                    tf.seek(0)
                    if os.path.exists(tf.name):
                        new_view = self.view.window().open_file(tf.name)

                        new_view.set_syntax_file(utils.te_get_setting('te_syntax', utils.DEFAULT_SYNTAX))
                        new_view.settings().set('tsqleasy_is_here', True)
                        new_view.set_line_endings('unix')
        else:
            self.view.window().status_message('No connection to SQL server')
