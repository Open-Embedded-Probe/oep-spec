# Checks of the OEP v1 registry

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

`test_registry_v1.py` checks the numbering rules, table structure, reserved values and so on of the [registry](../../registry/README.md), and that the [generated files per language](../../generated/oep-v1/README.md) match it. It also checks that the generator refuses invalid definitions.

To run only these checks, run the following from the repository root.

```sh
cd tests
uv run pytest registry_v1
```

When a rule of the specification changes, the matching checks are updated too. For the guide to all checks, see [tests/README.md](../README.md).
