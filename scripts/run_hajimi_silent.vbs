' 赛博养Gemini · 无窗口静默常驻后台启动器 (VBS)
Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取工程根目录 (脚本所在目录的上一级)
scriptPath = WScript.ScriptFullName
scriptFolder = fso.GetParentFolderName(scriptPath)
projectRoot = fso.GetParentFolderName(scriptFolder)

' 切换工作目录到工程根目录
ws.CurrentDirectory = projectRoot

' 探测 pythonw.exe (无窗口静默执行器)
pythonExe = "pythonw.exe"
If fso.FileExists("F:\开发工具\VSCode\tools\python\pythonw.exe") Then
    pythonExe = "F:\开发工具\VSCode\tools\python\pythonw.exe"
End If

cmd = """" & pythonExe & """ ""src\hajimi_web_ui.py"" --no-browser"

' 0 = 隐藏所有黑框与控制台窗口，后台静默常驻；False = 启动后立即退出当前 VBS 宿主
ws.Run cmd, 0, False
