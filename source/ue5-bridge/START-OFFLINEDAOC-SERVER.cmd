@echo off
setlocal
title OfflineDAoC - Server launcher
if not defined DAOC_INSTALL (
    echo Set DAOC_INSTALL to your playable OfflineDAoC folder first.
    pause
    exit /b 1
)
set "DOTNET_ROOT=%DAOC_INSTALL%\tools\dotnet"
set "DOTNET_ROOT_X64=%DOTNET_ROOT%"
set "DOTNET_MULTILEVEL_LOOKUP=0"
if not exist "%DOTNET_ROOT%\dotnet.exe" (
    echo The bundled .NET runtime was not found in the selected installation.
    pause
    exit /b 1
)
if not exist "%DAOC_INSTALL%\runtime\OfflineDAoC.dll" (
    echo The normal OfflineDAoC launcher was not found in the selected installation.
    pause
    exit /b 1
)
pushd "%DAOC_INSTALL%\runtime"
"%DOTNET_ROOT%\dotnet.exe" "%DAOC_INSTALL%\runtime\OfflineDAoC.dll"
set "DAOC_LAUNCHER_EXIT=%ERRORLEVEL%"
popd
if not "%DAOC_LAUNCHER_EXIT%"=="0" (
    echo The OfflineDAoC launcher exited with code %DAOC_LAUNCHER_EXIT%.
    pause
)
exit /b %DAOC_LAUNCHER_EXIT%
