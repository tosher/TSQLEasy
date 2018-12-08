#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from .base import *
from .base import te_utils as utils

# TODO: Get procedures (functions) list (with params)
# TODO: Completions to TSQL operators
# TODO: Processes, locks, etc..


class TsqlEasyEventDump(sublime_plugin.EventListener):

    def on_load(self, view):
        if self.check_tab(view):
            utils.te_reload_aliases_from_file()

    def on_activated(self, view):
        if self.check_tab(view):
            utils.te_reload_aliases_from_file()

    def check_tab(self, view):
        title = utils.te_get_title()
        if title and title.endswith('.sql'):
            return True
        return False

    def _is_alias(self, val):
        ''' check string is table alias '''
        utils.te_reload_aliases_from_file()
        if not utils.global_alias.get_alias(val.lower()):
            return False
        return True

    def on_query_completions(self, view, prefix, locations):
        # auto_completions = [view.extract_completions(prefix)]
        if self.check_tab(view):
            view = sublime.active_window().active_view()
            position = view.sel()[0].begin()
            word_cursor = view.substr(view.word(position)).strip('\n').strip()
            pre_position = position - len(word_cursor) - 1
            pre_word_char = view.substr(pre_position).strip('\n').strip()

            word_before = None
            if word_cursor == u'.':
                word_before = view.substr(view.word(position - 1))
                position = position - 1
            elif pre_word_char == u'.':
                word_before = view.substr(view.word(pre_position))
                position = pre_position

            infocls = utils.te_sql_info()
            if word_before is not None:
                if self._is_alias(word_before):
                    return (infocls.get_columns(infocls.table_name_from_position(position)))
                else:
                    return (infocls.get_tables(word_before))
            else:
                return (infocls.get_tables())
