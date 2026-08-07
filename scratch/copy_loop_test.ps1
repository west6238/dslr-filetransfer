$shell = New-Object -ComObject Shell.Application
$myComp = $shell.NameSpace(17)
$device = $myComp.Items() | Where-Object { $_.Name -like "*D90*" }
$storage = $device.GetFolder().Items() | Select-Object -First 1
$dcim = $storage.GetFolder().Items() | Where-Object { $_.Name -eq "DCIM" }
$folder100 = $dcim.GetFolder().Items() | Select-Object -First 1
$pic1 = $folder100.GetFolder().Items() | Select-Object -First 1
$destDir = "C:\workbin4py\usbapp_autorun_v2\scratch\test_copy"
$destFolder = $shell.NameSpace($destDir)
Write-Host "Copying:" $pic1.Name "to" $destDir
$destFolder.CopyHere($pic1, 16)

for ($i=0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    $files = Get-ChildItem $destDir
    if ($files.Count -gt 0) {
        Write-Host "Success! Files:" $files.Name
        break
    }
}
