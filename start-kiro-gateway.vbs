Set WshShell = CreateObject("WScript.Shell")
WshShell.Environment("Process")("KIRO_ENV_FILE") = "D:\code\kiro-router\.env"
WshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.local\bin\kiro-gateway.exe""", 0, False
