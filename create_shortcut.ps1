$ws = New-Object -ComObject WScript.Shell
$startupPath = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup\EnglishTeacherBot.lnk")
$shortcut = $ws.CreateShortcut($startupPath)
$shortcut.TargetPath = "c:\Users\genev\Desktop\2333\start_bot.bat"
$shortcut.WorkingDirectory = "c:\Users\genev\Desktop\2333"
$shortcut.WindowStyle = 7
$shortcut.Save()
Write-Host "Shortcut created at: $startupPath"
