# Open Embedded Probe — Project Purpose and Scope

[日本語](project-concept.ja.md)

Status: **guide** (not normative). The project's purpose and scope, agreed upstream: the project name, the purpose centred on interoperability, the principle that every communication path a function needs is either an OEP native path or an explicit external binding, and the principle that incompatible derivatives are not identified as OEP. This document does not prescribe a protocol structure or technical solution; the v1 specification does that ([OEP core](oep-core.md) and the standard interfaces).

## Background

Embedded development uses many kinds of probes between a host and a target to provide debugging, programming, communication, signal control, observation, measurement, and related functions.

The meaning and use of these functions are often designed separately for each product, hardware implementation, firmware, connection method, and host application. As a result, even similar functions require dedicated support for each pairing of a probe and a host application.

This fragmentation causes problems such as:

- each new probe implementation or function requiring corresponding host-side integration;
- host applications becoming dependent on a particular product, board, firmware, or connection method;
- functions with the same meaning being repeatedly implemented in incompatible ways;
- no common agreement for consistently exposing and using multiple functions provided by one probe;
- difficulty adding implementation-specific functions while preserving interoperability for shared functions;
- USB designs tending to require a separate device identity for each added function or application; and
- the same function tending to require a separate design when used through a connection other than USB.

USB device identity is one concrete setting in which the broader problem becomes visible. The use of USB or a shared PID is not itself the purpose of the project.

## Purpose

Open Embedded Probe provides specifications that allow embedded-development probes to expose the functions they provide with shared meaning, so those functions can be used interoperably by different probe implementations and host software.

The project aims to reduce integrations confined to individual products or connection methods. A probe provider and a host-software provider should be able to use functions they understand in common without prior knowledge of each other's particular implementation.

## Interoperability in OEP

Interoperability in OEP does not mean only that one particular probe can be connected to one particular host application through a dedicated integration.

It means that independently implementing a common specification on the probe and host sides enables them to use functions they both understand without adding an agreement specific to that pairing.

In such a state, it is conceptually possible for:

- a probe to expose the functions it provides to a host;
- a host to understand the available functions and their meaning;
- a host to use a function and a probe to communicate results and state with shared meaning;
- differences and limits arising from functions, implementations, and configurations to be handled;
- functions understood by both sides to remain usable when other functions are not understood by one side;
- new or implementation-specific functions to be added while preserving interoperability of existing functions;
- one probe to provide multiple functions consistently;
- different hardware, firmware, or connection methods to provide functions with the same meaning; and
- the communication needed by a proprietary function and its dedicated host to be expressed within OEP.

These are required properties, not decisions about the technology used to expose, identify, select, or operate functions.

### Communication paths that OEP manages

OEP is not limited to standardized functions. Proprietary functions, experimental functions, and hosts or probes specialized for a function can also be implemented.

An OEP function treats each host–probe communication it needs as one of the following paths:

- **OEP native path** — operations, data, state, results, and failures are carried by the OEP protocol;
- **external binding** — the relationship between the OEP function and an external interface or external protocol is made explicit through OEP, and part of the communication is carried over that external path.

With an external binding, routing, conversion, conditions of use, and so on are set through OEP, and the actual data can be carried directly over USB CDC, USB Audio, or another standard interface. A proprietary or unpublished protocol can also be used as an external binding.

Every communication path a function needs must be made explicit as an OEP native path or an external binding. A function must not implicitly depend on undeclared external communication that OEP cannot see.

When the connection interface differs (USB, UART, network, and so on), communication over it still uses the OEP protocol. A connection interface is the path that carries OEP itself; an external binding is the relationship that ties the communication of one function to an external interface or protocol. The two are kept distinct.

The meaning and data format of a proprietary function may be ones that the common part of OEP and general hosts do not understand. A dedicated host and probe for that function can exchange the meaning and data they agreed on over an OEP native path or an explicit external binding. Publishing the specification of a proprietary function is not required.

A function may be proprietary, its specification may be unpublished, its data may use the representation of another protocol inside, and a proprietary protocol may be used as an external binding. It must, however, be distinguishable so that it is not mistaken for a standard path usable by general hosts. This principle does not decide, at this stage, how proprietary functions or external bindings are identified, nor their extension format or data representation.

The following communication does not in itself count as undeclared external communication:

- the underlying USB, UART, network, or other communication that carries OEP;
- connection-specific procedures, such as USB enumeration, that bring the connection to a state in which OEP communication can start;
- SWD, JTAG, UART, or other communication used between the probe and the target;
- an external binding explicitly tied to an OEP function; and
- another function or protocol placed alongside, independent of OEP functions.

When an external interface or another protocol is used as a path an OEP function needs, it is made explicit as an external binding, not as an independent function placed alongside.

### Distinguishing incompatible derivatives

Modifying, forking, or porting the OEP source code or specification does not by itself make the implementation non-OEP. A port to different hardware, software, or connection interface interoperates as an OEP implementation if it meets the OEP requirements.

On the other hand, a change that does not meet the mandatory OEP requirements, such as making an OEP function depend on undeclared external communication or giving a standard function a different meaning, is treated as a separate protocol derived from OEP. Such an implementation must not claim conformance or compatibility with OEP, and must not use a protocol name or protocol identity that could be mistaken for the OEP protocol. Using an explicit external binding does not by itself make a derivative incompatible.

Incompatible derivatives cannot use the OEP project's USB VID:PID or another common identity assigned to it. They use their own identity and must be mechanically distinguishable from OEP implementations.

One physical device can carry an OEP endpoint, external bindings, and other functions independent of OEP. An external binding may share one USB VID:PID with the OEP endpoint as part of a registered or permitted profile. Another protocol independent of OEP must be distinguishable so that a host does not mistake it for the OEP endpoint, an OEP function, or its external binding.

The right to fork under the license of the software or the specification documents, the right to claim conformance to OEP, the conditions for using the OEP name to indicate compatibility, and the right to use a project identity are treated as separate matters.

## Relationship in scope

OEP primarily concerns interoperability between:

- the **probe side** — hardware or software that provides development-support functions for an embedded target; and
- the **host side** — software that uses functions provided by a probe.

The goal is for multiple probe implementations and multiple host implementations to connect without pairwise, dedicated integrations.

## Project scope

OEP concerns the common specifications needed for the probe and host sides to interoperate over functions provided by a probe:

- shared meaning for functions and operations;
- representation of available functions and their constraints;
- interactions between a probe and a host;
- compatibility and extensibility across implementations;
- requirements for demonstrating interoperability; and
- rules for using OEP in different connection environments.

## Non-goals

OEP does not have the following as goals in themselves:

- building one universal probe or a single product;
- requiring every probe to provide the same set of functions;
- standardizing on a particular MCU, board, firmware framework, operating system, or programming language;
- assuming only one connection method;
- replacing every existing debugging, programming, or measurement mechanism;
- making OEP functions depend on undeclared external communication that OEP cannot see;
- treating a device identity as sufficient proof of functions, quality, conformance, authenticity, or safety; or
- making one reference implementation the specification itself.

## Successful outcome

The project's central success criterion is demonstrating this state:

> Multiple independently developed probe implementations and multiple independently developed host implementations can use commonly defined functions without adding an agreement specific to each pairing.

The project also aims to preserve interoperability for shared functions when new functions or implementation differences are introduced.

Performance, number of supported functions, use of a particular connection method, or support for particular hardware is not by itself a success criterion for the project as a whole.

## Where the technical decisions are

This document leaves the following to the specification. The v1 specification ([OEP core](oep-core.md), the standard interfaces `oep-if-*.md`, and `registry/oep-v1.toml`) now defines them:

- classification of functions and selection of the first functions to standardize;
- protocol structure, message model, and wire encoding;
- identification of functions, implementations, devices, and related entities;
- connection, discovery, and communication methods;
- versioning, extension, compatibility, and lifecycle rules; and
- USB identification.

The definition and verification of conformance, and governance, are not settled by the specification yet (the use of the project's USB VID:PID is set by oep-probe-arduino's PID-USE.md); the change process is in [CONTRIBUTING](../CONTRIBUTING.md).
