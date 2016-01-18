#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os.path
import sublime

pythonver = sys.version_info[0]

st_version = 2
if int(sublime.version()) > 3000:
    st_version = 3

odbc_lib_path = os.path.join(os.path.dirname(__file__), 'lib', 'st%d_%s_%s' % (st_version, sublime.platform(), sublime.arch()))
sys.path.append(odbc_lib_path)
try:
    import pyodbc
    print('TSQLEasy: PyODBC was loaded successfully.')
except (ImportError) as e:
    print('TSQLEasy: PyODBC is not available: %s' % e)


class SQLCon:

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
        self.defaultschema = self._get_default_schema()

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

    def _get_default_schema(self):
        if self.sqlconnection is not None:
            self.dbexec('SELECT SCHEMA_NAME()')
            if self.sqldataset:
                return self.sqldataset[0][0]

    def dbconnect(self):
        self.sqlconnection = None
        self.sqlcursor = None
        try:
            self.sqlconnection = pyodbc.connect(self.connection_string, autocommit=self.autocommit, timeout=self.timeout)
            if self.autocommit:
                self.sqlconnection.autocommit = True
            self.sqlcursor = self.sqlconnection.cursor()
        except Exception:
            raise

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
            raise

        try:
            self.sqlcolumns = self.sqlcursor.description
            self.sqldataset = self.sqlcursor.fetchall()
        except pyodbc.ProgrammingError as e:
            if str(e).startswith('No results'):
                pass
            else:
                raise
        except Exception as e:
            raise
