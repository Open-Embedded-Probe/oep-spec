# Open Embedded Probe — Project Purpose and Scope

[日本語](project-concept.ja.md)

Status: **Exploratory upstream draft.** Only the project name is settled at this time. This document is a basis for agreeing on the problem, purpose, and scope. It does not prescribe a protocol structure or technical solution.

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
- one probe to provide multiple functions consistently; and
- different hardware, firmware, or connection methods to provide functions with the same meaning.

These are required properties, not decisions about the technology used to expose, identify, select, or operate functions.

## Relationship in scope

OEP primarily concerns interoperability between:

- the **probe side** — hardware or software that provides development-support functions for an embedded target; and
- the **host side** — software that uses functions provided by a probe.

The goal is for multiple probe implementations and multiple host implementations to connect without pairwise, dedicated integrations.

The precise boundaries of “probe” and “embedded-development function” will be clarified during requirements work. UART, GPIO, SWD, JTAG, and logic capture are candidates inherited from the starting investigation; this document does not decide to adopt, classify, or require them.

## Project scope

OEP concerns the common specifications needed for the probe and host sides to interoperate over functions provided by a probe.

This scope may eventually include the following, but this document does not decide their contents or implementation:

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
- treating a device identity as sufficient proof of functions, quality, conformance, authenticity, or safety; or
- making one reference implementation the specification itself.

## Successful outcome

The project's central success criterion is demonstrating this state:

> Multiple independently developed probe implementations and multiple independently developed host implementations can use commonly defined functions without adding an agreement specific to each pairing.

The project also aims to preserve interoperability for shared functions when new functions or implementation differences are introduced.

Performance, number of supported functions, use of a particular connection method, or support for particular hardware is not by itself a success criterion for the project as a whole.

## Not decided by this document

The following matters will be derived and considered incrementally after the purpose and scope are agreed:

- classification of functions and selection of the first functions to standardize;
- protocol structure, message model, and wire encoding;
- identification of functions, implementations, devices, and related entities;
- connection, discovery, and communication methods;
- versioning, extension, compatibility, and lifecycle rules;
- the definition and verification of conformance;
- USB profiles, VID/PID, and project-identity governance; and
- repository, implementation, and governance structure.

Existing proposals and research about these matters are inputs for future design work, not settled decisions.
