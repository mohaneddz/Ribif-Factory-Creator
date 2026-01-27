@echo off
set ROOT_DIR=%~dp0
set OUTPUT_FILE=%ROOT_DIR%combined.txt

if exist "%OUTPUT_FILE%" del "%OUTPUT_FILE%"

for /r "%ROOT_DIR%" %%f in (*.py) do (
    echo.>>"%OUTPUT_FILE%"
    echo ---->>"%OUTPUT_FILE%"
    echo %%f>>"%OUTPUT_FILE%"
    echo ---->>"%OUTPUT_FILE%"
    echo.>>"%OUTPUT_FILE%"

    type "%%f">>"%OUTPUT_FILE%"

    echo.>>"%OUTPUT_FILE%"
    echo --- >>"%OUTPUT_FILE%"
    echo %%f>>"%OUTPUT_FILE%"
    echo --- >>"%OUTPUT_FILE%"
)
