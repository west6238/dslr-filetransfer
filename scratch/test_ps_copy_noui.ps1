$ErrorActionPreference = "Stop"

Write-Host "Initializing Shell.Application..."
$shell = New-Object -ComObject Shell.Application
$myComp = $shell.NameSpace(17)

$device = $null
foreach ($item in $myComp.Items()) {
    if ($item.Name -match "D90" -or $item.Name -match "Digital") {
        $device = $item
        break
    }
}

if (-not $device) {
    Write-Host "Camera not found."
    exit
}

Write-Host "Found Camera:" $device.Name

$targetFile = $null

function Find-Image {
    param([System.__ComObject]$folderObj, [int]$depth)
    
    if ($script:targetFile -ne $null -or $depth -gt 5) { return }
    
    foreach ($item in $folderObj.Items()) {
        if ($script:targetFile -ne $null) { break }
        
        if ($item.IsFolder) {
            Find-Image $item.GetFolder() ($depth + 1)
        } else {
            if ($item.Name -match "\.(jpg|jpeg|png|nef|cr2|mp4)$") {
                $script:targetFile = $item
                break
            }
        }
    }
}

Write-Host "Searching for 1 image file..."
Find-Image $device.GetFolder() 0

if (-not $targetFile) {
    Write-Host "No image file found."
    exit
}

Write-Host "Found target:" $targetFile.Name

$destPath = "C:\temp"
if (-not (Test-Path $destPath)) {
    New-Item -ItemType Directory -Force -Path $destPath | Out-Null
}

$destFolder = $shell.NameSpace($destPath)
$targetFilePath = Join-Path $destPath $targetFile.Name

if (Test-Path $targetFilePath) {
    Remove-Item -Force $targetFilePath
}

Write-Host "Starting copy to temp folder..."
$destFolder.CopyHere($targetFile, 0)

Write-Host "Copy command sent. Waiting for completion..."
$timeout = 20
while ($timeout -gt 0) {
    Start-Sleep -Seconds 1
    if (Test-Path $targetFilePath) {
        $info = Get-Item $targetFilePath
        if ($info.Length -gt 0) {
            Write-Host "Copy Success! File size: $($info.Length) bytes"
            exit
        }
    }
    $timeout--
}

Write-Host "Copy timeout or failed."
