"""Guards that the server.json manifest stays consistent with the package.

These run in CI so a version/name drift across pyproject, server.json, README,
and the Dockerfile fails fast before a tagged release is published.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVER_NAME = "io.github.jtl-neo/crossref-mcp"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((ROOT / "server.json").read_text())


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_manifest_is_valid_json(manifest):
    assert manifest["name"] == SERVER_NAME
    assert manifest["$schema"].startswith("https://static.modelcontextprotocol.io/")


def test_manifest_version_matches_pyproject(manifest, pyproject):
    version = pyproject["project"]["version"]
    assert manifest["version"] == version
    for pkg in manifest["packages"]:
        assert pkg["version"] == version, pkg["registryType"]


def test_pypi_and_oci_packages_present(manifest):
    types = {p["registryType"] for p in manifest["packages"]}
    assert {"pypi", "oci"} <= types
    pypi = next(p for p in manifest["packages"] if p["registryType"] == "pypi")
    assert pypi["identifier"] == "crossref-mcp"


def test_server_name_consistent_across_files(pyproject):
    readme = (ROOT / "README.md").read_text()
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert f"mcp-name: {SERVER_NAME}" in readme
    assert f'io.modelcontextprotocol.server.name="{SERVER_NAME}"' in dockerfile
