"""registry/oep-v1.toml keeps the v1 numbering rules, and generated/oep-v1/ matches it (tools/oepgen1.py)."""

import importlib.util
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("key", ["closed_tail", "fields"])
def test_undefined_op_schema_keys_are_rejected(key):
    """Only documented registry keys are accepted; layouts live in normative text."""
    reg, _ = gen.load()
    reg["interface"][0]["op"][0][key] = True
    assert any("unknown keys" in e for e in gen.check(reg))


def test_the_link_test_and_port_speed_are_oep_probe_link():
    """D3: fn 0 has no link ops; oep.probe.link has source, sink and the optional port_speed (oep-if-link §1)."""
    reg, _ = gen.load()
    assert not {o["name"] for o in reg["core"]["op"]} & {"link_source", "link_sink", "port_speed"}
    link = next(i for i in reg["interface"] if i["name"] == "oep.probe.link")
    assert {o["name"]: (o["code"], o["lock"]) for o in link["op"]} == {
        "source": (0x10, False), "sink": (0x11, False), "port_speed": (0x12, True), "port_state": (0x13,False)}
    assert link["enum"]["port_speed_step"] == {"try": 0, "commit": 1, "revert": 2}


def test_the_core_has_no_name_and_keeps_only_what_is_mandatory():
    """core §0: the core is fn 0 without a name (not an [[interface]]); plan and restart are interfaces of their own (oep-if-plan,
    oep-if-restart), and the generated modules give the core no name."""
    reg, digest = gen.load()
    assert "oep.core" not in {i["name"] for i in reg["interface"]} and "name" not in reg["core"]
    assert not {o["name"] for o in reg["core"]["op"]} & {"plan_apply", "plan_release", "restart"}
    assert not {"plan_roles", "restart_max_ms"} & set(reg["core"]["tlv"]["describe"])
    plan = next(i for i in reg["interface"] if i["name"] == "oep.probe.plan")
    assert {o["name"]: (o["code"], o["lock"]) for o in plan["op"]} == {"plan_apply": (0x10, True), "plan_release": (0x11, True)}
    restart = next(i for i in reg["interface"] if i["name"] == "oep.probe.restart")
    assert {o["name"]: (o["code"], o["lock"]) for o in restart["op"]} == {"restart": (0x10, True)}
    assert restart["tlv"]["describe"]["restart_max_ms"] == 0x40
    ns = {}
    exec(gen.py(reg, digest), ns)
    assert not hasattr(ns["CORE"], "name") and "oep.core" not in ns["INTERFACES"] and ns["PROBE_PLAN"].lock_free == set()
    reg["core"]["name"] = "oep.core"
    assert any("core: unknown keys" in e for e in gen.check(reg))


def test_target_family_is_a_string_when_present():
    """core §12 rule 8: the target family is in the registry, not in the name."""
    reg, _ = gen.load()
    assert next(i for i in reg["interface"] if i["name"] == "oep.wire.rvswd")["target"]
    assert "target" not in next(i for i in reg["interface"] if i["name"] == "oep.fixture.gpio")
    reg["interface"][0]["target"] = ""
    assert any("target must be" in e for e in gen.check(reg))


def test_one_request_header_and_one_tlv_header():
    """No role bit for a session id and no long TLV form remain in the registry (core §2.2, §4.1)."""
    reg, _ = gen.load()
    assert "role_session_flag" not in reg["constants"] and "tlv_len_long" not in reg["constants"]


def test_common_tables_are_generated():
    reg, digest = gen.load()
    assert "kUsbVendorBulkSubclass = 0x4F" in gen.cpp(reg, digest)
    assert "kUsbProjectVid = 0x1209" in gen.cpp(reg, digest) and "kUsbProjectPid = 0x4F45" in gen.cpp(reg, digest)
    assert '"mark_detail_lost"' in gen.py(reg, digest) and "COMMON" in gen.js(reg, digest)
    assert reg['common']['enum']['mark_kind'] == {'lost':1,'clear':2,'host':3}
    console = next(i for i in reg['interface'] if i['name'] == 'oep.target.console')
    assert console['enum']['mark_kind'] == {'reset':0x40,'restart':0x41}
    assert 'mark_detail_closed' not in reg['common']['enum']


def test_a_broken_rule_is_reported():
    reg, _ = gen.load()
    reg["interface"][1]["op"].append({"code": 0x10, "name": "duplicate", "lock": True})
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
    dm["retired"] = {"dmi_step": [[0x11, 0x11]]}
    dm["enum"]["dmi_step"]["wide_write"] = 0x11
    cap = next(i for i in reg["interface"] if i["name"] == "oep.fixture.logic")
    cap["tlv"]["describe"]["features"] = reg["describe_common"]["features"]
    errors = gen.check(reg)
    assert any("retired range" in e for e in errors) and any("repeats a common tag" in e for e in errors)


def test_line_names_are_generated_for_every_output():
    reg, digest = gen.load()
    names = reg["core"]["line_names"]
    assert names
    h, p, j = gen.cpp(reg, digest), gen.py(reg, digest), gen.js(reg, digest)
    for name in names:
        assert f'kLineName{gen.camel(name)} = "{name}"' in h
        assert f"{name!r}: " in p
        assert f"{name}: " in j
    ns = {}
    exec(p, ns)
    assert ns["CORE"].line_names == names


def test_a_private_line_name_in_the_registry_is_reported():
    reg, _ = gen.load()
    reg["core"]["line_names"]["x-acme"] = "private"
    assert any("not a standard name" in e for e in gen.check(reg))


def test_settings_are_named_not_numbered():
    reg,_ = gen.load()
    # the items by name (core §13.1); the probe numbers them in its describe setting order: no item numbers here
    assert list(reg['core']['settings'])[:3]==['channel.{}.label','channel.{}.idle','channel.{}.disable']
    assert all(isinstance(v, str) for v in reg['core']['settings'].values())
    owners = {i['name'] for i in reg['interface'] if 'settings' in i}
    assert owners == {'oep.wire.rvswd','oep.wire.swio','oep.wire.swd','oep.fixture.uart','oep.target.console'}
    assert not any(i['name'] == 'oep.probe.config' for i in reg['interface'])
    # one value's get answer: header 5, more 1, generation 4, count 1, the value's fixed part 7 (core §13.5)
    lim = reg['limits']
    assert lim['setting_get_overhead_bytes'] == reg['limits']['result_header_bytes'] + 1 + 4 + 1 + 7
    assert lim['wifi_min_max_frame'] == lim['setting_get_overhead_bytes'] + 64          # the 64-digit key (transports §7)
    assert lim['label_max_bytes'] <= reg['constants']['min_max_frame'] - lim['setting_get_overhead_bytes']
    # a setting TLV with the longest name fits the core's 64-byte describe value (55 bytes)
    assert 6 + lim['setting_name_max_bytes'] <= reg['constants']['min_max_frame'] - 9
    gpio=next(i for i in reg['interface'] if i['name']=='oep.fixture.gpio')
    assert 'drive_levels' not in gpio['tlv']['describe']


def test_interface_operation_and_tlv_boundaries():
    reg, _ = gen.load()
    iface = reg['interface'][0]
    iface['op'].append({'code': 0x0F, 'name': 'private_common', 'lock': True})
    assert any('common-operation range' in e for e in gen.check(reg))
    iface['op'][-1]['code'] = 0xFF
    iface.setdefault('tlv', {})['future'] = {'last': 0x7E}
    assert gen.check(reg) == []
    iface['tlv']['future']['named'] = 0x7F               # every context's named extension (core §2.2)
    assert any('named extension' in e for e in gen.check(reg))
    del iface['tlv']['future']['named']
    iface['tlv']['future']['zero'] = 0
    assert any('is reserved' in e for e in gen.check(reg))


def test_generated_lock_free_operations_cover_the_last_byte():
    reg, digest = gen.load()
    reg['interface'][0]['op'].append({'code': 0xFF, 'name': 'last', 'lock': False})
    assert '0x8000000000000000ull' in gen.cpp(reg, digest)
    assert 'LOCK_FREE_OPS_3 0x8000000000000000ull' in gen.c(reg, digest)
    ns = {}
    exec(gen.py(reg, digest), ns)
    assert 0xFF in ns['PROBE_PLAN'].lock_free


def test_common_describe_prefix_cannot_be_used_for_private_tags():
    reg, _ = gen.load()
    reg['interface'][0].setdefault('tlv', {}).setdefault('describe', {})['private'] = 0x3F
    assert any('common describe range' in e for e in gen.check(reg))


def test_numbering_rules():
    """core §2.5: a family's interfaces give one name one number and one number one name; no interface uses 0x7F (the
    named extension); the named lists are in the registry as names (core §7.7)."""
    reg,_ = gen.load()
    assert gen.check(reg) == []
    fams = {}
    for i in reg['interface']:
        if 'family' in i:
            fams.setdefault(i['family'], []).append(i['name'])
    assert sorted(fams) == ['capture', 'wire']
    console = next(i for i in reg['interface'] if i['name'] == 'oep.target.console')
    assert list(console['names']['mechanism']) == ['sdi', 'dmdata', 'dmseq'] and 'mechanism' not in console.get('enum', {})
    assert list(reg['core']['names']['netif']) == ['wifi', 'ethernet'] and 'netif' not in reg['core']['enum']
