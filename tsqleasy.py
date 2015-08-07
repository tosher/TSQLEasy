#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import re
import hashlib
import time
import os.path
from datetime import datetime
import tempfile
import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import sqlodbccon
else:
    import sqlodbccon

# TODO: Get procedures (functions) list (with params)
# TODO: Completions to TSQL operators
# TODO: Processes, locks, etc..

DEFAULT_SYNTAX = 'Packages/TSQLEasy/TSQL.tmLanguage'


class SQLAlias():
    aliases = {}
    text_hash = ''

    def __init__(self):
        pass

    def set_alias(self, alias, name):
        if alias not in self.aliases or self.aliases[alias] != name:
            self.aliases[alias] = name

    def get_alias(self, alias):
        return self.aliases.get(alias, '')

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
# edited by Caio Hamamura - will get schema too
sqlreq_tables = 'SELECT Distinct TABLE_NAME as name, TABLE_SCHEMA as schemaname FROM information_schema.TABLES'
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
    driver = server_list[server_active]['driver']
    if driver:
        server = server_list[server_active]['server']
        server_port = server_list[server_active]['server_port'] if 'server_port' in server_list[server_active] else '1433'
        username = server_list[server_active]['username']
        password = server_list[server_active]['password']
        database = server_list[server_active]['database']
        autocommit = server_list[server_active]['autocommit'] if 'autocommit' in server_list[server_active] else True
        timeout = server_list[server_active]['timeout'] if 'timeout' in server_list[server_active] else 0

        sqlcon = sqlodbccon.SQLCon(server=server, driver=driver, serverport=server_port, username=username, password=password, database=database, sleepsecs=5, autocommit=autocommit, timeout=timeout)
        return sqlcon
    else:
        return None


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
    # edited by Caio Hamamura - will get schema and square brackets (optionally)
    pattern = r'[^\w](from|join)\s{0,}(\[?\w+?\]?\.?\[?\w+\]?)\s(as\s)?\s{0,}(\w+)'
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
        if line.startswith('from') or ' from' in line:
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
        if global_alias.set_text_hash(text.encode('utf-8')):
            global_alias.aliases = {}
            te_get_all_aliases(text)
            sublime.status_message('Aliases were reloaded.')
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


def te_get_columns(position=None):
    te_reload_aliases_from_file()
    view = sublime.active_window().active_view()
    if position is None:
        position = view.sel()[0].begin() - 1
    table_name = view.substr(view.word(position))

    # print('Get columns for table %s' % table_name.lower())
    columns = []
    # check auto aliases
    al = global_alias.get_alias(table_name.lower())
    if al:
        # print('%s is a alias of %s' % (table_name.lower(), al))
        table_name = al

    sqlcon = te_get_connection()
    if sqlcon is not None:
        sqlcon.dbexec(sqlreq_columns, [table_name])
        if sqlcon.sqldataset:
            for row in sqlcon.sqldataset:
                column = row.name
                if column:
                    columns.append(('%s\tTable column' % column, column))
        sqlcon.dbdisconnect()
    return columns


def te_get_tables(schema=None):
    ''' schema in arguments to filter tables by schema '''
    tables = []
    sqlcon = te_get_connection()

    if schema is None:
        schema = sqlcon.defaultschema

    if sqlcon is not None:
        sqlcon.dbexec(sqlreq_tables)
        if sqlcon.sqldataset:
            # will filter tables by schema
            for row in sqlcon.sqldataset:
                if schema is None or row.schemaname.lower() == schema.lower():
                    tables.append(('%s\tSQL table' % row.name, row.name))
        sqlcon.dbdisconnect()
    return tables


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


class TsqlEasyEventDump(sublime_plugin.EventListener):

    def on_load(self, view):
        if self.check_tab(view):
            te_reload_aliases_from_file()

    def on_activated(self, view):
        if self.check_tab(view):
            te_reload_aliases_from_file()

    def check_tab(self, view):
        title = te_get_title()
        if title and title.endswith('.sql'):
            return True
        return False

    def _is_alias(self, val):
        ''' check string is table alias '''
        te_reload_aliases_from_file()
        if not global_alias.get_alias(val.lower()):
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

            if word_before is not None:
                if self._is_alias(word_before):
                    return (te_get_columns(position))
                else:
                    return (te_get_tables(word_before))
            else:
                return (te_get_tables())


class TsqlEasyExecSqlCommand(sublime_plugin.TextCommand):

    def run(self, view):
        self.sqlcon = te_get_connection()
        self.view.set_line_endings('windows')
        if self.view.sel()[0]:
            self.sql_query = self.view.substr(self.view.sel()[0])
        else:
            self.sql_query = self.view.substr(sublime.Region(0, self.view.size()))
        if self.sqlcon is not None and self.sql_query:
            queries = self.sql_query.split('\n--go\n')
            text = ''
            for query in queries:
                if query:
                    dt_before = time.time()
                    self.sqlcon.dbexec(query)
                    dt_after = time.time()
                    timedelta = dt_after - dt_before
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    text += self.get_pretty(timedelta, current_time)
            self.sqlcon.dbdisconnect()

            result_in_new_tab = te_get_setting('te_result_in_new_tab')
            if result_in_new_tab:
                new_view = sublime.active_window().new_file()
                new_view.set_name('TSQLEasy result (%s)' % current_time)
                new_view.settings().set("word_wrap", False)
                new_view.run_command('tsql_easy_insert_text', {'position': 0, 'text': text})
            else:
                sublime.active_window().run_command('show_panel', {'panel': 'console', 'toggle': True})
                print(text)

            sublime.status_message('Executed.')
        else:
            sublime.status_message('Nothing to execute.')

    def getval(self, value):
        if value is None:
            return '{null}'
        else:
            if pythonver >= 3:
                return str(value)
            else:
                if isinstance(value, unicode):
                    return value
                elif isinstance(value, str):
                    return value.decode(te_get_encodings())
                else:
                    return str(value)

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
            max_widths[col] = len(max([row[col] for row in data_copy], key=len))
        cols_order = [tup[0] for tup in title_row]

        def custom_just(col, value):
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
        res_header = '\n------ SQL Result ------\n\n'
        res_body = ''
        column_names = False
        show_request_in_result = te_get_setting('te_show_request_in_result', True)
        if self.sqlcon.sqldataset:
            for row in self.sqlcon.sqldataset:
                row_as_dict = {}
                if not column_names:
                    # column sql name and printed name will be the same
                    title_row = [(val[0], val[0]) for val in self.sqlcon.sqlcolumns]
                    column_names = True
                for col in title_row:
                    row_as_dict[col[0]] = self.getval(getattr(row, col[0]))
                data_rows.append(row_as_dict)

            res_body = self.table_print(data_rows, title_row)
        else:
            res_body = 'Completed: Result without dataset\n'
        if show_request_in_result:
            res_header = ('------ SQL Request ------\n'
                          '%s\n'
                          '------ SQL Result -------\n\n' % (self.sql_query))

        res_footer = ('\n------ SQL result stats ------\n'
                      'Records count: %s | '
                      'Rows affected: %s | '
                      'Execution time: %s secs | '
                      'Received at: %s' % (len(data_rows), self.sqlcon.sqlcursor.rowcount, round(timedelta, 3), received_time))
        return '%s%s%s' % (res_header, res_body, res_footer)


class TsqlEasyOpenConsoleCommand(sublime_plugin.WindowCommand):

    def run(self):
        prefix = 'Console_'
        tf = tempfile.NamedTemporaryFile(mode='w+t', suffix='.sql', prefix=prefix, dir=None, delete=True)
        new_view = sublime.active_window().open_file(tf.name)

        new_view.set_syntax_file(te_get_setting('te_syntax', DEFAULT_SYNTAX))
        new_view.settings().set('tsqleasy_is_here', True)

        new_view.settings().set("word_wrap", False)
        new_view.set_line_endings('unix')
        tf.close()


class TsqlEasyOpenServerObjectCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        position = self.view.sel()[0].begin()
        word_cursor = self.view.substr(self.view.word(position)).strip('\n').strip()
        sqlreq = "exec sp_helptext @objname = ?"
        sqlcon = te_get_connection()
        if sqlcon is not None:
            sqlcon.dbexec(sqlreq, [word_cursor])
            text = ''
            if sqlcon.sqldataset:
                text = ''.join([row.Text for row in sqlcon.sqldataset])

                if pythonver < 3:
                    text = text.encode('utf-8')

            sqlcon.dbdisconnect()
            if text:
                prefix = '%s_tmp_' % word_cursor
                with tempfile.NamedTemporaryFile(mode='w+t', suffix='.sql', prefix=prefix, dir=None, delete=True) as tf:

                    tf.write(text.replace('\r', ''))
                    tf.seek(0)
                    if os.path.exists(tf.name):
                        new_view = sublime.active_window().open_file(tf.name)

                        new_view.set_syntax_file(te_get_setting('te_syntax', DEFAULT_SYNTAX))
                        new_view.settings().set('tsqleasy_is_here', True)
                        new_view.set_line_endings('unix')
        else:
            sublime.status_message('No connection to SQL server')


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
        self.view.set_syntax_file(te_get_setting('te_syntax', DEFAULT_SYNTAX))
        self.view.settings().set('tsqleasy_is_here', True)
