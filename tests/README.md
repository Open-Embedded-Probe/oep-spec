# Automated checks of the specification

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

This directory holds only checks of the current specification itself.

- [registry_v1/](registry_v1/README.md): consistency of `registry/oep-v1.toml`, the generated files and the numbering rules
- [vectors/](vectors/README.md): shared wire vectors computed from the normative rules, and their self-consistency
- `test_docs.py`: the layout where only the Japanese version is maintained, and local document links

```sh
cd tests
uv run pytest
```

Tests of probe / host implementations, hardware tests and comparisons of past design candidates are not kept here. They run in the implementation repositories that own them.
