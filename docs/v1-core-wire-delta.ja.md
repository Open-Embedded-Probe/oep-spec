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
| フレーム（UART） | COBS + CRC-16、0x00 で区切る。CRC は仮置きで CRC-16/CCITT-FALSE（多項式 0x1021、初期値 0xFFFF、反転なし、"123456789" → 0x29B1）、メッセージの後ろに little endian で付ける。COBS は 254 byte のブロックに分ける標準の形 |
| フレーム（USB の Vendor / HID） | 1 回の転送 = 1 メッセージ |
| 要求 | `role(0x01) corr(u16) fn(u16) op(u8) payload` = 見出し 6 byte |
| 応答 | `role(0x02) corr(u16) resolution(u8) detail(u8) payload` = 見出し 5 byte |
| resolution | 0x00 rejected / 0x01 completed / 0x02 accepted |

どちらのフレームを使うかは transport で決まる。probe は自分の transport を知っている（UART の probe は COBS）。host は
USB の VID:PID で USB-UART の変換チップ（CH340 / CH343 / CP210x / FT232 など）を見分けて COBS を選び、指定で上書きも
できる。壊れた応答や応答なしのとき、host は session_id の無い要求（読むだけの要求、open）だけを 1 回送り直し、状態を
変える要求は送り直さない（シーケンスが無いので二重実行になりうる）。

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
- v0 の probe から送る role のうち 0x03 activity update、0x04 activity outcome は v1 では使わず、予約として残す。
  0x05 と 0x06 は §4.5 の通知に使う。

## 4.5 probe から送る通知（仮置き、2026-09-25 の実験で動作を確認）

**probe から自動で送る仕組みを v1 に入れる。** 後から足すと、応答だけを想定した host が壊れるため。probe の対応は任意、
host は購読しなければ何も受け取らない。

### host の義務（全 host）

- 受け取ったフレームを **role で振り分ける**。corr で照合するのは role 0x02（応答）だけ。0x05 / 0x06 のフレームの
  バイト 1〜2 は fn なので、role を見ずに corr として照合すると、fn がたまたま corr と同じ値のときに応答と取り違える
  （oep-client-python は 2026-09-25 まで role を見ていなかった）。
- 知らない role のフレームは捨てる。

### 形

```text
データ   role=0x06 | fn(u16) | seq(u16) | position(u32) | data         見出し 9 byte
出来事   role=0x05 | fn(u16) | seq(u16) | kind(u8) | payload           見出し 6 byte（形は仮。未実験）
```

- `seq` は fn ごとのフレームの通し番号（一周する）。抜けがあればフレームが失われた。
- `position` はその fn のストリームの中のバイト位置（一周する）。前のフレームの終わりと合わなければ、その間は
  probe の中で押し出された（host が遅れた）。
- 送ったデータは、そのインターフェースの位置指定の読み出し（ポーリング）でも読めるようにする（コンソールと同じ）。

### 購読とクレジット（core の操作、番号は仮）

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x30 | subscribe | fn(u16)、credit(u32) | — |
| 0x31 | credit | fn(u16)、add(u32) | — |
| 0x32 | unsubscribe | fn(u16) | — |

- probe は購読された fn のデータだけを、クレジットの残りバイト数の範囲で送る。0 になったら止まり、credit で再開する。
  止まっている間も取り込みは続くので、押し出された分は position の飛びで分かる。
- 送り出さないインターフェースは subscribe を rejected unavailable にする。
- **クレジットの枠（送りかけを許すバイト数）は、線の速さ × 許せる遅れで決める。** 送りかけのデータの後ろに他の要求の
  応答が並ぶため。
- 購読は接続に属し、切断で消える。session_id との関係（ロックの持ち主だけが購読できるか）は未決。

### 実験（2026-09-25、oep.test.counter: 指定の速さでバイトを生み、8 KiB を超えて遅れたら押し出す試作のインターフェース）

| 項目 | P4（USB-Serial/JTAG、長さ付きフレーム） | classic ESP32（UART 経由、COBS） |
|---|---|---|
| 購読なし | 何も来ない | 何も来ない |
| クレジット 4096 → +8192 | 4096 で止まり、12288 まで再開。止まっている間の 45 KB は position の飛びで検出 | 同じ（114 KB を検出） |
| 流量（枠 32 KiB / 4 KiB） | 500 kB/s まで全量、欠落なし。800 kB/s 以上は約 640 kB/s で頭打ち（あふれは position の飛びで検出） | 10 kB/s まで全量。20 kB/s は線の上限 11 kB/s で頭打ち |
| 送っている間の他の要求（lock_state） | 枠 32 KiB で中央値 0.6 ms（普段 0.45 ms）。**クレジット無制限では 9.8 ms** | 枠 4 KiB で 85〜240 ms（普段 4.8 ms）。4 KiB は約 370 ms 分 |
| 化け、seq の抜け | 0 | 0 |

- 流量が少ないとフレームが細かくなる（P4 で 50 kB/s のとき 14 万フレーム、1 フレーム約 1 バイト）。**何バイトたまるか、
  何 ms 経つまで待って送るかを subscribe で指定する形が要る**（未実装）。
- この試作の送り出しの上限（640 kB/s）はポーリング（811 KiB/s）より低い。通知の利点は速さではなく、応答の待ち時間と、
  host が位置を管理しなくてよいこと。
- 出来事（0x05）は未実験。候補: fixture の GPIO の割り込み（エッジ）、probe のハートビート（生きていること、boot_id）、
  target の停止やリセット、キャプチャの完了、ロックの期限切れの予告。

## 5. core（fn 0）の操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | confirm | magic | magic、revision、max_frame、window、max_inflight | 不要 |
| 0x02 | list | flags(u8、bit0 = exact)、first(u8)、prefix_len(u8)、prefix | total(u8)、count(u8)、entries | 不要 |
| 0x03 | describe | fn(u16)、first(u8) | more(u8)、TLV。fn 0 は probe 全体の宣言 | 不要 |
| 0x04 | plan_apply | role_assignment の TLV（0x90、critical: fn(u16) role(u8) channel(u16)）の並び | — | 必要 |
| 0x05 | plan_release | — | — | 必要 |
| 0x10 | open | session_id(u32)、lease_ms(u32)、force(u8) | lease_ms(u32)、boot_id(u32)、resumed(u8) | open がロックを取る |
| 0x11 | end | — | — | 必要（role 0x81） |
| 0x12 | keepalive | — | — | 必要（role 0x81） |
| 0x13 | lock_state | — | locked(u8)、remaining_ms(u32) | 不要 |
| 0x20 | status | activity(u16) | 上記 §4 | 不要 |
| 0x21 | cancel | activity(u16) | —（止められなければ rejected unavailable） | 必要 |

- list の entry: `fn(u16) instance(u16) revision(u8) flags(u8) name_len(u8) name`。件数と開始位置は u8（probe が
  255 を超えるインターフェースを持つことは想定しない。必要になったら広げる）。
- open の `resumed` は、同じ session_id でロックを立て直した（再開）とき 1。
- plan は v0 と同じ形（全インターフェースが自分の役割を受け入れたときだけ適用、1 つずつ）。割り当ては probe の状態で、
  セッションの終わりやロックの期限切れでは解かない（plan_release でだけ解く）。
- 最初の実装（2026-09-24）では、fixture（gpio / uart / capture）の各操作の payload は v0 のまま。
- op の番号は仮。

## 5.5 `oep.wire.<線>` と `oep.target.riscv-dm` の操作（仮置き、最初の実装の形）

名前の置き方は [能力の名前の階層](capability-name-hierarchy.ja.md)。番号と書式は仮で、ch32rv のレビュー
（2026-09-24）を受けて足したものを含む。

`oep.wire.rvswd` / `oep.wire.swio`:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | — | count(u8)、kind(u8) swdio(u16) swclk(u16) DMSTATUS(u32) の並び（生の値） |
| 0x02 | attach | method(u8: 0 止めない / 1 止める) | connection(u8)、DMSTATUS(u32)、flags(u8: bit0 保留中の havereset を確認応答した) |
| 0x03 | detach | connection(u8) | — |
| 0x04 | attach_under_reset | channel(u16、0xffff = probe の既定値)、hold_ms(u16) | connection(u8)、dpc(u32) |

- attach は保留中の havereset を先に確認応答する（V00x の DM は確認応答まで DMSTATUS の halt / running を固定する）。
- attach_under_reset はリセットの線を保持して attach し、離しながら halt を打ち続ける（タイミングが厳しいので probe の
  1 操作）。host が指定できるのは probe が許可したチャンネルだけ。任意の op（持たない probe は unsupported）。
  持たない probe では、host は `oep.fixture.gpio` の解放と attach をまとめて送って再試行する（窓の縁の競争）。

`oep.target.riscv-dm`（最初の byte は connection）:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | dmi | 手順の並び（下表） | done(u16)、status(u8: 0 ok / 1 書式 / 2 アクセス / 3 待ち切れ)、read の値 |
| 0x02 | halt | — | — |
| 0x03 | resume | — | — |
| 0x04 | reset | mode(u8: 0 走らせる / 1 走らせて実行を確認 / 2 最初の命令の前で止める) | flags(u8)、attempts(u8)、pc(u32)（mode 2 では dpc） |
| 0x05 | read_block | address(u32)、count(u16) | 語の並び |
| 0x06 | write_block | address(u32)、語の並び | — |
| 0x07 | run | pc(u32)、timeout_ms(u16)、n(u8)、n × (regno u16、value u32) | stopped(u8)、dpc(u32)、a0(u32)、elapsed_us(u32) |
| 0x08 | step | — | moved(u8)、dpc_before(u32)、dpc_after(u32) |

DMI の手順:

| kind | 手順 | 引数 |
|---:|---|---|
| 0x01 | 書く | address(u8)、value(u32) |
| 0x02 | 読む | address(u8)（値を応答に足す） |
| 0x03 | 読む回数を上限に待つ | address(u8)、mask(u32)、value(u32)、max_reads(u16) |
| 0x04 | 待ち | us(u32) |
| 0x05 | 時間を上限に待つ | address(u8)、mask(u32)、value(u32)、max_us(u32)（線の速さに依らず同じ意味） |

- reset の mode 2 は haltreq を保ったまま ndmreset を解く。semihosting、gdb の `monitor reset halt`、動いている
  ウォッチドッグの上からの書き込みに使う（IWDG は hart を止めても数え続ける）。
- step は dcsr.step を立てて resume を 1 回だけ出し、成否は dpc が動いたかで判定する（L103 は allresumeack を立てず、
  resume の出し直しは 2 ステップ進めてしまう）。prv は変えない（U モードのスケッチのステップ実行）。
- run は dcsr の ebreakm と prv = M を立てる（host のローダー用。割り込みは host が mstatus = 0 で止める）。
  止まった位置が開始位置のままなら、走らなかったとみなして resume を出し直す。
- 一つの要求は一つの hart の操作で、DMI の手順のリストは probe の都合（線の再試行、立て直し）を書けない。
  リセットや回復のようにタイミングと線の立て直しが要るものは、部品（reset、attach_under_reset）にする。

## 5.6 `oep.wire.swd` と `oep.target.arm-adi` の操作（仮置き、2026-09-24 の最初の実装）

`oep.wire.swd`（scan の kind は 0x02 = arm-adi）:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | — | count(u8)、kind(u8) swdio(u16) swclk(u16) DPIDR(u32) の並び |
| 0x02 | attach | [TARGETSEL(u32)]（multidrop のときだけ） | connection(u8)、DPIDR(u32)、flags(u8: bit0 dormant から起こした) |
| 0x03 | detach | connection(u8) | — |

- attach は JTAG から SWD への切り替えを試し、答えがなければ dormant から起こす（RP2350 の SWD v2 は後者でだけ答える）。
  電源投入（CTRL/STAT の CDBGPWRUPREQ / CSYSPWRUPREQ）は host が DP の書き込みで行う。
- attach_under_reset は持たない（任意の op）。

`oep.target.arm-adi`（最初の byte は connection）:

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | transfer | 転送の並び: req(u8: bit0 APnDP、bit1 RnW、bit2-3 A[3:2]) と、書き込みなら value(u32) | done(u16)、status(u8: 0 ok / 1 書式 / 2 FAULT / 3 応答なし・パリティ / 4 WAIT のまま)、ack(u8)、読んだ値の並び |
| 0x02 | read_block | address(u32)、count(u16) | 語の並び |
| 0x03 | write_block | address(u32)、語の並び | — |

- transfer は生の転送で、AP の読み出しが 1 つ遅れて返るのもそのまま（host が RDBUFF か次の AP の読み出しで受け取る）。
  WAIT は probe の中で再試行する。FAULT で止まるので、host は ABORT で sticky を消す。
- read_block / write_block は今の MEM-AP の TAR / DRW を使う。SELECT（TAR / DRW のある bank）と CSW（32 bit、単一増加、
  保護の属性）は host が先に設定する。probe は 1 KiB の境界ごとに TAR を書き直し、1 つ遅れる読み出しを並べ直す。
- **flash の書き込みまで通した**（2026-09-24、RP2040-Zero → Pro Micro RP2350）: host が core 0 を止め、DCRSR / DCRDR で
  レジスタを置き、SRAM の BKPT へ戻る形で boot ROM の flash 関数（connect_internal_flash → exit_xip → range_erase →
  range_program → flush_cache → enter_cmd_xip）を呼ぶ。98 KiB のイメージを消去 0.3 秒、書き込み 3.0 秒、読み戻しの
  検証 2.0 秒。ROM の reboot でチップごと再起動し、USB が再列挙して probe の firmware が戻った。target の知識
  （ROM の表の引き方、関数の並び、CSW のセキュア属性、DHCSR の C_MASKINTS がリセットを越えて残ること）はすべて host 側
  （oep-client-python の `arm.CortexM`、`rp2350`）。
- 実測（RP2040-Zero → Pro Micro RP2350、ADIv6、半周期 500 ns）: 読み出し約 47 KiB/s。AP は 0x2000 / 0x4000（Cortex-M33 の
  AHB-AP、IDR 0x34770008）、0xA000（APB-AP）、0x80000（RP-AP）。AHB-AP は非セキュア（CSW bit 30）で上がってきて、
  そのままでは SRAM が FAULT になる（セキュアにすると読める）。

## 6. 長さの確認（64 byte のフレーム）

- list の応答: 見出し 5 + list の見出し 2 + 1 項目（7 + 名前 48）= 62 byte。
- 状態を変える要求の見出し: 6 + 4 = 10 byte。payload に 54 byte 使える。

## 未決

1. confirm の応答の形（v0 と同じでよいか、v1 の revision をどう示すか）。
2. op の番号の割り当て。
3. UART の binding のシーケンス（重複の判定）の置き場（[UART connection epoch](uart-connection-epoch.ja.md) の候補から）。
