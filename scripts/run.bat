@echo off
REM Cursor Settings 한글 패치 - Windows 원클릭 스크립트
REM
REM 사용법:
REM   scripts\run.bat          # 추출 + 패치 적용
REM   scripts\run.bat --revert # 원본 복원
REM   scripts\run.bat --dry-run # 시뮬레이션만 실행
REM   scripts\run.bat --extract-only # 문자열 추출만

setlocal
cd /d "%~dp0\.."

where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] python 또는 python3이 설치되어 있지 않습니다.
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
)

echo.
echo ================================================
echo   Cursor Settings 한글 패치 도구 (Windows)
echo ================================================
echo.

if "%1"=="--revert" (
    echo [INFO] 원본 복원 중...
    %PYTHON% src\patch.py --revert
    echo [OK] 원본 복원 완료! Cursor를 재시작해주세요.
    goto :eof
)

if "%1"=="--dry-run" (
    echo [INFO] 문자열 추출 중...
    %PYTHON% src\extract.py -o translations\strings.json
    echo [INFO] 패치 시뮬레이션 중...
    %PYTHON% src\patch.py -d translations\ko.json --dry-run
    goto :eof
)

if "%1"=="--extract-only" (
    echo [INFO] 문자열 추출 중...
    %PYTHON% src\extract.py -o translations\strings.json
    echo [OK] 추출 완료. translations\ 디렉토리를 확인하세요.
    goto :eof
)

REM 기본: 통합 재패치
%PYTHON% src\repatch.py
echo.
echo [OK] 패치 적용 완료! Cursor를 재시작해주세요.
