"""Fixed Hyper-V operations against one explicitly owned VM; no general PowerShell API."""
import base64
import ipaddress
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .safety import Denied


def regular(path, *, directory=False, serviced_system_file=False):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise Denied("Execution configuration requires canonical absolute paths")
    for parent in [*reversed(path.parents), path]:
        info = parent.lstat()
        if parent.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise Denied("Execution configuration cannot use links or reparse paths")
    info = path.stat()
    allowed_system = {Path(os.environ.get("WINDIR", "C:/Windows")) / name for name in
                      ("System32/OpenSSH/ssh.exe", "System32/WindowsPowerShell/v1.0/powershell.exe")}
    # Windows servicing legitimately hardlinks these OS binaries to WinSxS. This exception
    # never applies to project inputs, credentials, host-key files or ownership leases.
    if serviced_system_file and path not in allowed_system:
        raise Denied("Only the fixed Windows transport executables are serviced system files")
    if (not path.is_dir() if directory else not path.is_file() or info.st_nlink != 1 and not serviced_system_file):
        raise Denied("Execution configuration path has an unsupported type")
    return path


def guest_path(value, user):
    if not isinstance(value, str) or any(c in value for c in '\r\n\x00\"<>|?*'):
        raise Denied("Invalid guest path")
    path = PureWindowsPath(value)
    home = PureWindowsPath("C:/Users") / user
    if (path.drive.upper() != "C:" or ".." in path.parts or ":" in value[2:]
            or not path.is_relative_to(home) or path == home):
        raise Denied("Guest paths must remain under the configured local guest account")
    return str(path)


@dataclass(frozen=True)
class Settings:
    vm_id: str
    owner_id: str
    checkpoint_id: str
    switch_id: str
    storage: Path
    host_ip: str
    ssh_user: str
    identity_file: Path
    known_hosts: Path
    python: str
    guest_root: str
    inputs: tuple
    timeout: int = 60
    boot_timeout: int = 90

    @classmethod
    def parse(cls, config):
        import re
        if os.name != "nt":
            raise Denied("Hyper-V execution requires a supported Windows host; no host fallback")
        value = config.get("coding_execution", {})
        keys = set(cls.__dataclass_fields__)
        if not isinstance(value, dict) or set(value) - keys - {"backend"} or keys - {"timeout", "boot_timeout"} - set(value):
            raise Denied("Incomplete or unknown Hyper-V execution configuration")
        fields = {key: value[key] for key in keys if key in value}
        for key in ("vm_id", "owner_id", "checkpoint_id", "switch_id"):
            try:
                if str(uuid.UUID(fields[key])) != fields[key]:
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise Denied("Hyper-V identities must be explicit canonical UUIDs") from None
        try:
            address = ipaddress.IPv4Address(fields["host_ip"])
            if not address.is_private or address.is_loopback or address.is_link_local:
                raise ValueError
        except (ValueError, TypeError, ipaddress.AddressValueError):
            raise Denied("Hyper-V SSH requires a literal private host gateway address") from None
        user = fields["ssh_user"]
        if not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}", user):
            raise Denied("Use an explicit local Standard-user guest account")
        for key in ("storage", "identity_file", "known_hosts"):
            if not isinstance(fields[key], str):
                raise Denied("Invalid execution configuration path")
            try:
                fields[key] = regular(fields[key], directory=key == "storage")
            except OSError:
                raise Denied("Configured VM storage/SSH path is missing or inaccessible") from None
            if fields[key].is_relative_to(Path(config["paths"]["workspace"]).resolve()):
                raise Denied("VM ownership and SSH configuration must remain outside the editable project")
        for key in ("python", "guest_root"):
            fields[key] = guest_path(fields[key], user)
        inputs = fields["inputs"]
        if (not isinstance(inputs, list) or not 1 <= len(inputs) <= 32
                or any(not isinstance(p, str) or not p or len(p) > 200 or p.startswith(("/", "\\"))
                       or any(c in p for c in ':\\\r\n\x00[]{}') or ".." in p.split("/")
                       or any(c in str(PureWindowsPath(p).parent) for c in '*?') for p in inputs)):
            raise Denied("Provide bounded, project-relative input patterns")
        fields["inputs"] = tuple(inputs)
        for key, default, maximum in (("timeout", 60, 120), ("boot_timeout", 90, 180)):
            n = fields.get(key, default)
            if type(n) is not int or not 1 <= n <= maximum:
                raise Denied("VM time budgets must be bounded positive integer seconds")
            fields[key] = n
        return cls(**fields)


# Every mutation checks the exact VM, ownership marker, checkpoint, storage and NIC.
# Unknown rules are rejected, not silently repaired. Only bootstrap DHCP rules are removed.
CONTROL = r'''
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$vm=Get-VM -Id $p.vm_id -ErrorAction Stop
$baseNote='local-agent-owned-v1:'+$p.owner_id
$runNote=$baseNote+':run:'+$p.run_id
if(($vm.Notes -cne $baseNote -and ($p.run_id -eq '' -or $vm.Notes -cne $runNote)) -or $vm.Name -notlike 'Local-Agent-Isolated-*'){throw 'VM ownership mismatch'}
$checkpoint=@(Get-VMSnapshot -VM $vm|Where-Object {$_.Id.ToString() -ceq $p.checkpoint_id})
if($checkpoint.Count -ne 1){throw 'Owned baseline checkpoint missing'}
if(@(Get-VMDvdDrive -VMSnapshot $checkpoint[0]).Count -ne 0){throw 'Baseline media outside the reviewed input set'}
$baselineDisks=@(Get-VMHardDiskDrive -VMSnapshot $checkpoint[0])
if($baselineDisks.Count -ne 1 -or -not $baselineDisks[0].Path.StartsWith($p.storage+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Baseline disk outside owned storage'}
$disks=@(Get-VMHardDiskDrive -VM $vm)
if($disks.Count -ne 1){throw 'Exactly one owned virtual disk is required'}
foreach($disk in $disks){
  if(-not $disk.Path -or -not $disk.Path.StartsWith($p.storage+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Disk outside owned storage'}
  $path=$disk.Path;$seen=@{}
  while($path){
    if($seen.ContainsKey($path) -or -not $path.StartsWith($p.storage+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Unexpected virtual disk parent'}
    $seen[$path]=$true;$vhd=Get-VHD -Path $path -ErrorAction Stop;$path=$vhd.ParentPath
  }
}
if(@(Get-VMDvdDrive -VM $vm).Count -ne 0){throw 'Guest media cannot expose extra host inputs'}
$nics=@(Get-VMNetworkAdapter -VM $vm)
if($nics.Count -ne 1 -or $nics[0].SwitchId.ToString() -cne $p.switch_id){throw 'Unexpected guest network configuration'}
$nic=$nics[0]
function Rules([bool]$bootstrap){
  $rules=@(Get-VMNetworkAdapterExtendedAcl -VMNetworkAdapter $nic)
  $expected=3;if($bootstrap){$expected=6}
  if($rules.Count -ne $expected){throw 'Unexpected network policy count'}
  foreach($r in $rules){
    $base=($r.Weight -eq 100 -and $r.Action.ToString() -eq 'Deny' -and $r.RemoteIPAddress -eq 'ANY' -and $r.LocalIPAddress -eq 'ANY' -and $r.LocalPort -eq 'ANY' -and $r.RemotePort -eq 'ANY' -and $r.Protocol -eq 'ANY' -and -not $r.Stateful)
    $ssh=($r.Weight -eq 1000 -and $r.Action.ToString() -eq 'Allow' -and $r.Direction.ToString() -eq 'Inbound' -and $r.RemoteIPAddress -eq $p.host_ip -and $r.LocalIPAddress -eq 'ANY' -and $r.LocalPort -eq '22' -and $r.RemotePort -eq 'ANY' -and $r.Protocol -eq 'TCP' -and $r.Stateful -and $r.IdleSessionTimeout -eq 120)
    $dhcp=($bootstrap -and $r.Action.ToString() -eq 'Allow' -and $r.Protocol -eq 'UDP' -and -not $r.Stateful -and (($r.Weight -eq 2000 -and $r.Direction.ToString() -eq 'Outbound' -and $r.RemoteIPAddress -eq '255.255.255.255' -and $r.LocalPort -eq '68' -and $r.RemotePort -eq '67') -or ($r.Weight -eq 2100 -and $r.Direction.ToString() -eq 'Outbound' -and $r.RemoteIPAddress -eq $p.host_ip -and $r.LocalPort -eq '68' -and $r.RemotePort -eq '67') -or ($r.Weight -eq 2000 -and $r.Direction.ToString() -eq 'Inbound' -and $r.RemoteIPAddress -eq $p.host_ip -and $r.LocalPort -eq '68' -and $r.RemotePort -eq '67')))
    if(-not ($base -or $ssh -or $dhcp)){throw 'Unexpected network policy rule'}
  }
  if(@($rules|Where-Object {$_.Weight -eq 100 -and $_.Direction.ToString() -eq 'Inbound'}).Count -ne 1 -or @($rules|Where-Object {$_.Weight -eq 100 -and $_.Direction.ToString() -eq 'Outbound'}).Count -ne 1 -or @($rules|Where-Object Weight -eq 1000).Count -ne 1){throw 'Required deny/SSH policy missing'}
}
switch($p.operation){
 'inspect' {Rules $false}
 'prepare' {
   if($vm.State.ToString() -ne 'Off' -or $vm.Notes -cne $baseNote -or $p.run_id -eq ''){throw 'VM is already claimed/running; preserve its current session'}
   Rules $false
   Set-VM -VM $vm -Notes $runNote
   Restore-VMSnapshot -VMSnapshot $checkpoint[0] -Confirm:$false
   $vm=Get-VM -Id $p.vm_id;$nic=@(Get-VMNetworkAdapter -VM $vm)[0];Rules $false
   Set-VM -VM $vm -Notes $runNote
   Add-VMNetworkAdapterExtendedAcl -VMNetworkAdapter $nic -Action Allow -Direction Outbound -RemoteIPAddress '255.255.255.255' -LocalPort 68 -RemotePort 67 -Protocol UDP -Weight 2000
   Add-VMNetworkAdapterExtendedAcl -VMNetworkAdapter $nic -Action Allow -Direction Outbound -RemoteIPAddress $p.host_ip -LocalPort 68 -RemotePort 67 -Protocol UDP -Weight 2100
   Add-VMNetworkAdapterExtendedAcl -VMNetworkAdapter $nic -Action Allow -Direction Inbound -RemoteIPAddress $p.host_ip -LocalPort 68 -RemotePort 67 -Protocol UDP -Weight 2000
   Rules $true;Start-VM -VM $vm
 }
 'bootstrap' {Rules $true}
 'seal' {
   Rules $true
   foreach($r in @(Get-VMNetworkAdapterExtendedAcl -VMNetworkAdapter $nic|Where-Object Weight -In 2000,2100)){
     Remove-VMNetworkAdapterExtendedAcl -VMNetworkAdapter $nic -Direction $r.Direction -Weight $r.Weight -Confirm:$false
   }
   Rules $false
 }
 'stop' {
   if($vm.State.ToString() -ne 'Off'){
     if($p.run_id -eq '' -or $vm.Notes -cne $runNote){throw 'Running VM is not owned by this task; preserve it'}
     Stop-VM -VM $vm -TurnOff -Force -Confirm:$false
   }
   Restore-VMSnapshot -VMSnapshot $checkpoint[0] -Confirm:$false
   $vm=Get-VM -Id $p.vm_id
   Set-VM -VM $vm -Notes $baseNote
 }
 default {throw 'Unsupported fixed VM operation'}
}
$vm=Get-VM -Id $p.vm_id;$nic=@(Get-VMNetworkAdapter -VM $vm)[0]
[pscustomobject]@{vm_id=$vm.Id.ToString();state=$vm.State.ToString();addresses=@($nic.IPAddresses);checkpoint=$checkpoint[0].Id.ToString()}|ConvertTo-Json -Depth 3 -Compress
'''


class Controller:
    def __init__(self, settings, run_id=""):
        self.settings = settings
        self.run_id = run_id
        self.powershell = Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"

    def call(self, operation):
        if operation not in {"inspect", "prepare", "bootstrap", "seal", "stop"}:
            raise Denied("Unsupported VM operation")
        s = self.settings
        payload = {key: str(getattr(s, key)) for key in
                   ("vm_id", "owner_id", "checkpoint_id", "switch_id", "storage", "host_ip")}
        payload["operation"] = operation
        if self.run_id and (len(self.run_id) != 32 or any(c not in "0123456789abcdef" for c in self.run_id)):
            raise Denied("Invalid VM run identity")
        payload["run_id"] = self.run_id
        data = base64.b64encode(json.dumps(payload).encode()).decode()
        script = "$p=ConvertFrom-Json([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + data + "')));" + CONTROL
        encoded = base64.b64encode(script.encode("utf-16-le")).decode()
        try:
            regular(self.powershell, serviced_system_file=True)
            result = subprocess.run([str(self.powershell), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                    check=False, capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode or len(result.stdout) > 8192:
                raise ValueError
            value = json.loads(result.stdout)
            if (set(value) != {"vm_id", "state", "addresses", "checkpoint"}
                    or value["vm_id"] != s.vm_id or value["checkpoint"] != s.checkpoint_id
                    or value["state"] not in {"Off", "Running"} or not isinstance(value["addresses"], list)):
                raise ValueError
            return value
        except (OSError, ValueError, subprocess.TimeoutExpired):
            raise Denied("Owned VM management/policy validation failed; no host fallback. Inspect the configured VM and baseline.") from None
