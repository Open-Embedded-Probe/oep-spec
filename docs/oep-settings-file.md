# Open Embedded Probe — settings file v1

[日本語](oep-settings-file.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **normative** (v1). For the freeze state and the language and compatibility policy, see [versions and stability](versioning.md).
This document defines the shape of the file, and the procedure, by which a host exports a probe's settings ([OEP core](oep-core.md) §13) and memo area ([oep.probe.memo](../interfaces/oep-if-memo.md)),
and imports them again into the same probe or another probe.
It does not define the format of the save inside the probe (core §13.7). The purpose is that files written by different hosts, such as a browser and a CLI, can be read by each other.

## 1. Why it is needed

- When the firmware version or configuration changes, a probe does not use unusable values in its save, and removes them at the next save (core §13.7). It is fine for them to disappear because the host can export them first
  and import them again later.
- The flow of a firmware update: export → write the firmware → import. For a probe without saving, import at every connection.

## 2. Shape of the file

One UTF-8 JSON (RFC 8259). No BOM. The extension `.oep-settings.json` is recommended (informative).

```json
{
  "oep_settings": 1,
  "probe": { "model": "rp2350", "unit_id": "9489dd2ae0953650", "firmware": "1.0.0" },
  "settings": {
    "core": {
      "channel.GPIO14.label": "NRST",
      "channel.GPIO14.idle": "pull-up",
      "channel.GPIO2.disable": true,
      "wifi.0.ssid": "lab",
      "wifi.0.passphrase": { "secret": true },
      "ipv4.wifi.mode": "static",
      "ipv4.wifi.address": "192.168.1.23"
    },
    "oep.wire.rvswd/0": { "channel.GPIO5.rest": "low" },
    "oep.fixture.uart/0": { "passthrough.cdc0.rx": "GPIO1", "passthrough.cdc0.baud": 115200 }
  },
  "memo": {
    "oep.probe.memo/port/x035": "{\"target\":\"ch32x035-1a2b3c4d\"}",
    "io.github.example.bench/blob": { "bytes": "00ff10" }
  }
}
```

(The wifi, ipv4, rest and passthrough items of the example are defined by their own documents.)

| Member | Value |
|---|---|
| `oep_settings` | A number. The version of the file shape. This document is 1. A reader does not use a file of an unknown version |
| `probe` | An object. The probe that exported: `unit_id` (mandatory), `model`, `firmware` (if present in the fn 0 describe, its text as it is; core §7.5) |
| `settings` | An object. A member per category (§2.1) |
| `memo` | An object. Optional. All objects of the memo area (§2.4) |

- A reader skips unknown members (at the top level and inside `probe`). A writer does not put members not in this document at the top level or in `probe`.
- The same member name is not put twice in the same object. A reader does not use a file with duplicates.

### 2.1 Categories

The names of the members of `settings` are categories (core §13.1):

- The core's category is `core`.
- An interface's category is its name, `/` and the instance in decimal (`oep.fixture.uart/0`).

The value of a member is an object, a mapping from a flat name per item to a value. A category without values need not be written.

### 2.2 Flat names

A flat name is the item name (core §13.1) with `{}` replaced by the export name of the key (core §13.3: a channel name, a decimal number, a transport name, a netif name).
An item without a key keeps the item name.

- A reader finds the item that matches a flat name by comparing with the names declared in the category: for an item without a key, the one with the same name; for an item with a key, one whose parts before and after `{}`
  match the beginning and end of the flat name, with a non-empty part in between (the key name). A key name can contain `.` (others' netif names, core §7.7).
- A flat name that matches 2 or more items (`a.b.c` matching both `a.{}` and `a.b.{}` and so on) is not used and is shown to the user. An owner does not put such a pair of names
  in the same category.

### 2.3 Values

Values are written in the export form of the item's form (core §13.3):

| form | JSON | Example |
|---|---|---|
| bytes | A string of lowercase hexadecimal digits (2 characters per byte, may be empty) | `"0a1b"` |
| text | A string | `"NRST"` |
| u32 | An integer 0 to 4294967295 | `115200` |
| ipv4 | `"a.b.c.d"` (each 0 to 255 in decimal, no leading 0) | `"192.168.1.23"` |
| bool | `true`, `false` | `true` |
| enum | The name of the choice (setting_choice of core §13.2) | `"pull-up"` |
| channel | The channel name | `"GPIO1"` |
| transport | The transport name | `"cdc0"` |
| fn | `"name/instance"` | `"oep.wire.swio/0"` |

- For the value of a secret item (core §13.5), `{ "secret": true }` is written instead of the value. The value cannot be read from the probe, so it is not in the file either.
- A reader does not use JSON values that do not match the form (wrong shape, out of range, non-integer numbers), and shows them to the user.

### 2.4 Memo area

The names of the members of `memo` are the names of memo area objects (oep-if-memo §1), and the values are their data:

- If the data is valid UTF-8, the string as it is. Even if the content is JSON, it is put in as a string without parsing (so that the bytes do not change).
- Otherwise `{ "bytes": "<hex>" }` (written the same way as bytes in §2.3).

- An object whose name is not valid UTF-8 cannot be written to the file (JSON names are strings).
- A file without `memo` says nothing about the memo area. Importing does not touch the memo area.
- An empty object `{}` expresses that the memo area is empty.

## 3. Export

1. Read confirm, list and describe of fn 0, and the describe of each fn, and get the item declarations (setting, setting_choice), channel names, transports and netif names.
2. Read all values with get of fn 0 (from the start if the generation changes midway).
3. Write all values, converting numbers to the names of §2 (values that came from initial values are written too, without distinction; core §13.4). Secret values are written as
   `{ "secret": true }` as in §2.3 (only that there is a value).
4. If the probe has `oep.probe.memo`, list all objects with list, read each with read, and write them to `memo` (`{}` if there are none).
   Objects whose data CRC-32 does not match crc (oep-if-memo §3) and objects whose name is not UTF-8 are not written, and are shown to the user.
   The file of a probe without `oep.probe.memo` has no `memo`.

## 4. Import

Importing makes the probe's values the values of the file. If the file has `memo`, the probe's memo area is also made the objects of the file.

1. Read the declarations as in step 1 of export, and read the current values with get.
2. For each value of the file, look up the category's fn (fn 0 for `core`; for an interface, the one in list with the same name and instance), the item and key (§2.2) and the value (§2.3)
   to current numbers. What cannot be looked up (the category, item, key or reference is not on the current probe) is not sent.
   - If the file has `memo`, read the memo area's list and decide as follows:
     - If the probe does not have `oep.probe.memo`, send no objects, and show them as things that cannot be looked up.
     - Among the file's objects, those whose size and crc in list are the same as their data are not written (oep-if-memo §4.2). The others are written.
       Those whose data is longer than max_object are not sent, and are shown as things that cannot be looked up.
     - Objects on the probe that are not in the file are deleted.
3. Where possible, show the following to the user and get confirmation (it MAY be skipped when the user specified skipping confirmation beforehand, for example `--yes` of a CLI):
   - what cannot be looked up;
   - values that are rewritten, values newly put, values unset (values of the probe not in the file);
   - objects to write, objects to delete;
   - that the unit_id or model of `probe` differs from the current probe.
4. Secret values:
   - if the current probe has that value, do not touch it (not even unset);
   - if not, ask the user for input, or do not put it.
5. Send unset first and set after (so that moving a label to another channel does not collide with the uniqueness rule (core §13.8)). With many values, requests MAY be split
   (each request is accepted all together or does nothing; core §13.5). Refused values are shown to the user.
6. For the memo area, send delete first and write after (so as not to collide with max_objects). An object remains once it has been written completely (oep-if-memo §3).
   This is unrelated to the settings save. Refused ones are shown to the user.
7. If the probe has save, save, and check with state.

- For a probe without saving, the host MAY import automatically on connection (only a file the user chose).
- When exporting a file, the host has no means to put secret values into the file (they cannot be read from the probe). It also does not add secrets the user entered by hand
  to the file (keeping the rule that the file holds no secrets).

## 5. Test vectors

`tests/vectors/settings_file.json` holds sets of declarations (describe TLVs), get values, memo area objects and files, and the sets of set, unset, secret, memo area write and delete, and things that cannot be looked up
when importing into a probe with other numbers. The browser (JS) and CLI (Python) implementations check the conversions of export and import with the same vectors.
