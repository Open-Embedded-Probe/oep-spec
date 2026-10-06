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
    assert (gen.OUT / "oep_v1_registry_c.h").read_text() == gen.c(reg, digest)
    assert (gen.OUT / "oep_v1_registry.py").read_text() == gen.py(reg, digest)
    assert (gen.OUT / "oep_v1_registry.js").read_text() == gen.js(reg, digest)


def test_no_op_has_an_open_ended_form():
    """Every form is counted (core §2.3): the op key closed_tail is gone and the generator refuses it."""
    reg, _ = gen.load()
    assert not [o for i in reg["interface"] for o in i["op"] if "closed_tail" in o]
    reg["interface"][0]["op"][0]["closed_tail"] = True
    assert any("unknown keys" in e for e in gen.check(reg))


def test_the_link_test_and_port_speed_are_oep_link():
    """D3: fn 0 has no link ops; oep.link has source, sink and the optional port_speed (oep-if-link §1)."""
    reg, _ = gen.load()
    core = next(i for i in reg["interface"] if i["name"] == "oep.core")
    assert not {o["name"] for o in core["op"]} & {"link_source", "link_sink", "port_speed"}
    link = next(i for i in reg["interface"] if i["name"] == "oep.link")
    assert {o["name"]: (o["code"], o["lock"]) for o in link["op"]} == {
        "source": (0x01, False), "sink": (0x02, False), "port_speed": (0x03, True)}
    assert link["enum"]["port_speed_step"] == {"try": 0, "commit": 1, "revert": 2}


def test_one_request_header_and_one_tlv_header():
    """No role bit for a session id and no long TLV form remain in the registry (core §2.2, §4.1)."""
    reg, _ = gen.load()
    assert "role_session_flag" not in reg["constants"] and "tlv_len_long" not in reg["constants"]


def test_common_tables_are_generated():
    reg, digest = gen.load()
    assert "kUsbVendorBulkSubclass = 0x4F" in gen.cpp(reg, digest)
    assert "kUsbProjectVid = 0x1209" in gen.cpp(reg, digest) and "kUsbProjectPid = 0x4F45" in gen.cpp(reg, digest)
    assert '"mark_detail_closed"' in gen.py(reg, digest) and "COMMON" in gen.js(reg, digest)


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
    cap = next(i for i in reg["interface"] if i["name"] == "oep.fixture.logic")
    cap["tlv"]["describe"]["features"] = 0x06
    errors = gen.check(reg)
    assert any("reserved range" in e for e in errors) and any("repeats a common tag" in e for e in errors)


def test_line_names_are_generated_for_every_output():
    reg, digest = gen.load()
    names = next(i for i in reg["interface"] if i["name"] == "oep.probe.config")["line_names"]
    assert names
    h, p, j = gen.cpp(reg, digest), gen.py(reg, digest), gen.js(reg, digest)
    for name in names:
        assert f'kLineName{gen.camel(name)} = "{name}"' in h
        assert f"{name!r}: " in p
        assert f"{name}: " in j
    ns = {}
    exec(p, ns)
    assert ns["PROBE_CONFIG"].line_names == names


def test_a_private_line_name_in_the_registry_is_reported():
    reg, _ = gen.load()
    next(i for i in reg["interface"] if i["name"] == "oep.probe.config")["line_names"]["x-acme"] = "private"
    assert any("not a standard name" in e for e in gen.check(reg))
