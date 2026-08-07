Add-Type -AssemblyName System.Windows.Forms

$shell = New-Object -ComObject Shell.Application
$myComp = $shell.NameSpace(17)
$device = $myComp.Items() | Where-Object { $_.Name -like "*D90*" }
$storage = $device.GetFolder().Items() | Select-Object -First 1
$dcim = $storage.GetFolder().Items() | Where-Object { $_.Name -eq "DCIM" }
$folder100 = $dcim.GetFolder().Items() | Where-Object { $_.Name -eq "100NCD90" }
$pic1 = $folder100.GetFolder().Items() | Select-Object -First 1

$destDir = "C:\workbin4py\usbapp_autorun_v2\scratch\test_copy"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
$destFolder = $shell.NameSpace($destDir)

Write-Host "Copying pic1:" $pic1.Name
$destFolder.CopyHere($pic1, 16)

$targetFile = Join-Path $destDir $pic1.Name
for ($i=0; $i -lt 30; $i++) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 200
    if (Test-Path $targetFile) {
        $size = (Get-Item $targetFile).Length
        Write-Host "SUCCESS! File created. Size: $size bytes"
        if ($size -gt 0) { break }
    }
}
