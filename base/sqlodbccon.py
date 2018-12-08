#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os.path
import sublime


odbc_lib_path = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        'lib',
        'st3_%s_%s' % (sublime.platform(), sublime.arch())
    )
)

sys.path.append(odbc_lib_path)

# macos workable hint to use system lib
# sys.path.append('~/.pyenv/versions/3.3.6/lib/python3.3/site-packages')

try:
    import pyodbc
    print('TSQLEasy: PyODBC was loaded successfully.')
except (ImportError) as e:
    print('TSQLEasy: PyODBC is not available: %s' % e)


class SQLCon(object):

    defaultschema = None

    def __init__(self, dsn=None, server='127.0.0.1', driver='SQL Server', serverport=1433, username="",
                 password="", database="", sleepsecs=5, autocommit=True, timeout=0):

        self.dsn = dsn
        self.driver = driver
        self.server = server
        self.serverport = serverport
        self.username = username
        self.password = password
        self.database = database
        self.sleepsecs = int(sleepsecs)
        self.autocommit = autocommit
        self.timeout = timeout
        self.connection_string = self._get_connection_string()
        self.sqlconnection = None
        self.sqlcursor = None
        self.dbconnect()
        # self.defaultschema = self._get_default_schema()

    def _get_connection_string(self):
        if not self.dsn:
            driver = 'DRIVER={%s}' % self.driver
            server = 'SERVER=%s,%s' % (self.server, self.serverport) if self.serverport else 'SERVER=%s' % (self.server)
        else:
            driver = None
            server = 'DSN=%s' % self.dsn

        db = 'DATABASE=%s' % self.database

        if not self.username:
            auth = 'Trusted_Connection=yes'
        else:
            # password escaping for SQL Server
            auth_format = 'UID=%s;PWD={%s}' if driver == 'SQL Server' else 'UID=%s;PWD=%s'
            auth = auth_format % (self.username, self.password)

        connection_string = ';'.join([val for val in [driver, server, db, auth] if val])

        return connection_string

    # def _get_default_schema(self):
    #     if self.sqlconnection is not None:
    #         self.dbexec('SELECT SCHEMA_NAME()')
    #         if self.sqldataset:
    #             return self.sqldataset[0][0]

    def dbconnect(self):
        self.sqlconnection = None
        self.sqlcursor = None
        try:
            self.sqlconnection = pyodbc.connect(self.connection_string, autocommit=self.autocommit, timeout=self.timeout)
            # self.sqlconnection.setencoding('utf-8')
            if self.autocommit:
                self.sqlconnection.autocommit = True
            self.post_connection_setup()
            self.sqlcursor = self.sqlconnection.cursor()
        except Exception:
            raise

    def post_connection_setup(self):
        pass

    def dbdisconnect(self):
        if self.sqlconnection:
            self.sqlconnection.close()

    def dbexec(self, sql_string, sql_params=None):

        self.sqldataset = []
        self.sqlcolumns = ()

        if sql_params is None:
            sql_params = []

        if not isinstance(sql_params, list) and not isinstance(sql_params, tuple):
            raise Exception('Wrong sql_params type: %s' % type(sql_params))

        if self.sqlcursor is None or self.sqlconnection is None:
            raise Exception("SQL: No connection to server")

        try:
            self.sqlcursor.execute(sql_string, sql_params)
        except Exception as e:
            raise Exception('Error while request execution: %s, query: %s, params: %s' % (e, sql_string, sql_params))

        try:
            self.sqlcolumns = self.sqlcursor.description
            self.sqldataset = self.sqlcursor.fetchall()
        except pyodbc.ProgrammingError as e:
            if str(e).startswith('No results'):
                pass
            else:
                raise(e)
        except Exception as e:
            raise(e)


class ConSQLServer(SQLCon):
    defaultschema = None

    def __init__(self, dsn=None, driver='SQL Server', server='127.0.0.1', serverport=1433,
                 username="", password="", database="",
                 sleepsecs=5, autocommit=True, timeout=0):

        # super(ConSQLServer, self).__init__(
        super().__init__(
            dsn=dsn, driver=driver, server=server, serverport=serverport,
            username=username, password=password, database=database,
            sleepsecs=sleepsecs, autocommit=autocommit, timeout=timeout)

        self.defaultschema = self._get_default_schema()

    def _get_default_schema(self):
        if self.sqlconnection is not None:
            self.dbexec('SELECT SCHEMA_NAME()')
            if self.sqldataset:
                return self.sqldataset[0][0]


class ConPostgreSQLServer(SQLCon):
    defaultschema = None

    def __init__(self, dsn=None, driver='"PostgreSQL Unicode(x64)"', server='127.0.0.1', serverport=5432,
                 username="", password="", database="",
                 sleepsecs=5, autocommit=True, timeout=0):

        # super(ConSQLServer, self).__init__(
        super().__init__(
            dsn=dsn, driver=driver, server=server, serverport=serverport,
            username=username, password=password, database=database,
            sleepsecs=sleepsecs, autocommit=autocommit, timeout=timeout)

        self.defaultschema = self._get_default_schema()

    def _get_default_schema(self):
        if self.sqlconnection is not None:
            self.dbexec('SELECT current_schema();')
            if self.sqldataset:
                return self.sqldataset[0][0]

    def post_connection_setup(self):
        self.sqlconnection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
        self.sqlconnection.setencoding(encoding='utf-8')
