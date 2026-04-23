@echo off
rem Edit KIRO_ENV_FILE to the absolute path of your .env file
set KIRO_ENV_FILE=D:\code\kiro-router\.env
powershell -WindowStyle Hidden -Command "& '%USERPROFILE%\.local\bin\kiro-gateway.exe'"
