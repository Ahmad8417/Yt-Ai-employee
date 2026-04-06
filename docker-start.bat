@echo off
REM Docker Startup Script for Windows
REM AI Employee Gold Tier - Docker Compose Management

echo.
echo ==========================================
echo    AI Employee - Gold Tier Docker Manager
echo ==========================================
echo.

REM Check if .env exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Copying from .env.example...
    copy .env.example .env
    echo.
    echo Please edit .env with your configuration before continuing.
    echo.
    notepad .env
    exit /b 1
)

REM Menu
:menu
cls
echo.
echo ==========================================
echo    AI Employee - Gold Tier Docker Manager
echo ==========================================
echo.
echo  1. Start all services (first time setup)
echo  2. Start services (background)
echo  3. Stop all services
echo  4. Restart services
echo  5. View logs
echo  6. Check status
echo  7. Open Odoo (http://localhost:8069)
echo  8. Open pgAdmin (http://localhost:5050)
echo  9. Backup database
echo  10. Clean up (WARNING: removes data!)
echo  0. Exit
echo.
set /p choice="Enter choice: "

if "%choice%"=="1" goto first_time
if "%choice%"=="2" goto start_bg
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto status
if "%choice%"=="7" goto open_odoo
if "%choice%"=="8" goto open_pgadmin
if "%choice%"=="9" goto backup
if "%choice%"=="10" goto cleanup
if "%choice%"=="0" goto end
goto menu

:first_time
echo.
echo Building and starting all services...
docker-compose up -d --build
echo.
echo Waiting for services to initialize...
timeout /t 30 /nobreak >nul
echo.
echo Checking service health...
docker-compose ps
echo.
echo.
echo ==========================================
echo Services started! Access URLs:
echo   Odoo:       http://localhost:8069
echo   pgAdmin:    http://localhost:5050
echo ==========================================
echo.
echo IMPORTANT: Complete Odoo setup at http://localhost:8069
echo   1. Create database with credentials from .env
echo   2. Install Accounting module
echo   3. Configure API access
echo.
pause
goto menu

:start_bg
echo.
echo Starting services in background...
docker-compose up -d
echo.
echo Services started!
docker-compose ps
pause
goto menu

:stop
echo.
echo Stopping services...
docker-compose down
echo.
echo Services stopped.
pause
goto menu

:restart
echo.
echo Restarting services...
docker-compose restart
echo.
echo Services restarted.
docker-compose ps
pause
goto menu

:logs
echo.
echo Viewing logs (Press Ctrl+C to stop)...
docker-compose logs -f
goto menu

:status
echo.
echo Service Status:
docker-compose ps
echo.
pause
goto menu

:open_odoo
echo.
echo Opening Odoo in browser...
start http://localhost:8069
goto menu

:open_pgadmin
echo.
echo Opening pgAdmin in browser...
start http://localhost:5050
goto menu

:backup
echo.
echo Creating backup...
set BACKUP_DATE=%date:~-4,4%%date:~-10,2%%date:~-7,2%
docker-compose exec db pg_dump -U odoo ai_employee_db > backup_%BACKUP_DATE%.sql
echo Backup saved to: backup_%BACKUP_DATE%.sql
pause
goto menu

:cleanup
echo.
echo WARNING: This will delete all data including:
echo   - Odoo database
echo   - All invoices and accounting data
echo   - pgAdmin configuration
echo.
echo Are you sure? (Type YES to confirm)
set /p confirm="Confirm: "
if "%confirm%"=="YES" (
    docker-compose down -v
    echo.
    echo All data has been removed.
) else (
    echo.
    echo Cleanup cancelled.
)
pause
goto menu

:end
echo.
echo Goodbye!
exit /b 0
