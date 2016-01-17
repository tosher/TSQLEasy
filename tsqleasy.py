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
DEFAULT_REPORT_SYNTAX = 'Packages/Markdown/Markdown.tmLanguage'


class SQLAlias():
    aliases = {}
    text_hash = ''

    def __init__(self):
        pass

    def set_alias(self, alias, name):
        if self.aliases.get(alias, '') != name:
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
    driver = server_list[server_active].get('driver', None)
    if driver:
        dsn = server_list[server_active].get('dsn', None)
        server = server_list[server_active].get('server', None)
        server_port = server_list[server_active].get('server_port', 1433)
        username = server_list[server_active]['username']
        password = server_list[server_active]['password']
        database = server_list[server_active]['database']
        autocommit = server_list[server_active]['autocommit'] if 'autocommit' in server_list[server_active] else True
        timeout = server_list[server_active]['timeout'] if 'timeout' in server_list[server_active] else 0

        sqlcon = sqlodbccon.SQLCon(dsn=dsn, server=server, driver=driver, serverport=server_port, username=username, password=password, database=database, sleepsecs=5, autocommit=autocommit, timeout=timeout)
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
    ''' get table columns for completions '''
    sqlreq_columns = "SELECT c.name FROM sys.columns c WHERE c.object_id = OBJECT_ID(?)"

    te_reload_aliases_from_file()
    view = sublime.active_window().active_view()
    if position is None:
        position = view.sel()[0].begin() - 1
    table_name = view.substr(view.word(position))

    columns = []
    # check auto aliases
    al = global_alias.get_alias(table_name.lower())
    if al:
        table_name = al

    sqlcon = te_get_connection()
    if sqlcon.sqlconnection is not None:
        sqlcon.dbexec(sqlreq_columns, (table_name,))
        if sqlcon.sqldataset:
            for row in sqlcon.sqldataset:
                column = row.name
                if column:
                    columns.append(('%s\tTable column' % column, column))
        sqlcon.dbdisconnect()
    return columns


def te_get_tables(schema=None):
    ''' get tables list with filter by schema for completions '''

    sqlreq_tables = 'SELECT Distinct TABLE_NAME as name FROM information_schema.TABLES WHERE TABLE_SCHEMA = (?)'

    tables = []
    sqlcon = te_get_connection()

    if schema is None:
        schema = sqlcon.defaultschema

    if sqlcon.sqlconnection is not None and schema:
        sqlcon.dbexec(sqlreq_tables, (schema,))
        if sqlcon.sqldataset:
            for row in sqlcon.sqldataset:
                tables.append(('%s\tSQL table' % row.name, row.name))
        sqlcon.dbdisconnect()
    return tables


def te_show_data(sql_query, setup, **kwargs):

    def get_data():
        cols_data = {}

        if cols:
            for col in cols:
                cols_data[col['prop']] = len(col['colname'])

            for row in rows:
                for col in cols:

                    value = ''
                    maxlen = col.get('maxlen', None)
                    # field_type = col.get('type', None)
                    col_prop = col['prop']

                    value = str(row[columns_indexes.get(col_prop)]).strip().replace('\r', ' ')
                    if maxlen:
                        value = ' '.join(value.splitlines())
                    # if field_type == 'datetime':
                    #     value = rl_get_datetime(value)

                    value_len = len(cut(value, maxlen))
                    if value_len > cols_data[col_prop]:
                        cols_data[col_prop] = value_len
        return cols_data

    def cut(val, maxlen):
        if maxlen:
            if len(val) > maxlen:
                return '%s..' % val[:maxlen - 2]
        return val

    def pretty(value, length, align='left'):

        align_sign = '<'
        if align == 'left':
            align_sign = '<'
        elif align == 'center':
            align_sign = '^'
        elif align == 'right':
            align_sign = '>'

        line_format = '{0:%s%s}' % (align_sign, length)
        return line_format.format(value)

    cols = te_get_setting(setup, {})
    if cols:
        content = ''

        shortcuts = [
            '[Enter](View query)',
            '[r](Refresh rows)']

        content_header = '%s\n\n' % ' '.join(shortcuts)
        if kwargs.get('title', None):
            content_header += '## %s\n' % kwargs['title']

        sqlcon = te_get_connection()
        sql_params = kwargs.get('sql_params', ())
        if sqlcon.sqlconnection is not None and sql_query:
            text = ''
            # dt_before = time.time()
            sqlcon.dbexec(sql_query, sql_params)
            rows = sqlcon.sqldataset
            # columns_indexes = {v[0]: k for k, v in enumerate(sqlcon.sqlcolumns)}
            columns_indexes = dict((v[0], k) for k, v in enumerate(sqlcon.sqlcolumns))
            # dt_after = time.time()
            # timedelta = dt_after - dt_before
            # current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # text += self.get_pretty(timedelta, current_time)
            sqlcon.dbdisconnect()

        content_header += 'Total processes: %s\n\n' % len(rows)

        table_data_widths = get_data()
        # content_header_line = '%s-\n' % ('-' * (sum([val for val in table_data_widths.values()]) + len(cols) * 3))

        content_header_line = ' | '.join(['-' * table_data_widths.get(col['prop'], 0) for col in cols])
        content_header_line = '| %s |\n' % content_header_line

        table_header = '| ' + ' | '.join(pretty(col['colname'], table_data_widths[col['prop']], 'center') for col in cols)
        table_header = '%s |\n' % table_header

        if rows:
            for row in rows:
                table_row = '|'
                for col in cols:

                    value = ''
                    maxlen = col.get('maxlen', None)
                    # field_type = col.get('type', None)
                    col_prop = col['prop']

                    value = str(row[columns_indexes.get(col_prop)]).strip().replace('\r', ' ')
                    if maxlen:
                        value = ' '.join(value.splitlines())

                    # if field_type == 'datetime':
                    #     value = rl_get_datetime(value)

                    value = cut(value, maxlen)
                    align = col.get('align', 'left')
                    table_row += ' %s |' % pretty(value, table_data_widths[col_prop], align)
                table_row += '\n'
                content += table_row
        else:
            text = 'No data'
            line_format = '|{:^%s}|\n' % (len(content_header_line) - 3)
            content += line_format.format(text)

        # content_footer_line = content_header_line.replace('|', '-')

        # return Markdown compatible report
        return ''.join([
                content_header,
                # '```\n',
                # content_header_line,
                table_header,
                content_header_line,
                content,
                # content_footer_line,
                # '```\n'
            ])


def te_validate_screen(screen_type):

    message = ''
    is_valid = sublime.active_window().active_view().settings().get(screen_type, False)

    if not is_valid:
        if screen_type == 'te_activity_monitor':
            message = 'This command is provided for the Activity monitor!'
        elif screen_type == 'te_long_queries':
            message = 'This command is provided for the Long running queries report!'
        else:
            message = 'This command is not provided for this view!'

    return (is_valid, message)


class TsqlEasySetActiveServerCommand(sublime_plugin.WindowCommand):
    server_keys = []
    server_on = '>'
    server_off = ' ' * 3
    server_active = ''

    def run(self):
        self.server_active = te_get_setting('te_server_active', 'Offline')
        servers = te_get_setting('te_sql_server')
        self.server_keys = [self.is_active(x) for x in servers.keys()]
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.server_keys, self.on_done), 1)

    def is_active(self, server_key):
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

    res_view = None

    def run(self, view, query=None):
        self.sqlcon = te_get_connection()
        self.view.set_line_endings('windows')
        if query:
            self.sql_query = query
        elif self.view.sel()[0]:
            self.sql_query = self.view.substr(self.view.sel()[0])
        else:
            self.sql_query = self.view.substr(sublime.Region(0, self.view.size()))

        if self.sqlcon.sqlconnection is not None and self.sql_query:
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

            result_in_tab = te_get_setting('te_result_in_tab', False)
            result_in_new_tab = te_get_setting('te_result_in_new_tab', False)

            if result_in_tab:
                if not self.res_view or result_in_new_tab or self.res_view.id() not in [v.id() for v in sublime.active_window().views()]:
                    self.res_view = sublime.active_window().new_file()
                self.res_view.set_name('TSQLEasy result (%s)' % current_time)
                self.res_view.settings().set("word_wrap", False)
                self.res_view.run_command('tsql_easy_insert_text', {'position': self.res_view.size(), 'text': text})
                sublime.active_window().focus_view(self.res_view)

            else:
                panel_name = 'result_panel'
                if not self.res_view:
                    if int(sublime.version()) >= 3000:
                        self.res_view = sublime.active_window().create_output_panel(panel_name)
                    else:
                        self.res_view = sublime.active_window().get_output_panel(panel_name)
                self.res_view.run_command('tsql_easy_insert_text', {'position': self.res_view.size(), 'text': text + '\n'})
                self.res_view.show(self.res_view.size())
                sublime.active_window().run_command("show_panel", {"panel": "output." + panel_name})

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
                elif isinstance(value, bytearray):
                    # http://obsoleter.com/2012/8/28/pyodbc-and-sql-server-binary-fields/
                    hs = ["{0:0>2}".format(hex(b)[2:].upper()) for b in value]
                    return '0x' + ''.join(hs)
                else:
                    return unicode(str(value))

    def get_pretty(self, timedelta, received_time):

        show_request_in_result = te_get_setting('te_show_request_in_result', True)

        data_rows = []
        data_text = ''
        if self.sqlcon.sqldataset:

            # table header row
            header_list = [val[0] for val in self.sqlcon.sqlcolumns]
            data_rows.append(header_list)

            for row in self.sqlcon.sqldataset:
                row_list = [self.getval(val) for val in row]
                data_rows.append(row_list)

            data_text = self.table_print(data_rows)
        else:
            data_text = 'Completed: result without dataset'

        res_request = ''
        if show_request_in_result:
            res_request = ''.join([
                '------ SQL request ------',
                '\n',
                self.sql_query,
                '\n'])

        res_data = ''.join([
            '------ SQL result -------',
            '\n',
            data_text])

        data_stats = ' | '.join([
            'Records count: %s' % len(data_rows),
            'Rows affected: %s' % self.sqlcon.sqlcursor.rowcount,
            'Execution time: %s secs' % round(timedelta, 3),
            'Received at: %s' % received_time])

        res_stats = ''.join([
            '------ SQL result stats ------',
            '\n',
            data_stats,
            '\n',
            '\n'])

        return '\n'.join([val for val in [res_request, res_data, res_stats] if val])

    def _get_max_lens(self, rows):
        max_lens = []
        rows_by_cols = zip(*rows)
        for row in rows_by_cols:
            max_lens.append(len(max(row, key=len)))
        return max_lens

    def _pretty(self, value, length, align='left'):

        align_sign = '<'
        if align == 'left':
            align_sign = '<'
        elif align == 'center':
            align_sign = '^'
        elif align == 'right':
            align_sign = '>'

        line_format = u'{0:%s%s}' % (align_sign, length)

        return line_format.format(value)

    def table_print(self, rows):

        HEADER_LINE_CROSS = '---'
        FOOTER_LINE_CROSS = '---'
        INTABLE_LINE_CROSS = '-+-'

        text = ''
        is_header_ready = False
        ml = self._get_max_lens(rows)

        line_list = ['-' * l for l in ml]
        line_header = '--%s--\n' % HEADER_LINE_CROSS.join(line_list)
        line_intable = '--%s--\n' % INTABLE_LINE_CROSS.join(line_list)
        line_footer = '--%s--\n' % FOOTER_LINE_CROSS.join(line_list)

        text += line_header

        for row in rows:
            line_list = [self._pretty(val, ml[idx]) for idx, val in enumerate(row)]
            row_line = ' | '.join(line_list)
            row_line = '| %s |\n' % row_line
            text += row_line
            if not is_header_ready:
                text += line_intable
                is_header_ready = True
        text += line_footer
        return text


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
        sqlcon = te_get_connection()
        if sqlcon.sqlconnection is not None:
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


class TsqlEasyActivityMonitorCommand(sublime_plugin.TextCommand):

    def run(self, edit, is_refresh=False):

        # OUTER APPLY Fn_get_sql(sp.sql_handle)
        sql_query = '''
        SELECT sp.spid,
            -- TEXT as query,
            Db_name(sp.dbid) as dbname,
            sp.cpu,
            sp.memusage,
            sp.status,
            sp.loginame,
            sp.hostname,
            sp.blocked,
            sp.waittime,
            sp.lastwaittype,
            sp.waitresource,
            convert(varchar(255), sp.login_time) as login_time,
            convert(varchar(255), sp.last_batch) as last_batch,
            sp.cmd,
            sp.open_tran,
            sp.program_name
        FROM sys.sysprocesses as sp
        -- OUTER APPLY sys.dm_exec_sql_text(sp.sql_handle)
        WHERE sp.spid > ?
        ORDER BY sp.spid
        '''

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title = 'Activity monitor (at %s)' % current_time
        min_pid = te_get_setting('te_activity_monitor_min_pid', 50)
        query_params = {'title': title, 'sql_params': (min_pid,)}

        if not is_refresh:
            r = self.view.window().new_file()
            r.set_name(title)
            r.settings().set('te_activity_monitor', True)
            syntax_file = te_get_setting('te_report_syntax', DEFAULT_REPORT_SYNTAX)
            r.set_syntax_file(syntax_file)
        else:
            is_valid, message = te_validate_screen('te_activity_monitor')
            if not is_valid:
                sublime.message_dialog(message)
                return

            r = self.view
            r.set_read_only(False)
            r.erase(edit, sublime.Region(0, self.view.size()))

        text = te_show_data(sql_query=sql_query, setup='te_activity_monitor_columns', **query_params)
        r.settings().set("word_wrap", False)
        r.run_command('tsql_easy_insert_text', {'position': 0, 'text': text + '\n\n'})
        r.set_scratch(True)
        r.set_read_only(True)


class TsqlEasyLongQueriesCommand(sublime_plugin.TextCommand):

    def run(self, edit, is_refresh=False):

        # http://dba.stackexchange.com/questions/66249/how-do-i-find-a-long-running-query-with-process-id-process-name-login-time-u
        sql_query = '''
        SELECT
            cast(cast(query_hash as varbinary) as bigint) as query_hash
            ,creation_time
            ,last_execution_time
            ,total_physical_reads
            ,total_logical_reads
            ,total_logical_writes
            ,execution_count
            ,total_worker_time
            ,total_elapsed_time
            ,total_elapsed_time / execution_count avg_elapsed_time
            /*
            ,SUBSTRING(st.text, (qs.statement_start_offset/2) + 1,
                ((CASE statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset END
                - qs.statement_start_offset)/2) + 1) as query
            */
        FROM sys.dm_exec_query_stats as qs
        -- CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        ORDER BY total_elapsed_time / execution_count DESC;
        '''

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title = 'Long running queries (at %s)' % current_time
        query_params = {'title': title}

        if not is_refresh:
            r = self.view.window().new_file()
            r.set_name(title)
            r.settings().set('te_long_queries', True)
            syntax_file = te_get_setting('te_report_syntax', DEFAULT_REPORT_SYNTAX)
            r.set_syntax_file(syntax_file)
        else:
            is_valid, message = te_validate_screen('te_long_queries')
            if not is_valid:
                sublime.message_dialog(message)
                return

            r = self.view
            r.set_read_only(False)
            r.erase(edit, sublime.Region(0, self.view.size()))

        text = te_show_data(sql_query=sql_query, setup='te_long_queries_columns', **query_params)
        r.settings().set("word_wrap", False)
        r.run_command('tsql_easy_insert_text', {'position': 0, 'text': text + '\n\n'})
        r.set_scratch(True)
        r.set_read_only(True)


class TsqlEasyShowQueryCommand(sublime_plugin.TextCommand):
    def run(self, edit):

        row_id = None
        try:
            line = self.view.substr(self.view.line(self.view.sel()[0].end()))
            row_id = line.split('|')[1].strip()  # TODO: require ID in first column
        except:
            pass

        if row_id:
            self.get_query(int(row_id))

    def get_query(self, row_id):

        long_queries = self.view.settings().get('te_long_queries', False)
        activity_monitor = self.view.settings().get('te_activity_monitor', False)

        if activity_monitor:
            sql_query = '''
            SELECT
                TEXT AS query,
                sp.status,
                sp.blocked
            FROM sys.sysprocesses as sp
            OUTER APPLY sys.dm_exec_sql_text(sp.sql_handle)
            WHERE sp.spid = ?
            '''
        elif long_queries:
            # TODO: Plan show
            # --CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) st2
            sql_query = '''
            SELECT
                SUBSTRING(st.text, (qs.statement_start_offset/2) + 1,
                    ((CASE statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset END
                    - qs.statement_start_offset)/2) + 1) AS statement_text
            FROM sys.dm_exec_query_stats as qs
            CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
            where query_hash = cast(cast(? as bigint) as varbinary)
            '''
        else:
            sublime.status_message('Error: Unknown mode')

        if row_id:
            sqlcon = te_get_connection()
            if sqlcon.sqlconnection is not None and sql_query:
                sqlcon.dbexec(sql_query, (row_id,))
                rows = sqlcon.sqldataset

                if rows:
                    if activity_monitor:
                        process_query = rows[0][0]
                        process_query = process_query.strip() if process_query else '-- No query'
                        process_status = rows[0][1].strip()
                        process_blocked_by = rows[0][2]
                    elif long_queries:
                        long_query = rows[0][0]
                        long_query = long_query.strip() if long_query else '-- No query'

                    index_of_textend = self.view.size()
                    self.view.set_read_only(False)

                    if activity_monitor:
                        text = '\n### PID: %s (%s)\n' % (row_id, process_status)
                        if process_blocked_by:
                            text += 'Blocked by: %s\n' % process_blocked_by
                        text += '```sql\n'
                        text += '%s\n' % process_query.replace('\r', '')
                        text += '```\n'
                    elif long_queries:
                        text = '\n### Query hash: %s\n' % row_id
                        text += '```sql\n'
                        text += '%s\n' % long_query.replace('\r', '')
                        text += '```\n'

                    self.view.run_command('tsql_easy_insert_text', {'position': index_of_textend, 'text': text})
                    self.view.show(index_of_textend)
                    self.view.sel().clear()
                    self.view.sel().add(index_of_textend)
                    self.view.set_read_only(True)

                sqlcon.dbdisconnect()
        else:
            sublime.status_message('Error: ROW ID is not found')
