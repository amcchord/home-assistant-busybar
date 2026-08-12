"""Repository-level contract tests."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "busybar"


def test_manifest_contract() -> None:
    """Manifest identity and local-first class remain intentional."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["domain"] == "busybar"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "local_push"
    assert manifest["requirements"] == ["busylib==1.3.0"]
    assert manifest["version"]


def test_strings_and_translation_have_same_topology() -> None:
    """English translations cover all source string sections."""
    strings = json.loads((COMPONENT / "strings.json").read_text())
    translations = json.loads((COMPONENT / "translations" / "en.json").read_text())
    assert translations.keys() == strings.keys()
    assert translations["services"].keys() == strings["services"].keys()
    assert translations["entity"].keys() == strings["entity"].keys()


def test_every_registered_service_is_documented() -> None:
    """Service UI metadata and translated descriptions stay in sync."""
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    strings = json.loads((COMPONENT / "strings.json").read_text())
    assert services.keys() == strings["services"].keys()
