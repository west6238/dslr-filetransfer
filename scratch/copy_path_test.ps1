$shell = New-Object -ComObject Shell.Application
$myComp = $shell.NameSpace(17)
$device = $myComp.Items() | Where-Object { $_.Name -like "*D90*" }
$storage = $device.GetFolder().Items() | Select-Object -First 1
$dcim = $storage.GetFolder().Items() | Where-Object { $_.Name -eq "DCIM" }
$folder100 = $dcim.GetFolder().Items() | Select-Object -First 1
$pic1 = $folder100.GetFolder().Items() | Select-Object -First 1
$destDir = "C:\workbin4py\usbapp_autorun_v2\scratch\test_copy"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
$destFolder = $shell.NameSpace($destDir)

Write-Host "Copying path:" $pic1.Path
$destFolder.CopyHere($pic1.Path)

Start-Sleep -Seconds 3
Get-ChildItem $destDir
