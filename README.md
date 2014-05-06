# Sublime Text plugin: TSQL Easy

[TSQL Easy](https://github.com/tosher/TSQLEasy) is a plugin for Sublime Text editor (ver. 2/3) that adds possibility to read/write/execute sql requests to Microsoft SQL Server and some IDE-like functionality.
Server connections based on [pyODBC](https://code.google.com/p/pyodbc/) library.

## Main features
* Manage connections to SQL Servers.
* Execute sql requests on SQL Server.
* Completions of table names from server.
* Completions of table columns from server.
* Possibility to receive code of procedure, functions by text under cursor.
* Possibility to open local code of procedures (functions, etc.) with the same name (**ProcedureName** -> **ProcedureName.sql**) by text under cursor.
* Improved syntax highlighting for TSQL.

**Warning!** Require server connection for work or use fake server with empty **driver** value for work offline without completions, etc.

### PyODBC
Now, package includes pyODBC versions:
* Windows: ST2/3 x32/x64
* Linux: ST2/3 x64
* Pull request are welcome! :)

## Install

### Package Control
The easiest way to install this is with [Package Control](http://wbond.net/sublime\_packages/package\_control).

 * If you just went and installed Package Control, you probably need to restart Sublime Text before doing this next bit.
 * Bring up the Command Palette (Command+Shift+p on OS X, Control+Shift+p on Linux/Windows).
 * **Temporary!** Select "Package Control: Add Repository" and add
 <pre>
 https://github.com/tosher/TSQLEasy.git
 </pre>
 * Select "Package Control: Install Package" (it'll take a few seconds)
 * Select TSQL Easy when the list appears.

Package Control will automatically keep **TSQL Easy** up to date with the latest version.

### Other methods
First find your Sublime Text 2 Packages folder:

    - OS X: ~/Library/Application Support/Sublime Text 2/Packages/
    - Windows: %APPDATA%/Sublime Text 2/Packages/
    - Linux: ~/.Sublime Text 2/Packages/

If you have Git, you can clone this repo to "/packages-folder/TSQLEasy/"
<pre>
git clone --recursive git://github.com/tosher/TSQLEasy.git
</pre>
or,

Download this repo using the "ZIP" button above, unzip and place the files in "/packages-folder/TSQLEasy/"

