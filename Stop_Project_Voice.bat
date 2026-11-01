@echo off
echo Stopping Project Voice...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Project Voice stopped successfully.
pause
