# OEP specification and guides

[日本語](README.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

This directory holds the normative text for the protocol as a whole, the common guides for implementations, and the maintenance policy of the specification. The normative text of the standard interfaces is in [interfaces/](../interfaces/README.md), and the source of truth for the numbers on the wire is in [registry/](../registry/README.md).

## Reading order

1. [Purpose and scope](project-concept.md): what OEP covers, and the roles of host / probe.
2. [Getting started](getting-started.md): the flow from connecting to using a function.
3. [OEP core](oep-core.md) and [transport](oep-transports.md): the normative text for messages, sessions, discovery of functions and transports.
   [Settings file](oep-settings-file.md): the shape of the file that exports probe settings and imports them again (normative).
4. [Conformance requirements](conformance.md): the requirements an implementation meets, and how to check them.

## Guide by purpose

| Purpose | Document |
|---|---|
| Implement a host | [Host development guide](host-development-guide.md) |
| Implement a probe | [Probe development guide](probe-development-guide.md) |
| Define your own functions and checks | [Extension development guide](extension-development-guide.md) |
| Extend self-update or privileged operations | [Extension examples by use case](extension-use-cases.md) |
| Check at which layer to test peripherals, and what the probe's functions can test | [Layers of peripheral testing and probe functions](peripheral-testing.md) |
| Look up terms | [Glossary](glossary.md) |
| Handle safety and trust in the connected party | [Safety and security](security.md) |
| Identify USB devices | [USB identity](usb-identity.md) |
| Check revisions and compatibility | [Versions and stability](versioning.md) |
| Decide which repository holds information | [Responsibilities between repositories](repository-boundaries.md) |
| Review the specification | [Review guide](review-guide.md) |

The start of each document shows whether it is normative or a guide. Changes follow the [contribution procedure](../CONTRIBUTING.md), and until the freeze the Japanese version is maintained as authoritative.
