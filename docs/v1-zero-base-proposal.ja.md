# v1 のゼロベース再検討と仕様案（2026-10-01）

状態: **案（未決）**。[凍結前の全面見直し](v1-freeze-review-2026-10-01.ja.md)（59 項目）を受けて、「あるべき姿」を今の文書に縛られずに
考え直し、**シンプルで伸ばしやすい形になっているか**、**伸ばせない所は本当に伸ばせなくてよいか**を部位ごとに判定した。
結論は「骨格（層、フレーム、TLV、セッション、発見、plan、資源の寿命、通知）はそのままでよい。直すのは**長さの規律**を全部に
通すことと、**意味の規則** 7 つ。意図的に固定する所を一覧にして理由を書く」。

各節の ★ はユーザーに選んでもらう項目。見直しの項目番号は `見直し N` と書く。

---

## 0. 結論（先に）

| 判定 | 中身 |
|---|---|
| **残す** | 3 層の線引き、`fn / op / TLV` の 3 段の番号空間、要求 = 固定部 + critical / 非 critical の TLV、応答 = 固定部 + TLV、rejected / completed の二分、1 つのロック + lease + session_id、資源の寿命の表（end で残す / 期限切れと force で外す）、list / describe / plan、通知の seq、COBS + CRC-16 と長さつきフレームの 2 系統、revision は固定部を変えるときだけ |
| **直す（規律）** | **「長さを持たない容器を無くす」**: 応答の data に len、データフレームに len、gpio read に count、dmi / transfer に nvals。TLV の len に 0xFF → u16 の逃げ道（★）。可変部は前に長さ、並びは count × (len, 要素)。これで「後ろに足せない所」は意図した 4 か所だけになる |
| **直す（意味）** | (1) describe は宣言だけ、状態は別 op。(2) boot_id は confirm で返す（ロック無しで取れる）。(3) 期限切れ後の黙った再開を止める。(4) 資源番号は probe で 1 つの空間、一周を許す。(5) 時刻は起動からの ns（u64）の一本。(6) エラー理由の判定順を 1 行で決める。(7) probe は op の外に target の状態を持ち越さない（block op の自己完結） |
| **意図的に固定** | フレームの見出し（confirm の revision で替える）、COBS / CRC の方式（経路の種類ごと）、op と tag の u8 空間（インターフェースを分ける）、要求の並びの要素に len を置かないこと（host が probe に合わせる）、link_source / link_sink |

---

## 1. 設計の原則（判定に使ったもの）

1. **容器は自分の長さを知る。** フレーム、TLV、並びの要素、バイト列（data）のどれも、読む側が「どこで終わるか」を要求や外の知識なしに
   分かる。これが成り立つ所には、後から何でも足せる（読む側は知らない後ろを飛ばす）。成り立たない所は「意図して固定した」と書く。
2. **伸ばし方は 1 つだけ。** 形 = 固定部 + 後ろ。書く側は後ろにだけ足す、読む側は知っている長さより後ろを飛ばす。応答と出来事の
   「後ろ」は TLV、入れ子の形（TLV の値、並びの要素）の「後ろ」は長さで飛ばすバイト。
3. **要求は probe に合わせる、応答は host に合わせる。** host は revision と describe で probe を知ってから送るので、要求の並びの
   要素に len は要らない（足すものは TLV）。応答は新しい probe が古い host に読まれるので、並びの要素に len を置く。
4. **値の幅は、ハードウェアの性質で決まるものは u32。** ADC のビット数、チャンネル数、速さ、しきい値は u32。u8 / u16 は、プロトコルの
   都合で上限が決まるもの（1 フレームの中の数、fn、資源の番号）だけ。describe のビット集合は u32 か `base + bitmap`。
5. **宣言と状態を混ぜない。** describe は起動の間変わらない宣言。変わるもの（接続、保存の有無、スロットの状態）は状態を返す op。
   ページングと host の cache が成り立つ。
6. **仕組みより不変条件。** 「probe は op の応答を返したあと、target の状態を持ち越さない」のような一文で言える規則を選ぶ。
   境界条件（host が raw で触った、host が死んだ）を個別に書かなくてよくなる。
7. **識別子と時計は 1 つずつ。** probe の起動 = boot_id、probe の時計 = 起動からの ns（u64）。位置が 0 に戻る所には世代番号。
8. **断り方の順は 1 つ。** 書式 → 定義にあるが持たない → 状態と資源。同じ状況に 2 つの理由を作らない。

---

## 2. 拡張性の棚卸し

| 部位 | 今の伸ばし方 | 判定 | 根拠 |
|---|---|---|---|
| フレームの見出し（role, corr, fn, op, session_id / resolution, detail） | confirm の revision | **固定でよい** | 替えるときは revision。host は min_rev〜max_rev で交渉できる |
| フレームの方式（COBS + CRC-16 / length / HID report） | 経路の種類 | **固定でよい** | 新しい経路は transport kind を足して自分の方式を定める |
| TLV `tag(u8) len(u8) value` | 繰り返し | **★ 要検討** | 255 byte を超える 1 つの値（較正の表、長い text）が表せない。繰り返しが「並び」か「連結」かは tag ごとに決める必要 |
| 要求 = 固定部 + TLV | TLV（critical で安全） | 十分 | — |
| 応答 = 固定部 + TLV | TLV | 十分。**ただし閉じた末尾を除く** | read 系、gpio read、dmi / transfer、link_sink（見直し 1） |
| 出来事 payload | 後ろに足す（フレーム長で終わりが分かる） | 十分 | — |
| データフレーム `fn seq position data` | なし | **直す** | data の前に len が無く、flags も付けられない |
| 応答の並び `count(u8) × (len(u8), 要素)` | 要素の後ろ | 十分 | count u8 は 1 フレームの中の数なので足りる |
| 要求の並び `count × 要素` | TLV | **固定でよい** | 原則 3 |
| TLV の値の固定の形（slot 項目、describe の値） | 後ろに足す | 十分。**ただし hash の規則が要る** | 見直し 4 |
| op（u8 / インターフェース） | 0x01〜0xEF | 十分 | 足りなければインターフェースを分ける（名前が違う = 別の fn） |
| reject reason（u8） | 0x40〜0x7F をインターフェース | 十分 | — |
| 資源の番号（u16、再利用しない） | — | **直す** | 使い切る（見直し 14）。一周を許せばよい |
| describe の TLV（宣言 + 状態） | tag を足す | **直す** | 状態が入るとページングと cache が崩れる（見直し 29） |
| probe.config の項目 | 項目の後ろに足す、新しい tag | 十分。**ただし hash と削除の規則** | 見直し 4、19 |
| 値の幅: trigger value u16、gpio modes u8、zero i32 | — | **直す** | 原則 4（見直し 9、22） |
| 時刻: mark ms u32 / capture ns u64 / heartbeat ms u32 | — | **直す** | 原則 7（見直し 18） |
| 位置（u64、start で 0 に戻る） | — | **直す** | 世代（見直し 8） |
| インターフェース名の長さ | — | **直す** | 上限が無い（見直し 15） |
| 1 要求の最長時間 | — | **直す** | lease との関係が無い（見直し 26） |

---

## 3. 提案

### 3.1 本体: フレームと TLV

**(a) ★ TLV の長さの逃げ道。** `len = 0xFF` を「続く u16 が本当の長さ」の印にする（`tag, 0xFF, len(u16), value`）。普通の TLV は今のまま
2 byte の見出し。255 byte までの値は今までどおりで、読む側の変更は 1 分岐。
- 選ばない場合: 「255 byte を超える値は同じ tag の繰り返しで**連結**する。並びを表す繰り返しとどちらかは tag の定義が決める」を §2.2 に
  書く。今の標準インターフェースで 255 を超える候補は calibration の factory（ESP32 の eFuse は 64 byte 以内）と role_channels
  （base + bitmap の繰り返しで済む）だけなので、v1 は逃げ道なしでも困らない。
- 推奨: **(a) を入れる**。コストがほぼ無く、「容器は自分の長さを知る」が TLV でも成り立つ。

**(b) 閉じた末尾を無くす**（見直し 1）。

```text
read（common §1.2、console、uart、capture）: start(u64), flags(u8), len(u16 / capture は u32), data, [TLV]
gpio read:                                   n(u8), n × level(u8), [TLV]
riscv-dm dmi / arm-adi transfer:             done(u16), status(u8), [ack(u8)], nvals(u16), nvals × value(u32), [TLV]
i2c / spi read_rx:                           そのまま（count を持つ）。registry の closed_tail を外す
link_sink の要求 / link_source の応答:        閉じたまま（試験用。意図的）
```

**(c) データフレーム**（core §11.2）: `role 0x06 | fn | seq | payload`、payload = `position(u64), len(u16), data, [TLV]`。
flags が要るときは TLV で足す。

**(d) confirm の応答に boot_id**（見直し 20）: `"OEP!", revision, flags, max_frame, window, max_inflight, boot_id(u32), [TLV]`。
boot_id は起動ごとに必ず変える（0「不明」は廃止）。ロック無しの host（Monitor、discovery）が再起動を知れる。open の応答の boot_id は
そのまま残す（同じ値）。

**(e) 1 要求の最長時間**（見直し 26）: fn 0 の describe に `max_op_ms(u32)`（既定 2000）を足し、「probe は 1 つの要求にこれ以上かけず、
超えうる op（run、dmi の wait、capture の start、save）は引数の和がこれを超えれば rejected unsupported。処理中は lease を数えない」。

### 3.2 セッション

- **(a) 期限切れ後の黙った再開を止める**（見直し 3）。§6.2 の表の「空き + 最後の session_id と同じ」を 2 つに分ける:
  **end で空いた**（資源は残っている）→ 再開して処理する（今のまま）。**期限切れか force で空いた**（資源は外した）→ rejected
  `expired`（新 reason 0x0E）。host は open からやり直し、open の応答の `resumed` は 2 =「資源を外した後の再開」とする。
- **(b) 1 つのセッションの 0x81 の要求は 1 つの経路で送る**（見直し 27）。読むだけの 0x01 は別経路でよい。
- **(c) §6.2 の表に 2 行**（見直し 28）: 「自分が持つ + 同じ ID の open（force なし）」= lease を作り直し resumed 1、表は捨てる。
  「rejected locked の open」では表を捨てない。

### 3.3 資源の番号

- **probe で 1 つの空間**（connection、stream、ほかインターフェースが振るもの）、u16、1 から進める（見直し 14）。
- **一周を許す**: 65535 の次は 1。閉じた番号は十分離れてから再利用してよい（直近に閉じた 1024 個は再利用しない、など probe が決める）。
  失敗した attach、同じ場所の再 open は番号を消費しない。
- 対応しない種類の資源（swd の connection を riscv-dm に）は rejected unavailable（cause 6）。

### 3.4 発見

- **(a) describe は宣言だけ**（見直し 29）。probe.config の `slot_state` / `bind_state` / storage の「状態と hash」は describe から出し、
  `state` op（0x05、ロック不要: `storage_state(u8), storage_hash(u32), unreadable_reason(u8), n_slots × (len, slot_state), n_binds × (len, bind_state), [TLV]`）に
  移す。describe の storage は `max_bytes(u32), max_save_ms(u32)` だけ。capture の describe の mode の「置き場の量は今の空き」も
  「最大」に限る。これで describe は boot_id が同じ間 cache できる。
- **(b) 名前**: 1〜64 byte、`a-z 0-9 - .`（見直し 15）。
- **(c) instance**: 同名のインターフェースを fn の昇順に 0 から。probe は同名の口の順を firmware の版を越えて保つ（見直し 30）。
- **(d) iProduct `OEP` 接頭を恒久の規範に**。vendor bulk は class 0xFF かつ `bInterfaceSubClass = 0x4F ('O'), bInterfaceProtocol = 0x45 ('E')`、
  HID は usage page 0xFF4F / usage 0x45 に固定（見直し 16）。1209:4F45 は参照 firmware の値として usb-identity に置き、取得後に core を
  書き換える計画をやめる。「serial = unit_id は probe が serial を選べる口に限る。unit_id は個体で一意。固有番号の無い probe は乱数を
  保存して使う」。
- **(e) アドレス** `oep://<unit_id>[/<slot name>]` を core §7.5 の小節に（見直し 46）。

### 3.5 時刻

- **probe の時計は起動からの ns（u64）の一本**（見直し 18）。マークの `time_ms(u32)` → `time_ns(u64)`、heartbeat の payload
  `boot_id(u32), uptime_ns(u64)`、probe.config の `last_try_ms` → `last_try_ns`。capture はすでにこの時計。

### 3.6 断り方の順（core §4.3 に 1 行）

1. 書式と値域の外（長さ、未定義の値、`address > 0x7F`、`mode > 3`）→ **malformed**。
2. 定義にはあるが、この probe が持たない（mode、format、rate の範囲外、trigger type、知らない critical TLV）→ **unsupported**
   （critical TLV なら tag、固定部なら無し）。
3. 今の状態・資源で受けられない（plan、接続、動いている、容量）→ **unavailable**（cause 付き）。
4. 番号で指す資源を知らない → **no_connection**。
各インターフェースの行をこれに揃える（見直し 47）。設定どうしの矛盾（重複、消したものを指す）は 1、probe の資源との衝突は 3。

### 3.7 `oep.probe.config`

- **(a) 削除は op にする**（見直し 19）: `unset`（0x05: `n(u8), n × (len(u8), tag(u8), key)`）。「キーだけの項目で消す」規則を廃止し、
  core §2.3 の「短ければ壊れた値」を例外なしにする。
- **(b) hash と保持**（見直し 4、6）: 「probe は host が送った項目のバイト列をそのまま持つ（critical bit だけ外す）。get と hash はそれを
  正規の順（tag 昇順、キー昇順）に並べたもの。probe が自分で後ろに足すことはしない。storage の hash は今の fn に読み替えた後の値、
  読めなければ 0」。
- **(c) 容量の単位**: `max_bytes` は正規形の byte 数で、その長さ以下なら必ず保存できる。保存は丸ごと置き換え（途中で電源が落ちても
  前か新しい保存のどちらかが読める）。`max_save_ms` は lease の上限より短い。
- **(d) `uart` 項目**（0x06: `fn(u16), baud(u32), format(u8)`、キー fn）（見直し 5）。起動時に configure 相当を掛ける。「ストリームは
  plan が作り、plan を解くと消える。CDC の口の line coding は無視する（OEP の configure だけが効く）」。
- **(e) slot の mechanism 0xFF = コンソールなし**。wire_fn は target_id scheme を持つ線に限る（見直し 7）。lock の n は scheme の値の
  長さと同じ（見直し 45）。
- **(f) slot / bind の置き換え・削除で、そのスロットが使っていた接続とコンソールの分を外す**（見直し 23）。
- **(g) get**: 正規の順で first 番目から。どのページも同じ hash を返し、変わったら host は読み直す。

### 3.8 線とデバッグ

- **(a) ★ block op の自己完結**（見直し 2）: read_block / write_block（と reset mode 1 の内部の halt）は、使った GPR、DATA1 / DATA0、
  abstractauto を**応答を返す前に**戻す。probe は op の外に target の状態を持ち越さない。これで「host が raw DMI で何をしても」
  「host が死んでも」の境界条件が消える。コストは op ごとに DMI 数回（数十 µs）。
  - 選ばない場合: 「halt 後に host から dmi の書き（kind 0x01）が 1 つでも来たら、覚えた値を戻してから捨てる」「connection を閉じる前に
    止まっている hart の値を戻す」「覚える契機は hart が止まっているのを最初に見た op」を §4.2 に書く（今の probe 0.0.21 の動き）。
- **(b) ★ attach の一本化**（見直し 12）: `attach_under_reset` を op から外し、`attach` の TLV `reset(critical: channel(u16), hold_ms(u16))`
  にする。応答は 1 つの形 `connection, id(u32: DMSTATUS / DPIDR), flags(u8), speed_hz(u32), [TLV dpc]`。swd の op 0x04 の予約も消える。
  - 選ばない場合: attach_under_reset の応答に `flags(u8)` を足して attach と並べる。
- **(c) run の応答は常に同じ形**。`stopped` に 2 =「止められなかった（dpc と値は無効）」（見直し 13）。
- **(d) max_speed は必須（無ければ malformed）。idle_clock と pins は任意、送るときは critical**（見直し 36）。
- **(e) scan**: 「並びに組が残っていれば少なくとも 1 組は試す。tried = 0 は使い切ったときだけ」「見つかった = DMSTATUS.version が 2 か 3 /
  DPIDR が妥当」「書くのは dmactive だけで終わったら戻す」「外れた組は空きの状態に戻す」（見直し 32）。
- **(f) reset の線はオープンドレインで low、離すときは駆動をやめる**（見直し 33）。
- **(g) SWD**: targetsel は critical 必須、scan の TLV に targetsel、speed は `min(max_speed, max_clock_hz)`、再同期の手順（見直し 34）。
- **(h) 線切れ判定は要求の中だけ。判定した要求は status line、connection はその後に閉じる**（見直し 31）。
- **(i) havereset を見たら覚えた値を捨て、mark restart**。sysbus は使ってよく SBCS は戻さない（見直し 37）。

### 3.9 コンソール

- **(a) ストリームの寿命は connection と同じ「使っているもの」の数え方**（見直し 23）: セッション、スロット（bind）。close と lease 切れは
  自分の分を外すだけ、全員が外れたら閉じる。閉じたあとも次の open まで読める規則はそのまま。
- **(b) 1 つの connection に生きているストリームは 1 つ**（見直し 24）。
- **(c) `streams` op**（0x08、ロック不要: `count × (len, stream, connection, mechanism, users(u8), state(u8))`）（見直し 20）。
- **(d) write の意味**: 「accepted は方式の送り枠に入れた分。枠が空いていなければ accepted 0 = failed。0 < accepted < count = partial」
  （見直し 25）。
- **(e) マークの detail を registry に**（見直し 50）。

### 3.10 キャプチャ

- **(a) 世代**: status と区画の情報に `generation(u32)`（start ごとに増える）。read の要求にも `generation` を置き、違えば rejected
  unavailable（cause 6）。古い read が新しいデータを黙って返さない（見直し 8）。
- **(b) trigger の value は u32**、zero は i64 か b ≤ 31（見直し 9）。samples は総数、足りないときは短い区画、force は trigger_index =
  その瞬間、即時は triggered を送らない。
- **(c) w に 64 / 128**（describe channels のビット 6 / 7）、「w ≥ 8 は w/8 byte の LE」で一般化（見直し 10）。
- **(d) segments に more**（見直し 11）。
- **(e) state 5 からは release で自動再開**、stopped reason 2 は送らない（見直し 38）。write_pos は捨てた分を含む、flags は start で 0
  （見直し 39）。
- **(f) group**: bind はセッションの資源、束ねた fn の plan 操作は unavailable cause 4、start の原子性、triggered は両方に出る
  （見直し 40）。
- **(g) rate**: 「範囲内なら最も近い実現可能な値、範囲外は unsupported」、trigger の describe は `types(u32), max_pretrigger(u32)`
  （見直し 41）。scale はピンの電圧への 1 次式（減衰込み）、vrefint に `nominal_mv`（見直し 17）。
- **(h) 出来事の kind を group とトラックで揃える**（triggered 3、stopped 2）（見直し 21）。

### 3.11 fixture

- **(a) gpio**: read の応答に `n(u8)`、describe の modes は u32（見直し 11、22）。
- **(b) uart**: format の未定義の値は malformed、critical で送る、baud は actual を返し ±5% を超えれば unsupported、lost の detail
  （見直し 43）。
- **(c) i2c-target / spi-target**: 見直し 42 の各点を 1 行ずつ。reset は「configure 直後と同じ状態」、列の深さは describe、CS は low で
  有効、未 arm の転送は捨てて数える、MISO は tx の外では 0。u8 の数は 255 で止める。

---

## 4. 意図的に伸ばせないままにする所（理由つき）

| 部位 | 理由 |
|---|---|
| フレームの見出し（要求 6 / 10 byte、応答 5 byte、通知 5 / 6 byte） | 替えるのは本体の revision。confirm で交渉できるので、固定でも将来の道は閉じない |
| COBS + CRC-16 / `length(u16)` / HID report の詰め方 | 経路の種類ごとに決まる。新しい方式は新しい transport kind で定める |
| op（u8）、TLV の tag（u8、bit7 critical）、reject reason（u8）、出来事の kind（u8） | 足りなくなったらインターフェースを分ける（名前が違えば別の fn）。空間を広げるより名前で分ける方が host に優しい |
| 要求の並びの要素に len を置かない | host は revision と describe で probe を知ってから送る。足すものは TLV（原則 3） |
| 応答の固定部そのもの | 固定部を変えるのは revision + 新しい fn。足すものは TLV。これが「伸ばし方は 1 つ」の意味 |
| link_source / link_sink | 線の試験用。意味を足す理由が無い |
| confirm の前の 64 byte | 交渉の前の約束。小さいほど安全 |
| probe.config の項目のキー（slot u8、port u8、fn u16、channel u16） | 1 台の probe の中の数。u8 で足りる（スロット 255、口 255） |

---

## 5. 影響と進め方

- **形が変わるもの**（spec → fake → probe → client の順で一度に）: read 系の応答（3.1b）、データフレーム（3.1c）、confirm（3.1d）、
  dmi / transfer の応答、gpio read、marks の time、heartbeat、probe.config の state op と unset、slot の mechanism、uart 項目、
  attach（3.8b を選べば）、capture の status / segments / read / trigger、i2c / spi の closed_tail、registry の enum 追加。
- **意味だけ変わるもの**（文書と実装の規則）: 期限切れ後の再開、資源番号、block op の自己完結、ストリームの寿命、断り方の順、scan、
  reset 線、SWD、state 5 の復帰、write_pos。
- **追随**: oep-client-python（fake を含む）、oep-probe-arduino、oep-client-js、ch32rv、WireSkein（read / status / segments の形）、
  bench（prepare.py の describe / state の読み分け）。
- **大きさの見積もり**: spec 2 日、fake + Python 1 日、probe 2 日、JS 1 日、peer の追随 1〜2 日。前回の 13 項目と同じ規模の 2 倍程度。
- **順序**: ★ を決める → core の 3.1〜3.6 を先に書く（ほかの文書がこれに依る）→ インターフェースの文書 → registry → 生成 → fake →
  probe → client → peer に通知。

---

## 5.1 peer の意見（届いたもの）

- **bench（ArduinoCore-CH32RV tests/bench、2026-10-01）**: 見直し 1（read 系に長さ）と 2（block op の自己完結）はどちらも推奨案に賛成。
  2 は「テストが途中で例外を投げ、hart が止まったまま connection が閉じると target が壊れたまま次のテストに渡る」のが一番困る点で、
  op の外に状態を持ち越さない案ならこの事故が起きない。コスト（DMI 数回）は問題なし、reg_probe の秒数で前後を測って返す。
  1 は client の返り値の形（gpio.read、read_rx の (pending, data)、uart の read、capture の read）が保たれればベンチの変更は不要。
  変わるならリリースノートに書くこと。

## 6. 決めてもらうこと（★）

| # | 項目 | 推奨 | 選ばない場合 |
|---|---|---|---|
| 1 | TLV の len に 0xFF → u16 の逃げ道（3.1a） | 入れる | 255 を超える値は繰り返しで連結、tag ごとに定義 |
| 2 | read 系 / データフレーム / dmi の応答に長さを置く（3.1b, c） | 置く | 今のまま。registry の closed_tail を揃えるだけ |
| 3 | 期限切れ後の再開を rejected `expired` にする（3.2a） | する | 再開を許し、open の応答に印だけ |
| 4 | describe から状態を出して state op に（3.4a） | 出す | 今のまま。「状態の TLV は宣言の後ろ」と順序だけ決める |
| 5 | block op の自己完結（3.8a） | する | 今の probe の動きを規範に書く |
| 6 | attach の一本化（3.8b） | する | attach_under_reset に flags を足すだけ |
| 7 | iProduct `OEP` を恒久の規範に、interface の subclass / protocol を固定（3.4d） | する | 1209:4F45 取得後に core を書き換える今の計画 |
| 8 | 時刻を ns（u64）の一本に（3.5） | する | mark の後ろに time_ns を足すだけ（ms も残る） |
| 9 | capture の read に generation を要求する（3.10a） | する | status に generation を足すだけ（read は黙って返す） |

ほかの項目（3.3、3.6、3.7、3.9、3.10b〜h、3.11）は案のとおりで進めてよいか、まとめて可否をもらう。
