"""Prove this override differs from Home Assistant Core only as intended."""

from __future__ import annotations

import json
from pathlib import Path
import sys


EXPECTED_HACS = {"name": "LG webOS TV aiowebostv 0.9.2 override"}
EXPECTED_MANIFEST_CHANGES = {
    "issue_tracker": "https://github.com/home-assistant-libs/aiowebostv/issues",
    "requirements": ["aiowebostv==0.9.2"],
    "version": "2026.1.3+aiowebostv.0.9.2",
}


def main() -> None:
    """Run the single exact-diff check."""
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} CORE_WEBOSTV_COMPONENT")

    repo = Path(__file__).resolve().parent
    override = repo / "custom_components" / "webostv"
    upstream = Path(sys.argv[1]).resolve()
    expected_root = {
        "custom_components",
        "hacs.json",
        "LICENSE",
        "README.md",
        Path(__file__).name,
    }
    assert {path.name for path in repo.iterdir() if path.name != ".git"} == expected_root

    upstream_files = {
        path.relative_to(upstream) for path in upstream.rglob("*") if path.is_file()
    }
    override_files = {
        path.relative_to(override) for path in override.rglob("*") if path.is_file()
    }
    assert override_files == upstream_files

    allowed_component_changes = {Path("diagnostics.py"), Path("manifest.json")}
    for relative_path in upstream_files - allowed_component_changes:
        assert (override / relative_path).read_bytes() == (
            upstream / relative_path
        ).read_bytes(), relative_path

    upstream_diagnostics = (upstream / "diagnostics.py").read_text()
    marker = '    "largeIcon",\n'
    assert upstream_diagnostics.count(marker) == 1
    expected_diagnostics = upstream_diagnostics.replace(
        marker, f'{marker}    "macAddress",\n'
    )
    assert (override / "diagnostics.py").read_text() == expected_diagnostics

    expected_manifest = json.loads((upstream / "manifest.json").read_text())
    assert expected_manifest["requirements"] == ["aiowebostv==0.7.5"]
    expected_manifest.update(EXPECTED_MANIFEST_CHANGES)
    assert json.loads((override / "manifest.json").read_text()) == expected_manifest
    assert json.loads((repo / "hacs.json").read_text()) == EXPECTED_HACS
    assert (repo / "LICENSE").read_bytes() == (
        upstream.parents[2] / "LICENSE.md"
    ).read_bytes()
    readme = (repo / "README.md").read_text()
    assert "connectivity/pointer experiment" in readme
    assert "not a guaranteed `WRITE_SETTINGS` fix" in readme
    assert "Helper or fan state alone does not pass" in readme
    print(
        "PASS: only aiowebostv metadata, macAddress redaction, and approved root files differ from Core 2026.1.3"
    )


if __name__ == "__main__":
    main()
