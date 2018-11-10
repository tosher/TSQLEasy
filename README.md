# Sublime Text plugin: TSQL Easy

[TSQL Easy](https://github.com/tosher/TSQLEasy) is a plugin for Sublime Text 3 editor that adds possibility to read/write/execute sql requests to Microsoft SQL Server and some IDE-like functionality.
Server connections based on [pyODBC](https://code.google.com/p/pyodbc/) library.

**NOTE**: Sublime text 2 is not supported anymore. Please use Sublime text 3.

## Main features
* Manage connections to SQL Servers.
* Execute sql requests on SQL Server.
* Completions of table names from server.
* Completions of table columns from server.
* Possibility to receive code of procedure, functions by text under cursor.
* Possibility to open local files with the same name as stored procedure (function, etc.): **ProcedureName** -> **ProcedureName.sql**.
* Improved syntax highlighting for TSQL.
* Reports: 
    - Activity monitor
    - Long running queries

**Warning!** Server connection required for full functionality or use fake server with empty **driver** value for work offline without completions, etc.

### PyODBC
Now, package includes [pyODBC](https://code.google.com/p/pyodbc/) (4.0.22) binaries:

* Windows: ST3 x64 (x32 with old pyodbc 3.0.7)
* Linux: ST3 x64
* OSX: ST3 x64

## Commands
* Open console - open new console for sql requests
* Server select - change predefined sql server connection
* Execute - execute the request (<kbd>F5</kbd>)
* Open server object - open procedure or function under cursor from server
* Open local object - open procedure or function under cursor from local path
* Activity monitor (+refresh, +show query)
* Long running queries (+refresh, +show query)

## Install

### Package Control
The easiest way to install this is with [Package Control](http://wbond.net/sublime\_packages/package\_control).

 * If you just went and installed Package Control, you probably need to restart Sublime Text before doing this next bit.
 * Bring up the Command Palette (<kbd>Command</kbd>+<kbd>Shift</kbd>+<kbd>p</kbd> on OS X, <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>p</kbd> on Linux/Windows).
 * Select "Package Control: Install Package" (it'll take a few seconds)
 * Select `TSQL Easy` when the list appears.

Package Control will automatically keep `TSQL Easy` up to date with the latest version.

## Screenshots

SQL Request

![SQL request](https://raw.githubusercontent.com/wiki/tosher/TSQLEasy/images/tsql_easy_scr1.png)

Activity monitor

![SQL request](https://raw.githubusercontent.com/wiki/tosher/TSQLEasy/images/tsql_easy_scr2.png)

Long running queries

![SQL request](https://raw.githubusercontent.com/wiki/tosher/TSQLEasy/images/tsql_easy_scr3.png)
