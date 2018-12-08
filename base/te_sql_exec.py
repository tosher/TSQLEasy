#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os
import time
from datetime import datetime
import sublime
import sublime_plugin
from . import te_utils as utils
sys.path.append(os.path.join(os.path.dirname(__file__), "../libs"))
from ..libs.terminaltables.other_tables import WindowsTable as SingleTable


class TsqlEasyExecSqlCommand(sublime_plugin.TextCommand):

    res_view = None

    def run(self, view, query=None):
        # self.sqlcon = utils.te_get_connection()
        self.sqlcon = utils.te_sql_info().get_connection()
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
                    error = None
                    dt_before = time.time()
                    try:
                        self.sqlcon.dbexec(query)
                    except Exception as e:
                        error = '%s: %s' % (type(e).__name__, e.args[1])
                    dt_after = time.time()
                    timedelta = dt_after - dt_before
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    text += self.result_text(timedelta, current_time, query, error)

            self.sqlcon.dbdisconnect()

            result_in_tab = utils.te_get_setting('te_result_in_tab', False)
            result_in_new_tab = utils.te_get_setting('te_result_in_new_tab', False)

            if result_in_tab:
                if not self.res_view or result_in_new_tab or self.res_view.id() not in [v.id() for v in self.view.window().views()]:
                    self.res_view = self.view.window().new_file()
                self.res_view.set_name('TSQLEasy result (%s)' % current_time)
                self.res_view.settings().set("word_wrap", False)
                self.res_view.run_command('tsql_easy_insert_text', {'position': self.res_view.size(), 'text': text})
                self.view.window().focus_view(self.res_view)

            else:
                panel_name = 'result_panel'
                if not self.res_view:
                    self.res_view = self.view.window().create_output_panel(panel_name)
                self.res_view.run_command('tsql_easy_insert_text', {'position': self.res_view.size(), 'text': text + '\n'})
                self.res_view.show(self.res_view.size())
                self.view.window().run_command("show_panel", {"panel": "output." + panel_name})

            self.view.window().status_message('Executed.')
        else:
            self.view.window().status_message('Nothing to execute.')

    def getval(self, value):
        if value is None:
            return '{null}'
        return str(value)

    def result_text(self, timedelta, received_time, query, error=None):
        show_request_in_result = utils.te_get_setting('te_show_request_in_result', True)
        data_text = '' if error is None else error
        result_data = []

        if not error:
            if self.sqlcon.sqldataset:

                # table header row
                header_list = [val[0] for val in self.sqlcon.sqlcolumns]
                result_data.append(header_list)

                for row in self.sqlcon.sqldataset:
                    row_list = [self.getval(val) for val in row]
                    result_data.append(row_list)

                data_text = SingleTable(result_data).table
            else:
                data_text = 'Completed: result without dataset'

        res_request = ''
        if show_request_in_result:
            res_request = ''.join(
                [
                    '------ SQL request ------',
                    '\n',
                    query,
                    '\n'
                ]
            )

        res_data = ''.join(
            [
                '------ SQL result -------',
                '\n',
                data_text
            ]
        )

        data_stats = ' | '.join(
            [
                'Records count: %s' % (len(result_data) - 1),
                'Rows affected: %s' % self.sqlcon.sqlcursor.rowcount,
                'Execution time: %s secs' % round(timedelta, 3),
                'Received at: %s' % received_time
            ]
        )

        res_stats = ''.join(
            [
                '------ SQL result stats ------',
                '\n',
                data_stats,
                '\n',
                '\n'
            ]
        )

        return '\n'.join([val for val in [res_request, res_data, res_stats] if val])

    def is_visible(self, *args):
        is_console = self.view.settings().get('tsqleasy_is_here', False)
        title = utils.te_get_title()
        if not title:
            return False

        if is_console or title.endswith('.sql'):
            return True
        return False
