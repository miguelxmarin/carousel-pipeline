@echo off
REM ============================================================
REM  Carousel Pipeline - Daily Run
REM  Runs every day automatically via Windows Task Scheduler.
REM  Generates content, slides, and posts EN + FR + ES.
REM ============================================================

set PIPELINE_DIR=C:\Users\migue\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\6a9b2b5d-e3e4-44a1-9547-4f5b15cd23fc\3761d0e1-454c-4368-a0da-df4778e9ccc1\skills\carousel-pipeline
set PYTHON=C:\Users\migue\AppData\Local\Programs\Python\Python313\python.exe
set LOG_DIR=%PIPELINE_DIR%\logs

cd /d "%PIPELINE_DIR%"

echo [%DATE% %TIME%] Starting carousel pipeline... >> "%LOG_DIR%\scheduler.log"

"%PYTHON%" scripts\daily_run.py --langs en,fr,es --analytics >> "%LOG_DIR%\scheduler.log" 2>&1

echo [%DATE% %TIME%] Pipeline finished. >> "%LOG_DIR%\scheduler.log"
