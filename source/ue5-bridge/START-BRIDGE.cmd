@echo off
if not defined DAOC_INSTALL (echo Set DAOC_INSTALL to your playable folder first. & exit /b 1)
dotnet run --project "%~dp0Launcher\BridgeLauncher.csproj" -- %*
