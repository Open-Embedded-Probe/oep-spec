# Open Embedded Probe — purpose and scope of the project

[日本語](project-concept.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It defines the purpose and scope of the project. This document does not prescribe the structure of the protocol or technical solutions. Those are defined by the v1 specification ([OEP core](oep-core.md) and the interface documents).

## Background

In embedded development, many kinds of probes are used between host and target, providing functions such as debugging, programming, communication, signal control, observation and measurement.

The meaning and usage of these functions are often designed individually per product, hardware, firmware, connection method and host application. As a result, even when the functions are similar, each combination of probe and host application needs its own dedicated support.

This fragmentation has problems such as the following.

- Each time a new probe implementation or function is added, the host side also needs individual support
- Host applications tend to depend on a particular product, board, firmware or connection method
- Functions with the same meaning are implemented again and again in incompatible ways
- When one probe provides several functions, there is no common agreement for offering and using them consistently
- It is hard to keep interoperability with common functions while adding implementation-specific functions
- When USB is used, the design tends to prepare an individual device identity each time functions or applications are added
- When the same function is used over a connection method other than USB, it tends to be redesigned as a separate mechanism

The problem of USB device identity is one concrete example where this problem surfaces. Using USB or a common PID is not itself the purpose of the project.

## Purpose

Open Embedded Probe provides a specification by which the functions that embedded-development probes provide are offered with a common meaning, so that different probe implementations and host software can be used with each other.

It aims to reduce dedicated integrations closed to individual products or connection methods, so that probe providers and host software providers can use functions they commonly understand without knowing each other's particular implementations in advance.

## Interoperability in OEP

Interoperability in OEP does not mean only that a particular probe and a particular host application can be connected individually.

It refers to the state in which, because the probe side and the host side each implement the common specification, both can use the functions they understand without adding arrangements dedicated to a particular combination.

In that state, conceptually, the following are possible.

- A probe can offer the functions it provides to the host
- A host can understand the available functions and their meaning
- A host can use functions, and a probe can convey results and state with a common meaning
- Differences and limitations due to functions, implementations and configurations can be handled
- Even if there are functions one side does not understand, the functions both understand can be used
- Interoperability of existing functions can be kept even when new functions or implementation-specific functions are added
- One probe can provide several functions in a consistent form
- Functions with the same meaning can be provided from different hardware, firmware or connection methods
- Even when making a third-party function and its dedicated host, the necessary exchanges can be expressed within the scope of OEP

These show the necessary properties, and do not decide with which technology offering, identifying, selecting and operating functions is achieved.

### Communication paths that OEP manages

OEP does not limit its use to standardized functions only. It also allows third-party functions, experimental functions, and hosts or probes specialized for such functions to be implemented.

An OEP function treats the host–probe communication it needs as one of the following paths.

- **OEP native path** — operations, data, state, results and failures are carried by the OEP protocol
- **external binding** — the relation between an OEP function and an external interface or external protocol is stated explicitly on OEP, and part of the communication is carried over that external path

With an external binding, routing, conversion, conditions of use and so on are set through OEP, and the actual data can be carried directly over USB CDC, USB Audio or other standard interfaces. Third-party or non-public protocols can also be used for an external binding.

The communication paths a function needs must be stated explicitly as an OEP native path or an external binding. A function must not depend implicitly on undeclared external communication that OEP cannot recognize.

Even when the connection interface differs, such as USB, UART or network, communication over it is done with the OEP protocol. A connection interface is a path that carries OEP itself, while an external binding is a relation that ties the communication of an individual function to an external interface or protocol. The two are distinguished.

The meaning and data format of a third-party function may be something the common part of OEP or general hosts cannot understand. A dedicated host and probe that support that function can exchange meanings and data they agreed on themselves over an OEP native path or an explicit external binding. Publishing the specification of a third-party function is not mandatory.

Being a third-party function, having a non-public specification, using a representation of another protocol inside data, or using a third-party protocol as an external binding are allowed. They are, however, distinguished so that they are not mistaken for standard paths that general hosts can use. This document does not decide how third-party functions or external bindings are identified, nor the extension format or data representation (the specification defines them: [OEP core](oep-core.md) §12 and so on).

The following communication does not in itself mean undeclared external communication.

- Lower-level communication such as USB, UART or network that carries OEP
- Connection-specific procedures, such as USB enumeration, that bring things to a state where communication by OEP can start
- Communication such as SWD, JTAG or UART used between probe and target
- External bindings explicitly tied to an OEP function
- Separate functions or separate protocols placed alongside, independent of OEP functions

When an external interface or another protocol is used as a path an OEP function needs, it is stated explicitly as an external binding, not as an independent function placed alongside.

### Distinction from incompatible derivatives

Changing, forking or porting the source code or specification of OEP does not in itself make the implementation not OEP. Even a port to different hardware, software or connection interface can interoperate as an OEP implementation if it meets the requirements of OEP.

On the other hand, changes that do not meet the mandatory requirements of OEP, such as making OEP functions depend on undeclared external communication or giving standard functions a different meaning, are treated as a separate protocol derived from OEP. Such an implementation must not claim conformance or compatibility with OEP, and must not use a protocol name or protocol identity that could be mistaken for the OEP protocol. Using an explicit external binding alone does not make it an incompatible derivative.

Incompatible derivatives cannot use the OEP project's USB VID:PID or other common identities. They must use their own identity and be mechanically distinguishable from OEP implementations.

An OEP endpoint, external bindings and separate functions independent of OEP can be placed together on the same physical device. An external binding may share one USB VID:PID with an OEP endpoint as part of a registered or permitted profile. A separate protocol independent of OEP must be distinguishable so that the host does not mistake it for an OEP endpoint, an OEP function or its external binding.

The right to fork under the license of the software or specification documents, the right to claim conformance to OEP, the conditions for using the OEP name in compatibility statements, and the right to use the project identity are treated as separate matters.

## Relation covered

The central relation OEP covers is interoperability between the following two parties.

- **Probe side** — hardware or software that provides development-support functions for an embedded target
- **Host side** — software that uses the functions a probe provides

It aims for several probe implementations and several host implementations to connect without one-to-one dedicated integration.

## Scope of the project

OEP covers the common specification needed for the probe side and the host side to interoperate on the functions a probe provides.

- The common meaning of functions and operations
- The expression of the functions provided and their constraints
- The exchanges between probe and host
- Compatibility and extensibility between different implementations
- Requirements for checking interoperability
- Rules for using OEP in various connection environments

## Non-goals

OEP does not have as its purpose, at least, the following in themselves.

- Making one kind of universal probe or a single product
- Requiring the same set of functions of every probe
- Making a particular MCU, board, firmware framework, OS or programming language the standard
- Assuming only a particular connection method
- Replacing all existing debug, programming and measurement mechanisms
- Making OEP functions depend on undeclared external communication that OEP cannot recognize
- Guaranteeing functions, quality, conformance, authenticity or safety by device identity alone
- Making one reference implementation the specification itself

## The state of success

The central success condition of the project is being able to demonstrate the following state.

> Several independently made probe implementations and several host implementations can use commonly defined functions with each other, without adding arrangements dedicated to individual combinations.

In addition, it aims to keep the interoperability of shared functions even when new functions or implementation differences are introduced.

Performance, the number of supported functions, particular connection methods and support for particular hardware are not, by themselves, success conditions of the whole project.

## Where technical decisions are made

The following are not decided in this document but left to the specification. The v1 specification ([OEP core](oep-core.md), the `oep-if-*.md` of the interfaces whose names begin with `oep.`, and `registry/oep-v1.toml`) defines them.

- The classification of functions, and the functions standardized first
- The structure of the protocol, the message model and the wire encoding
- How functions, implementations, devices and so on are identified
- How connection, discovery and communication are done
- The rules for versioning, extension, compatibility and lifecycle
- USB identity

The definition of conformance and how to check it are defined by [conformance](conformance.md), the procedure for changes by [CONTRIBUTING](../CONTRIBUTING.md), and the responsibilities between repositories by [OEP responsibilities between repositories](repository-boundaries.md). The terms of use of the project's USB VID:PID are defined by `PID-USE.md` of `oep-probe-arduino`, which manages it.
