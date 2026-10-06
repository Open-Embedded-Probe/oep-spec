# /// script
# requires-python = ">=3.11"
# ///
"""Generate the OEP v1 constants (C++ header, C header, Python and JS modules) from registry/oep-v1.toml, after checking the numbering
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
           "limits", "reference", "describe_common", "usb", "common", "core", "interface"}
    if set(reg) - top:
        errors.append(f"unknown table kinds {sorted(set(reg) - top)} (registry header)")
    if set(reg.get("common", {})) - {"enum"}:
        errors.append(f"unknown common tables {sorted(set(reg['common']) - {'enum'})} (registry header)")
    iface_keys = {"name", "revision", "fn", "target", "op", "tlv", "enum", "event", "status", "reject_reasons", "reserved", "line_names"}
    core_keys = {"op", "tlv", "enum", "event", "status", "reject_reasons", "reserved"}
    for iface in reg.get("interface", []):
        if set(iface) - iface_keys:
            errors.append(f"{iface.get('name')}: unknown interface keys {sorted(set(iface) - iface_keys)} (registry header)")
        if "target" in iface and not (isinstance(iface["target"], str) and iface["target"]):
            errors.append(f"{iface.get('name')}: target must be a non-empty string (registry header)")
    if set(reg.get("core", {})) - core_keys:
        errors.append(f"core: unknown keys {sorted(set(reg['core']) - core_keys)} (registry header)")
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
    for iface in [reg["core"]] + reg["interface"]:
        n = iface.get("name", "core")
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
            if set(op) - {"code", "name", "lock", "fields"}:
                errors.append(f"{n}: op {op['name']} has unknown keys {sorted(set(op) - {'code', 'name', 'lock', 'fields'})}")
        if iface is reg["core"]:
            ranges = [(0x01, 0x0F), (0x10, 0x1F)]
            for c, opname in codes.items():
                if not any(a <= c <= b for a, b in ranges):
                    errors.append(f"core: op {opname} = {c:#x} outside the core ranges")
        else:
            # core §11.3: 0x30 subscribe and 0x32 unsubscribe are reserved in every interface's op space; both or neither
            sub, unsub = reg["constants"]["op_subscribe"], reg["constants"]["op_unsubscribe"]
            for c, want in ((sub, "subscribe"), (unsub, "unsubscribe")):
                if c in codes and codes[c] != want:
                    errors.append(f"{n}: op {codes[c]} = {c:#x} uses the number reserved for {want} (core §11.3)")
                if want in codes.values() and codes.get(c) != want:
                    errors.append(f"{n}: op {want} must be {c:#x} (core §11.3)")
            if (codes.get(sub) == "subscribe") != (codes.get(unsub) == "unsubscribe"):
                errors.append(f"{n}: subscribe and unsubscribe go together (core §11.3)")
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


def units(reg: dict) -> list[tuple[str, dict]]:
    """The core (no name; namespace `core`) and then every interface (namespace: its name without `oep.`)."""
    return [("core", reg["core"])] + [(iface["name"].removeprefix("oep."), iface) for iface in reg["interface"]]


SPDX_C = "// SPDX-License-Identifier: MIT"
SPDX_PY = "# SPDX-License-Identifier: MIT"


def camel(s: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[_\-.]+", s) if part)


def ident(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_")


def cpp(reg: dict, digest: str) -> str:
    L = [SPDX_C, "// Generated by oep-spec tools/oepgen1.py from registry/oep-v1.toml - do not edit.",
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
    for unit, iface in units(reg):
        ns = ident(unit)
        L += ["", f"namespace {ns} {{"]
        if "name" in iface:
            L += [f'constexpr const char *kName = "{iface["name"]}";', f"constexpr uint8_t kRevision = {iface['revision']};"]
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


def c(reg: dict, digest: str) -> str:
    """The C++ header's values as C macros (C firmware, Zephyr, bindgen): OEP_V1_<GROUP>_<NAME>, interfaces
    OEP_V1_<INTERFACE>_<KIND>_<NAME>. Strings are string literals; numbers are unsigned literals."""
    def up(*parts: str) -> str:
        return "_".join(ident(p).upper() for p in parts if p)

    def d(name: str, v) -> str:
        return f'#define {name} "{v}"' if isinstance(v, str) else f"#define {name} {v:#x}u"
    L = [SPDX_C, "// Generated by oep-spec tools/oepgen1.py from registry/oep-v1.toml - do not edit.",
         f"// registry schema {reg['registry']['schema']}, sha256 {digest}",
         "#ifndef OEP_V1_REGISTRY_C_H", "#define OEP_V1_REGISTRY_C_H", "",
         f'#define OEP_V1_REGISTRY_HASH "{digest}"', f"#define OEP_V1_PROTOCOL_REVISION {reg['protocol']['revision']}u"]
    for k, v in reg["constants"].items():
        L.append(d(up("OEP_V1", k), v))
    for group in ("roles", "resolutions", "outcomes", "reject_reasons", "status", "describe_common", "timing", "usb", "limits",
                  "reference"):
        L.append("")
        for k, v in reg.get(group, {}).items():
            L.append(d(up("OEP_V1", group, k), v))
    L.append("")
    for enum, values in reg.get("common", {}).get("enum", {}).items():
        for k, v in values.items():
            L.append(d(up("OEP_V1_COMMON", enum, k), v))
    for unit, iface in units(reg):
        ns = up("OEP_V1", unit)
        L.append("")
        if "name" in iface:
            L += [f'#define {ns}_NAME "{iface["name"]}"', f"#define {ns}_REVISION {iface['revision']}u"]
        for op in iface["op"]:
            L.append(d(up(ns, "OP", op["name"]), op["code"]))
        lock = sum(1 << op["code"] for op in iface["op"] if not op.get("lock") and op["code"] < 64)
        L.append(f"#define {ns}_LOCK_FREE_OPS {lock:#x}ull   // bit n = op n needs no lock")
        for context, tags in iface.get("tlv", {}).items():
            for k, v in tags.items():
                L.append(d(up(ns, "TLV", context, k), v))
        for k, v in iface.get("event", {}).items():
            L.append(d(up(ns, "EVENT", k), v))
        for group, prefix in (("status", "STATUS"), ("reject_reasons", "REJECT")):
            for k, v in iface.get(group, {}).items():
                L.append(d(up(ns, prefix, k), v))
        for enum, values in iface.get("enum", {}).items():
            for k, v in values.items():
                L.append(d(up(ns, enum, k), v))
        for k in iface.get("line_names", {}):
            L.append(d(up(ns, "LINE_NAME", k), k))
    L += ["", "#endif  // OEP_V1_REGISTRY_C_H", ""]
    return "\n".join(L)


def py(reg: dict, digest: str) -> str:
    L = [SPDX_PY, '"""Generated by oep-spec tools/oepgen1.py from registry/oep-v1.toml - do not edit."""', "",
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
    for unit, iface in units(reg):
        var = ident(unit).upper()
        ops = ", ".join(f'"{o["name"]}": 0x{o["code"]:02X}' for o in iface["op"])
        free = ", ".join(f'0x{o["code"]:02X}' for o in iface["op"] if not o.get("lock"))
        tlv = ", ".join(f'"{c}": {{' + ", ".join(f'"{k}": 0x{v:02X}' for k, v in t.items()) + "}"
                        for c, t in iface.get("tlv", {}).items())
        ev = ", ".join(f'"{k}": 0x{v:02X}' for k, v in iface.get("event", {}).items())
        en = ", ".join(f'"{e}": {{' + ", ".join(f'"{k}": 0x{v:02X}' for k, v in vals.items()) + "}"
                       for e, vals in iface.get("enum", {}).items())
        own = ", ".join(f'"{k}": 0x{v:02X}' for g in ("status", "reject_reasons") for k, v in iface.get(g, {}).items())
        lines = ", ".join(f"{k!r}: {v!r}" for k, v in iface.get("line_names", {}).items())
        head = (f'name="{iface["name"]}", revision={iface["revision"]}, target={json.dumps(iface.get("target")) if "target" in iface else "None"}, '
                if "name" in iface else "")
        lock_free = f"{{{free}}}" if free else "set()"
        L += [f'{var} = _NS({head}op={{{ops}}}, lock_free={lock_free},',
              f"    tlv={{{tlv}}}, event={{{ev}}}, enum={{{en}}}, own={{{own}}},",
              f"    line_names={{{lines}}})"]
        if "name" in iface:
            L.append(f'INTERFACES["{iface["name"]}"] = {var}')
    return "\n".join(L) + "\n"


def js(reg: dict, digest: str) -> str:
    """The same shape as py(): objects keyed by the registry's snake_case names; lock_free is a Set."""
    def obj(d: dict) -> str:
        return "{" + ", ".join(f"{k}: 0x{v:02X}" if re.fullmatch(r"[A-Za-z_]\w*", k) else f'"{k}": 0x{v:02X}'
                               for k, v in d.items()) + "}"
    L = ["// @ts-check", SPDX_C, "// Generated by oep-spec tools/oepgen1.py from registry/oep-v1.toml - do not edit.", "",
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
    for unit, iface in units(reg):
        var = ident(unit).upper()
        free = ", ".join(f"0x{o['code']:02X}" for o in iface["op"] if not o.get("lock"))
        tlv = "{" + ", ".join(f"{c}: {obj(t)}" for c, t in iface.get("tlv", {}).items()) + "}"
        en = "{" + ", ".join(f"{e}: {obj(v)}" for e, v in iface.get("enum", {}).items()) + "}"
        own = {k: v for g in ("status", "reject_reasons") for k, v in iface.get(g, {}).items()}
        ops = {o["name"]: o["code"] for o in iface["op"]}
        L += [f"export const {var} = {{"]
        if "name" in iface:
            L.append(f"  name: '{iface['name']}', revision: {iface['revision']}, target: {json.dumps(iface.get('target'))},")
        L += [
              f"  op: {obj(ops)},",
              f"  lock_free: new Set([{free}]),",
              f"  tlv: {tlv},",
              f"  event: {obj(iface.get('event', {}))}, enum: {en}, own: {obj(own)},",
              "  line_names: Object.freeze({" + ", ".join(f"{k}: {json.dumps(v)}" for k, v in iface.get("line_names", {}).items()) + "}),",
              "};"]
        if "name" in iface:
            L.append(f"INTERFACES['{iface['name']}'] = {var};")
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
    outputs = {OUT / "oep_v1_registry.h": cpp(reg, digest), OUT / "oep_v1_registry_c.h": c(reg, digest),
               OUT / "oep_v1_registry.py": py(reg, digest),
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
