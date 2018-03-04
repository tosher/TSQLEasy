#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

from datetime import datetime
import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasyActivityMonitorCommand(sublime_plugin.TextCommand):
    # OUTER APPLY Fn_get_sql(sp.sql_handle)
    # NOTE: pyodbc return empty result with comment like:
    # -- OUTER APPLY sys.dm_exec_sql_text(sp.sql_handle)
    sql_query = '''
    SELECT
        sp.spid,
        /* TEXT as query, */
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
    /* OUTER APPLY sys.dm_exec_sql_text(sp.sql_handle) */
    WHERE sp.spid > ?
    ORDER BY sp.spid
    '''

    def run(self, edit):
        view = self.prepare_view(edit)
        self.show(view)

    def set_title(self, view):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.title = 'Activity monitor (at %s)' % current_time
        view.set_name(self.title)

    def prepare_view(self, edit):
        view = self.view.window().new_file()
        view.settings().set('te_activity_monitor', True)
        syntax_file = utils.te_get_setting('te_report_syntax', utils.DEFAULT_REPORT_SYNTAX)
        view.set_syntax_file(syntax_file)
        return view

    def show(self, view):
        self.set_title(view)
        min_pid = utils.te_get_setting('te_activity_monitor_min_pid', 50)
        sql_params = (min_pid,)
        text = utils.te_show_data(title=self.title, sql_query=self.sql_query, sql_params=sql_params, setup_columns='te_activity_monitor_columns')
        view.settings().set("word_wrap", False)
        view.run_command('tsql_easy_insert_text', {'position': 0, 'text': text + '\n\n'})
        view.set_scratch(True)
        view.set_read_only(True)


class TsqlEasyActivityMonitorRefreshCommand(TsqlEasyActivityMonitorCommand):

    def prepare_view(self, edit):
        view = self.view
        view.set_read_only(False)
        view.erase(edit, sublime.Region(0, view.size()))
        return view

    def is_visible(self, *args):
        is_actmon = self.view.settings().get('te_activity_monitor', False)

        if is_actmon:
            return True
        return False
