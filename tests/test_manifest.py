"""Repository-level contract tests."""

import json
from pathlib import Path

import yaml
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.util import yaml as ha_yaml

from custom_components.busybar.const import VERSION

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "busybar"


def test_manifest_contract() -> None:
    """Manifest identity and local-first class remain intentional."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["domain"] == "busybar"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "local_push"
    assert manifest["dependencies"] == ["http"]
    assert manifest["requirements"] == ["busylib==1.3.0", "segno==1.6.6"]
    assert manifest["version"] == VERSION


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


def test_bundled_blueprints_are_valid() -> None:
    """All one-click automation recipes satisfy Home Assistant's schema."""
    blueprint_dir = ROOT / "blueprints" / "automation" / "busybar"
    paths = sorted(blueprint_dir.glob("*.yaml"))
    assert len(paths) >= 13
    for path in paths:
        Blueprint(
            ha_yaml.load_yaml_dict(path),
            path=str(path),
            expected_domain="automation",
            schema=AUTOMATION_BLUEPRINT_SCHEMA,
        )
