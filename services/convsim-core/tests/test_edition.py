# SPDX-License-Identifier: Apache-2.0
"""Demo edition (Steam Next Fest demo, issue #495).

The demo is the same build narrowed to one curated model and five curated
conversations, selected with ``CONVSIM_EDITION=demo``. These tests pin three
things: the curated list points at real official-pack content, the full app is
byte-for-byte unaffected apart from the new ``edition`` health field, and every
API surface the demo hides in the UI is also refused server-side.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from convsim_core import edition
from convsim_core.app import create_app
from convsim_core.config import ServiceConfig
from convsim_core.services.model_registry_service import load_and_persist_registry
from tests.helpers import make_pack_zip

_REPO_ROOT = Path(__file__).resolve().parents[3]
_OFFICIAL_PACKS = _REPO_ROOT / "packs" / "official"
_REGISTRY_PATH = _REPO_ROOT / "model-registry" / "registry.yaml"

_STARTER_MODEL_ID = "qwen3-4b-instruct-q4_k_m"


def _config(tmp_path: Path, **overrides) -> ServiceConfig:
    base = dict(
        host="127.0.0.1",
        port=7355,
        data_dir=str(tmp_path / "data"),
        log_dir=str(tmp_path / "logs"),
        db_dir=str(tmp_path / "db"),
        packs_dir=str(tmp_path / "packs"),
        exports_dir=str(tmp_path / "exports"),
        cache_dir=str(tmp_path / "cache"),
        crash_bundles_dir=str(tmp_path / "crashes"),
        models_dir=str(tmp_path / "models" / "llm"),
        local_dev_packs_dir=str(tmp_path),
        official_packs_dir=str(_OFFICIAL_PACKS),
        model_registry_path=str(_REGISTRY_PATH),
    )
    base.update(overrides)
    return ServiceConfig(**base)


@pytest.fixture()
def demo_client(tmp_path, monkeypatch):
    monkeypatch.setenv("CONVSIM_WHISPER_CPP_BINARY_PATH", str(tmp_path / "no-whisper-cli"))
    app = create_app(_config(tmp_path, edition="demo"))
    with TestClient(app) as c:
        yield c, app


@pytest.fixture()
def full_client(tmp_path, monkeypatch):
    monkeypatch.setenv("CONVSIM_WHISPER_CPP_BINARY_PATH", str(tmp_path / "no-whisper-cli"))
    app = create_app(_config(tmp_path))
    with TestClient(app) as c:
        yield c, app


def _official_pack_index() -> dict[str, Path]:
    """pack_id → pack directory, read from the real bundled manifests."""
    index: dict[str, Path] = {}
    for manifest in sorted(_OFFICIAL_PACKS.glob("*/manifest.yaml")):
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        index[data["pack_id"]] = manifest.parent
    return index


# ── Curation: the five point at real, shippable content ───────────────────────


def test_demo_curates_exactly_five_conversations():
    assert len(edition.DEMO_SCENARIOS) == 5
    assert len(set(edition.DEMO_SCENARIO_IDS)) == 5, "scenario ids must be unique"


def test_demo_scenarios_exist_in_official_packs():
    index = _official_pack_index()
    for s in edition.DEMO_SCENARIOS:
        assert s.pack_id in index, f"{s.pack_id} is not a bundled official pack"
        scenario_file = index[s.pack_id] / "scenarios" / f"{s.scenario_id}.yaml"
        assert scenario_file.is_file(), f"{scenario_file} missing"
        data = yaml.safe_load(scenario_file.read_text(encoding="utf-8"))
        # Scenario slugs are file stems; the YAML id must agree so the card the
        # demo Home renders and the session it starts are the same scenario.
        assert data["scenario_id"] == s.scenario_id


def test_demo_scenarios_are_one_per_player_facing_pack():
    """One flagship per pack, and never the tutorial or sample packs."""
    assert len(set(edition.DEMO_PACK_IDS)) == 5
    for pack_id in edition.DEMO_PACK_IDS:
        assert pack_id.startswith("official."), pack_id
    assert "tutorial.first_words" not in edition.DEMO_PACK_IDS


def test_demo_scenarios_are_the_flagship_of_each_pack():
    """The curation rule: the one scenario per pack with an authored difficulty ladder."""
    index = _official_pack_index()
    for s in edition.DEMO_SCENARIOS:
        data = yaml.safe_load(
            (index[s.pack_id] / "scenarios" / f"{s.scenario_id}.yaml").read_text(encoding="utf-8")
        )
        options = data["difficulty"]["options"]
        assert all("label" in opt and "description" in opt for opt in options.values()), (
            f"{s.scenario_id}: every difficulty option must carry a label and description"
        )


def test_demo_content_ratings_are_pg13_or_milder():
    """A Next Fest demo must not need an age gate the base app does not have."""
    index = _official_pack_index()
    for pack_id in edition.DEMO_PACK_IDS:
        data = yaml.safe_load((index[pack_id] / "manifest.yaml").read_text(encoding="utf-8"))
        assert data["content_rating"] in ("G", "PG", "PG-13"), pack_id


# ── Config ────────────────────────────────────────────────────────────────────


def test_edition_defaults_to_full(tmp_path):
    assert _config(tmp_path).edition == "full"
    assert not edition.is_demo(_config(tmp_path))


def test_edition_env_var_selects_demo(monkeypatch):
    monkeypatch.setenv("CONVSIM_EDITION", "demo")
    assert ServiceConfig().edition == "demo"


def test_edition_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("CONVSIM_EDITION", "trial")
    with pytest.raises(Exception):
        ServiceConfig()


def test_filter_demo_scenarios_keeps_curated_order():
    shuffled = [
        {"pack_id": "official.language_cafe", "scenario_id": "spanish_coffee"},
        {"pack_id": "official.job_interview_basic", "scenario_id": "hostile_executive_interview"},
        {"pack_id": "official.job_interview_basic", "scenario_id": "behavioral_interview"},
        {"pack_id": "other.pack", "scenario_id": "behavioral_interview"},  # same stem, wrong pack
    ]
    kept = edition.filter_demo_scenarios(
        shuffled, pack_id=lambda r: r["pack_id"], scenario_id=lambda r: r["scenario_id"]
    )
    assert [r["scenario_id"] for r in kept] == ["behavioral_interview", "spanish_coffee"]
    assert kept[0]["pack_id"] == "official.job_interview_basic"


# ── Full edition: unchanged apart from the new health field ───────────────────


def test_full_edition_health_reports_full(full_client):
    client, _ = full_client
    body = client.get("/api/health").json()
    assert body["edition"] == "full"
    assert body["demo"] is None


def test_full_edition_serves_whole_library(full_client):
    client, _ = full_client
    scenarios = client.get("/api/scenarios").json()
    ids = {s["scenario_id"] for s in scenarios}
    assert set(edition.DEMO_SCENARIO_IDS) <= ids
    assert "hostile_executive_interview" in ids
    assert len(scenarios) > 5


def test_full_edition_workbench_reachable(full_client):
    client, _ = full_client
    assert client.get("/api/workbench/packs").status_code == 200


# ── Demo edition: health ──────────────────────────────────────────────────────


def test_demo_health_reports_edition_and_curated_content(demo_client):
    client, _ = demo_client
    body = client.get("/api/health").json()
    assert body["edition"] == "demo"
    assert body["demo"]["scenario_ids"] == list(edition.DEMO_SCENARIO_IDS)
    assert body["demo"]["pack_ids"] == list(edition.DEMO_PACK_IDS)
    assert body["demo"]["model_id"] == _STARTER_MODEL_ID


def test_demo_model_id_can_be_pinned(tmp_path, monkeypatch):
    monkeypatch.setenv("CONVSIM_WHISPER_CPP_BINARY_PATH", str(tmp_path / "no-whisper-cli"))
    app = create_app(_config(tmp_path, edition="demo", demo_model_id="qwen3-8b-instruct-q4_k_m"))
    with TestClient(app) as client:
        body = client.get("/api/health").json()
        assert body["demo"]["model_id"] == "qwen3-8b-instruct-q4_k_m"
        registry = client.get("/api/models").json()["registry"]
        assert [m["id"] for m in registry] == ["qwen3-8b-instruct-q4_k_m"]


# ── Demo edition: scenarios and packs ─────────────────────────────────────────


def test_demo_scenario_list_is_exactly_the_five_in_order(demo_client):
    client, _ = demo_client
    scenarios = client.get("/api/scenarios").json()
    assert [s["scenario_id"] for s in scenarios] == list(edition.DEMO_SCENARIO_IDS)
    assert [s["pack_id"] for s in scenarios] == [s.pack_id for s in edition.DEMO_SCENARIOS]


def test_demo_scenario_list_filters_apply_within_the_five(demo_client):
    client, _ = demo_client
    scenarios = client.get("/api/scenarios", params={"language": "es"}).json()
    assert [s["scenario_id"] for s in scenarios] == ["spanish_coffee"]


def test_demo_hidden_scenario_detail_is_404(demo_client):
    client, _ = demo_client
    resp = client.get("/api/scenarios/hostile_executive_interview")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_demo_curated_scenario_detail_is_served(demo_client):
    client, _ = demo_client
    resp = client.get("/api/scenarios/behavioral_interview")
    assert resp.status_code == 200
    assert resp.json()["pack_id"] == "official.job_interview_basic"


def test_demo_packs_list_only_curated_packs_and_counts(demo_client):
    client, _ = demo_client
    body = client.get("/api/packs").json()
    assert body["total"] == 5
    assert {p["pack_id"] for p in body["packs"]} == set(edition.DEMO_PACK_IDS)
    assert all(p["scenario_count"] == 1 for p in body["packs"])


# ── Demo edition: sessions ────────────────────────────────────────────────────


def _session_body(scenario_id: str, language: str = "en") -> dict:
    return {
        "scenario_id": scenario_id,
        "difficulty": "standard",
        "language": language,
        "player_role_name": "Demo Player",
        "save_transcript": True,
        "runtime_id": "fake",
    }


def test_demo_refuses_session_for_hidden_scenario(demo_client):
    client, _ = demo_client
    # hostile_executive_interview is also in the built-in catalogue, so this
    # proves the guard runs before catalogue resolution.
    resp = client.post("/api/sessions", json=_session_body("hostile_executive_interview"))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == edition.EDITION_RESTRICTED


def test_demo_every_curated_scenario_is_playable(demo_client):
    client, _ = demo_client
    for s in client.get("/api/scenarios").json():
        resp = client.post(
            "/api/sessions",
            json=_session_body(s["scenario_id"], s["supported_languages"][0]),
        )
        assert resp.status_code == 201, f"{s['scenario_id']}: {resp.text}"
        start = client.post(f"/api/sessions/{resp.json()['session_id']}/start")
        assert start.status_code == 200, f"{s['scenario_id']}: {start.text}"


# ── Demo edition: models and install ──────────────────────────────────────────


def test_demo_models_registry_is_the_single_curated_model(demo_client):
    client, _ = demo_client
    body = client.get("/api/models").json()
    assert [m["id"] for m in body["registry"]] == [_STARTER_MODEL_ID]
    assert body["registry"][0]["role"] == "starter"
    assert body["total"] == 1
    assert body["ollama_models"] == []


def test_demo_setup_install_refuses_other_models(demo_client):
    client, _ = demo_client
    resp = client.post("/api/setup/install", json={"registry_id": "qwen3-8b-instruct-q4_k_m"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == edition.EDITION_RESTRICTED


def test_demo_setup_install_accepts_the_curated_model(demo_client):
    client, _ = demo_client
    with patch("convsim_core.routers.setup_install._run_pipeline", new_callable=AsyncMock):
        resp = client.post("/api/setup/install", json={"registry_id": _STARTER_MODEL_ID})
    assert resp.status_code == 200, resp.text
    assert resp.json()["registry_id"] == _STARTER_MODEL_ID


def test_demo_direct_install_refuses_other_models(demo_client):
    client, _ = demo_client
    resp = client.post("/api/models/install", json={"registry_id": "qwen3-14b-instruct-q4_k_m"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == edition.EDITION_RESTRICTED


# ── Demo edition: full-app-only surfaces ──────────────────────────────────────


def test_demo_refuses_pack_import(demo_client, tmp_path):
    client, _ = demo_client
    zip_bytes = make_pack_zip(tmp_path)
    resp = client.post(
        "/api/packs/import/zip",
        files={"file": ("pack.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == edition.EDITION_RESTRICTED


def test_demo_refuses_workbench(demo_client):
    client, _ = demo_client
    resp = client.get("/api/workbench/packs")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == edition.EDITION_RESTRICTED


def test_demo_privacy_controls_still_available(demo_client):
    """Privacy controls (gate F-06) are never trimmed, whatever the edition."""
    client, _ = demo_client
    assert client.get("/api/privacy/folders").status_code == 200
    assert client.post("/api/privacy/clear").status_code == 200


def test_registry_starter_role_backs_the_demo_model(demo_client):
    """The demo model is the registry's starter tier unless pinned."""
    _, app = demo_client
    conn = app.state.db.connection()
    load_and_persist_registry(conn, _REGISTRY_PATH)
    assert edition.resolve_demo_model_id(conn, app.state.service_config) == _STARTER_MODEL_ID
