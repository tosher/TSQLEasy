#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasyShowQueryCommand(sublime_plugin.TextCommand):
    TABLE_SPLIT_CHAR = '│'

    sql_query_actmon = '''
    SELECT
        TEXT AS query,
        sp.status,
        sp.blocked
    FROM sys.sysprocesses as sp
    OUTER APPLY sys.dm_exec_sql_text(sp.sql_handle)
    WHERE sp.spid = ?
    '''

    # TODO: Plan show
    # --CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) st2
    sql_query_longq = '''
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

    def run(self, edit):

        row_id = None
        try:
            line = self.view.substr(self.view.line(self.view.sel()[0].end()))
            row_id = line.split(self.TABLE_SPLIT_CHAR)[1].strip()  # TODO: require ID in first column
        except Exception:
            pass

        if row_id:
            self.get_query(row_id)

    def get_query(self, row_id):

        long_queries = self.view.settings().get('te_long_queries', False)
        activity_monitor = self.view.settings().get('te_activity_monitor', False)

        if activity_monitor:
            sql_query = self.sql_query_actmon
        elif long_queries:
            sql_query = self.sql_query_longq
        else:
            self.view.window().status_message('Error: Unknown mode')

        if row_id:
            # sqlcon = utils.te_get_connection()
            sqlcon = utils.te_sql_info().get_connection()
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
                    self.view.show(index_of_textend + 1)
                    self.view.sel().clear()
                    self.view.sel().add(index_of_textend + 1)
                    self.view.set_read_only(True)

                sqlcon.dbdisconnect()
        else:
            self.view.window().status_message('Error: ROW ID is not found')

    def is_visible(self, *args):
        is_actmon = self.view.settings().get('te_activity_monitor', False)
        is_longq = self.view.settings().get('te_long_queries', False)

        if is_actmon or is_longq:
            return True
        return False
