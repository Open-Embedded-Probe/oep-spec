# Defining and checking your own interface

[日本語](extension-development-guide.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). The requirements for definitions follow [core §12](oep-core.md#12-extension-rules-how-to-write-an-interface), and the requirements for conformance follow [conformance checks](conformance.md).
It shows the format and the way to proceed for a project that uses OEP to make the specification and checks of its own functions.

## Scope to decide first

The specification of a function is managed by the project that owns its name. Give it your own reverse-DNS name, and put the function the probe provides in list.
The host chooses (name, instance, revision), resolves it to the fn of the current boot, and calls it.
instance is a fixed identifier that allows gaps; if a saved pair is not found, it is treated as not offered.

To start the definition small, choose the operations and common parts the first function needs.
If pin assignment is needed, define its taking and releasing; if it makes resources, define their kind, owner and lifetime.
If you adopt positioned streams, define the operations you adopt, such as read of the [common parts](../interfaces/oep-if-common.md).
If you provide notifications, define subscribe/unsubscribe and the events. There is no obligation to adopt all standard OEP functions.

For appending byte strings and marks, choose the common stream; if the generation, segments and sample times of an acquisition are needed, choose the capture contract.
Optional functions also need implementation, tests and maintenance on the adopting side, so add them in units that can be defined down to failure, end and the limits on retained amounts.

Self-update, privileged product operations and protecting the connection of shared equipment are shown in [extension examples by use case](extension-use-cases.md).
It covers examples that define conditions for a function with a new name, and examples that protect the connection before OEP is reached.
Changing the conditions of the existing core's open/force or of reading standard functions cannot be derived from adding optional extensions alone.

## Format of a definition and a small example

The following is an example of an illustrative third-party function named `io.example.echo` that has no state and returns the byte string it received.
Choose real names from a domain you own. This does not provide a product endpoint or an implemented sample.

| Item to define | Choice in this example |
|---|---|
| Name, revision | io.example.echo, revision 1 |
| Target family, external specifications | Does not depend on the target. No external specification |
| Op table | op 0x10 echo, mandatory, no lock needed |
| Request | n(u16), n bytes, trailing TLVs |
| completed success | n(u16), the same n bytes as the request, trailing TLVs |
| failed / partial | This operation does not produce them |
| describe | Declare 0x10 in ops and the limit of n in max_length. 48 bytes as an example |
| Own TLVs, reasons, status, events | No additional definitions. Unknown TLVs and common refusals follow the core |
| State, resources, pins, notifications | None are made, and the operation causes no state change |
| Out of range | If n exceeds the declared limit, unsupported. The structure and the order of refusal follow core §4.3 |
| Handling unknown values | No own enums/flags. Common answers follow core §2.4 |

With max_frame=64, the largest data request of this example is 10+2+48=60 bytes, and the success answer 5+2+48=55 bytes.
The trailing TLVs also count toward the frame limit. The limit stays at the declared 48; the host does not raise it on its own from the spare frame room.
The fn 0 operations and declarations the core requires are implemented separately. The max_op_ms of fn 0 is decided including this function.
Fixed parts, TLV values and array elements are not extended at the end; additional information is carried in new TLVs.

describe can be paged, but one TLV is not split. With max_frame=64, values are up to 55 bytes, and a channel_group is up to 17 roles per group.
Many assignments also need to fit in one request. For example, 32 assignments of plan are 266 bytes; choose the frame you need.
A new extension can define a pageable query op for a large list, but existing mandatory declarations cannot be omitted because of it.
If adding a narrow transport would limit mandatory declarations, that transport also uses a large frame, or it is designed as the contract of another revision.

For additional information on array elements, define for example a repeated answer TLV `index(u8), attribute`, and state that the index is the 0-based element number within that page.
Old hosts can skip the TLV without the length of the fixed element changing. In a definition that uses notifications, also state whether the remainder below the threshold is sent or discarded when generation ends, and how losses are judged.

## From the specification to 3 layers of checks

| Layer | Target and representative checks |
|---|---|
| Core | confirm, discovery, header/TLV, session, resending and time for every endpoint. The contracts that apply to the transports and resources provided |
| Common extension | Uniqueness of name/revision/instance, ops, the fixed shape of describe and its invariance within the same boot, refusal of ops not offered. The contracts of the adopted resources, notifications and common parts |
| Individual extension | The operations of that function and their observable effects. In this example, echo of empty and of the limit, refusal beyond the limit, the returned byte string, not changing state |

Write each case of the individual checks as "specification reference → initial state → request → expected answer → effect observed independently → cleanup".
The checks of standard OEP GPIO/UART/wire/target also use this format; for third-party functions, swap the adapter of the individual operations.
Do not make expected answers from an implementation; take the meaning defined in the specification as the expected value. Compare not only the refusal answer but also the effects before and after the refusal.
Distinguish not applicable, when a particular configuration is absent, from not executed, when observations or preconditions that should be prepared are missing.

First check small configurations, invariance on refusal and lifetimes with representative cases, and feed the results back into reviewing the specification.
A PASS of selected cases carries its check scope; to claim full conformance, check all contracts that apply in the [conformance requirements](conformance.md).
The calling project passes the choice of equipment, wiring, stimuli and observation explicitly. The location or inventory of particular equipment is not embedded in the common checker.
Record in the results the SPEC commit/tag, the probe firmware, the capabilities used, the identification of the checker and configuration, the requests/answers and the observations.

## When extending

Optional TLVs/ops/events that keep the existing shapes and behaviour can be added to the same revision. Optional ops are declared in ops, and capabilities other than ops in that describe.
Changes that break existing contracts, such as making things mandatory, fixed shapes, state transitions and resource lifetimes, raise the revision after the freeze.
A function with a different meaning is defined under a different name. Do not add your own numbers (op, tag, enum values) to an interface of another owner.
To add information to an interface of another owner, use the places identified by name (core §2.5, §12 rule 7):

| What to add | Where | Example |
|---|---|---|
| Information in a standard request, answer or describe | A named extension TLV (tag 0x7F, `name_len, name, data`, core §2.2) | Add your own output strength to set of gpio |
| Choices a standard lists by name | A name list (core §7.7) | A third-party console mechanism |
| Your own settings | Settings items of an interface under your own name (core §13.1) | The board's host name, an NTP server |
| A new function | An interface under your own name | Self-update, test signals |

Named extensions are limited to things whose standard behaviour continues correctly whether a host that does not know the name skips them (non-critical) or refuses them (critical).
Things that change the meaning of standard behaviour (the meaning of an answer's fixed part, state transitions, resource lifetimes) are not made named extensions but functions under your own name.
For chip-specific procedures, first consider whether the host can handle them; if time conditions on the probe side are needed, define them as a function with a dedicated name.

## What to fix and what to leave open

When defining an interface, decide where to fix things by number and where to leave them open by name.
Others can extend later only where it was left open (core §12 rule 7).

| Kind | What | How it is decided |
|---|---|---|
| Fixed | Op numbers and shapes, the fixed parts of requests and answers, state transitions, resource lifetimes, reasons for refusal, event kinds | Only the owner assigns numbers (core §2.5). Things that do not work correctly if the side that does not know them ignores them |
| Open: name lists | Choices that grow per implementation (mechanisms, sensors, network ports) | List them by name in describe from the start, and in requests use the position in the list as the number (core §7.7). The owner decides the shape of the list's elements, and whoever adds follows that shape too |
| Open: named extensions | Additional information that stays correct if the side that does not know it skips it, optional specifications in requests | Open in every context even without defining it (core §2.2). The owner need do nothing |

When someone else adds an extension, think in this order.

1. Does the meaning stay the same even if a party that does not know it ignores it? If so, make it a non-critical named extension (additional information in answers, optional specifications in requests).
2. Is it safe if a party that does not know it refuses it? If so, make it a critical named extension (a specification in a request without which the result would differ).
3. Anything that is neither (changing a fixed shape or meaning, adding operations) is a change to what was fixed. It cannot be done within the owner's definition:

| What to change | Who | How |
|---|---|---|
| The fixed shape or meaning, or mandatory operations, of your own definition | The owner | A new revision (core §2.8). If the old revision is also offered as another fn, old hosts keep working |
| The fixed shape or meaning of someone else's definition | Someone else | Make it an interface under your own name. Propose the next revision to the owner |
| Adding operations to someone else's definition | Someone else | Put them in an interface under your own name. Requests carry the other's fn and list numbers, looked up by name from that boot's list and describe |
| The shape or meaning of a named extension's data | The owner of that name | Use a new name (names have no revision, core §2.2) |

In every case, the host does not remember numbers but looks them up from names (fn from list, list numbers from describe, looked up again when the boot_id changes).
When yet another party extends an interface under someone else's name, the same rules apply. Examples of use are in [extension examples](extension-use-cases.md) §7.
