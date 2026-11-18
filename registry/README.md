# The wire number registry

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

[oep-v1.toml](oep-v1.toml) is the only definition of the wire numbers and constants of OEP v1. It holds ops, TLV tags, enums, the common status, USB identification constants and so on. The meaning of each value and the structure of payloads are defined in [core](../docs/oep-core.md), [transport](../docs/oep-transports.md) and the [standard interfaces](../interfaces/README.md). The comments at the top of the TOML explain the table structure of the registry.

## How to update

Update the normative documents and the registry in the same change, and run from the repository root:

```sh
python3 tools/oepgen1.py
python3 tools/oepgen1.py --check
```

The generated constants are in [generated/oep-v1/](../generated/oep-v1/README.md). For a change that affects the wire vectors, also update the [vectors](../tests/vectors/README.md) and run the [automated checks](../tests/README.md). Number assignment and compatibility decisions follow [Contributing](../CONTRIBUTING.md) and [Versions and stability](../docs/versioning.md).
