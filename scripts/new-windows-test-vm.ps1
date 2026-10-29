param(
    [string]$IsoPath = (Join-Path (Split-Path $PSScriptRoot -Parent) '.runtime\windows-vm\Windows11.iso')
)
$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$vmName = 'Studio-Release-Test'
$vmFolder = Join-Path $repositoryRoot '.runtime\vm-tests\Studio-Release-Test'

if (-not (Test-Path -LiteralPath $IsoPath -PathType Leaf)) {
    throw "Windows ISO missing: $IsoPath. Supply -IsoPath with the downloaded image's full path."
}
$resolvedIso = (Resolve-Path -LiteralPath $IsoPath).Path
if ([IO.Path]::GetExtension($resolvedIso) -ine '.iso') { throw 'Select a Windows ISO file.' }
if (Test-Path -LiteralPath $vmFolder) { throw "VM directory already exists; preserve it: $vmFolder" }
try {
    $existing = @(Get-VM -ErrorAction Stop)
    if ($existing | Where-Object { $_.Name -eq $vmName }) {
        throw "VM already exists; preserve it: $vmName"
    }
    $switch = @(Get-VMSwitch -Name 'Default Switch' -ErrorAction Stop)
    if ($switch.Count -ne 1) { throw 'Expected one existing Default Switch; no network changes were made.' }
} catch {
    throw "VM preflight failed; no VM was created. Run this script in normal Administrator PowerShell. $($_.Exception.Message)"
}

# Fail before creating a folder if a required Hyper-V command is missing.
foreach ($commandName in @('New-VM', 'Set-VMProcessor', 'Set-VMMemory', 'Set-VMFirmware',
        'Set-VMKeyProtector', 'Enable-VMTPM', 'Add-VMDvdDrive', 'Get-VMDvdDrive')) {
    $null = Get-Command $commandName -ErrorAction Stop
}
try {
    New-Item -ItemType Directory -Path $vmFolder -ErrorAction Stop | Out-Null
    $createdVM = New-VM -Name $vmName -Generation 2 -Path $vmFolder -MemoryStartupBytes 16GB `
        -NewVHDPath (Join-Path $vmFolder 'system.vhdx') -NewVHDSizeBytes 128GB -SwitchName $switch[0].Name
    Set-VMProcessor -VM $createdVM -Count 4
    Set-VMMemory -VM $createdVM -DynamicMemoryEnabled $false
    Set-VMFirmware -VM $createdVM -EnableSecureBoot On -SecureBootTemplate MicrosoftWindows
    Set-VMKeyProtector -VM $createdVM -NewLocalKeyProtector
    Enable-VMTPM -VM $createdVM
    Add-VMDvdDrive -VM $createdVM -Path $resolvedIso
    $dvd = @(Get-VMDvdDrive -VM $createdVM)
    if ($dvd.Count -ne 1) { throw 'Expected one installer DVD drive; VM has not been started.' }
    Set-VMFirmware -VM $createdVM -FirstBootDevice $dvd[0]
} catch {
    throw "VM setup stopped. Preserve any partial '$vmName' VM and '$vmFolder'; do not rerun or delete them blindly. $($_.Exception.Message)"
}

Write-Host 'VM configured and left off so you can catch the DVD boot prompt.'
Write-Host 'In Virtual Machine Connection, click Start, click inside the display and press Space when prompted.'
Write-Host 'After Windows setup, prepare the Standard user account in docs/windows-test-vm.md.'
Start-Process -FilePath vmconnect.exe -ArgumentList @('localhost', $vmName)
