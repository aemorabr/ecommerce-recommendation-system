@echo off
REM PostgreSQL Container Management Script

if "%1"=="" goto usage
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="status" goto status
if "%1"=="logs" goto logs
if "%1"=="shell" goto shell
if "%1"=="remove" goto remove
goto usage

:start
echo Starting PostgreSQL container...
podman start ecommerce-postgres
if %errorlevel% neq 0 (
    echo Container doesn't exist. Creating new one...
    podman run -d ^
      --name ecommerce-postgres ^
      -e POSTGRES_DB=ecommerce ^
      -e POSTGRES_USER=postgres ^
      -e POSTGRES_PASSWORD=postgres ^
      -p 5432:5432 ^
      postgres:15-alpine
    echo Waiting for PostgreSQL to be ready...
    timeout /t 10 /nobreak >nul
)
echo PostgreSQL is running!
goto end

:stop
echo Stopping PostgreSQL container...
podman stop ecommerce-postgres
echo PostgreSQL stopped!
goto end

:restart
echo Restarting PostgreSQL container...
podman restart ecommerce-postgres
echo PostgreSQL restarted!
goto end

:status
echo PostgreSQL Container Status:
podman ps -a --filter name=ecommerce-postgres
echo.
echo Connection test:
podman exec ecommerce-postgres pg_isready -U postgres
goto end

:logs
echo PostgreSQL Container Logs:
podman logs ecommerce-postgres
goto end

:shell
echo Connecting to PostgreSQL shell...
podman exec -it ecommerce-postgres psql -U postgres -d ecommerce
goto end

:remove
echo Stopping and removing PostgreSQL container...
podman stop ecommerce-postgres 2>nul
podman rm ecommerce-postgres
echo PostgreSQL container removed!
goto end

:usage
echo Usage: postgres-podman.bat [command]
echo.
echo Commands:
echo   start    - Start PostgreSQL container
echo   stop     - Stop PostgreSQL container
echo   restart  - Restart PostgreSQL container
echo   status   - Show container status
echo   logs     - Show container logs
echo   shell    - Connect to PostgreSQL shell
echo   remove   - Stop and remove container
echo.
echo Examples:
echo   postgres-podman.bat start
echo   postgres-podman.bat shell
echo   postgres-podman.bat logs
goto end

:end
