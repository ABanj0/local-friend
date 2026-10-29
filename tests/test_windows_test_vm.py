"""Operator script safety contracts; Hyper-V calls are replaced, not live VM acceptance."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/new-windows-test-vm.ps1'
POWERSHELL = shutil.which('powershell.exe')
HARNESS = r'''
param([string]$Scenario)
$ErrorActionPreference = 'Stop'
$global:vmTestCalls = [System.Collections.Generic.List[object]]::new()
function Record($kind, $data) { $global:vmTestCalls.Add(@{kind=$kind; data=$data}) }
function Get-VM {
    [CmdletBinding()]param()
    if ($Scenario -eq 'denied') { throw 'Access denied' }
    if ($Scenario -eq 'existing') { [pscustomobject]@{Name='Studio-Release-Test'} }
}
function Get-VMSwitch {
    [CmdletBinding()]param($Name)
    if ($Scenario -eq 'no_switch') { throw 'Default Switch unavailable' }
    [pscustomobject]@{Name=$Name}
}
function New-VM {
    [CmdletBinding()]param($Name,$Generation,$Path,$MemoryStartupBytes,$NewVHDPath,$NewVHDSizeBytes,$SwitchName)
    Record 'new' $PSBoundParameters
    [pscustomobject]@{Name=$Name;Id='owned-fixture'}
}
function Set-VMProcessor { [CmdletBinding()]param($VM,$Count) Record 'processor' $PSBoundParameters }
function Set-VMMemory { [CmdletBinding()]param($VM,$DynamicMemoryEnabled) Record 'memory' $PSBoundParameters }
function Set-VMFirmware {
    [CmdletBinding()]param($VM,$EnableSecureBoot,$SecureBootTemplate,$FirstBootDevice)
    Record 'firmware' $PSBoundParameters
}
function Set-VMKeyProtector { [CmdletBinding()]param($VM,[switch]$NewLocalKeyProtector) Record 'key' $PSBoundParameters }
function Enable-VMTPM {
    [CmdletBinding()]param($VM)
    Record 'tpm' $PSBoundParameters
    if ($Scenario -eq 'partial') { throw 'fixture TPM failure' }
}
function Add-VMDvdDrive { [CmdletBinding()]param($VM,$Path) Record 'dvd' $PSBoundParameters }
function Get-VMDvdDrive {
    [CmdletBinding()]param($VM)
    if ($Scenario -eq 'ambiguous_dvd') { return @('dvd1','dvd2') }
    'owned-dvd'
}
function Start-VM { [CmdletBinding()]param($VM) Record 'start' $PSBoundParameters }
function Start-Process { [CmdletBinding()]param($FilePath,$ArgumentList) Record 'connect' $PSBoundParameters }
$errorText = $null
try { & (Join-Path $PSScriptRoot 'scripts/new-windows-test-vm.ps1') }
catch { $errorText = $_.Exception.Message }
@{error=$errorText;calls=@($global:vmTestCalls.ToArray())} | ConvertTo-Json -Depth 10 -Compress
'''


@unittest.skipUnless(POWERSHELL, 'Windows PowerShell required for operator script contracts')
class WindowsTestVMScriptTests(unittest.TestCase):
    def exercise(self, scenario):
        with tempfile.TemporaryDirectory(prefix='studio-vm-script-') as folder:
            root = Path(folder)
            (root / 'scripts').mkdir()
            shutil.copyfile(SCRIPT, root / 'scripts' / SCRIPT.name)
            iso = root / '.runtime/windows-vm/Windows11.iso'
            iso.parent.mkdir(parents=True)
            if scenario != 'missing_iso':
                iso.write_bytes(b'fixture, not installation media')
            destination = root / '.runtime/vm-tests/Studio-Release-Test'
            if scenario == 'directory':
                destination.mkdir(parents=True)
                (destination / 'preserve.txt').write_text('untouched', encoding='utf-8')
            harness = root / 'harness.ps1'
            harness.write_text(HARNESS, encoding='utf-8')
            result = subprocess.run(
                [POWERSHELL, '-NoProfile', '-NonInteractive', '-File', str(harness), scenario],
                capture_output=True, text=True, timeout=20, check=True,
            )
            record = json.loads(result.stdout.strip().splitlines()[-1])
            record['directory_exists'] = destination.is_dir()
            if scenario == 'directory':
                self.assertEqual((destination / 'preserve.txt').read_text(), 'untouched')
            return record

    def test_missing_iso_creates_nothing(self):
        result = self.exercise('missing_iso')
        self.assertIn('Windows ISO missing', result['error'])
        self.assertEqual(result['calls'], [])
        self.assertFalse(result['directory_exists'])

    def test_provider_denial_fails_before_any_mutation(self):
        result = self.exercise('denied')
        self.assertIn('Administrator PowerShell', result['error'])
        self.assertIn('Access denied', result['error'])
        self.assertEqual(result['calls'], [])
        self.assertFalse(result['directory_exists'])

    def test_existing_vm_is_preserved(self):
        result = self.exercise('existing')
        self.assertIn('VM already exists', result['error'])
        self.assertEqual(result['calls'], [])
        self.assertFalse(result['directory_exists'])

    def test_existing_directory_is_preserved(self):
        result = self.exercise('directory')
        self.assertIn('VM directory already exists', result['error'])
        self.assertEqual(result['calls'], [])

    def test_missing_switch_does_not_create_vm_or_network(self):
        result = self.exercise('no_switch')
        self.assertIn('Default Switch unavailable', result['error'])
        self.assertEqual(result['calls'], [])
        self.assertFalse(result['directory_exists'])

    def test_partial_failure_preserves_resources_without_start_or_cleanup(self):
        result = self.exercise('partial')
        self.assertIn('Preserve any partial', result['error'])
        self.assertIn('fixture TPM failure', result['error'])
        self.assertTrue(result['directory_exists'])
        self.assertEqual([c['kind'] for c in result['calls']],
                         ['new', 'processor', 'memory', 'firmware', 'key', 'tpm'])

    def test_ambiguous_dvd_never_starts_vm(self):
        result = self.exercise('ambiguous_dvd')
        self.assertIn('Expected one installer DVD', result['error'])
        self.assertNotIn('start', [c['kind'] for c in result['calls']])

    def test_success_configures_only_returned_vm_and_opens_console_before_manual_start(self):
        result = self.exercise('success')
        self.assertIsNone(result['error'])
        calls = result['calls']
        self.assertEqual([c['kind'] for c in calls],
                         ['new', 'processor', 'memory', 'firmware', 'key', 'tpm', 'dvd',
                          'firmware', 'connect'])
        created = calls[0]['data']
        self.assertEqual(created['Name'], 'Studio-Release-Test')
        self.assertEqual(created['Generation'], 2)
        self.assertEqual(created['MemoryStartupBytes'], 16 * 1024**3)
        self.assertEqual(created['NewVHDSizeBytes'], 128 * 1024**3)
        self.assertEqual(created['SwitchName'], 'Default Switch')
        for call in calls[1:-1]:
            self.assertEqual(call['data']['VM']['Id'], 'owned-fixture')
        self.assertEqual(calls[1]['data']['Count'], 4)
        self.assertFalse(calls[2]['data']['DynamicMemoryEnabled'])
        self.assertEqual(calls[3]['data']['EnableSecureBoot'], 'On')
        self.assertEqual(calls[3]['data']['SecureBootTemplate'], 'MicrosoftWindows')
        self.assertEqual(calls[-2]['data']['FirstBootDevice'], 'owned-dvd')
        self.assertEqual(calls[-1]['data']['FilePath'], 'vmconnect.exe')
        self.assertEqual(calls[-1]['data']['ArgumentList'], ['localhost', 'Studio-Release-Test'])
