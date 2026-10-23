"""settings_file.json: an independent export and import of the settings file (docs/oep-settings-file.ja.md, core §13)."""
import ipaddress
import json
import struct
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = tomllib.loads((ROOT / "registry" / "oep-v1.toml").read_text(encoding="utf-8"))
CORE = REG["core"]
DATA = json.loads(Path(__file__).with_name("settings_file.json").read_text(encoding="utf-8"))
FORM = {v: k for k, v in CORE["enum"]["setting_form"].items()}
KEY_KIND = {v: k for k, v in CORE["enum"]["setting_key_kind"].items()}
KIND_ROUTE = {CORE["enum"]["transport_kind"][t]: r for t, r in (
    ("uart_bridge", "bridge"), ("usb_cdc", "cdc"), ("usb_serial_jtag", "usj"), ("vendor_bulk", "bulk"), ("hid", "hid"), ("tcp", "tcp"))}
assert {CORE["enum"]["route_kind"][r] for r in KIND_ROUTE.values()} == set(KIND_ROUTE)   # the route names' short names (core §13.3)


def tlvs(raw: bytes) -> list[tuple[int, bytes]]:
    out, at = [], 0
    while at < len(raw):
        tag, n = raw[at], struct.unpack_from("<H", raw, at + 1)[0]      # tag(u8) len(u16) value (core §2.2)
        out.append((tag & 0x7F, raw[at + 3:at + 3 + n]))
        at += 3 + n
    return out


def items(raw: bytes) -> list[dict]:
    """The setting and setting_choice TLVs of one fn's describe (core §13.2)."""
    common, out = REG["describe_common"], []
    for tag, value in tlvs(raw):
        if tag == common["setting"]:
            form, kind, keys, max_len, flags = struct.unpack_from("<BBHBB", value)
            out.append({"name": value[6:].decode(), "form": FORM[form], "kind": KEY_KIND[kind], "keys": keys,
                        "secret": bool(flags & CORE["enum"]["setting_flag"]["secret"]), "choices": {}})
        elif tag == common["setting_choice"]:
            out[value[0] - 1]["choices"][value[1]] = value[2:].decode()
    return out


class Probe:
    def __init__(self, decl: dict):
        d = CORE["tlv"]["describe"]
        fn0 = tlvs(bytes.fromhex(decl["fn0_describe_tlvs_hex"]))
        self.info = {k: v.decode() for t, v in fn0 for k in ("unit_id", "model", "firmware") if t == d[k]}
        self.channel = {struct.unpack_from("<H", v)[0]: v[2:].decode() for t, v in fn0 if t == d["channel_name"]}
        routes, seen = {}, {}
        for t, v in fn0:
            if t == d["transport"]:
                short = KIND_ROUTE[v[1]]
                routes[v[0]] = f"{short}{seen.get(short, 0)}"
                seen[short] = seen.get(short, 0) + 1
        self.route = routes
        self.netif = {k: v.decode() for k, v in enumerate((v for t, v in fn0 if t == d["netif"]), 1)}
        self.fns = {0: ("core", items(bytes.fromhex(decl["fn0_describe_tlvs_hex"])))}
        for e in decl["list"]:
            self.fns[e["fn"]] = (f'{e["name"]}/{e["instance"]}', items(bytes.fromhex(e["describe_tlvs_hex"])))

    def key_name(self, item, key):
        return {"none": None, "channel": lambda: self.channel[key], "index": lambda: str(key), "transport": lambda: self.route[key],
                "netif": lambda: self.netif[key]}[item["kind"]]() if item["kind"] != "none" else None

    def flat(self, item, key):
        return item["name"] if item["kind"] == "none" else item["name"].replace("{}", self.key_name(item, key))

    def to_json(self, item, data):
        f = item["form"]
        if f == "bytes": return data.hex()
        if f == "text": return data.decode()
        if f == "u32": return struct.unpack("<I", data)[0]
        if f == "ipv4": return str(ipaddress.IPv4Address(data))
        if f == "bool": return data[0] != 0
        if f == "enum": return item["choices"][data[0]]
        if f == "channel": return self.channel[struct.unpack("<H", data)[0]]
        if f == "transport": return self.route[data[0]]
        if f == "fn": return self.fns[struct.unpack("<H", data)[0]][0]
        raise AssertionError(f)

    def from_json(self, item, value):
        f = item["form"]
        rev = lambda d: {n: k for k, n in d.items()}
        if f == "bytes": return bytes.fromhex(value)
        if f == "text": return value.encode()
        if f == "u32": return struct.pack("<I", value)
        if f == "ipv4": return ipaddress.IPv4Address(value).packed
        if f == "bool": return bytes([1 if value else 0])
        if f == "enum": return bytes([rev(item["choices"])[value]])
        if f == "channel": return struct.pack("<H", rev(self.channel)[value])
        if f == "transport": return bytes([rev(self.route)[value]])
        if f == "fn": return struct.pack("<H", {c: fn for fn, (c, _) in self.fns.items()}[value])
        raise AssertionError(f)

    def resolve(self, category, flat):
        """(fn, number, key, item) for a flat name (settings file §2.2), or None."""
        found = []
        for fn, (cat, its) in self.fns.items():
            if cat != category:
                continue
            for number, item in enumerate(its, 1):
                if item["kind"] == "none":
                    if flat == item["name"]:
                        found.append((fn, number, 0, item))
                    continue
                head, tail = item["name"].split("{}")
                if flat.startswith(head) and flat.endswith(tail) and len(flat) > len(head) + len(tail):
                    name = flat[len(head):len(flat) - len(tail)]
                    names = {"channel": self.channel, "transport": self.route, "netif": self.netif,
                             "index": {k: str(k) for k in range(item["keys"])}}[item["kind"]]
                    keys = [k for k, n in names.items() if n == name]
                    if keys:
                        found.append((fn, number, keys[0], item))
        return found[0] if len(found) == 1 else None


def values(raw: bytes):
    at = 0
    while at < len(raw):
        fn, number, key, n = struct.unpack_from("<HBHH", raw, at)     # core §13.5: no origin (core §13.4)
        yield fn, number, key, raw[at + 7:at + 7 + n]
        at += 7 + n


def test_export():
    for case in DATA["export"]:
        p = Probe(case["probe"])
        out = {"oep_settings": 1, "probe": p.info, "settings": {}}
        for fn, number, key, data in values(bytes.fromhex(case["get_values_hex"])):   # every value (settings file §3)
            category, its = p.fns[fn]
            item = its[number - 1]
            out["settings"].setdefault(category, {})[p.flat(item, key)] = {"secret": True} if item["secret"] else p.to_json(item, data)
        assert out == case["file"], case["name"]


def test_import():
    for case in DATA["import"]:
        p = Probe(case["probe"])
        current = {(fn, number, key): data for fn, number, key, data in values(bytes.fromhex(case["current_values_hex"]))}
        sets, unresolved, secret_missing, wanted = [], [], [], set()
        for category, members in case["file"]["settings"].items():
            for flat, value in members.items():
                r = p.resolve(category, flat)
                if r is None:
                    unresolved.append([category, flat])
                    continue
                fn, number, key, item = r
                wanted.add((fn, number, key))
                if item["secret"]:
                    if (fn, number, key) not in current:
                        secret_missing.append([category, flat])
                    continue
                data = p.from_json(item, value)
                if current.get((fn, number, key)) != data:
                    sets.append({"fn": fn, "number": number, "key": key, "data_hex": data.hex()})
        unsets = [{"fn": fn, "number": n, "key": k} for (fn, n, k) in current if (fn, n, k) not in wanted]
        assert sets == case["expected_set"], case["name"]
        assert unsets == case["expected_unset"]
        assert secret_missing == case["secret_without_value"]
        assert unresolved == case["unresolved"]
