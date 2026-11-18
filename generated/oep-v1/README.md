# OEP v1 generated constants

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

The constants generated from [registry/oep-v1.toml](../../registry/oep-v1.toml), one file per implementation language.

| File | Use |
|---|---|
| `oep_v1_registry.h` | header for C++ |
| `oep_v1_registry_c.h` | header for C |
| `oep_v1_registry.py` | module for Python |
| `oep_v1_registry.js` | module for JavaScript |

They define constants only; they hold no protocol encoder / decoder and no host / probe implementation. Each implementation takes them in together with the commit or tag of the specification it follows.

## Generating again and checking

Run at the repository root.

```sh
python3 tools/oepgen1.py
python3 tools/oepgen1.py --check
```

Do not edit the generated code by hand. The embedded registry hash checks that it matches the source TOML; it is no guarantee of wire compatibility. Compatibility is judged by [versioning](../../docs/versioning.md).
