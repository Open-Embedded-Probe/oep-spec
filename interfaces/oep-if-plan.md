# OEP interface: plan v1

[日本語](oep-if-plan.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [Versions and stability](../docs/versioning.md). The core is [OEP core](../docs/oep-core.md). The only definition of the numbers is `registry/oep-v1.toml`.

| Name | revision | Role | Target family |
|---|---:|---|---|
| `oep.probe.plan` | 1 | the assignment (plan) of which channel to use for which role of which interface | used for every family |

- **A plan role** is a role that the document of an interface says is assigned through plan (the number of the role and the declaration of the pins that can be chosen, role_channels /
  channel_group, are decided by the document of that interface and its describe, core §7.4). A role whose pins are chosen by a request argument (such as pins of attach of a wire) is
  not a plan role.
- A probe that puts in list an interface with plan roles puts `oep.probe.plan` in list. A probe with no interface that has plan roles
  does not put it in list. A probe puts at most one `oep.probe.plan` in list.
- A plan is a resource of the session (core §9). The host applies a saved assignment again explicitly.

## 1. Operations

| op | Name | Request | Answer | Lock | Required |
|---:|---|---|---|---|---|
| 0x10 | plan_apply | sequence of role_assignment TLVs | — | needed | required |
| 0x11 | plan_release | n(u8), n × fn(u16) | — | needed | required |

describe (in addition to the common tags of core §7.4):

| tag | Name | Value |
|---:|---|---|
| 0x40 | plan_roles | u32. The number of role_assignments a plan can hold at once (the total of all fns). A probe with a limit always puts it |

## 2. plan

A plan is held **per fn**.

### 2.1 plan_apply

- The request is a sequence of role_assignment TLVs (0x10: fn(u16), role(u8), channel(u16); repeated). One assignment is identified by
  (fn, role, channel) (some functions have several channels for the same role, such as gpio).
- **Only the assignments of the fns that appear in the request are replaced atomically**; the plans of the other fns are kept as they are. With the current assignments of the replaced fns taken as removed,
  each interface checks without side effects (including the contention check of core §8.1), and the plan is applied only when all of them accept. If even one refuses,
  rejected with nothing changed (the current plan of the fns that were to be replaced also stays).
- An assignment that stays with the same (fn, role, channel) is neither released nor taken again, and keeps the level, direction, pull and strength of the pin and the state of the function.
  Only the assignments removed are released, and only the assignments added are taken. For an fn whose set of assignments does not change, nothing is done.
  If the function of an fn being changed is running, it is refused with unavailable (cause 6), following the definition of that interface.
  A change of a resource bound to another fn is unavailable (cause 4). Atomicity is a contract about the acceptance of the whole request and the update of the state;
  it does not require switching several pins electrically at the same time.
- **Number of assignments**: a plan_apply after which the total of the assignments (all fns) exceeds plan_roles is
  rejected unavailable with nothing changed (cause 2: not enough resources. The same refusal as core §8.1. The form of the request is correct, so it is not malformed).
- The answer is completed success with no payload.

### 2.2 plan_release

- `n(u8), n × fn(u16)`. Releases the plans of the listed fns (n = 0 is all fns). If an existing fn has no plan, it is ignored.
  All targets are checked before releasing. A nonexistent fn is unknown_function, and one bound to another fn that cannot be released is unavailable (cause 4); the whole request is refused with nothing changed.
  At the end of a session, dependent resources are released first following core §9, so this refusal does not stop the cleanup.
- The answer is completed success with no payload.

### 2.3 Pins

Taking and releasing pins and the idle state follow core §8. No release processing is done for the assignments kept in §2.1.
The operation that starts use, and whether pins of outputs driven by settings can be taken, are defined by the adopting interface.

### 2.4 How to refuse

plan_apply (in the order of core §4.3):

| Situation | reason |
|---|---|
| form error, the same (fn, role, channel) twice, fn 0 listed | malformed |
| the fn does not exist | unknown_function |
| the role does not exist in that interface (not a plan role), the channel is not a candidate in role_channels, matches no channel_group, does not meet the number of roles or the pin combination defined by the individual function | unsupported (the tag as received) |
| exceeds plan_roles, contention for pins or resources (core §8.1), an output idle the interface refuses | unavailable (cause 2 / 1 / 5) |
| the target of the change is running, bound to another fn | unavailable (cause 6 / 4) |

plan_release: a form error (n does not match the number of fns that follow) is malformed.
