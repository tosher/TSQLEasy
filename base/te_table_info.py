#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import te_utils as utils


class TsqlEasyTableInfoCommand(sublime_plugin.TextCommand):
    res_view = None
    DDL_CMD = '''
    declare @nome sysname = '{table}'
    declare
      @table sysname,
      @schema sysname

    select
      @table = parsename(@nome, 1),
      @schema = isnull(parsename(@nome, 2), 'dbo');

    with columndef (tablename, colname, colnum, calc, decla, ident, declb)
    as (
      select
        tablename = i.table_name,
        colname = i.column_name,
        colnum = i.ordinal_position,
        calc = case when
          cp.definition is not null then
            ' as ' + cp.definition
            else null
        end,
        decla = case
          when (data_type in ('varchar', 'nvarchar', 'char',
            'nchar', 'binary', 'varbinary')) then
            case
              when (character_maximum_length = -1) then
                data_type + '(max)'
              else data_type + '(' +
               convert(varchar(6), character_maximum_length) + ')'
            end
          when (data_type in ('decimal', 'numeric')) then
              data_type + '(' + convert(varchar(4), numeric_precision) +
                ',' + convert(varchar(4), numeric_scale) + ')'
          when (data_type in ('bit', 'money', 'smallmoney', 'int', 'smallint',
            'tinyint', 'bigint', 'date', 'time', 'datetime', 'smalldatetime',
            'datetime2', 'datetimeoffset', 'datetime2', 'float',
            'real', 'text', 'ntext', 'image',
            'timestamp', 'uniqueidentifier', 'xml')) then
            data_type
          else 'unknown type'
        end,
        ident = case when (select columnproperty(object_id(t.table_name),
          i.column_name,'IsIdentity')) = 1 then 'identity' else '' end,
        declb = case
          when (i.is_nullable = 'YES') then 'null'
          else 'not null'
        end
      from information_schema.columns i
      join information_schema.tables t on
        t.table_name = i.table_name and t.table_schema = i.table_schema
      left join sys.computed_columns cp on
        cp.object_id = object_id(t.table_name) and cp.name = i.column_name
      where i.table_schema = @schema
        and t.table_type = 'BASE TABLE'
        and i.table_name = @table
      )
    select
      substring((select
            char(10) + colname + ' ' +
            case when calc is not null then calc
            else decla + ' ' + ident + ' ' + declb end
        from columndef
        where tablename = t.tablename
        order by colnum
        for xml path (''))
      , 2, 15000)
    from (select distinct
        tablename
      from columndef) t
    union all
    select '\n-------- Primary Key --------\n'
    union all
    select
      constraint_name + ' ' +
      stuff((select ', ' +
        cast(i.column_name as varchar(50)) [text()]
             from information_schema.key_column_usage i
             where objectproperty(object_id(i.constraint_schema + '.' +
               i.constraint_name), 'isprimarykey') = 1
              and i.table_schema = @schema
              and i.table_name = u.table_name
             for xml path(''), type)
            .value('.','nvarchar(max)'),1,2,' ')
    from information_schema.key_column_usage u
    where objectproperty(object_id(u.constraint_schema + '.' +
      u.constraint_name), 'isprimarykey') = 1
      and u.table_schema = @schema
      and u.table_name = @table
    group by u.table_name, u.constraint_name
    union all
    select '\n-------- Unique Keys --------\n'
    union all
    select
       u.constraint_name + ' ' +
       stuff((select ', ' +
         cast(i.column_name as varchar(50)) [text()]
              from information_schema.constraint_column_usage i
              where objectproperty(object_id(i.constraint_schema + '.' +
                i.constraint_name), 'IsUniqueCnst') = 1
               and i.table_schema = @schema
               and i.table_name = u.table_name
              for xml path(''), type)
             .value('.','nvarchar(max)'),1,2,' ')
     from information_schema.constraint_column_usage u
     where objectproperty(object_id(u.constraint_schema + '.' +
       u.constraint_name), 'IsUniqueCnst') = 1
       and u.table_schema = @schema
       and u.table_name = @table
     group by u.table_name, u.constraint_name
     union all
     select '\n-------- Defaults --------\n'
     union all
     select
         d.name + ' ' + d.definition +
           ' for [' +  c.name + ']' + char(10)
     from sys.default_constraints d
     inner join sys.columns c on
         d.parent_object_id = c.object_id
         and d.parent_column_id = c.column_id
     inner join sys.tables t on
         t.object_id = c.object_id
     where t.schema_id = schema_id(@schema)
       and t.name = @table
    union all
    select '\n-------- Foreign Keys --------\n'
    union all
    select fk.name + ' ' + stuff((select ',' + c.name
      from sys.columns as c
      inner join sys.foreign_key_columns as fkc on
        fkc.parent_column_id = c.column_id
        and fkc.parent_object_id = c.[object_id]
      where fkc.constraint_object_id = fk.[object_id]
      order by fkc.constraint_column_id
      for xml path(N''), type).value(N'.[1]', N'nvarchar(max)'), 1, 1, N'')
      + ' references ' + rs.name + '.' + rt.name
      + '(' + stuff((select ',' + c.name
        from sys.columns as c
        inner join sys.foreign_key_columns as fkc on
          fkc.referenced_column_id = c.column_id
          and fkc.referenced_object_id = c.[object_id]
        where fkc.constraint_object_id = fk.[object_id]
        order by fkc.constraint_column_id
        FOR XML PATH(N''), TYPE).value(N'.[1]', N'nvarchar(max)'),1,1,N'')+')'+
         char(10)
    from sys.foreign_keys as fk
    inner join sys.tables as rt
      on fk.referenced_object_id = rt.[object_id]
    inner join sys.schemas as rs
      on rt.[schema_id] = rs.[schema_id]
    inner join sys.tables as ct
      on fk.parent_object_id = ct.[object_id]
    inner join sys.schemas as cs
      on ct.[schema_id] = cs.[schema_id]
    where rt.is_ms_shipped = 0
      and ct.is_ms_shipped = 0
      and rs.schema_id = schema_id(@schema)
      and rt.schema_id = schema_id(@schema)
      and cs.schema_id = schema_id(@schema)
      and ct.schema_id = schema_id(@schema)
      and fk.parent_object_id = object_id(@table)
    '''

    def run(self, edit):
        if not ('sql' in self.view.settings().get('syntax').lower()):
            return
        table = self.view.substr(self.view.sel()[0])
        if not table:
            return

        panel_name = 'result_panel'
        if not self.res_view:
            self.res_view = sublime.active_window().create_output_panel(panel_name)

        # self.sqlcon = utils.te_get_connection()
        self.sqlcon = utils.te_sql_info().get_connection()
        try:
            self.sqlcon.dbexec(self.DDL_CMD.format(table=table))
        except Exception as e:
            error = '%s: %s' % (type(e).__name__, e.args[1])
            self.view.insert(edit, 0, error)

        data_rows = '-------- table: {table} --------\n'.format(table=table)
        if self.sqlcon.sqldataset:
            for row in self.sqlcon.sqldataset:
                row_list = [self.getval(val) for val in row]
                data_rows += ''.join(row_list)

        data_rows += '\n{}'.format('-' * (26 + len(table)))
        self.res_view.run_command('select_all')
        self.res_view.run_command('right_delete')
        self.res_view.run_command(
            'tsql_easy_insert_text', {
                'position': self.res_view.size(),
                'text': '{}\n'.format(data_rows)
            }
        )
        self.res_view.show(self.res_view.size())
        sublime.active_window().run_command(
            'show_panel',
            {
                'panel': 'output.{}'.format(panel_name)
            }
        )

    def getval(self, value):
        if value is None:
            return '{null}'
        else:
            return str(value)

    def is_visible(self, *args):
        if utils.ConDispatcher.is_sqlserver():
            return True
        return False
