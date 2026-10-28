"""Record build inputs and artifact hashes without claiming installation acceptance."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from datetime import UTC, datetime
from pathlib import Path


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def nsis_tag_hash(raw, *, unsigned):
    """Prediction only; Tauri restores the original EXE after bundling its tagged copy."""
    if unsigned is not True:
        return {"status": "unavailable", "reason": "signed_or_unknown_PE"}
    original, tagged = b"__TAURI_BUNDLE_TYPE_VAR_UNK", b"__TAURI_BUNDLE_TYPE_VAR_NSS"
    if raw.count(original) == 1 and raw.count(tagged) == 0:
        payload = raw.replace(original, tagged, 1)
        derivation = "unsigned_tauri_nsis_bundle_tag_v1"
    elif raw.count(original) == 0 and raw.count(tagged) == 1:
        payload = raw
        derivation = "unsigned_build_input_already_nsis_tagged"
    else:
        return {"status": "unavailable", "reason": "missing_or_ambiguous_bundle_tag"}
    return {"status": "predicted", "derivation": derivation, "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


def nsis_main_payload(path):
    if not path.is_file():
        return {"status": "unavailable", "reason": "missing_main_binary"}
    try:
        import pefile  # Installed by the Windows PyInstaller build extra.
    except ImportError:
        return {"status": "unavailable", "reason": "PE_inspection_dependency_missing"}
    raw = path.read_bytes()
    try:
        with pefile.PE(data=raw, fast_load=True) as image:
            certificate = image.OPTIONAL_HEADER.DATA_DIRECTORY[4]
            unsigned = certificate.VirtualAddress == 0 and certificate.Size == 0
    except (pefile.PEFormatError, AttributeError, IndexError):
        return {"status": "unavailable", "reason": "unrecognized_PE_layout"}
    return nsis_tag_hash(raw, unsigned=unsigned)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sidecar", required=True, type=Path)
    parser.add_argument("--bundle-succeeded", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    release = root / "desktop/src-tauri/target/release"
    artifacts = [args.sidecar.resolve(), release / "local-agent-studio.exe"]
    installers = list((release / "bundle/nsis").glob("*.exe")) if args.bundle_succeeded else []
    artifacts.extend(installers)
    if not args.sidecar.is_file():
        parser.error("Built sidecar does not exist")
    inputs = [root / name for name in ("pyproject.toml", "uv.lock", "desktop/package-lock.json",
                                       "desktop/src-tauri/Cargo.lock", "desktop/agent.example.toml",
                                       "desktop/src-tauri/tauri.conf.json", "scripts/build-desktop.ps1",
                                       "scripts/release-manifest.py")]
    for directory, pattern in [("local_agent", "*.py"), ("desktop/src", "*"),
                               ("desktop/src-tauri/src", "*.rs")]:
        inputs.extend(path for path in (root / directory).rglob(pattern) if path.is_file())

    def label(path):
        return str(path.relative_to(root)) if path.is_relative_to(root) else path.name

    manifest = {
        "created_utc": datetime.now(UTC).isoformat(),
        "bundle_succeeded": args.bundle_succeeded,
        "installation_verified": False,
        "platform": platform.platform(), "build_python": platform.python_version(),
        "python_build_environment": sorted(
            [{"name": dist.metadata["Name"], "version": dist.version} for dist in importlib.metadata.distributions()],
            key=lambda package: package["name"].lower()),
        "artifacts": {label(path): fingerprint(path) for path in artifacts if path.is_file()},
        "inputs": {label(path): fingerprint(path) for path in sorted(set(inputs))},
        "scope": "Hashes and build-environment versions; not a complete binary SBOM or installation certification.",
    }
    if installers:
        manifest["expected_nsis_main_payload"] = nsis_main_payload(release / "local-agent-studio.exe")
        manifest["expected_nsis_main_payload"]["scope"] = (
            "Prediction for unsigned default Tauri NSIS patching; not an extracted payload, "
            "signature verification, or installation certification.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Build manifest: {args.output}")


if __name__ == "__main__":
    main()
