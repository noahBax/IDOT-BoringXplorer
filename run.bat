set CURR_DIR=%~dp0
cd /d "%CURR_DIR%"
call Scripts\activate
python ProcessingReports\index.py
deactivate
