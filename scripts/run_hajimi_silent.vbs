' 赛博养Gemini · 无窗口静默常驻后台启动器 (VBS)
Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptPath = WScript.ScriptFullName
scriptFolder = fso.GetParentFolderName(scriptPath)
projectRoot = fso.GetParentFolderName(scriptFolder)
ws.CurrentDirectory = projectRoot

pythonExe = "pythonw.exe"
If fso.FileExists("F:\开发工具\VSCode\tools\python\pythonw.exe") Then
    pythonExe = "F:\开发工具\VSCode\tools\python\pythonw.exe"
End If

serverScript = projectRoot & "\src\hajimi_web_ui.py"

cmd = chr(34) & pythonExe & chr(34) & " " & chr(34) & serverScript & chr(34) & " --no-browser"
ws.Run cmd, 0, False
