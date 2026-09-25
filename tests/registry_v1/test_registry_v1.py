"""registry/oep-v1.toml keeps the v1 numbering rules, and generated/oep-v1/ matches it (tools/oepgen1.py)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("oepgen1", ROOT / "tools" / "oepgen1.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_numbering_rules_hold():
    reg, _ = gen.load()
    assert gen.check(reg) == []


def test_generated_files_match_the_registry():
    reg, digest = gen.load()
    assert (gen.OUT / "oep_v1_registry.h").read_text() == gen.cpp(reg, digest)
    assert (gen.OUT / "oep_v1_registry.py").read_text() == gen.py(reg, digest)


def test_a_broken_rule_is_reported():
    reg, _ = gen.load()
    reg["interface"][1]["op"].append({"code": 0x01, "name": "duplicate", "lock": True})
    assert any("used by" in e for e in gen.check(reg))


def test_crlf_checkout_gives_the_same_hash(tmp_path, monkeypatch):
    crlf = tmp_path / "oep-v1.toml"
    crlf.write_bytes(gen.REGISTRY.read_bytes().replace(b"\n", b"\r\n"))
    _, digest = gen.load()
    monkeypatch.setattr(gen, "REGISTRY", crlf)
    assert gen.load()[1] == digest


def test_reserved_ranges_and_common_tags_are_checked():
    reg, _ = gen.load()
    dm = next(i for i in reg["interface"] if i["name"] == "oep.target.riscv-dm")
    dm["enum"]["dmi_step"]["wide_write"] = 0x11
    cap = next(i for i in reg["interface"] if i["name"] == "oep.fixture.capture")
    cap["tlv"]["describe"]["features"] = 0x06
    errors = gen.check(reg)
    assert any("reserved range" in e for e in errors) and any("repeats a common tag" in e for e in errors)
