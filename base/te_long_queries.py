#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

from datetime import datetime
import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasyLongQueriesCommand(sublime_plugin.TextCommand):

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

    def run(self, edit):
        view = self.prepare_view(edit)
        self.show(view)

    def set_title(self, view):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.title = 'Long running queries (at %s)' % current_time
        view.set_name(self.title)

    def prepare_view(self, edit):
        view = self.view.window().new_file()
        view.settings().set('te_long_queries', True)
        syntax_file = utils.te_get_setting('te_report_syntax', utils.DEFAULT_REPORT_SYNTAX)
        view.set_syntax_file(syntax_file)
        return view

    def show(self, view):
        self.set_title(view)
        text = utils.te_show_data(title=self.title, sql_query=self.sql_query, sql_params=None, setup_columns='te_long_queries_columns')
        view.settings().set("word_wrap", False)
        view.run_command('tsql_easy_insert_text', {'position': 0, 'text': text + '\n\n'})
        view.set_scratch(True)
        view.set_read_only(True)

    def is_visible(self, *args):
        if utils.ConDispatcher.is_sqlserver():
            return True
        return False


class TsqlEasyLongQueriesRefreshCommand(TsqlEasyLongQueriesCommand):

    def prepare_view(self, edit):
        view = self.view
        view.set_read_only(False)
        view.erase(edit, sublime.Region(0, self.view.size()))
        return view

    def is_visible(self, *args):
        is_longq = self.view.settings().get('te_long_queries', False)

        if is_longq:
            return True
        return False
