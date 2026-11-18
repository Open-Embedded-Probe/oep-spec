# Extension examples: self-update, privileged operations, shared equipment

[日本語](extension-use-cases.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It applies the definition method of the [extension development guide](extension-development-guide.md) to use cases.
The `io.example.*` names below are illustrative names and do not represent additions to standard OEP or implemented functions.
The actual names, revisions, ops, fixed shapes and authentication methods are defined by the project that owns the name. There is no need to add numbers to the OEP registry.

These examples use the core's optional policy decision (core §4.3) and the contracts of named functions.
No authentication method is added to the core. To protect existing core/standard operations, refuse by the policy decision, and keep the rules for the lock, resending and resource lifetimes.

## 1. Choosing where to extend from the use case

| Use case | Where to extend | Host flow |
|---|---|---|
| Update the app itself with an existing USB/UART loader | A new interface that moves to update mode (§2) | Discovery, session, entry operation, transfer with another protocol, rediscover the app |
| Send an image to your own loader over OEP | A new interface that handles images (§3) | Discover the loader, transfer in pieces, verify and commit, rediscover the app |
| Allow strong product operations only to maintainers | A new interface whose authorization conditions are defined from the start (§4) | Discovery, session, authentication, permitted operations, state check |
| Protect shared equipment from unauthorized users | A transport/service that manages access to the OEP connection (§5) | Get authentication and permission for the connection, then use ordinary OEP |
| Add a little product information to standard functions | Named extension TLVs, name lists (§6) | Only hosts that know them use them; other hosts skip them |
| A device that is not a probe uses only the core, and others extend its function | An interface under your own name, and the places identified by name (§7) | Each host uses only the names it knows, and looks up numbers from names |

Capabilities are found with list and describe. Hosts that do not use named functions are not required to implement them or their authentication UI.
Added functions are expressed as new fns; list and ops are not increased or decreased within the same boot to match the authentication state (core §7.2/§7.3).

## 2. Moving from the app to another loader

Consider an app that speaks OEP and is also the target of its own update. In OEP's roles, that device is a probe.
For example, `io.example.boot` represents the entry to updating. There is no need to make wires or connections for an external target.

| Operation example | Input / result | Lock | Meaning to design |
|---|---|---|---|
| status | The current mode, the state of the last accepted transition | Not needed | Reads the current state and causes no transition |
| enter | The identifier of the destination → the result of accepting the transition request | Needed | Moves to the specified loader. Sends the answer and then transitions |

describe declares the selectable destinations and the next protocol. For example, vendor USB ISP, UART ISP, or a loader of your own that speaks OEP.
The deadline the host waits for, USB re-enumeration or a baud change, and how the unit is matched are handled by the definition of that destination and the host adapter.
Chip-specific BOOT switching and the Flash layout are put in the specification of the implementation that owns the function.

Example host procedure:

1. Find the function with confirm/list/describe, and resolve the saved (name, instance, revision) to this time's fn.
2. open, and if needed meet the authorization conditions of that new function. The probe validates the destination and the transition conditions before any side effect.
3. After reading the answer of enter, close the OEP connection and switch to the declared loader's protocol.
4. Match the same device and transfer the image. A loader that does not speak OEP is not required to use OEP framing or the boot baud.
5. When back in the app, start again from confirm. Do not carry over the previous session, fn or resources; read the declarations of the new boot.

If the answer is lost, recover by checking which of app / loader is running. Do not blindly re-execute enter with a new corr.
A loader with another protocol may not have the same USB serial, so do not assume matching is always possible by unit_id alone.
Even if the entry is authenticated, write permission to the destination loader and the authenticity of the image are not automatically guaranteed. Align the update policy of the destination too.

The standard `oep.probe.restart` is the contract to return within restart_max_ms to an internal state that can accept OEP on the original transport.
Do not add, with a third-party TLV, the meaning of moving to a loader that does not return to OEP to that existing operation. Define it as a function under your own name, as in the example above.

## 3. A loader receives its own image over OEP

Boot the loader itself as an OEP probe, and put for example `io.example.update` in list.
The app and the loader can be expressed with different boot_ids and function lists. The contracts of the same unit's unit_id and of the same model's transport indexes are kept (core §7.5).
Standard OEP does not define the image format, Flash layout or signature method, so the owner of this extension defines them.

| Operation example | Meaning to design |
|---|---|
| begin | Validates the image's target, identifier and length, and starts the update. Also define when erasing starts |
| write | Sends in pieces with offset/count/data. The answer shows up to where writing was confirmed |
| status | Reads the image being updated, the confirmed range, and states such as uncommitted / bootable |
| finish | Verifies and commits the whole image. If moving to the app, define the order of the answer and the transition |

begin/write/finish need the lock. status does not change state and returns only information that may be public.
describe declares the limit of the image area, the functional limit of write, and the supported verification methods. Current progress is returned by status.

When deciding the fixed shape, put count in the write request, followed by data and extension TLVs.
For example, with the fixed part offset(u32)/count(u16)/data, at frame 64 at most 48 bytes can be used for data (64 − request header 10 − offset 4 − count 2).
If you put additional identifiers or proofs, subtract their bytes too. The host splits so as to fit both the functional limit and the transport's max_frame.
The time of all processing is included in max_op_ms of fn 0, and long erases and the like are handled by the limit of each operation or by split procedures.

Points this function's definition decides:

- The range that may be written. State the boundary so that writing the image does not break the loader itself, keys or boot settings.
- The measurement point of write progress. failed or a lost answer alone does not mean the Flash has not changed.
- Resending the identical request follows core §5.1. On result_lost, read the state with status and the like; do not automatically re-execute the same erase/write with a new corr.
- The update state when the session ends. The right to operate and temporary buffers are released; the handling of already written Flash and persistent progress records is defined separately.
  If it can be resumed in the next session, match and authorize that image again. Do not carry over previous resource numbers.
- Verification of the image and the commit point at which it becomes bootable. Choose transfer checksums, signatures/MACs, or a development mode the user can rewrite freely according to the trust conditions needed.

On small devices, a single app area and an independent loader can be chosen. Retrying with the loader after a failed update and keeping the old app are different things.
If returning to the old app is needed, add A/B or backup / swap as requirements of that implementation.
An update entry that only the app executes cannot guarantee recovery after the app is broken, so prepare the boot conditions and communication path of an independent loader.
If the OEP core does not fit in the loader, the "only the entry is OEP" configuration of §2 can be chosen.

## 4. Setting permissions only for a new function

For example, `io.example.control` has a query of public state and product-specific operations only maintainers can execute.
The proof needed and the refusal on insufficient permission are defined from the start of that name/revision. This is not an example of overriding standard GPIO or raw debug with authentication.
In a configuration where the same strong effect can also be executed by another public function, design the public scope including that other function.

| Operation example | Lock | Meaning to design |
|---|---|---|
| status | Not needed | Returns public state. Does not pretend to be authorized or change permissions |
| authorize | Needed | Verifies the proof, and sets the permission for operations usable from this session |
| service | Needed | Executes a product-specific operation after checking the person, permission, target and arguments |

The host does authorize after an ordinary open, and uses service. authorize, which changes permissions, is not defined as a lock-free read (core §6.3).
Methods and the supported set of operations are expressed in describe, and the current permission by a state query. Authorization does not change list/describe of the same boot.
Permissions are not limited to a single level, and can be expressed as sets of targets and operations. Methods and bit counts are not made requirements common to all probes.

A session_id is not personal authentication. The same ID learned in plaintext can be used, so tie this function's permission to an authenticated connection / person or to a per-operation proof.
If per-operation proofs are used, define a method that includes boot/session, corr, fn/op and arguments in what it protects against tampering and reuse for another request.
Refusing a request that omits the needed proof is made part of the contract of that new interface.
A proof in the request alone does not guarantee the probe's identity or the authenticity of answers. Needed integrity and confidentiality of answers/notifications are also handled by the transport or that method.

Permissions are not carried over across the end of the session, force by another ID or restart. Expiry and explicit revocation are also put in that function's definition.
Even if a past success of authorize/service is received by a resend, it is not treated as the current permission or resources having been restored. The current state is queried with a new corr.

The core's resend decision comes before individual operations, but the optional policy decision comes before resending.
For an extension that returns secrets, either protect it, including its old answers, with an authenticated and encrypted transport, or choose a configuration that does not keep byte records of those requests (core §5.1).
If authorization is checked only within service, cached answers are not protected. To also refuse resends after revocation, check the same permission in the policy decision of core §4.3 too.
A method that returns secrets in plaintext after authorization does not guarantee confidentiality from parties who can read the transport.

If this example does not include core operations in the policy, a session ends even by force from an unauthorized user.
If the continuation of work also needs protection, combine it with the protection of the whole connection in §5.

## 5. When core operations of shared equipment also need protection

On a shared bench, connections and GPIO and so on being released by force can itself disturb work.
Here a configuration can be used that puts an authenticated tunnel or a service that manages connections in front, so that only permitted users reach the control OEP endpoint.
Inside a connection that has been authenticated, the existing core open/force/resending are handled as usual.

Do not hand the control OEP connection as it is to observation-only users. If needed, provide observation from another public API.
If the same control endpoint can be reached from another unprotected USB/UART/TCP transport, that protection can be bypassed. Align the public scope of the entries.
Only hiding the force button in the host's screen is not access control to the endpoint.

If a broker answers OEP requests itself, it is itself a probe and implements the ordinary core contract.
When protecting inside the endpoint, for example according to the role authenticated on the transport, refuse an observer's open/force or GPIO/debug operations by the policy decision of core §4.3.
The refusal is unavailable cause 7, returns no resend answer either, and does not change the owner, lease or resources. Requests that pass the policy proceed to the ordinary lock decision.
It answers confirm/list/describe/clock/lock_state, so do not put secrets in the information they expose.

If this configuration also refuses open before authentication, establish authentication before the OEP connection, on an authenticated transport, or by a physical presence check.
If the lock-requiring authorize of §4 is the only entry, authentication cannot happen before open and it gets stuck. The same applies to a maintainer's force while another owner holds the lock.
Do not replace the state of an authenticated connection with the session_id, and apply the same policy to other unprotected transports too.
Policy changes apply to new requests and resends. If accepted operations or notifications being sent need to be stopped at once, define cancellation and transport disconnection on revocation in that method.

## 6. Adding to standard functions by name

Examples that add a little product information without rebuilding a standard interface. No numbers are taken; things are identified by name (core §2.2, §7.7, §12 rule 7).

- **Output strength**: put `io.example.gpio-drive` as a named extension TLV (tag 0x7F) in the describe of `oep.fixture.gpio`, listing the selectable strengths (mA).
  Attach the extension TLV with the same name to the set request as critical (0xFF), and send the strength per channel. A probe that does not know this name refuses with unsupported, so
  it never runs at the default strength while the strength was meant to be specified. A host that does not know this name attaches nothing, and the probe runs at the default strength.
- **Third-party settings items**: declare the item `ntp-server` (text) in the interface `io.example.board` (core §13.1; a settings-only interface is fine).
  The host can display and input it by name and form, and get/set/save are the same as for standard items.
- **Factory calibration**: the calibration answer of `oep.fixture.analog` gives scheme a name such as `com.espressif.esp32.adc-efuse` and returns the raw data (capture §3.7).

In each, the side that does not know the name only skips or refuses it, and standard behaviour does not change. If the meaning of standard behaviour needs to change,
do not make it a named extension; make it an interface under your own name, or ask the owner of that name (the project for `oep.`) to change the definition.

## 7. A device that uses only the core, and a chain of extensions

A device without pins can also speak OEP with only the core. As an example, consider a thermometer. Author A defines `io.example.thermo` (revision 1).
fn 0 has confirm, list, describe, clock and sessions, and has neither channels nor plan (core §7.5: a device without channels does not attach channels).

| Author | Name | Content |
|---|---|---|
| A | `io.example.thermo` | read (no lock needed; count, count × (sensor(u8), value(i32, m°C))), set_interval. describe makes sensor a name list (core §7.7) |
| B | `com.b.*` | Adds humidity and an averaging specification to A's function. Has its own sensor and a calibration operation |
| C | `org.c.*` | Adds a certificate number to B's calibration answer |

How to extend, and what happens on a host that does not know the name:

| What is added | Where | What happens on the side that does not know it |
|---|---|---|
| An optional op of A (history) and answer TLVs | The owner A adds them to the same revision (core §2.8) | Old hosts skip the TLVs, and use the op only after checking ops for it |
| B's humidity in read's answer and describe | A named extension (`com.b.humidity`) | A's hosts skip it. Even if C lists it in another form, the names differ, so they do not mix |
| B's averaging specification in set_interval | A critical named extension (`com.b.average`) | Firmware that does not know it refuses with unsupported (tag 0xFF) and changes nothing |
| B's sensor | Put `com.b.probe-tip` in the sensor name list | A's sensor numbers move. Hosts that look up by name read the same sensor |
| B's calibration operation | B's interface `com.b.thermo-calib` (another fn) | Invisible to A's hosts. Requests carry A's fn and the sensor number, looked up from names |
| C's certificate number | A named extension in B's calibration answer (`org.c.cert`) | B's hosts skip it |
| A widens the value to i64 | The owner A's new revision 2 (listed as another fn beside 1) | Hosts that know only revision 1 keep using 1. They do not use firmware with only 2 (no misreading) |

What happens when the rules are broken (in both cases the side that does not know silently gets it wrong):

- B uses a TLV number of A's answer (0x02) for humidity. If A later defines 0x02 as the battery voltage (a correct addition), B's hosts read the voltage as humidity on new firmware.
  With a named extension, absence is known as absence.
- B makes a specification that turns read's values into °F a non-critical named extension. Firmware that does not know it answers in °C, and B's host reads that as °F.
  Even if made critical, the meaning of the answer's fixed part changes per request, and generic tools that read communication records cannot know it.
  Things that change a fixed meaning go in an interface under B's name, or in A's next revision ("what to fix and what to leave open" in the [extension development guide](extension-development-guide.md)).

## 8. How to check the extension examples

In addition to the [conformance requirements](conformance.md) and the 3 layers of the extension development guide, observe the effects of each example.

| Example | Boundaries to check individually |
|---|---|
| Entry to update mode | Invariance on refusal of unsupported destinations, not disconnecting before the answer, checking the destination when the answer is lost, return to the app and a new boot |
| Image transfer over OEP | Refusing out-of-area / over-limit before side effects, splitting to fit the frame, checking progress after a lost answer, being able to return to the loader after power loss |
| Privileged operations | Invariance on refusal without proof / for another person / for another target, revocation, permission cleared after end/force, not restoring permission from an old success, protection of cached answers |
| Protection of the whole connection | That unauthorized connections cannot reach the control endpoint, whether there are unprotected transports, the core behaviour of permitted connections |
| Core-only devices and chains of extensions | That the core checks pass without pins, that each host skips or is refused unknown names, that numbers looked up from names read the same thing even when the list order changes, that another revision is not misread |

Each project brings the concrete fixed shapes, failures, lifetimes and observation methods of the examples it adopts into its own specification and checks them.
Do not use only the operation names or tables of this guide as a wire specification between implementations.
