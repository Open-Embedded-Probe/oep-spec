# Open Embedded Probe Specification

[日本語](README.ja.md)

Open Embedded Probe (OEP) is a project that aims to let embedded-development probes expose their functions with shared meaning so different probe implementations and host software can use them interoperably.

Only the project name is settled at this time. Everything in this repository—including the purpose, scope, requirements, technical approach, and governance—is an exploratory draft, not a released protocol specification.

**Update (2026-09-26):** a v1 candidate specification now exists, in Japanese first: the normative core
[docs/oep-core.ja.md](docs/oep-core.ja.md), the standard interfaces `docs/oep-if-*.ja.md`, and the number registry
[registry/oep-v1.toml](registry/oep-v1.toml). The implementations follow it and are checked on hardware. It is not a released
specification and may still change incompatibly. English versions will follow once it settles; the English documents below
predate it. A map of the documents is [docs/review-guide.ja.md](docs/review-guide.ja.md) (Japanese).

The work begins by defining the problem, purpose, meaning of interoperability, scope, and success criteria. Function classification, protocol structure, connection methods, and the treatment of USB and PIDs will be considered incrementally from that upstream agreement.

- [Project purpose and scope](docs/project-concept.md)
- [Research and transition memo](memo.md)

**Update (2026-09-29):** serial ports now carry OEP frames and a target's console on one line (core §3.4), and probes
register slots and binds (`oep.probe.config`). Implementations:

- [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino) — the Arduino library `OpenEmbeddedProbe` and probe firmware
- [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python) — the Python host (`pip install oep-client-python`, `import oep_client`), the `oep` command and a fake probe

## Current documentation and language approach

The current documents are written in English and Japanese. English files use `.md`, their Japanese counterparts use `.ja.md`, and each translated pair links to the other language. Whether this becomes a formal project rule remains undecided.

Language rules for source code, test vectors, machine-readable registries, and protocol fields remain undecided.

## License

The contents of this repository are licensed under the [MIT License](LICENSE).

Whether and how this license relates to future use of a USB VID:PID, as well as the existence, acquisition, terms, and governance of any project PID, remains undecided. No project PID is currently available for general use.
