#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import re
import hashlib
import time
import os.path
from datetime import datetime
import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import sqlodbccon
else:
    import sqlodbccon


class SQLAlias():
    aliases = {}
    text_hash = ''

    def __init__(self):
        pass

    def set_alias(self, alias, name):
        if alias not in self.aliases or self.aliases[alias] != name:
            self.aliases[alias] = name

    def get_alias(self, alias):
        # print('alias is %s' % alias)
        if alias in self.aliases:
            return self.aliases[alias]
        else:
            return ''

    def alias_list(self):
        for alias in self.aliases:
            print('[%s] as <%s>' % (self.aliases[alias], alias))

    def set_text_hash(self, text):
        text_hash = hashlib.md5(text).hexdigest()
        if text_hash != self.text_hash:
            self.text_hash = text_hash
            return True
        else:
            return False

    def get_text_hash(self, text):
        return self.text_hash


global_alias = SQLAlias()
# list of tables
sqlreq_tables = 'SELECT Distinct TABLE_NAME as name FROM information_schema.TABLES'
# list of columns
sqlreq_columns = "SELECT c.name FROM sys.columns c WHERE c.object_id = OBJECT_ID(?)"


def te_get_setting(key, default_value=None):
    settings = sublime.load_settings('TSQLEasy.sublime-settings')
    return settings.get(key, default_value)


def te_set_setting(key, value):
    settings = sublime.load_settings('TSQLEasy.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('TSQLEasy.sublime-settings')


def te_get_connection():
    server_active = te_get_setting('te_server_active')
    server_list = te_get_setting('te_sql_server')
    server = server_list[server_active]['server']
    driver = server_list[server_active]['driver']
    server_port = server_list[server_active]['server_port']
    username = server_list[server_active]['username']
    password = server_list[server_active]['password']
    database = server_list[server_active]['database']
    autocommit = server_list[server_active]['autocommit']

    sqlcon = sqlodbccon.SQLCon(server=server, driver=driver, serverport=server_port, username=username, password=password, database=database, sleepsecs="5", autocommit=autocommit)
    return sqlcon


def te_get_encodings():
    profile = te_get_setting('te_sql_profile')
    if profile:
        encodings = te_get_setting('te_encodings')
        return encodings[profile]
    else:
        return 'utf-8'


def te_get_alias(string_data):
    ''' get string alias by caps characters '''

    rs = re.findall('[A-Z][^A-Z]*', string_data)
    fs = ''
    for word in rs:
        fs += word[0]
    return fs


def te_get_all_aliases(text):
    # get aliases from substrings FROM and JOIN
    text = text.lower()
    pattern = r'[^\w](from|join)\s{0,}(\w+)\s(as\s)?\s{0,}(\w+)'
    aliases_strings = re.findall(pattern, text)
    if aliases_strings:
        for alias in aliases_strings:
            if alias[1] and alias[3]:
                global_alias.set_alias(alias[3].strip('\n').strip(), alias[1].strip('\n').strip())
    del aliases_strings

    # get aliases from section FROM whithou JOINs..
    is_from_section = False
    words = ('where', 'join', 'order', 'select', 'insert', 'update', 'with', 'group')
    for line in text.split('\n'):
        line = line.strip().strip(',')
        if line[0:4] == 'from' or ' from' in line:
            is_from_section = True
        if is_from_section and any(wo in line for wo in words):
            is_from_section = False
        if is_from_section:
            pattern = r'^(.*?)\s(as\s)?(.*)'
            aliases_strings = re.findall(pattern, line)
            if aliases_strings:
                for alias in aliases_strings:
                    if alias[0] and alias[2]:
                        global_alias.set_alias(alias[2].strip('\n').strip(), alias[0].strip('\n').strip())
            del aliases_strings


def te_reload_aliases_from_file():
    if not sublime.active_window():
        return
    view = sublime.active_window().active_view()
    if view is not None:
        all_text_region = sublime.Region(0, view.size())
        text = view.substr(all_text_region)
        if global_alias.set_text_hash(text.encode(te_get_encodings())):
            global_alias.aliases = {}
            te_get_all_aliases(text)
            sublime.status_message('Aliases was reloaded.')
            # print current aliases..
            # global_alias.alias_list()
        else:
            sublime.status_message('Text unchanged. Using old aliases.')


def te_get_title():
    ''' returns page title of active tab from view_name or from file_name'''
    if not sublime.active_window() or sublime.active_window() is None:
        return ''
    if not sublime.active_window().active_view() or sublime.active_window().active_view() is None:
        return ''
    view_name = sublime.active_window().active_view().name()
    if view_name:
        return view_name
    else:
        file_name = sublime.active_window().active_view().file_name()
        if file_name:
            return file_name


class TsqlEasySetActiveServerCommand(sublime_plugin.WindowCommand):
    server_keys = []
    server_on = '>'
    server_off = ' ' * 3
    server_active = ''

    def run(self):
        self.server_active = te_get_setting('te_server_active')
        servers = te_get_setting('te_sql_server')
        self.server_keys = [self.is_checked(x) for x in servers.keys()]
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.server_keys, self.on_done), 1)

    def is_checked(self, server_key):
        checked = self.server_on if server_key == self.server_active else self.server_off
        return '%s %s' % (checked, server_key)

    def on_done(self, index):
        if index >= 0 and not self.server_keys[index].startswith(self.server_on):
            te_set_setting("te_server_active", self.server_keys[index].strip())


class TsqlEasyInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, position, text):
        self.view.insert(edit, position, text)


class TsqlEasyGetTableCommand(sublime_plugin.TextCommand):
    ''' Get table list from db '''

    def run(self, edit):
        self.tables = []
        sqlcon = te_get_connection()
        sqlcon.dbexec(sqlreq_tables)
        if sqlcon.sqldataset:
            for row in sqlcon.sqldataset:
                self.tables.append(row.name)
            sqlcon.dbdisconnect()
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.tables, self.on_done), 1)
        else:
            sqlcon.dbdisconnect()

    def on_done(self, index):
        if index >= 0:
            position = self.view.sel()[0].begin()
            table_name = self.tables[index]
            alias = te_get_alias(table_name).lower()
            if alias:
                global_alias.set_alias(alias.strip('\n').strip(), table_name.strip('\n').strip())
            text = '%s as %s' % (table_name, alias) if alias else table_name
            self.view.run_command("tsql_easy_insert_text", {"position": position, "text": text})


class TsqlEasyGetColumnCommand(sublime_plugin.TextCommand):
    ''' Get columns list for table or table alias
        Fires in strings like tablename. или table_alias.'''

    dot_exists = False
    profile = ''

    def run(self, edit):
        te_reload_aliases_from_file()
        current_position = self.view.sel()[0].begin() - 1
        table_name = self.view.substr(self.view.word(current_position))

        # print('Get columns for table %s' % table_name.lower())
        self.columns = []
        # check auto aliases
        al = global_alias.get_alias(table_name.lower())
        if al:
            # print('%s is a alias of %s' % (table_name.lower(), al))
            table_name = al

        sqlcon = te_get_connection()
        sqlcon.dbexec(sqlreq_columns, [table_name])
        if sqlcon.sqldataset:
            for row in sqlcon.sqldataset:
                column = row.name
                if column:
                    self.columns.append(column)
        sqlcon.dbdisconnect()
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.columns, self.on_done), 1)

    def on_done(self, index):
        if index >= 0:
            position = self.view.sel()[0].begin()
            word_cursor = self.view.substr(self.view.word(position)).strip('\n').strip()
            self.dot_exists = True if word_cursor == '.' else False
            text = self.columns[index] if self.dot_exists else '.%s' % self.columns[index]
            self.view.run_command("tsql_easy_insert_text", {"position": position, "text": text})


class TsqlEasyAutoCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        ''' by context run command for table or for columns
        now:
        if current word is space - get table
        if current word is dot - get column
        it's not so good, because table can be like db_name.tablename
        '''
        self.view.set_syntax_file('Packages/TSQLEasy/TSQL.tmLanguage')
        position = self.view.sel()[0].begin()
        word_cursor = self.view.substr(self.view.word(position)).strip('\n').strip()
        if word_cursor == u'.':
            self.view.run_command("tsql_easy_get_column")
        else:
            self.view.run_command("tsql_easy_get_table")


class TsqlEasyEventDump(sublime_plugin.EventListener):

    def on_load(self, view):
        if self.check_tab():
            te_reload_aliases_from_file()

    def on_activated(self, view):
        if self.check_tab():
            te_reload_aliases_from_file()

    def check_tab(self):
        tab_name = te_get_title()
        if not tab_name or tab_name[-4:] == '.sql':
            return True
        return False


class TsqlEasyExecSqlCommand(sublime_plugin.TextCommand):

    def run(self, view):
        self.source_encodings = te_get_encodings()
        self.view.set_syntax_file('Packages/TSQLEasy/TSQL.tmLanguage')
        self.sqlcon = te_get_connection()
        self.sql_query = self.view.substr(self.view.sel()[0])
        if self.sql_query:
            dt_before = time.time()
            self.sqlcon.dbexec(self.sql_query)
            dt_after = time.time()
            timedelta = dt_after - dt_before
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            text = self.get_pretty(timedelta, current_time)
            self.sqlcon.dbdisconnect()

            result_in_new_tab = te_get_setting('te_result_in_new_tab')
            if result_in_new_tab:
                # sublime.active_window().run_command('new_pane', {'move': True})
                # sublime.active_window().run_command('set_layout', {"cols": [0.0, 1.0], "rows": [0.0, 0.6, 1.0], "cells": [[0, 0, 1, 1], [0, 1, 1, 2]]})
                # sublime.active_window().focus_group(1)
                new_view = sublime.active_window().new_file()
                new_view.set_name('TSQLEasy result (%s)' % current_time)
                new_view.settings().set("word_wrap", False)
                new_view.run_command('tsql_easy_insert_text', {'position': 0, 'text': text})
            else:
                print(text)

            sublime.status_message('Executed.')
        else:
            sublime.status_message('Nothing to execute.')

    def validate(self, value):
        if value is None:
            return '{null}'
        else:
            if pythonver >= 3:
                return value
            else:
                return value.decode(self.source_encodings)

    def table_print(self, data, title_row):
        """
        http://howto.pui.ch/post/37471158914/python-print-list-of-dicts-as-ascii-table
        data: list of dicts,
        title_row: e.g. [('name', 'Programming Language'), ('type', 'Language Type')]
        """
        result = ''
        max_widths = {}
        data_copy = [dict(title_row)] + list(data)
        for col in data_copy[0].keys():
            # max_widths[col] = max([len(str(row[col])) for row in data_copy])
            max_widths[col] = len(max([self.validate(row[col]) for row in data_copy], key=len))
        cols_order = [tup[0] for tup in title_row]

        def custom_just(col, value):
            value = self.validate(value)
            return value.ljust(max_widths[col])

        for row in data_copy:
            row_str = " | ".join([custom_just(col, row[col]) for col in cols_order])
            result += '| %s |\n' % (row_str)
            if data_copy.index(row) == 0:
                underline = "-+-".join(['-' * max_widths[col] for col in cols_order])
                result += '+-%s-+\n' % (underline)
        return result

    def get_pretty(self, timedelta, received_time):

        title_row = []
        data_rows = []
        res_body = ''
        column_names = False
        if self.sqlcon.sqldataset:
            for row in self.sqlcon.sqldataset:
                row_as_dict = {}
                if not column_names:
                    # column sql name and printed name will be the same
                    title_row = [(val[0], val[0]) for val in self.sqlcon.sqlcolumns]
                    column_names = True
                for col in title_row:
                    row_as_dict[col[0]] = str(getattr(row, col[0]))
                data_rows.append(row_as_dict)

            res_body = self.table_print(data_rows, title_row)
        else:
            res_body = 'Result without dataset\n'
        res_header = ('------ SQL Request ------\n'
                      '%s\n'
                      '-------------------------\n\n' % (self.sql_query))

        res_footer = ('\n------ SQL result stats ------\n'
                      'Records count: %s\n'
                      'Execution time: %s secs\n'
                      'Received at: %s' % (len(data_rows), round(timedelta, 3), received_time))
        return '%s%s%s' % (res_header, res_body, res_footer)


class TsqlEasyOpenProcedureCommand(sublime_plugin.TextCommand):
    proc_dirs = []
    filename = ''
    filename_abs_path = ''

    def run(self, view):
        self.view.set_syntax_file('Packages/TSQLEasy/TSQL.tmLanguage')
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
        self.proc_dirs = list(te_get_setting('te_procedure_path'))
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
        sublime.active_window().active_view().set_syntax_file('Packages/TSQLEasy/TSQL.tmLanguage')
