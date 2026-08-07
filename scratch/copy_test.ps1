
$shell = New-Object -ComObject Shell.Application
$myComp = $shell.NameSpace(17)
$device = $myComp.Items() | Where-Object { $_.Name -like "*D90*" }
Write-Host "Device:" $device.Name
if ($device) {
    $storage = $device.GetFolder().Items() | Select-Object -First 1
    Write-Host "Storage:" $storage.Name
    $dcim = $storage.GetFolder().Items() | Where-Object { $_.Name -eq "DCIM" }
    Write-Host "DCIM:" $dcim.Name
    $folder100 = $dcim.GetFolder().Items() | Select-Object -First 1
    Write-Host "Folder100:" $folder100.Name
    $pic1 = $folder100.GetFolder().Items() | Select-Object -First 1
    Write-Host "Found pic:" $pic1.Name
    $destDir = "C:\workbin4py\usbapp_autorun_v2\scratch\test_copy"
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    $destFolder = $shell.NameSpace($destDir)
    $destFolder.CopyHere($pic1, 16)
    Start-Sleep -Seconds 3
    Get-ChildItem $destDir
}
