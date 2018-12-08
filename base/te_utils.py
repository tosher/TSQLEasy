#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os
import re
import sublime
import sublime_plugin
from . import sqlodbccon
from .te_sql_alias import SQLAlias
sys.path.append(os.path.join(os.path.dirname(__file__), "../libs"))
from ..libs.terminaltables.other_tables import WindowsTable as SingleTable
from ..libs import sqlparse


DEFAULT_SYNTAX = 'Packages/TSQLEasy/TSQL.sublime-syntax'
DEFAULT_REPORT_SYNTAX = 'Packages/Markdown/Markdown.tmLanguage'

global_alias = SQLAlias()


class TsqlEasyInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, position, text):
        self.view.insert(edit, position, text)


def te_get_setting(key, default_value=None):
    settings = sublime.load_settings('TSQLEasy.sublime-settings')
    return settings.get(key, default_value)


def te_set_setting(key, value):
    settings = sublime.load_settings('TSQLEasy.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('TSQLEasy.sublime-settings')


# def te_get_connection():
#     server_active = te_get_setting('te_server_active')
#     server_list = te_get_setting('te_sql_server')
#     driver = server_list[server_active].get('driver', None)
#     if driver:
#         dsn = server_list[server_active].get('dsn', None)
#         server = server_list[server_active].get('server', None)
#         server_port = server_list[server_active].get('server_port', 1433)
#         username = server_list[server_active]['username']
#         password = server_list[server_active]['password']
#         database = server_list[server_active]['database']
#         autocommit = server_list[server_active]['autocommit'] if 'autocommit' in server_list[server_active] else True
#         timeout = server_list[server_active]['timeout'] if 'timeout' in server_list[server_active] else 0

#         try:
#             # sqlcon = postgresqlodbccon.SQLCon(
#             sqlcon = sqlodbccon.ConDispatcher.get(driver)(
#                 dsn=dsn,
#                 server=server,
#                 driver=driver,
#                 serverport=server_port,
#                 username=username,
#                 password=password,
#                 database=database,
#                 sleepsecs=5,
#                 autocommit=autocommit,
#                 timeout=timeout
#             )
#             return sqlcon
#         except Exception as e:
#             sublime.message_dialog(e.args[1])
#     else:
#         return None

# def te_get_encodings():
#     profile = te_get_setting('te_sql_profile')
#     if profile:
#         encodings = te_get_setting('te_encodings')
#         return encodings[profile]
#     else:
#         return 'utf-8'


def te_get_alias(string_data):
    ''' get string alias by caps characters '''

    rs = re.findall('[A-Z][^A-Z]*', string_data)
    fs = ''
    for word in rs:
        fs += word[0]
    return fs


def te_get_all_aliases(text):
    # get aliases from sections with FROM, JOIN

    # --------------------------------------------------
    # from TableOne AS to
    #     left join tabletwo ttw On to.ID = ttw.PersonID
    # --------------------------------------------------
    # text = text.lower()
    # pattern = r'[^\w](from|join)\s{0,}(\[?\w*\]?\.?\[?\w+\]?)\s+(as\s)?\s{0,}(\w+)'
    # aliases_strings = re.findall(pattern, text)
    # if aliases_strings:
    #     for alias in aliases_strings:
    #         if alias[1] and alias[3]:
    #             global_alias.set_alias(alias[3].strip('\n').strip(), alias[1].strip('\n').strip())
    # del aliases_strings

    # ----------- sqlparse try -----------------
    # NOTE: not supports "aliases from sections FROM without JOINs"
    requests = sqlparse.parse(text)
    # print([p.tokens for p in parsed])
    # print([sqlparse.sql.IdentifierList(p.tokens).get_identifiers() for p in parsed])

    for req in requests:
        ti = sqlparse.sql.IdentifierList(req.tokens).get_identifiers()
        for i in ti:
            if isinstance(i, sqlparse.sql.Comment):
                continue
            if not isinstance(i, sqlparse.sql.Identifier):
                continue

            # print('IDENT: {} | {} | {}'.format(str(i).strip().replace('\n', '|'), type(i), i.value))
            itokens = i.value.split()
            global_alias.set_alias(itokens[-1], itokens[0])

        # print('Tokens:')
        # for t in req.tokens:
        #     print('TOKEN: {}'.format(str(t).strip().replace('\n', '|')))

    # get aliases from sections FROM without JOINs..
    # except from line
    # SELECT *
    #     from TableOne to,
    # --------------------------
    #          tabletwo as ttw,
    #          TableThree tth
    # --------------------------

    # TODO: rework
    is_from_section = False
    words = ('where', 'join', 'order', 'select', 'insert', 'update', 'with', 'group')
    for line in text.split('\n'):
        line = line.strip().strip(',')
        if not line:
            continue
        if line.strip().startswith('--'):
            continue
        if line.startswith('from') or ' from' in line:
            line = line.split('from')[1].strip()
            is_from_section = True

        if is_from_section and any(re.match('(^|\s){}'.format(wo), line) for wo in words):
            is_from_section = False

        if is_from_section:
            pattern = r'^([\w]*?)\s(as\s)?([\w]*)'
            aliases_strings = re.findall(pattern, line)
            if aliases_strings:
                for alias in aliases_strings:
                    if alias[0] and alias[2]:
                        global_alias.set_alias(alias[2].strip('\n').strip(), alias[0].strip('\n').strip())
            del aliases_strings
    # debug
    global_alias.alias_list()


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
            sublime.active_window().status_message('Aliases were reloaded.')
        else:
            sublime.active_window().status_message('Text unchanged. Using old aliases.')


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


# def te_get_columns(position=None):
#     ''' get table columns for completions '''
#     # NOTE: Get error: Invalid character value for cast specification (22018):
#     # incorrect casting when like `WHERE int_obj = SOMEFUNC(str_obj)`?
#     # P.S. it works fine on pyodbc 3.0.7
#     # sqlreq_columns = "SELECT c.name FROM sys.columns as c WHERE c.object_id = OBJECT_ID(?)"
#     sqlreq_columns = "SELECT c.name FROM sys.columns as c WHERE c.object_id = ?"

#     te_reload_aliases_from_file()
#     view = sublime.active_window().active_view()
#     if position is None:
#         position = view.sel()[0].begin() - 1
#     table_name = view.substr(view.word(position))

#     columns = []
#     # check auto aliases
#     al = global_alias.get_alias(table_name.lower())
#     if al:
#         table_name = al

#     sqlcon = te_get_connection()
#     if sqlcon.sqlconnection is not None:

#         sql_params = (table_name,)

#         # NOTE: workaround!: check comment at request definition
#         # sqlcon.dbexec(sqlreq_columns, sql_params)
#         sqlcon.dbexec('SELECT OBJECT_ID(?) as object_id', sql_params)
#         object_id = sqlcon.sqldataset[0].object_id

#         if not object_id:
#             return

#         sql_params = (object_id,)
#         sqlcon.dbexec(sqlreq_columns, sql_params)
#         if sqlcon.sqldataset:
#             for row in sqlcon.sqldataset:
#                 column = row.name
#                 if column:
#                     columns.append(('%s\tTable column' % column, column))
#         sqlcon.dbdisconnect()
#     return columns

class ConDispatcher(object):
    drivers = {
        'sqlsrv': ['SQL Server', 'FreeTDS'],
        'postgresql': ['PostgreSQL Unicode(x64)', 'PostgreSQL Unicode(x32)', 'PostgreSQL ANSI(x64)', 'PostgreSQL ANSI(x32)']
    }

    @staticmethod
    def get():
        if ConDispatcher.is_sqlserver():
            return sqlodbccon.ConSQLServer
        elif ConDispatcher.is_postgresqlserver():
            return sqlodbccon.ConPostgreSQLServer
        else:
            return sqlodbccon.SQLCon

    @staticmethod
    def driver():
        server_active = te_get_setting('te_server_active')
        server_list = te_get_setting('te_sql_server')
        drv = server_list[server_active].get('driver', None)
        return drv

    @staticmethod
    def is_sqlserver():
        if ConDispatcher.driver() in ConDispatcher.drivers['sqlsrv']:
            return True
        return False

    @staticmethod
    def is_postgresqlserver():
        if ConDispatcher.driver() in ConDispatcher.drivers['postgresql']:
            return True
        return False


class SQLInfo(object):

    sqlreq_tables = None
    sqlreq_columns = None

    @staticmethod
    def get_connection():
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

            try:
                # sqlcon = postgresqlodbccon.SQLCon(
                sqlcon = ConDispatcher.get()(
                    dsn=dsn,
                    server=server,
                    driver=driver,
                    serverport=server_port,
                    username=username,
                    password=password,
                    database=database,
                    sleepsecs=5,
                    autocommit=autocommit,
                    timeout=timeout
                )
                return sqlcon
            except Exception as e:
                sublime.message_dialog(e.args[1])
        else:
            return None

    def table_name_from_position(position=None):
        te_reload_aliases_from_file()
        view = sublime.active_window().active_view()
        if position is None:
            position = view.sel()[0].begin() - 1
        table_name = view.substr(view.word(position))

        # check auto aliases
        al = global_alias.get_alias(table_name.lower())
        if al:
            table_name = al
        return table_name

    @classmethod
    def get_tables(cls, schema=None):
        ''' get tables list with filter by schema for completions '''

        if not cls.sqlreq_tables:
            return []

        tables = []
        sqlcon = SQLSrvInfo.get_connection()

        if schema is None:
            schema = sqlcon.defaultschema

        if sqlcon.sqlconnection is not None and schema:
            sqlcon.dbexec(cls.sqlreq_tables, (schema,))

            if sqlcon.sqldataset:
                for row in sqlcon.sqldataset:
                    tables.append(('%s\tSQL table' % row.name, row.name))
            sqlcon.dbdisconnect()
        return tables

    @classmethod
    def get_columns(cls, table_name=None, schema=None):
        ''' get table columns for completions '''
        return []

    @staticmethod
    def column_format(column):
        return '{}\tTable column'.format(column)


class SQLSrvInfo(SQLInfo):
    sqlreq_tables = 'SELECT DISTINCT TABLE_NAME as name FROM information_schema.TABLES WHERE TABLE_SCHEMA = ?'

    # NOTE: Get error: Invalid character value for cast specification (22018):
    # incorrect casting when like `WHERE int_obj = SOMEFUNC(str_obj)`?
    # P.S. it works fine on pyodbc 3.0.7
    # sqlreq_columns = "SELECT c.name FROM sys.columns as c WHERE c.object_id = OBJECT_ID(?)"
    sqlreq_columns = "SELECT c.name FROM sys.columns as c WHERE c.object_id = ?"

    @classmethod
    def get_columns(cls, table_name=None, schema=None):
        ''' get table columns for completions '''

        if not table_name or not cls.sqlreq_columns:
            # table_name = SQLSrvInfo.table_name_from_position()
            return []

        columns = []
        sqlcon = SQLSrvInfo.get_connection()
        if sqlcon.sqlconnection is not None:

            # NOTE: workaround!: check comment at request definition
            # sqlcon.dbexec(sqlreq_columns, sql_params)
            sqlcon.dbexec('SELECT OBJECT_ID(?) as object_id', (table_name,))
            object_id = sqlcon.sqldataset[0].object_id

            if not object_id:
                return

            sqlcon.dbexec(cls.sqlreq_columns, (object_id,))
            if sqlcon.sqldataset:
                for row in sqlcon.sqldataset:
                    column = row.name
                    if column:
                        columns.append((SQLInfo.column_format(column), column))
            sqlcon.dbdisconnect()
        return columns


class PostgreSQLInfo(SQLInfo):
    sqlreq_tables = 'SELECT table_name as name FROM information_schema.tables WHERE table_schema=?'
    sqlreq_columns = "SELECT column_name as name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?"

    @classmethod
    def get_columns(cls, table_name=None, schema=None):
        ''' get table columns for completions '''

        if not table_name or not cls.sqlreq_columns:
            # table_name = SQLSrvInfo.table_name_from_position()
            return []

        columns = []
        sqlcon = SQLSrvInfo.get_connection()

        if not schema:
            schema = sqlcon.defaultschema

        if sqlcon.sqlconnection is not None:
            sqlcon.dbexec(cls.sqlreq_columns, (schema, table_name))
            print(table_name, '|', schema, '|', sqlcon.sqldataset)
            if sqlcon.sqldataset:
                for row in sqlcon.sqldataset:
                    column = row.name
                    if column:
                        columns.append((SQLInfo.column_format(column), column))
            sqlcon.dbdisconnect()
        return columns


def te_sql_info():
    if ConDispatcher.is_sqlserver():
        return SQLSrvInfo
    elif ConDispatcher.is_postgresqlserver():
        return PostgreSQLInfo

    return SQLInfo


def te_show_data(title, sql_query, sql_params, setup_columns):
    def cut(val, maxlen):
        if maxlen:
            if len(val) > maxlen:
                return '%s..' % val[:maxlen - 2]
        return val

    cols = te_get_setting(setup_columns, {})
    if cols:
        shortcuts = [
            '[Enter](View query)',
            '[r](Refresh rows)']

        content_header = '%s\n\n' % ' '.join(shortcuts)
        content_header += '## %s\n' % title

        # sqlcon = te_get_connection()
        sqlcon = te_sql_info().get_connection()
        if sqlcon.sqlconnection is not None and sql_query:
            sqlcon.dbexec(sql_query, sql_params)
            rows = sqlcon.sqldataset
            columns_indexes = {v[0]: k for k, v in enumerate(sqlcon.sqlcolumns)}
            sqlcon.dbdisconnect()

        content_header += 'Total processes: %s\n\n' % len(rows)

        table_data = []

        if rows:
            table_header = [col['colname'] for col in cols]
            table_data.append(table_header)
            for row in rows:
                table_row = []
                for col in cols:

                    value = ''
                    maxlen = col.get('maxlen', None)
                    col_prop = col['prop']

                    value = str(row[columns_indexes.get(col_prop)]).strip().replace('\r', ' ')
                    if maxlen:
                        value = ' '.join(value.splitlines())
                        value = cut(value, maxlen)

                    table_row.append(value)
                table_data.append(table_row)
        else:
            table_data.append(['  No data found  '])

        table_text = SingleTable(table_data).table

        return ''.join(
            [
                content_header,
                table_text
            ]
        )
