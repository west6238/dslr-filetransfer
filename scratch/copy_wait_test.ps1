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

Write-Host "CopyHere started for:" $pic1.Name
$destFolder.CopyHere($pic1, 4 + 16)

# Wait up to 15 seconds for Windows Shell Copy to complete
$targetFile = Join-Path $destDir $pic1.Name
for ($i=0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Path $targetFile) {
        $size = (Get-Item $targetFile).Length
        Write-Host "FOUND FILE! Size: $size bytes"
        if ($size -gt 0) {
            Write-Host "COPY COMPLETE SUCCESS!"
            break
        }
    }
}
