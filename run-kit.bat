@echo off
rem Fallback when kit.exe does not start: needs Python 3.12 from python.org ("py" launcher). No other packages.
cd /d "%~dp0"
py -3 kit.py %*
pause
