# Open Embedded Probe Specification

[日本語](README.ja.md)

Open Embedded Probe (OEP) is a project that aims to let embedded-development probes expose their functions with shared meaning so different probe implementations and host software can use them interoperably.

Only the project name is settled at this time. Everything in this repository—including the purpose, scope, requirements, technical approach, and governance—is an exploratory draft, not a released protocol specification.

The work begins by defining the problem, purpose, meaning of interoperability, scope, and success criteria. Function classification, protocol structure, connection methods, and the treatment of USB and PIDs will be considered incrementally from that upstream agreement.

- [Project purpose and scope](docs/project-concept.md)
- [Research and transition memo](memo.md)

Implementation-repository structure currently under consideration:

- [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino) — Arduino probe implementation
- [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python) — Python client library and reference CLI

## Current documentation and language approach

The current documents are written in English and Japanese. English files use `.md`, their Japanese counterparts use `.ja.md`, and each translated pair links to the other language. Whether this becomes a formal project rule remains undecided.

Language rules for source code, test vectors, machine-readable registries, and protocol fields remain undecided.

## License

The contents of this repository are licensed under the [MIT License](LICENSE).

Whether and how this license relates to future use of a USB VID:PID, as well as the existence, acquisition, terms, and governance of any project PID, remains undecided. No project PID is currently available for general use.
