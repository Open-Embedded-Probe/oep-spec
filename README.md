# Open Embedded Probe Specification

[日本語](README.ja.md)

Open Embedded Probe (OEP) is a protocol that lets embedded-development probes (debuggers, logic analysers, test fixtures)
expose their functions with shared meaning, so that different probe implementations and different host software work
together. A host finds a probe's functions by name, asks each one what it can do, and uses it; per-target knowledge stays in
the host.

## Status

OEP v1 is a **candidate for the freeze**. The normative text and the registry are complete (no numbers are left to be
decided), and the reference implementations follow them and are tested on hardware. Until the freeze, breaking changes go
in without raising the revision; what the freeze stops and what stays free is in
[the scope of the freeze](docs/v1-freeze-decisions.md) §0.

**Language**: the English text is normative. The Japanese documents (`.ja.md`) are translations; where the two differ,
the English text is right. Some guides and records exist only in Japanese.

## Map of the documents

Every document in `docs/` states its status in its first lines: **normative**, **guide** or **record**.

**Normative** (the specification):

- [OEP core](docs/oep-core.md): layers, frames, messages, sessions, discovery, plan, lifetime of resources, notifications,
  how an interface is written.
- Standard interfaces: [common parts](docs/oep-if-common.md), [wire and debug](docs/oep-if-debug.md),
  [console](docs/oep-if-console.md) (framing: [dmseq](docs/target-console-dmseq.md)), [fixture](docs/oep-if-fixture.md),
  [capture](docs/oep-if-capture.md), [probe settings](docs/oep-if-probe-config.md).
- [registry/oep-v1.toml](registry/oep-v1.toml): the only definition of every number on the v1 wire.
  `tools/oepgen1.py` generates `generated/oep-v1/` (C++, Python, JS) from it; `python3 tools/oepgen1.py --check` verifies they
  are in sync.

**Guides** (not normative):

- [Review guide](docs/review-guide.md): what is where, the shortest reading order, and the state of every document.
- [Project purpose and scope](docs/project-concept.md).
- Host and probe development guides, release testing, USB identification (Japanese only:
  [host](docs/host-development-guide.ja.md), [probe](docs/probe-development-guide.ja.md),
  [release testing](docs/release-testing.ja.md), [USB identification](docs/usb-identity.ja.md)).

**Records** (not normative): reasons for decisions, measurements, reviews, and the history before v1. They are listed in
[the review guide](docs/review-guide.md) §5.1; most are Japanese only. The experiments are in `experiments/`, and the
test environment for them in `tests/` ([tests/README.ja.md](tests/README.ja.md)).

## How to start

1. Read the [OEP core](docs/oep-core.md), then the standard interfaces you need.
2. Take the numbers from `registry/oep-v1.toml`, or copy the generated files in `generated/oep-v1/`.
3. Try a host against the fake probe of oep-client-python (`python -m oep_client.fake_serve`, on a pty or TCP), and
   look at a probe with `oep dump --port <port>` from the same package (list and describe of every interface).

Reference implementations:

- [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino): the Arduino library `OpenEmbeddedProbe`
  and probe firmware.
- [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python): the Python host
  (`pip install oep-client-python`), the `oep` command and a fake probe.

USB identification: a host identifies an OEP probe automatically only by the project's own USB VID:PID, once it is listed
in the registry (none is listed now). A probe named by its unit_id is found by its USB serial number and checked with
confirm and describe; otherwise the user chooses the port (core §3.3).

## Contributing

This repository is the source of truth: changes are direct edits by the maintainers or pull requests to this repository.
See [CONTRIBUTING](CONTRIBUTING.md) for rule changes and wording changes, adding `oep.` names and registry values,
third-party interfaces, and errata.

## License

The specification text and the registry, like the rest of this repository, are licensed under the
[MIT License](LICENSE). The license does not grant the use of a project USB VID:PID.
