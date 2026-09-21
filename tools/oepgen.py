# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Generate the OEP v0 C library, Python module and test vectors from registry/oep-v0.yaml.

Usage:
  uv run tools/oepgen.py            # write into generated/
  uv run tools/oepgen.py --check    # exit 1 if generated/ differs from the registry
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry" / "oep-v0.yaml"
OUT = ROOT / "generated"

SCALAR = {"u8": ("B", 1, "uint8_t"), "u16": ("<H", 2, "uint16_t"),
          "u32": ("<I", 4, "uint32_t"), "u64": ("<Q", 8, "uint64_t")}


def load():
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def up(name):
    return name.upper()


def field_kind(f):
    t = f["type"]
    if t in SCALAR:
        return "scalar"
    if t.startswith("bytes[") and t.endswith("]"):
        return "fixed_bytes"
    if t == "bytes":
        return "bytes"
    if t == "array":
        return "array"
    raise ValueError(f"unknown field type {t}")


def fixed_bytes_len(f):
    return int(f["type"][6:-1])


def validate(reg):
    for owner_name, fields in list(reg["headers"].items()):
        for f in fields:
            assert field_kind(f) == "scalar", f"header {owner_name} must be scalar only"
    for d in reg["definitions"]:
        for op in d["operations"]:
            for direction in ("request", "result"):
                fields = op[direction]
                for i, f in enumerate(fields):
                    k = field_kind(f)
                    if k in ("bytes", "array"):
                        assert i == len(fields) - 1, f"{d['name']}.{op['name']}.{direction}: {f['name']} must be last"
                    if k == "array":
                        assert f["of"] in reg["structs"], f"unknown struct {f['of']}"
                        for sf in reg["structs"][f["of"]]:
                            assert field_kind(sf) == "scalar", "array element structs must be scalar only"


# --------------------------------------------------------------------------- reference codec
def struct_fixed_size(reg, fields):
    size = 0
    for f in fields:
        k = field_kind(f)
        if k == "scalar":
            size += SCALAR[f["type"]][1]
        elif k == "fixed_bytes":
            size += fixed_bytes_len(f)
    return size


def ref_pack(reg, fields, values):
    """Reference encoder used only to build the vectors."""
    out = bytearray()
    for f in fields:
        k = field_kind(f)
        v = values[f["name"]]
        if k == "scalar":
            out += struct.pack(SCALAR[f["type"]][0], v)
        elif k == "fixed_bytes":
            b = bytes(v)
            assert len(b) == fixed_bytes_len(f)
            out += b
        elif k == "bytes":
            out += bytes(v)
        elif k == "array":
            out.append(len(v))
            for item in v:
                out += ref_pack(reg, reg["structs"][f["of"]], item)
    return bytes(out)


def sample_values(reg, fields, seed):
    values = {}
    for i, f in enumerate(fields):
        k = field_kind(f)
        n = seed * 7 + i
        if k == "scalar":
            size = SCALAR[f["type"]][1]
            v = 0
            for b in range(size):
                v |= ((0x11 * (b + 1) + n) & 0xFF) << (8 * b)
            values[f["name"]] = v
        elif k == "fixed_bytes":
            values[f["name"]] = [(0x41 + (n + b) % 26) for b in range(fixed_bytes_len(f))]
        elif k == "bytes":
            values[f["name"]] = [(0xA0 + (n + b)) & 0xFF for b in range(3 + seed)]
        elif k == "array":
            count = 2 if seed == 0 else 0
            values[f["name"]] = [sample_values(reg, reg["structs"][f["of"]], seed * 3 + j + 1) for j in range(count)]
    return values


def build_vectors(reg):
    vectors = []
    for role, fields in reg["headers"].items():
        for seed in (0, 1):
            values = sample_values(reg, fields, seed)
            payload = ref_pack(reg, fields, values)
            vectors.append({"name": f"header.{role}.{seed}", "kind": "header", "role": role,
                            "fields": values, "bytes": (bytes([reg["roles"][role]]) + payload).hex()})
        # wrong role byte must not decode
        values = sample_values(reg, fields, 0)
        wrong = (reg["roles"][role] + 0x40) & 0xFF
        vectors.append({"name": f"header.{role}.wrong_role", "kind": "header_reject", "role": role,
                        "bytes": (bytes([wrong]) + ref_pack(reg, fields, values)).hex()})
        vectors.append({"name": f"header.{role}.truncated", "kind": "header_reject", "role": role,
                        "bytes": (bytes([reg["roles"][role]]) + ref_pack(reg, fields, values))[:-1].hex()})
    for d in reg["definitions"]:
        for op in d["operations"]:
            for direction in ("request", "result"):
                fields = op[direction]
                for seed in (0, 1):
                    values = sample_values(reg, fields, seed)
                    payload = ref_pack(reg, fields, values)
                    vectors.append({"name": f"{d['name']}.{op['name']}.{direction}.{seed}", "kind": "payload",
                                    "definition": d["name"], "operation": op["name"], "direction": direction,
                                    "fields": values, "bytes": payload.hex()})
                fixed = struct_fixed_size(reg, fields)
                has_var = fields and field_kind(fields[-1]) in ("bytes", "array")
                if fixed:
                    values = sample_values(reg, fields, 0)
                    payload = ref_pack(reg, fields, values)
                    vectors.append({"name": f"{d['name']}.{op['name']}.{direction}.truncated", "kind": "payload_reject",
                                    "definition": d["name"], "operation": op["name"], "direction": direction,
                                    "bytes": payload[:fixed - 1].hex()})
                if not has_var:
                    values = sample_values(reg, fields, 0)
                    payload = ref_pack(reg, fields, values) + b"\x00"
                    vectors.append({"name": f"{d['name']}.{op['name']}.{direction}.trailing", "kind": "payload_reject",
                                    "definition": d["name"], "operation": op["name"], "direction": direction,
                                    "bytes": payload.hex()})
    return vectors


# --------------------------------------------------------------------------- C generation
def c_struct_name(*parts):
    return "oep_v0_" + "_".join(parts)


def c_fields(reg, fields):
    lines = []
    for f in fields:
        k = field_kind(f)
        if k == "scalar":
            lines.append(f"    {SCALAR[f['type']][2]} {f['name']};")
        elif k == "fixed_bytes":
            lines.append(f"    uint8_t {f['name']}[{fixed_bytes_len(f)}];")
        elif k == "bytes":
            lines.append(f"    const uint8_t *{f['name']};")
            lines.append(f"    uint16_t {f['name']}_length;")
        elif k == "array":
            lines.append(f"    uint8_t {f['name']}_count;")
            lines.append(f"    struct {c_struct_name(f['of'])} {f['name']}[{f['max']}];")
    if not lines:
        lines.append("    uint8_t unused_;  /* empty payload */")
    return "\n".join(lines)


def c_pack_body(reg, fields, var="value", indent="    "):
    """Emit code that appends fields to out/cap, tracking `n`."""
    lines = []
    for f in fields:
        k = field_kind(f)
        name = f"{var}->{f['name']}"
        if k == "scalar":
            size = SCALAR[f["type"]][1]
            lines.append(f"{indent}if (cap - n < {size}u) return 0;")
            for b in range(size):
                lines.append(f"{indent}out[n++] = (uint8_t)({name} >> {8 * b});" if b else f"{indent}out[n++] = (uint8_t){name};")
        elif k == "fixed_bytes":
            size = fixed_bytes_len(f)
            lines.append(f"{indent}if (cap - n < {size}u) return 0;")
            lines.append(f"{indent}memcpy(out + n, {name}, {size}u); n += {size}u;")
        elif k == "bytes":
            lines.append(f"{indent}if (cap - n < {name}_length) return 0;")
            lines.append(f"{indent}if ({name}_length) memcpy(out + n, {name}, {name}_length);")
            lines.append(f"{indent}n += {name}_length;")
        elif k == "array":
            lines.append(f"{indent}if ({name}_count > {f['max']}u || cap - n < 1u) return 0;")
            lines.append(f"{indent}out[n++] = {name}_count;")
            lines.append(f"{indent}for (uint8_t i = 0; i < {name}_count; ++i) {{")
            lines.append(f"{indent}    size_t m = {c_struct_name(f['of'])}_pack(&{name}[i], out + n, cap - n);")
            lines.append(f"{indent}    if (!m) return 0;")
            lines.append(f"{indent}    n += m;")
            lines.append(f"{indent}}}")
    return "\n".join(lines)


def c_unpack_body(reg, fields, var="value", indent="    "):
    lines = []
    fixed = struct_fixed_size(reg, fields)
    last_kind = field_kind(fields[-1]) if fields else None
    if last_kind in ("bytes", "array"):
        if fixed:
            lines.append(f"{indent}if (len < {fixed}u) return false;")
    else:
        lines.append(f"{indent}if (len != {fixed}u) return false;")
    for f in fields:
        k = field_kind(f)
        name = f"{var}->{f['name']}"
        if k == "scalar":
            size = SCALAR[f["type"]][1]
            ctype = SCALAR[f["type"]][2]
            expr = " | ".join(f"(({ctype})in[n + {b}] << {8 * b})" if b else f"({ctype})in[n]" for b in range(size))
            lines.append(f"{indent}{name} = {expr}; n += {size}u;")
        elif k == "fixed_bytes":
            size = fixed_bytes_len(f)
            lines.append(f"{indent}memcpy({name}, in + n, {size}u); n += {size}u;")
        elif k == "bytes":
            lines.append(f"{indent}if (len - n > 0xFFFFu) return false;")
            lines.append(f"{indent}{name} = in + n; {name}_length = (uint16_t)(len - n); n = len;")
        elif k == "array":
            esize = struct_fixed_size(reg, reg["structs"][f["of"]])
            lines.append(f"{indent}if (len - n < 1u) return false;")
            lines.append(f"{indent}{name}_count = in[n++];")
            lines.append(f"{indent}if ({name}_count > {f['max']}u || len - n != (size_t){name}_count * {esize}u) return false;")
            lines.append(f"{indent}for (uint8_t i = 0; i < {name}_count; ++i) {{")
            lines.append(f"{indent}    if (!{c_struct_name(f['of'])}_unpack(in + n, {esize}u, &{name}[i])) return false;")
            lines.append(f"{indent}    n += {esize}u;")
            lines.append(f"{indent}}}")
    lines.append(f"{indent}(void)n; (void){var};")
    return "\n".join(lines)


def gen_c(reg, vectors):
    h = []
    c = []
    h.append("/* Generated by tools/oepgen.py from registry/oep-v0.yaml. Do not edit. */")
    h.append("#ifndef OEP_V0_H\n#define OEP_V0_H\n\n#include <stdbool.h>\n#include <stddef.h>\n#include <stdint.h>\n")
    h.append('#ifdef __cplusplus\nextern "C" {\n#endif\n')
    p = reg["protocol"]
    h.append(f"#define OEP_V0_PROTOCOL_VERSION {p['version']}u\n#define OEP_V0_PROTOCOL_REVISION {p['revision']}u\n")
    for k, v in reg["constants"].items():
        h.append(f'#define OEP_V0_CONST_{up(k)} "{v}"')
    h.append("")
    for section, prefix in (("roles", "ROLE"), ("resolutions", "RESOLUTION"), ("outcomes", "OUTCOME"),
                            ("reject_reasons", "REJECT")):
        for k, v in reg[section].items():
            h.append(f"#define OEP_V0_{prefix}_{up(k)} 0x{v:02x}u")
        h.append("")
    h.append(f"#define OEP_V0_TLV_CRITICAL_MASK 0x{reg['tlv']['critical_mask']:02x}u")
    for k, v in reg["tlv"]["core_tags"].items():
        h.append(f"#define OEP_V0_TLV_CORE_{up(k)} 0x{v:02x}u")
    h.append("")
    for d in reg["definitions"]:
        n = up(d["name"])
        h.append(f"#define OEP_V0_DEF_{n}_OWNER 0x{d['owner']:04x}u")
        h.append(f"#define OEP_V0_DEF_{n}_ID 0x{d['id']:04x}u")
        h.append(f"#define OEP_V0_DEF_{n}_REVISION {d['revision']}u")
        if "function" in d:
            h.append(f"#define OEP_V0_DEF_{n}_FUNCTION 0x{d['function']:04x}u")
        for op in d["operations"]:
            h.append(f"#define OEP_V0_{n}_OP_{up(op['name'])} 0x{op['op']:02x}u")
        h.append("")
    c.append('/* Generated by tools/oepgen.py from registry/oep-v0.yaml. Do not edit. */\n#include "oep_v0.h"\n\n#include <string.h>\n')

    def emit_struct(name, fields, header_role=None):
        sname = c_struct_name(name)
        h.append(f"struct {sname} {{\n{c_fields(reg, fields)}\n}};")
        if header_role is not None:
            h.append(f"/* pack writes the role byte first; unpack checks it and returns the header length. */")
            h.append(f"size_t {sname}_pack(const struct {sname} *value, uint8_t *out, size_t cap);")
            h.append(f"bool {sname}_unpack(const uint8_t *in, size_t len, struct {sname} *value, size_t *header_length);\n")
            fixed = struct_fixed_size(reg, fields)
            c.append(f"size_t {sname}_pack(const struct {sname} *value, uint8_t *out, size_t cap) {{\n    size_t n = 0;")
            c.append(f"    if (cap < 1u) return 0;\n    out[n++] = OEP_V0_ROLE_{up(header_role)};")
            c.append(c_pack_body(reg, fields))
            c.append("    return n;\n}\n")
            c.append(f"bool {sname}_unpack(const uint8_t *in, size_t len, struct {sname} *value, size_t *header_length) {{")
            c.append(f"    size_t n = 0;\n    if (len < {fixed + 1}u || in[0] != OEP_V0_ROLE_{up(header_role)}) return false;")
            c.append(f"    in += 1; len = {fixed}u;")
            c.append(c_unpack_body(reg, fields))
            c.append(f"    if (header_length) *header_length = {fixed + 1}u;\n    return true;\n}}\n")
        else:
            h.append(f"size_t {sname}_pack(const struct {sname} *value, uint8_t *out, size_t cap);")
            h.append(f"bool {sname}_unpack(const uint8_t *in, size_t len, struct {sname} *value);\n")
            c.append(f"size_t {sname}_pack(const struct {sname} *value, uint8_t *out, size_t cap) {{\n    size_t n = 0;")
            c.append(c_pack_body(reg, fields))
            c.append("    (void)value; (void)out; (void)cap;\n    return n;\n}\n")
            c.append(f"bool {sname}_unpack(const uint8_t *in, size_t len, struct {sname} *value) {{\n    size_t n = 0;")
            c.append(c_unpack_body(reg, fields))
            c.append("    (void)in;\n    return true;\n}\n")

    for name, fields in reg["structs"].items():
        emit_struct(name, fields)
    for role, fields in reg["headers"].items():
        emit_struct(f"{role}_header", fields, header_role=role)
    for d in reg["definitions"]:
        for op in d["operations"]:
            for direction in ("request", "result"):
                emit_struct(f"{d['name']}_{op['name']}_{direction}", op[direction])
    h.append("/* Returns the role byte of a message, or 0 when it is empty or unknown. */")
    h.append("uint8_t oep_v0_message_role(const uint8_t *msg, size_t len);\n")
    c.append("uint8_t oep_v0_message_role(const uint8_t *msg, size_t len) {\n    if (!len) return 0;\n    switch (msg[0]) {")
    for k, v in reg["roles"].items():
        c.append(f"    case OEP_V0_ROLE_{up(k)}:")
    c.append("        return msg[0];\n    default:\n        return 0;\n    }\n}\n")
    h.append('#ifdef __cplusplus\n}\n#endif\n\n#endif /* OEP_V0_H */\n')

    # vectors header: roundtrip functions per vector kind
    v = ["/* Generated by tools/oepgen.py. Test vectors for oep_v0. */", "#ifndef OEP_V0_VECTORS_H\n#define OEP_V0_VECTORS_H\n",
         '#include "oep_v0.h"\n#include <string.h>\n',
         "/* 0 = pack/unpack roundtrip reproduces the bytes, 1 = unpack must fail, 2 = unexpected. */",
         "struct oep_v0_vector { const char *name; const uint8_t *bytes; size_t length; int expect_reject;\n"
         "    int (*roundtrip)(const uint8_t *, size_t); };\n"]
    fns = []
    entries = []
    for i, vec in enumerate(vectors):
        data = bytes.fromhex(vec["bytes"])
        arr = ", ".join(f"0x{b:02x}" for b in data) or "0"
        v.append(f"static const uint8_t oep_v0_vec_{i}[] = {{{arr}}};")
        if vec["kind"] in ("header", "header_reject"):
            sname = c_struct_name(f"{vec['role']}_header")
            fn = f"oep_v0_rt_{vec['role']}_header"
            body = (f"static int {fn}(const uint8_t *in, size_t len) {{\n    struct {sname} v; size_t hl = 0; uint8_t out[512];\n"
                    f"    if (!{sname}_unpack(in, len, &v, &hl)) return 1;\n"
                    f"    size_t n = {sname}_pack(&v, out, sizeof out);\n"
                    f"    return (n == len && hl == len && memcmp(out, in, len) == 0) ? 0 : 2;\n}}")
        else:
            sname = c_struct_name(f"{vec['definition']}_{vec['operation']}_{vec['direction']}")
            fn = f"oep_v0_rt_{vec['definition']}_{vec['operation']}_{vec['direction']}"
            body = (f"static int {fn}(const uint8_t *in, size_t len) {{\n    struct {sname} v; uint8_t out[512];\n"
                    f"    memset(&v, 0, sizeof v);\n"
                    f"    if (!{sname}_unpack(in, len, &v)) return 1;\n"
                    f"    size_t n = {sname}_pack(&v, out, sizeof out);\n"
                    f"    return (n == len && memcmp(out, in, len) == 0) ? 0 : 2;\n}}")
        if body not in fns:
            fns.append(body)
        expect = 1 if vec["kind"].endswith("reject") else 0
        entries.append(f'    {{"{vec["name"]}", oep_v0_vec_{i}, sizeof oep_v0_vec_{i}{"" if data else " - 1"}, {expect}, {fn}}},')
    v.append("")
    v.extend(fns)
    v.append("\nstatic const struct oep_v0_vector oep_v0_vectors[] = {")
    v.extend(entries)
    v.append("};\n#define OEP_V0_VECTOR_COUNT (sizeof oep_v0_vectors / sizeof oep_v0_vectors[0])\n\n#endif\n")
    return "\n".join(h), "\n".join(c), "\n".join(v)


# --------------------------------------------------------------------------- Python generation
def py_pack_expr(reg, fields):
    lines = ["        out = bytearray()"]
    for f in fields:
        k = field_kind(f)
        n = f"self.{f['name']}"
        if k == "scalar":
            lines.append(f"        out += struct.pack('{SCALAR[f['type']][0]}', {n})")
        elif k == "fixed_bytes":
            size = fixed_bytes_len(f)
            lines.append(f"        if len({n}) != {size}: raise ValueError('{f['name']} must be {size} bytes')")
            lines.append(f"        out += bytes({n})")
        elif k == "bytes":
            lines.append(f"        out += bytes({n})")
        elif k == "array":
            lines.append(f"        if len({n}) > {f['max']}: raise ValueError('{f['name']} exceeds {f['max']}')")
            lines.append(f"        out.append(len({n}))")
            lines.append(f"        for item in {n}: out += item.pack()")
    lines.append("        return bytes(out)")
    return "\n".join(lines)


def py_unpack_expr(reg, fields, cls):
    fixed = struct_fixed_size(reg, fields)
    last = field_kind(fields[-1]) if fields else None
    lines = ["        n = 0"]
    if last in ("bytes", "array"):
        lines.append(f"        if len(data) < {fixed}: raise ValueError('short payload')")
    else:
        lines.append(f"        if len(data) != {fixed}: raise ValueError('payload length must be {fixed}')")
    args = []
    for f in fields:
        k = field_kind(f)
        if k == "scalar":
            fmt, size, _ = SCALAR[f["type"]]
            lines.append(f"        {f['name']} = struct.unpack_from('{fmt}', data, n)[0]; n += {size}")
        elif k == "fixed_bytes":
            size = fixed_bytes_len(f)
            lines.append(f"        {f['name']} = bytes(data[n:n + {size}]); n += {size}")
        elif k == "bytes":
            lines.append(f"        {f['name']} = bytes(data[n:]); n = len(data)")
        elif k == "array":
            esize = struct_fixed_size(reg, reg["structs"][f["of"]])
            ecls = "".join(w.title() for w in f["of"].split("_"))
            lines.append(f"        count = data[n]; n += 1")
            lines.append(f"        if count > {f['max']} or len(data) - n != count * {esize}: raise ValueError('bad array')")
            lines.append(f"        {f['name']} = [{ecls}.unpack(data[n + i * {esize}:n + (i + 1) * {esize}]) for i in range(count)]; n += count * {esize}")
        args.append(f"{f['name']}={f['name']}")
    lines.append(f"        return cls({', '.join(args)})")
    return "\n".join(lines)


def gen_py(reg):
    out = ['"""Generated by tools/oepgen.py from registry/oep-v0.yaml. Do not edit."""', "",
           "from __future__ import annotations", "", "import struct", "from dataclasses import dataclass, field", ""]
    p = reg["protocol"]
    out.append(f"PROTOCOL_VERSION = {p['version']}\nPROTOCOL_REVISION = {p['revision']}\n")
    for k, v in reg["constants"].items():
        out.append(f"CONST_{up(k)} = {v.encode().__repr__()}")
    out.append("")
    for section, prefix in (("roles", "ROLE"), ("resolutions", "RESOLUTION"), ("outcomes", "OUTCOME"),
                            ("reject_reasons", "REJECT")):
        for k, v in reg[section].items():
            out.append(f"{prefix}_{up(k)} = 0x{v:02x}")
        out.append(f"{prefix}S = {{" + ", ".join(f"'{k}': 0x{v:02x}" for k, v in reg[section].items()) + "}\n")
    out.append(f"TLV_CRITICAL_MASK = 0x{reg['tlv']['critical_mask']:02x}")
    for k, v in reg["tlv"]["core_tags"].items():
        out.append(f"TLV_CORE_{up(k)} = 0x{v:02x}")
    out.append("")
    for d in reg["definitions"]:
        n = up(d["name"])
        out.append(f"DEF_{n} = (0x{d['owner']:04x}, 0x{d['id']:04x}, {d['revision']})")
        if "function" in d:
            out.append(f"DEF_{n}_FUNCTION = 0x{d['function']:04x}")
        for op in d["operations"]:
            out.append(f"{n}_OP_{up(op['name'])} = 0x{op['op']:02x}")
    out.append("")

    def cls_name(*parts):
        return "".join(w.title() for w in "_".join(parts).split("_"))

    def py_type(f):
        k = field_kind(f)
        if k == "scalar":
            return "int", "0"
        if k in ("fixed_bytes", "bytes"):
            return "bytes", "b''"
        return f"list[{cls_name(f['of'])}]", "field(default_factory=list)"

    def emit(name, fields, role=None):
        cname = cls_name(name)
        out.append("@dataclass")
        out.append(f"class {cname}:")
        if role is not None:
            out.append(f"    ROLE = 0x{reg['roles'][role]:02x}")
        for f in fields:
            t, default = py_type(f)
            out.append(f"    {f['name']}: {t} = {default}")
        if not fields and role is None:
            out.append("    pass")
        out.append("")
        out.append("    def pack(self) -> bytes:")
        if role is not None:
            out.append(f"        out = bytearray([self.ROLE])")
            body = py_pack_expr(reg, fields).replace("        out = bytearray()\n", "")
            out.append(body)
        else:
            out.append(py_pack_expr(reg, fields))
        out.append("")
        out.append("    @classmethod")
        if role is not None:
            fixed = struct_fixed_size(reg, fields)
            out.append(f"    def unpack(cls, data: bytes) -> '{cname}':")
            out.append(f"        if len(data) < {fixed + 1} or data[0] != cls.ROLE: raise ValueError('not a {role} header')")
            out.append(f"        data = data[1:{fixed + 1}]")
            out.append(py_unpack_expr(reg, fields, cname))
            out.append("")
            out.append(f"    HEADER_LENGTH = {fixed + 1}")
        else:
            out.append(f"    def unpack(cls, data: bytes) -> '{cname}':")
            out.append(py_unpack_expr(reg, fields, cname))
        out.append("\n")

    for name, fields in reg["structs"].items():
        emit(name, fields)
    for role, fields in reg["headers"].items():
        emit(f"{role}_header", fields, role=role)
    for d in reg["definitions"]:
        for op in d["operations"]:
            for direction in ("request", "result"):
                emit(f"{d['name']}_{op['name']}_{direction}", op[direction])
    out.append("HEADER_CLASSES = {" + ", ".join(f"'{r}': {cls_name(r + '_header')}" for r in reg["headers"]) + "}")
    out.append("PAYLOAD_CLASSES = {")
    for d in reg["definitions"]:
        for op in d["operations"]:
            for direction in ("request", "result"):
                out.append(f"    ('{d['name']}', '{op['name']}', '{direction}'): {cls_name(d['name'], op['name'], direction)},")
    out.append("}\n")
    out.append("def message_role(msg: bytes) -> int:\n    \"\"\"Role byte of a message, or 0 when empty or unknown.\"\"\"\n"
               "    return msg[0] if msg and msg[0] in ROLES.values() else 0\n")
    return "\n".join(out)


def render(reg):
    validate(reg)
    vectors = build_vectors(reg)
    h, c, v = gen_c(reg, vectors)
    files = {
        "oep-v0-c/library.properties": ("name=OEP v0 Generated Codec\nversion=0.0.0\nauthor=Open Embedded Probe contributors\n"
                                       "maintainer=Open Embedded Probe contributors\nsentence=Generated OEP v0 wire codec.\n"
                                       "paragraph=Generated from registry/oep-v0.yaml by tools/oepgen.py.\ncategory=Other\n"
                                       "architectures=*\n"),
        "oep-v0-c/src/oep_v0.h": h + "\n",
        "oep-v0-c/src/oep_v0.c": c + "\n",
        "oep-v0-c/src/oep_v0_vectors.h": v + "\n",
        "oep-v0-py/oep_v0.py": gen_py(reg) + "\n",
        "oep-v0-vectors.json": json.dumps({"registry": REGISTRY.name, "vectors": vectors}, indent=1) + "\n",
    }
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = render(load())
    stale = []
    for rel, content in files.items():
        path = OUT / rel
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)} ({len(content)} bytes)")
    if args.check:
        if stale:
            print("stale:", *stale, sep="\n  ")
            sys.exit(1)
        print("generated/ is up to date")


if __name__ == "__main__":
    main()
