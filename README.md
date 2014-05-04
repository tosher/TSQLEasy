# Sublime Text plugin: TSQL Easy

[TSQL Easy](https://github.com/tosher/TSQLEasy) is a plugin for Sublime Text editor (ver. 2/3) that adds possibility to read/write/execute sql requests to Microsoft SQL Server through the use of pyodbc library.

## Main features
* Execute the selected text as sql request to SQL Server.
* Get table list from SQL server
* Get table columns list from SQL server
* Improved syntax highlighting for TSQL.

## Install

<del>
### Package Control

The easiest way to install this is with [Package Control](http://wbond.net/sublime\_packages/package\_control).

 * If you just went and installed Package Control, you probably need to restart Sublime Text 2 before doing this next bit.
 * Bring up the Command Palette (Command+Shift+p on OS X, Control+Shift+p on Linux/Windows).
 * Select "Package Control: Install Package" (it'll take a few seconds)
 * Select TSQL Easy when the list appears.

Package Control will automatically keep Mediawiker up to date with the latest version.
</del>

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

