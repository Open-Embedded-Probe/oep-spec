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
