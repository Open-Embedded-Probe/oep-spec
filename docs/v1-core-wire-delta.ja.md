# Open Embedded Probe — core wire model v1（v0 からの差分）

状態: **仮置き**（2026-09-24 の議論の合意）。実験してから調整する。土台は
[core wire model v0 draft](v0-core-wire-model.ja.md)。ここに書いていない部分（フレーム、要求と応答の見出し、
resolution、reject reason 0x01〜0x06、TLV の形、window）は v0 のまま。

関連: [セッションと排他](session-and-exclusivity.ja.md)、[能力の宣言モデル](capability-declaration-model.ja.md)、
[能力の名前の階層](capability-name-hierarchy.ja.md)、[コンソールのストリーム](console-stream.ja.md)。

## 1. v0 のまま使う部分

| 部分 | 形 |
|---|---|
| フレーム（USB CDC、USB-Serial/JTAG、TCP） | 長さ u16 + メッセージ。CRC なし |
| フレーム（UART） | COBS + CRC-16、0x00 で区切る |
| フレーム（USB の Vendor / HID） | 1 回の転送 = 1 メッセージ |
| 要求 | `role(0x01) corr(u16) fn(u16) op(u8) payload` = 見出し 6 byte |
| 応答 | `role(0x02) corr(u16) resolution(u8) detail(u8) payload` = 見出し 5 byte |
| resolution | 0x00 rejected / 0x01 completed / 0x02 accepted |

## 2. 要求の見出しの session_id

```text
role=0x01          | corr | fn | op | payload                      session_id なし
role=0x81 (bit7=1) | corr | fn | op | session_id(u32) | payload     session_id あり
```

- role の bit 7 を「session_id あり」のフラグにする。見出しは増えない。bit 7 の立った role を知らない v0 の probe は、
  未知の role として捨てる。
- 状態を変える要求は role 0x81 で送る。ロックなしで使える要求（confirm、list、describe、ロックの状態、status、
  コンソールの read / marks）は role 0x01 で送ってよい（0x81 で送れば期限を伸ばす）。
- open は session_id を payload で渡す（role 0x01）。

## 3. 追加の reject reason

| 値 | 名前 | 意味 | payload |
|---:|---|---|---|
| 0x05 | busy（v0 と同じ値） | 長い操作が実行中。ぶつかる要求にはすぐに返す | — |
| 0x07 | no session | ロックは空いているが、この session_id は最後の ID ではない。host は open からやり直す | — |
| 0x08 | locked | 他のセッションがロック中 | 残り時間 ms（u32）。今の session_id は返さない |
| 0x09 | session required | 状態を変える要求に session_id が無い（role 0x01） | — |

判定の表は [セッションと排他](session-and-exclusivity.ja.md) の「要求を受けたときの判定」。

## 4. 長い操作はポーリング

- accepted の応答は activity の番号（u16）を返す（v0 と同じ）。
- host は core の `status(activity)` を投げる。応答は completed（最終結果。payload はその操作の結果）か、accepted と
  進捗 `done(u32) total(u32)`（total が分からなければ 0）。
- 実行中の長い操作は probe 全体で 1 つ。最後の結果は同じ session_id の間だけ取り出せ、新しい session_id でロックが
  立ったら消える。
- v0 の probe から送る role（0x03 activity update、0x04 activity outcome、0x05 notification）は v1 では使わず、予約として
  残す（通知は将来の拡張）。0x06 data も v1 では使わない。

## 5. core（fn 0）の操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | confirm | magic | magic、revision、max_frame、window、max_inflight | 不要 |
| 0x02 | list | flags(u8、bit0 = exact)、first(u8)、prefix_len(u8)、prefix | total(u8)、count(u8)、entries | 不要 |
| 0x03 | describe | fn(u16)、first(u8) | more(u8)、TLV。fn 0 は probe 全体の宣言 | 不要 |
| 0x10 | open | session_id(u32)、lease_ms(u32)、force(u8) | lease_ms(u32)、boot_id(u32)、resumed(u8) | open がロックを取る |
| 0x11 | end | — | — | 必要（role 0x81） |
| 0x12 | keepalive | — | — | 必要（role 0x81） |
| 0x13 | lock_state | — | locked(u8)、remaining_ms(u32) | 不要 |
| 0x20 | status | activity(u16) | 上記 §4 | 不要 |
| 0x21 | cancel | activity(u16) | —（止められなければ rejected unavailable） | 必要 |

- list の entry: `fn(u16) instance(u16) revision(u8) flags(u8) name_len(u8) name`。件数と開始位置は u8（probe が
  255 を超えるインターフェースを持つことは想定しない。必要になったら広げる）。
- open の `resumed` は、同じ session_id でロックを立て直した（再開）とき 1。
- op の番号は仮。

## 6. 長さの確認（64 byte のフレーム）

- list の応答: 見出し 5 + list の見出し 2 + 1 項目（7 + 名前 48）= 62 byte。
- 状態を変える要求の見出し: 6 + 4 = 10 byte。payload に 54 byte 使える。

## 未決

1. confirm の応答の形（v0 と同じでよいか、v1 の revision をどう示すか）。
2. op の番号の割り当て。
3. UART の binding のシーケンス（重複の判定）の置き場（[UART connection epoch](uart-connection-epoch.ja.md) の候補から）。
