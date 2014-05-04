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

    def __init__(self, server='127.0.0.1', driver='SQL Server', serverport="1433", username="",
                 password="", database="", sleepsecs=5, autocommit=True):
        self.driver = driver
        self.server = server
        self.serverport = serverport
        self.username = username
        self.password = password
        self.database = database
        self.sleepsecs = int(sleepsecs)
        self.autocommit = autocommit
        self.connection_string = self._get_connection_string()
        self.sqlconnection = None
        self.sqlcursor = None
        self.dbconnect()

    def _get_connection_string(self):
        return 'DRIVER={%s};SERVER=%s,%s;DATABASE=%s;UID=%s;PWD=%s' % (self.driver, self.server, self.serverport, self.database, self.username, self.password)

    def dbconnect(self):
        self.sqlconnection = None
        self.sqlcursor = None
        try:
            self.sqlconnection = pyodbc.connect(self.connection_string, autocommit=self.autocommit)
            if self.autocommit:
                self.sqlconnection.autocommit = True
            self.sqlcursor = self.sqlconnection.cursor()
        except pyodbc.IntegrityError as e:
            print("SQL IntegrityError exception: %s" % e)
        except pyodbc.DataError as e:
            print("SQL DataError exception: %s" % e)
        except pyodbc.ProgrammingError as e:
            print("SQL ProgrammingError exception: %s" % e)
        except pyodbc.DatabaseError as e:
            print("SQL DatabaseError exception: %s" % e)
        except Exception as e:
            print("SQL Unknown exception: %s" % e)

    def dbdisconnect(self):
        if self.sqlconnection:
            self.sqlconnection.close()

    def dbexec(self, sql_string, sql_params=None):
        if sql_params is None:
            sql_params = []

        if not isinstance(sql_params, list):
            raise Exception('Wrong sql_params type: %s' % type(sql_params))

        if self.sqlcursor is None or self.sqlconnection is None:
            raise Exception("SQL: No connection to server")

        try:
            if sql_params:
                self.sqlcursor.execute(sql_string, sql_params)
            else:
                self.sqlcursor.execute(sql_string)
            try:
                # columns names, props..
                self.sqlcolumns = self.sqlcursor.description
                self.sqldataset = self.sqlcursor.fetchall()
            except pyodbc.OperationalError as e:
                print('OperationalError exception: %s' % e)
                self.sqldataset = []
            except Exception as e:
                print('Unknown exception: %s' % e)
                self.sqldataset = []
        except pyodbc.ProgrammingError as e:
            print("SQL ProgrammingError exception: %s" % e)
            self.sqldataset = []
        except pyodbc.DatabaseError as e:
            print("SQL DatabaseError exception: %s - %s" % (e[0], e[1].replace("\n", ".")))
            self.sqldataset = []
        except Exception as e:
            print('Unknown exception: %s' % e)
            self.sqldataset = []
