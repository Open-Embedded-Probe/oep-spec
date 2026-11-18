# Open Embedded Probe Specification

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Open Embedded Probe (OEP) is a protocol by which embedded-development probes (debuggers, logic analyzers, fixtures) offer their functions with a common meaning, so that different probes and hosts can be used in combination. The host holds the target-specific knowledge.

## Status and language

OEP v1 is before its freeze. Until the freeze, incompatible changes can go in without changing the revision, so an implementation states the Git commit or tag of the specification it follows.
The existing contracts of the core and transports are [provisionally fixed](docs/versioning.md#21-provisional-fixing-of-the-core), and ordinary functional additions are made in optional interfaces.

The Japanese documents (`.ja.md`) and the English ones (`.md`) are maintained together. Until the freeze (the official `v1.0.0` release) the Japanese text is authoritative and the English one its translation; from the freeze English is normative and Japanese the translation ([versioning](docs/versioning.md) §2).

## Sources of truth of the specification

- [OEP core](docs/oep-core.md) and [transport](docs/oep-transports.md)
- [Standard interfaces](interfaces/README.md)
- [registry/oep-v1.toml](registry/oep-v1.toml), which defines the numbers on the wire

The registry is the only definition of the numbers on the wire. Where a document and the registry disagree, that is a defect of the specification: the document is corrected, and both are made to agree in the same change. The generated files `generated/oep-v1/` are made from the registry and are not edited.

## Reading order

1. [Purpose and scope](docs/project-concept.md)
2. [Getting started](docs/getting-started.md)
3. [OEP core](docs/oep-core.md), [transport](docs/oep-transports.md), and the [interfaces](interfaces/README.md) you need
4. [Conformance requirements](docs/conformance.md)

When implementing, also see the [host development guide](docs/host-development-guide.md) or the [probe development guide](docs/probe-development-guide.md). Terms, security and the compatibility policy are collected in the [glossary](docs/glossary.md), [safety and security](docs/security.md) and [versions and stability](docs/versioning.md). The entry point for reviews is the [review guide](docs/review-guide.md).

## Directory layout

The `README.md` directly under each directory describes its content and how it is updated.

| Directory | Content |
|---|---|
| [docs/](docs/README.md) | Normative core and transport text, conformance requirements, development guides, maintenance policy |
| [interfaces/](interfaces/README.md) | Normative text of the standard interfaces and of the common parts and framing they use |
| [registry/](registry/README.md) | Definitions of the numbers and constants on the wire |
| [generated/](generated/README.md) | Per-language constants generated from the registry |
| [generated/oep-v1/](generated/oep-v1/README.md) | OEP v1 generated files for C, C++, Python and JavaScript |
| [tools/](tools/README.md) | Generation and consistency checks of the registry constants and the shared test vectors |
| [tests/](tests/README.md) | Automatic checks of the specification, registry, generated files and documents |
| [tests/registry_v1/](tests/registry_v1/README.md) | Checks of the v1 numbering rules and the generated files |
| [tests/vectors/](tests/vectors/README.md) | Wire vectors shared between implementations, and their self-consistency checks |

The root holds this guide, the [contribution procedure](CONTRIBUTING.md), the [change list](CHANGELOG.md) and the [license](LICENSE).

## Repository boundaries

[Responsibilities between repositories](docs/repository-boundaries.md) is authoritative. In short:

- `oep-spec`: the protocol, registry, generated files, shared test vectors, conformance requirements
- `oep-probe-arduino`: the probe implementation, platform-specific constraints, firmware build and tests
- `oep-client-python` / `oep-client-js`: host implementations, API, CLI, implementation tests
- `wireskein` / `wireskein-web` / `pytest-embedded-wireskein`: applications that use OEP, and their own data formats and operation

Implementation-specific procedures, hardware measurements, product constraints, investigation logs, applied proposals and review replies are not copied into this repository. Only the final rules, and the reasons needed for decisions that are hard to change later, stay in the current documents. Past history can be found in the Git history.

## Checks

```sh
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest
```

The shared vectors are in `tests/vectors/`. Each implementation takes them in and has its own unit tests and integration tests in its own repository.

## Contributing

For specification changes, registry additions, third-party interfaces and the handling of errata, see [CONTRIBUTING.md](CONTRIBUTING.md).

The specification, registry and generated files are published under the [MIT License](LICENSE). This license does not include permission to use the project's USB VID:PID. The terms of use of the VID:PID are set in the probe implementation repository that manages it.
