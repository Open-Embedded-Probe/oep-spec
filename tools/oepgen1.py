# /// script
# requires-python = ">=3.11"
# ///
"""Generate the OEP v1 constants (C++ header, Python module) from registry/oep-v1.toml, after checking the numbering
rules of docs/oep-core.ja.md §2.

Usage:
  uv run tools/oepgen1.py            # write into generated/oep-v1/
  uv run tools/oepgen1.py --check    # exit 1 if generated/oep-v1/ differs from the registry (or a rule is broken)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry" / "oep-v1.toml"
OUT = ROOT / "generated" / "oep-v1"


def load() -> tuple[dict, str]:
    # the hash is over the file with line endings normalized to LF (a CRLF checkout must give the same value)
    raw = REGISTRY.read_bytes().replace(b"\r\n", b"\n")
    return tomllib.loads(raw.decode()), hashlib.sha256(raw).hexdigest()[:16]


def check(reg: dict) -> list[str]:
    """The §0 numbering rules; a list of what is wrong."""
    errors = []
    # The table kinds the registry header lists; anything else needs a pull request that also updates the header.
    top = {"registry", "protocol", "constants", "roles", "resolutions", "outcomes", "reject_reasons", "status", "timing",
           "limits", "reference", "describe_common", "usb", "common", "interface"}
    if set(reg) - top:
        errors.append(f"unknown table kinds {sorted(set(reg) - top)} (registry header)")
    if set(reg.get("common", {})) - {"enum"}:
        errors.append(f"unknown common tables {sorted(set(reg['common']) - {'enum'})} (registry header)")
    iface_keys = {"name", "revision", "fn", "op", "tlv", "enum", "event", "status", "reject_reasons", "reserved", "line_names"}
    for iface in reg.get("interface", []):
        if set(iface) - iface_keys:
            errors.append(f"{iface.get('name')}: unknown interface keys {sorted(set(iface) - iface_keys)} (registry header)")
    if reg.get("registry", {}).get("schema") != 1:
        errors.append("registry.schema must be 1")
    for name, code in reg["reject_reasons"].items():
        if not 0x01 <= code <= 0x3F:
            errors.append(f"reject reason {name} = {code:#x} outside the core range 0x01-0x3F")
    for name, code in reg["status"].items():
        if not 0 <= code <= 0x3F:
            errors.append(f"status {name} = {code:#x} outside the common range")
    common = reg.get("describe_common", {})
    names = set()
    for iface in reg["interface"]:
        n = iface["name"]
        if n in names:
            errors.append(f"interface {n} listed twice")
        names.add(n)
        codes = {}
        for op in iface["op"]:
            c = op["code"]
            if c in codes:
                errors.append(f"{n}: op {c:#x} used by {codes[c]} and {op['name']}")
            codes[c] = op["name"]
            if not 0x01 <= c <= 0xEF:
                errors.append(f"{n}: op {op['name']} = {c:#x} outside 0x01-0xEF (0xF0-0xFF are experimental)")
            if set(op) - {"code", "name", "lock", "closed_tail", "fields"}:
                errors.append(f"{n}: op {op['name']} has unknown keys {sorted(set(op) - {'code', 'name', 'lock', 'closed_tail', 'fields'})}")
        if n == "oep.core":
            ranges = [(0x01, 0x0F), (0x10, 0x1F), (0x20, 0x2F), (0x30, 0x3F), (0x40, 0x4F)]
            for c, opname in codes.items():
                if not any(a <= c <= b for a, b in ranges):
                    errors.append(f"oep.core: op {opname} = {c:#x} outside the core ranges")
        for context, tags in iface.get("tlv", {}).items():
            seen = {}
            for tag_name, tag in tags.items():
                if tag in seen:
                    errors.append(f"{n}: tlv {context}: {tag:#x} used by {seen[tag]} and {tag_name}")
                seen[tag] = tag_name
                if tag in (0x7F, 0xFF, 0x00):
                    errors.append(f"{n}: tlv {context}.{tag_name} = {tag:#x} is reserved")
                if context == "describe" and tag == 0x3F:
                    errors.append(f"{n}: describe tag {tag_name} = 0x3f is reserved for response meta")
                if tag & 0x80:
                    errors.append(f"{n}: tlv {context}.{tag_name} = {tag:#x} has the critical bit set in the registry")
        for group in ("status", "reject_reasons"):
            for v_name, v in iface.get(group, {}).items():
                if not 0x40 <= v <= 0x7F:
                    errors.append(f"{n}: {group} {v_name} = {v:#x} outside the interface range 0x40-0x7F")
        for tag_name, tag in iface.get("tlv", {}).get("describe", {}).items():
            if tag in common.values() or tag_name in common:
                errors.append(f"{n}: describe tag {tag_name} = {tag:#x} repeats a common tag ([describe_common])")
        for what, ranges in iface.get("reserved", {}).items():
            if what == "op":
                values = codes
            elif what.startswith("tlv."):
                values = {v: k for k, v in iface.get("tlv", {}).get(what[4:], {}).items()}
            else:
                values = iface.get("enum", {}).get(what)
            if values is None:
                errors.append(f"{n}: reserved.{what} names no enum")
                continue
            items = values.items() if what in ("op",) or what.startswith("tlv.") else ((v, k) for k, v in values.items())
            for v, v_name in items:
                if any(lo <= v <= hi for lo, hi in ranges):
                    errors.append(f"{n}: {what} {v_name} = {v:#x} is in a reserved range")
        for line in iface.get("line_names", {}):
            if line.startswith("x-") or "." in line or not 1 <= len(line.encode()) <= 32 or not re.fullmatch(r"[a-z0-9_-]+", line):
                errors.append(f"{n}: line name {line!r} is not a standard name (1-32 of a-z 0-9 _ -, no x- prefix, no '.')")
        for kind_name, kind in iface.get("event", {}).items():
            if not 0x01 <= kind <= 0x7F:
                errors.append(f"{n}: event {kind_name} = {kind:#x} outside the interface range 0x01-0x7F")
    for enum, values in reg.get("common", {}).get("enum", {}).items():
        if enum == "mark_kind":
            for k, v in values.items():
                if not 0x01 <= v <= 0x3F:
                    errors.append(f"common mark_kind {k} = {v:#x} outside the standard range 0x01-0x3F")
    return errors


def camel(s: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[_\-.]+", s) if part)


def ident(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_")


def cpp(reg: dict, digest: str) -> str:
    L = ["// Generated by oep-spec tools/oepgen1.py from registry/oep-v1.toml - do not edit.",
         f"// registry schema {reg['registry']['schema']}, sha256 {digest}",
         "#pragma once", "", "#include <stdint.h>", "", "namespace oep {", "namespace v1 {", "namespace reg {", "",
         f'constexpr const char *kRegistryHash = "{digest}";',
         f"constexpr uint8_t kProtocolRevision = {reg['protocol']['revision']};"]
    for k, v in reg["constants"].items():
        L.append(f'constexpr const char *k{camel(k)} = "{v}";' if isinstance(v, str) else f"constexpr uint8_t k{camel(k)} = 0x{v:02X};")
    for group, prefix in (("roles", "Role"), ("resolutions", "Resolution"), ("outcomes", "Outcome"),
                          ("reject_reasons", "Reject"), ("status", "Status"), ("describe_common", "Describe")):
        L.append("")
        for k, v in reg[group].items():
            L.append(f"constexpr uint8_t k{prefix}{camel(k)} = 0x{v:02X};")
    L.append("")
    for k, v in reg["timing"].items():
        L.append(f"constexpr uint32_t k{camel(k)} = {v};")
    for group, prefix in (("usb", "Usb"), ("limits", "Limit"), ("reference", "Reference")):
        L.append("")
        for k, v in reg.get(group, {}).items():
            L.append(f'constexpr const char *k{prefix}{camel(k)} = "{v}";' if isinstance(v, str)
                     else f"constexpr uint32_t k{prefix}{camel(k)} = 0x{v:X};")
    L += ["", "namespace common {"]
    for enum, values in reg.get("common", {}).get("enum", {}).items():
        for k, v in values.items():
            L.append(f"constexpr uint8_t k{camel(enum)}{camel(k)} = 0x{v:02X};")
    L.append("}  // namespace common")
    for iface in reg["interface"]:
        ns = ident(iface["name"].removeprefix("oep."))
        L += ["", f"namespace {ns} {{", f'constexpr const char *kName = "{iface["name"]}";',
              f"constexpr uint8_t kRevision = {iface['revision']};"]
        for op in iface["op"]:
            L.append(f"constexpr uint8_t kOp{camel(op['name'])} = 0x{op['code']:02X};")
        lock = sum(1 << op["code"] for op in iface["op"] if not op.get("lock") and op["code"] < 64)
        L.append(f"constexpr uint64_t kLockFreeOps = 0x{lock:X}ull;   // bit n = op n needs no lock")
        for context, tags in iface.get("tlv", {}).items():
            for k, v in tags.items():
                L.append(f"constexpr uint8_t kTlv{camel(context)}{camel(k)} = 0x{v:02X};")
        for k, v in iface.get("event", {}).items():
            L.append(f"constexpr uint8_t kEvent{camel(k)} = 0x{v:02X};")
        for group, prefix in (("status", "Status"), ("reject_reasons", "Reject")):
            for k, v in iface.get(group, {}).items():
                L.append(f"constexpr uint8_t k{prefix}{camel(k)} = 0x{v:02X};")
        for enum, values in iface.get("enum", {}).items():
            for k, v in values.items():
                L.append(f"constexpr uint8_t k{camel(enum)}{camel(k)} = 0x{v:02X};")
        names = list(iface.get("line_names", {}))
        if names:
            for k in names:
                L.append(f'constexpr const char *kLineName{camel(k)} = "{k}";')
            L.append("constexpr const char *const kLineNames[] = {" + ", ".join(f'"{k}"' for k in names) + "};")
            L.append(f"constexpr unsigned kLineNameCount = {len(names)};")
        L.append(f"}}  // namespace {ns}")
    L += ["", "}  // namespace reg", "}  // namespace v1", "}  // namespace oep", ""]
    return "\n".join(L)


def py(reg: dict, digest: str) -> str:
    L = ['"""Generated by oep-spec tools/oepgen1.py from registry/oep-v1.toml - do not edit."""', "",
         "from types import SimpleNamespace as _NS", "",
         f'REGISTRY_HASH = "{digest}"', f"SCHEMA = {reg['registry']['schema']}",
         f"PROTOCOL_REVISION = {reg['protocol']['revision']}"]
    for k, v in reg["constants"].items():
        L.append(f"{k.upper()} = {v!r}" if isinstance(v, str) else f"{k.upper()} = 0x{v:02X}")
    for group in ("roles", "resolutions", "outcomes", "reject_reasons", "status", "describe_common", "timing", "usb", "limits", "reference"):
        L.append(f"{group.upper()} = {{" + ", ".join(f'"{k}": {v!r}' if isinstance(v, str) else f'"{k}": 0x{v:02X}'
                                                 for k, v in reg.get(group, {}).items()) + "}")
    en = ", ".join(f'"{e}": {{' + ", ".join(f'"{k}": 0x{v:02X}' for k, v in vals.items()) + "}"
                   for e, vals in reg.get("common", {}).get("enum", {}).items())
    L += [f"COMMON = _NS(enum={{{en}}})", "", "INTERFACES = {}"]
    for iface in reg["interface"]:
        var = ident(iface["name"].removeprefix("oep.")).upper()
        ops = ", ".join(f'"{o["name"]}": 0x{o["code"]:02X}' for o in iface["op"])
        free = ", ".join(f'0x{o["code"]:02X}' for o in iface["op"] if not o.get("lock"))
        closed = ", ".join(f'0x{o["code"]:02X}' for o in iface["op"] if o.get("closed_tail"))
        tlv = ", ".join(f'"{c}": {{' + ", ".join(f'"{k}": 0x{v:02X}' for k, v in t.items()) + "}"
                        for c, t in iface.get("tlv", {}).items())
        ev = ", ".join(f'"{k}": 0x{v:02X}' for k, v in iface.get("event", {}).items())
        en = ", ".join(f'"{e}": {{' + ", ".join(f'"{k}": 0x{v:02X}' for k, v in vals.items()) + "}"
                       for e, vals in iface.get("enum", {}).items())
        own = ", ".join(f'"{k}": 0x{v:02X}' for g in ("status", "reject_reasons") for k, v in iface.get(g, {}).items())
        lines = ", ".join(f"{k!r}: {v!r}" for k, v in iface.get("line_names", {}).items())
        L += [f'{var} = _NS(name="{iface["name"]}", revision={iface["revision"]}, op={{{ops}}}, lock_free={{{free}}},',
              f"    closed_tail={{{closed}}}, tlv={{{tlv}}}, event={{{ev}}}, enum={{{en}}}, own={{{own}}},",
              f"    line_names={{{lines}}})",
              f'INTERFACES["{iface["name"]}"] = {var}']
    return "\n".join(L) + "\n"


def js(reg: dict, digest: str) -> str:
    """The same shape as py(): objects keyed by the registry's snake_case names; lock_free / closed_tail are Sets."""
    def obj(d: dict) -> str:
        return "{" + ", ".join(f"{k}: 0x{v:02X}" if re.fullmatch(r"[A-Za-z_]\w*", k) else f'"{k}": 0x{v:02X}'
                               for k, v in d.items()) + "}"
    L = ["// @ts-check", "// Generated by oep-spec tools/oepgen1.py from registry/oep-v1.toml - do not edit.", "",
         f"export const REGISTRY_HASH = '{digest}';", f"export const SCHEMA = {reg['registry']['schema']};",
         f"export const PROTOCOL_REVISION = {reg['protocol']['revision']};"]
    for k, v in reg["constants"].items():
        L.append(f"export const {k.upper()} = '{v}';" if isinstance(v, str) else f"export const {k.upper()} = 0x{v:02X};")
    def objs(d: dict) -> str:
        return "{" + ", ".join((f"{k}: '{v}'" if isinstance(v, str) else f"{k}: 0x{v:02X}") for k, v in d.items()) + "}"
    for group in ("roles", "resolutions", "outcomes", "reject_reasons", "status", "describe_common", "timing", "usb", "limits", "reference"):
        L.append(f"export const {group.upper()} = Object.freeze({objs(reg.get(group, {}))});")
    en = "{" + ", ".join(f"{e}: {obj(v)}" for e, v in reg.get("common", {}).get("enum", {}).items()) + "}"
    L += [f"export const COMMON = {{ enum: {en} }};", "", "/** @type {Record<string, any>} */", "export const INTERFACES = {};"]
    for iface in reg["interface"]:
        var = ident(iface["name"].removeprefix("oep.")).upper()
        free = ", ".join(f"0x{o['code']:02X}" for o in iface["op"] if not o.get("lock"))
        closed = ", ".join(f"0x{o['code']:02X}" for o in iface["op"] if o.get("closed_tail"))
        tlv = "{" + ", ".join(f"{c}: {obj(t)}" for c, t in iface.get("tlv", {}).items()) + "}"
        en = "{" + ", ".join(f"{e}: {obj(v)}" for e, v in iface.get("enum", {}).items()) + "}"
        own = {k: v for g in ("status", "reject_reasons") for k, v in iface.get(g, {}).items()}
        ops = {o["name"]: o["code"] for o in iface["op"]}
        L += [f"export const {var} = {{",
              f"  name: '{iface['name']}', revision: {iface['revision']},",
              f"  op: {obj(ops)},",
              f"  lock_free: new Set([{free}]), closed_tail: new Set([{closed}]),",
              f"  tlv: {tlv},",
              f"  event: {obj(iface.get('event', {}))}, enum: {en}, own: {obj(own)},",
              "  line_names: Object.freeze({" + ", ".join(f"{k}: {json.dumps(v)}" for k, v in iface.get("line_names", {}).items()) + "}),",
              "};",
              f"INTERFACES['{iface['name']}'] = {var};"]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    reg, digest = load()
    errors = check(reg)
    for e in errors:
        print("registry:", e, file=sys.stderr)
    if errors:
        return 1
    outputs = {OUT / "oep_v1_registry.h": cpp(reg, digest), OUT / "oep_v1_registry.py": py(reg, digest),
               OUT / "oep_v1_registry.js": js(reg, digest)}
    if args.check:
        stale = [p for p, text in outputs.items() if not p.exists() or p.read_text() != text]
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)} (run tools/oepgen1.py)", file=sys.stderr)
        return 1 if stale else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for p, text in outputs.items():
        p.write_text(text)
        print("wrote", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
