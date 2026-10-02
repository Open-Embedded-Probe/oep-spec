# v1 のゼロベース再検討と仕様案（2026-10-01）

状態: **記録**（規範ではない。採用して規範に反映済み、2026-10-01。★ 9 つはすべて推奨案。§3 と §7 を core、common、debug、console、capture、fixture、probe-config、registry に入れた）。[凍結前の全面見直し](v1-freeze-review-2026-10-01.ja.md)（59 項目）を受けて、「あるべき姿」を今の文書に縛られずに
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

**(e) 1 要求の最長時間**（見直し 26）: fn 0 の describe に `max_op_ms(u32)` を足し、「probe は 1 つの要求にこれ以上かけず、超えうる op
（run、dmi の wait の和、capture の start、save、attach の hold_ms）は引数の和がこれを超えれば rejected unsupported。処理中は lease を
数えない」。値は probe が決める（規範に既定は置かない）。参照の firmware は 10000 ms（ch32rv の RAM loader は run を 2500 ms で呼ぶ。page erase と
書き込みの長さは chip 次第なので余裕を持つ）。host は describe の値を読んで timeout を詰める。

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
- **(d) iProduct `OEP` 接頭を恒久の規範に**（2026-10-02 に置き換え: [core §3.3](oep-core.ja.md)。iProduct と interface の文字列は見分けに使わない。暫定の手がかりは host 開発ガイド §1.7）。vendor bulk は class 0xFF かつ `bInterfaceSubClass = 0x4F ('O'), bInterfaceProtocol = 0x45 ('E')`、
  HID は usage page 0xFF4F / usage 0x45 に固定（見直し 16）。プロジェクトの VID:PID は参照 firmware の値として usb-identity に置き、取得後に core を
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
- **§7 の点検で増えた分**: 出来事の TLV 化、unsupported の payload、state のページング、uart の status、attach の細目、scan の TLV、run の nvals、
  generation の 3 か所、registry の `[usb]` / `[limits]`。形の変更は 1.5 倍ほどに増える。
- **大きさの見積もり**: spec 3 日、fake + Python 1.5 日、probe 3 日、JS 1 日、peer の追随 2 日。前回の 13 項目の 3 倍程度。
- **順序**: ★ を決める → core の 3.1〜3.6 を先に書く（ほかの文書がこれに依る）→ インターフェースの文書 → registry → 生成 → fake →
  probe → client → peer に通知。

---

## 5.1 peer の意見（届いたもの）

- **bench（ArduinoCore-CH32RV tests/bench、2026-10-01）**: 見直し 1（read 系に長さ）と 2（block op の自己完結）はどちらも推奨案に賛成。
  2 は「テストが途中で例外を投げ、hart が止まったまま connection が閉じると target が壊れたまま次のテストに渡る」のが一番困る点で、
  op の外に状態を持ち越さない案ならこの事故が起きない。コスト（DMI 数回）は問題なし、reg_probe の秒数で前後を測って返す。
  1 は client の返り値の形（gpio.read、read_rx の (pending, data)、uart の read、capture の read）が保たれればベンチの変更は不要。
  変わるならリリースノートに書くこと。
- **bench（同日、★ 3 / 5 / 8 / 9 と残り）**: 4 つとも推奨案で困らない。反対の点なし。条件:
  - ★ 3: ベンチは test ごとに 1 セッションで、keepalive は使うたびにしか送らず、60 s 黙る test では今でも lease が切れうる。
    expired で断られれば失敗の場所と理由が一致する（今は plan や connection が外れたまま通り、UART 無音や capture 空に化ける）。
    **client は expired を専用の例外（`Expired`、lease の長さ入り）にし、黙って open し直して続けない**こと。
  - ★ 5: ベンチは baud を毎回 OEP の configure で設定し、CDC の line coding には頼っていない。**ピンの無い fn の configure は今どおり
    unavailable で断る**こと（「configure を受けた最初の uart = ピンのある口」の見分けが依存）。baud ±5% 超で unsupported にも賛成。
  - ★ 9: **generation は client の LogicCapture が start / status で覚えて read に付け、`read_segment(segment)` の呼び方は据え置く**。
  - 3.8b（attach の一本化）はベンチが attach_under_reset を使っていないので影響なし。

## 6. 決めてもらうこと（★）

| # | 項目 | 推奨 | 選ばない場合 |
|---|---|---|---|
| 1 | TLV の len に 0xFF → u16 の逃げ道（3.1a） | 入れる | 255 を超える値は繰り返しで連結、tag ごとに定義 |
| 2 | read 系 / データフレーム / dmi の応答に長さを置く（3.1b, c） | 置く | 今のまま。registry の closed_tail を揃えるだけ |
| 3 | 期限切れ後の再開を rejected `expired` にする（3.2a） | する | 再開を許し、open の応答に印だけ |
| 4 | describe から状態を出して state op に（3.4a） | 出す | 今のまま。「状態の TLV は宣言の後ろ」と順序だけ決める |
| 5 | block op の自己完結（3.8a） | する | 今の probe の動きを規範に書く |
| 6 | attach の一本化（3.8b） | する | attach_under_reset に flags を足すだけ |
| 7 | iProduct `OEP` を恒久の規範に、interface の subclass / protocol を固定（3.4d）（2026-10-02 に置き換え: [core §3.3](oep-core.ja.md)。iProduct と interface の文字列は見分けに使わない。暫定の手がかりは host 開発ガイド §1.7） | する | プロジェクトの VID:PID の取得後に core を書き換える今の計画 |
| 8 | 時刻を ns（u64）の一本に（3.5） | する | mark の後ろに time_ns を足すだけ（ms も残る） |
| 9 | capture の read に generation を要求する（3.10a） | する | status に generation を足すだけ（read は黙って返す） |

ほかの項目（3.3、3.6、3.7、3.9、3.10b〜h、3.11）は案のとおりで進めてよいか、まとめて可否をもらう。

---

- **WireSkein（2026-10-01、採用後）**: 困る点なし。w = 64 / 128 は「little endian、チャンネル k がビット k」で受ける実装を済ませた（規範と同じ）。
  vrefint の `nominal_mv` は client の `Calibration.vrefint_nominal_mv` で取れるようにする。`Expired` は `Rejected`（→ `OepError`）の下に置く。
  generation は `LogicCapture.generation` で読めるようにする（ファイルの meta 用）。scale の「ピンの電圧への 1 次式」は WireSkein の仕様と同じ意味。
- **ch32rv（同日）**: dmi の応答の形と attach の一本化は困らない。max_op_ms の既定 2000 では RAM loader の run（2500 ms）が通らない →
  規範に既定を置かず参照 firmware は 10000 ms に（3.1e を直した）。halt で haltreq を下ろす規則は L103 の DMI link の件で危ない →
  「止まっている間は保ってよい」に直した（7.3-31）。ch32rv 側で直すもの: resume の前に raw で dpc を読むのをやめる（失敗時だけ）、raw を
  使ったら DATA0 / DATA1 を戻す、attach に max_speed を必ず付ける。ブローカーは expired を受けたら open からやり直し、client の connection を
  失ったものとして返す。規範と fake ができたら fake で試験を通してから実装を確定。

---

## 7. 方針を当てた漏れの点検（2026-10-01、ユーザーの採用後）

採用した 8 原則と §3 の案を、規範の文書の **すべての op、TLV、出来事、describe、項目、ビット**に機械的に当てて、§3 に書かれていなかった
漏れを 3 系統（core / config、debug / console、capture / fixture）で点検した。見つかった 79 件を、原則に従って決めた形で以下に書く。
判断が分かれうるものだけ ★ を付けた（ほかは原則からの帰結）。§3 の案と番号がぶつかった所も直した。

### 7.1 本体と共通部品

1. **出来事の payload も「固定部 + TLV」**（データフレームと同じ）。core §2.3 の「後ろに足す」の列挙から出来事を外し、§11.2 に
   `kind(u8), 固定部, [TLV]`。ハートビートは `boot_id(u32), uptime_ns(u64), [TLV]`。
2. **TLV の長い形の符号化は一意**: `len ≤ 254` は短い形、`255 以上` は長い形（`tag, 0xFF, len(u16)`）。別の形は malformed。probe.config の
   正規形もこの符号化。並びの要素の `len(u8)` には逃げ道は無い（要素は 255 byte 以内）。
3. **rejected unsupported の payload は常に `tag(u8), [TLV]`**、`0x00` = 固定部の値（tag 0x00 は TLV に使わないと §2.2 に明記）。固定部の
   どの要素かを返したいとき（gpio set の mode など）は TLV `channel` / `index` を後ろに（unavailable と同じ tag の空間）。
4. **断り方の順を全段で**（3.6 は payload の中だけだった）: 見出し（unknown_function → unknown_operation → session_required）→ 送り直し
   （§5.2: corr_reused / result_lost）→ セッション（no_session / expired / locked）→ window_exceeded → malformed → unsupported → unavailable →
   no_connection。payload で指す fn（describe、subscribe、plan、設定の項目）が無いときは unknown_function を流用。
5. **plan_apply の理由の表**: 形の誤り・同じ (fn, role, channel) の重複・fn 0 → malformed。role / channel が宣言に無い・channel_group に不一致 →
   unsupported（tag 0x90）。plan_roles 超え・取り合い・設定の plan → unavailable（cause 2 / 1 / 5）。fn が無い → unknown_function。
6. **plan 項目のキーは (fn, role, channel)**（gpio は 1 role に複数 channel）。正規形はその昇順。
7. **subscribe**: fn 0 の subscribe / unsubscribe は必ず実装。送り出さない fn への subscribe は rejected unsupported。購読の無い fn の
   unsubscribe は ok。mode 3（ストリーミング）を宣言する capture は features bit2 を立てる。
8. **値の幅**: `max_delay_ms` → u32、slot の `retry_s` → `retry_ms(u32)`、`bind_modes` → u32、`plan_roles` → u32。
9. **fn 0 describe の `label`（0x46）は firmware が持つ固定のラベルだけ**（★）。設定の label 項目は probe.config の get で読む（host は両方を
   合わせる）。describe を set で変えないため（原則 5）。freeze-decisions 12 の「core の describe に出す」を直す。
10. **describe の TLV の値（bitmap、text、組の並び）は閉じたまま**、足すときは新しい tag — §4 の表に載せる。ただし `channel_group` は
    `group, n(u8), n × (role, channel)` に、capture の `rate_list` / `tracks` / `budget` に `n(u8)`、calibration の `factory` に `raw_len(u16)` を置く。
11. **describe の tag 0x3F と probe.config の項目 tag 0x7E を「応答のメタ情報」のために予約**（宣言の空間とぶつけない）。
12. **`oep_pid`（0x4A）→ `discoverable`** に改名、意味は 3.4d の条件（iProduct `OEP` 接頭 + 固定の subclass / protocol で列挙している）（2026-10-02 に置き換え: [core §3.3](oep-core.ja.md)。iProduct と interface の文字列は見分けに使わない。暫定の手がかりは host 開発ガイド §1.7）。
13. **`max_op_ms` は fn 0 describe の tag 0x4D**。save もこれに従い、`max_save_ms` は describe から外す。attach の reset TLV の `hold_ms` も
    対象に入れる。1 要求を実行中も、**ほかの connection のコンソールの読みは続ける**（同じ connection は止める）。
14. **boot_id は 32 bit の乱数でよい**（同じ値になる確率は host が受け入れる）。**保存の無い probe は unit_id を firmware のビルド定数で
    持ってよい**（同じ firmware の個体を区別できないことを受け入れる）。
15. **資源番号の一周の残りの穴を明記**: 一周の後は古い番号が別の資源を指しうる。host は no_connection を受けた番号を捨て、長く持つ番号は
    connections / streams で確かめる。
16. **セッションの状態機械を 1 つの表に**: 行 = open(新 ID) / open(同 ID、保持中) / open(同 ID、end 後) / open(同 ID、期限切れ後 = expired) /
    open(force) / end / 期限切れ / 再起動 / 経路替え、列 = ロック / lease / 資源 / 購読 / §5.2 の表。決める升: 保持中の同 ID open は購読を残し
    通知の送り先をその経路に替える、§5.2 の表は open だけで捨てる（期限切れ後の送り直しは表の判定が expired より先）、end 後の再開の lease は
    前の open の値、2 経路から 0x81 を送った host の誤判定は host の責任。
17. **共通部品 §1 の「使うもの」から logic / analog を外す**。capture は「位置と区画と世代を持つ別の形」（from / マーク無し）。§1.5 は削り
    core §11.2（3.1c）を指す。
18. **`oep.fixture.uart` の位置とマークの serial は probe の起動の中では戻らない**（plan を解いて再び作っても続きから）（★。世代番号を置く
    代わり。実装が軽く、bind の口の位置も同じ規則）。uart にロック不要の `status`（0x07: `configured(u8), baud(u32), format(u8), [TLV]`）を足す。
19. **ストリームが閉じた理由のマーク** kind 0x09 `closed`、detail: 1 全員が外れた、2 lease 切れ / force、3 slot の置き換え・削除、4 connection
    が閉じた。`mark_detail_reset` の 3 は「attach の reset TLV（NRST）」、method 0（probe が選ぶ）は実際に使った方法を detail に。
20. **同じ場所・同じ mechanism の console open は、閉じたストリームを同じ番号で再び開く**（位置・マークは続き、mark attach、flags bit0）。
    別 mechanism の open で古い方は消える。arm-adi の connection への console open は unavailable cause 6（3.3 に揃える）。

### 7.2 `oep.probe.config`

21. **op 番号**: `unset` = 0x05、`state` = 0x06（3.4a と 3.7a が同じ 0x05 だった）。describe の 0x44 / 0x45 は reserved に。
22. **`state` のページング**: 要求 `first_slot(u8), first_bind(u8)`、応答 `more(u8), storage_state, storage_hash, unreadable_reason, n_slots × (len, slot_state),
    n_binds × (len, bind_state), [TLV]`。
23. **`unset` の規則**: 検証と原子性は set と同じ、応答は hash、無いキーは何もせず ok、結果が §1 を満たさなければ何も変えず malformed、消した
    slot / bind には 3.7f を適用。要求の並びに `len(u8)` を置くのは「tag ごとにキーの長さが違う」ための例外として §4 に載せる。
24. **`uart` 項目の関係**: その fn の plan に RX か TX が付いた時点（設定・セッションを問わず）で configure 相当を掛ける。plan が無くても set は
    通る。セッションの configure は、plan を解くか再起動するまで項目より勝つ。保存の読み替えの対象に uart の fn を足す。baud は set のときに
    actual を確かめ、±5% 超は unsupported。**ピンの無い fn の configure は今どおり unavailable**（bench の条件）。
25. **理由の表**（§2 の末尾に 1 つ）: その線が許さないピンの組 → unsupported、同じ wire_fn と同じピンのスロットが 2 つ・bind が無いスロットを
    指す → malformed（設定どうしの矛盾）、idle_clock 1 を rvswd 以外 → unsupported（attach と揃える）、port がシリアルの口でない → unsupported、
    bind kind 2 の fn が uart でない → unknown_function、保存なし（max_bytes 0）の save / erase → unsupported、erase 後は状態 0・hash 0。
26. **slot_state の `last_try_ns` は時刻**: `last_try_at_ns(u64)` = 試した時点の uptime、全ビット 1 = 試していない。
27. **at boot のスロットの生存確認**: probe は retry_ms ごとに DMSTATUS を読んで確かめてよい（書かない）。線切れを見たら接続を閉じて retry に入る
    （mechanism 0xFF のスロットでも「いない」が分かる）。
28. **slot の `max_speed` → `max_speed_hz`**（registry 名）。probe-config §1.2 の「CDC は bInterfaceProtocol 0」は開発ガイドへ。

### 7.3 線とデバッグ、コンソール

29. **run の応答に `nvals(u8)`**: `status, stopped, dpc, elapsed_us, nvals, nvals × value(u32), [TLV]`。stopped = 2 / status ≠ ok では nvals = 0。
30. **done / status を持たない op（scan、attach、detach）の failed は `status(u8), [TLV]`**。core §2.3 に「応答の固定部は (op, resolution, outcome)
    ごとに op が定める形」と一言（★。attach / scan の先頭に status を置いて形を 1 つにする案もあるが、成功の形を汚さない方を取る）。
31. **op の境界の表**（3.8a の一文表、debug §4 冒頭）: halt = allhalted を見る。**止まっている間 haltreq を保ってよい**（L103 は hart の状態が
    変わると DMI の link が落ち、halt 直後の読みが前の値になるため、参照の firmware は保つ）。resume / step / reset / detach と connection を
    閉じるときは下ろす。resume = haltreq 0 / resumereq 1 を 1 回、何も覚えず戻さない。step = dcsr.step と DATA を戻して返す。reset = 終わったら haltreq を下ろし havereset を確認応答。read / write_block = GPR、
    DATA1 / DATA0、abstractauto を戻す。run = pc / GPR / dcsr は host の指示どおり変えたまま（host の責任）、abstractauto と haltreq は戻す。
    dmi = probe は何も触らず何も戻さない（host が DATA を使ったら host が戻す）。どの op も hartsel は 0 にして返す。console = hart が止まって
    いる間 DATA0 に触れない。待ちは目安 100 ms。
32. **attach の一本化の細目**: 3 線とも `method(u8), [TLV]`（swd は method 1 を unsupported）。TLV 0x05 `reset`（critical: `channel(u16), hold_ms(u16)`）。
    reset + method 1 = 旧 attach_under_reset、reset + method 0 = NRST を hold_ms 保って離し走ったまま attach。既存 connection への reset TLV は
    reset op の NRST 相当として扱い mark reset。応答 `connection, id(u32), flags(u8), speed_hz(u32), [TLV 0x11 dpc]`。**flags は 3 線共通の
    `attach_flags`**: bit0 havereset_acked、bit1 existing、bit2 dormant_woken、bit3 halted（dpc TLV が有効）。失敗の status: 止まらない / 走らない =
    timeout、DM が応えない = line、cmderr = fault。
33. **scan にも TLV `max_speed`（critical）と `idle_clock`（rvswd、critical）**。無ければ probe の最も遅い速さ / high で試す。
34. **`max_speed < min_clock_hz` は unsupported（tag 0x01）**、3 線共通。
35. **connection と hart の状態機械の表**（debug §2）: lease 切れ / force = セッションの分を外し hart は触らない（止まっていれば止まったまま。
    host は attach(method 0) + resume で戻す）。end = 何も変えない。force detach = 線が落ちたときと同じ（at boot は retry、mark detach）。
    再起動 = 全部無くなる。2 セッション目 = §9 で資源が移り attach は flags bit1。bind のコンソールと host の open の重なり = 7.1-20。
36. **線切れ判定**: 要求の中で判定したら status line で返してから閉じる。**コンソールの読みの中で判定したら mark link-lost を付けて閉じる**。
    idle な connection は監視しない（at boot のスロットは 7.2-27）。
37. **havereset を見たら**（要求の中でもコンソールの読みの中でも）確認応答し、dmseq を未同期に戻し、mark restart（detail 1）。3.8i の「覚えた
    値を捨てる」は 3.8a では空なので消す。
38. **swd の connections entry の tid は `tid_scheme 2 = targetsel(u32)`**（同じピンで targetsel の違う connection を見分ける）。slot の錠には
    使わない（registry swd の `slot` ビットは `# always 0 in v1`）。
39. **arm-adi**: block は hart の状態を問わない、done は probe が送った語数、ack は線の順で bit0 が最初（OK=1, WAIT=2, FAULT=4、無応答 = status
    line）、req の上位 4 bit は 0 でなければ malformed、TAR は進めたまま SELECT / CSW は変えない。§6 末尾に「意図した非対称」の箇条書き。
40. **RV64 / 64 bit AP の伸ばし道を予約**: read_block / write_block の TLV 0x01 `address_hi(u32)` を reserved に。attach の dpc TLV は len で幅が
    分かるので 8 byte も許す。
41. **空の結果・端の値の表**（debug / console）: dmi n = 0・read_block count = 0 → success done 0、4 の倍数でない address → malformed、swio の
    scan で swclk ≠ 0xFFFF → malformed、使っていないセッションの detach → ok、閉じた stream の close → ok、max_reads / max_us = 0 → 1 回読む、
    run の timeout_ms = 0 → malformed、n_out の regno 重複 → 許す。
42. **命名**: `max_speed_hz`、dmi の `us` → `wait_us`、dmseq 文書の「host」→「probe」、「framing」→「mechanism」。**継続時間（timeout_ms、hold_ms、
    wait_us、elapsed_us、retry_ms）は今の単位のまま。u64 ns にするのは時計の値だけ**（3.5 の誤読を防ぐ）。
43. registry: `scan_kind`、riscv-dm `features` ビット、`attach_flags`、reset / read の flags、run の `stopped`、streams の `state`（0 open、1 closed）、
    attach の TLV 0x05 / 0x11、arm-adi `ack` ビット、mark kind 0x09、swd の `attach_answer` 節。

### 7.4 キャプチャと fixture

44. **ストリーミングのデータ payload に TLV `generation(u32)`、mode 3 では必ず付ける**（start の応答の後に前の世代の送り残しが届きうるため）。
45. **release の要求にも `generation(u32)`**（read と同じ。違えば unavailable cause 6）。**start の応答に `generation(u32)`** を固定部に
    （`blocking_ms, generation`）。group の start も各トラックの generation を +1 し、応答に `n × (fn, generation)` を TLV で。
46. **トラックの状態遷移表**（capture §3.2）: 行 = state 0〜6、列 = configure / start / stop / force / release / trigger / あふれ / 完了 /
    plan_release・lease 切れ。決める升: state 2 / 3 の configure・start → unavailable cause 6、stop を 1 / 4 / 5 / 6 で → ok 何もしない、force を
    2 以外で → ok 何もしない、4 / 5 / 6 からの configure なしの start → 可（世代 +1、区画は消える）、plan を解いたらデータも区画も消える（state 0、
    read は空）、plan 無しの configure / query → unavailable cause 6。
47. **state 6 の理由**: status の応答 TLV `error(u8)`（1 DMA / ペリフェラル、2 置き場、3 時計、0x40〜 固有）、stopped reason 3 の payload の後ろにも。
48. **group**: `start_ns` は取得（pretrigger のリングを含む）を始めた時刻、ずれの推定は即時トリガのときだけ、トリガ付きは trigger_ns と各トラックの
    trigger_index で合わせる。bind n = 0 は state 3 以外のときだけ。始めた後のトラックの失敗 → 組は state 6・stopped reason 3・ほかも止める。
    start 前の start_ns は全ビット 1。features は bit1 force、bit2 通知（query は無いので bit0 は 0）。`trigger_track` は critical。force は triggered
    を送り trigger_fn = 0。
49. **mode 3 の start は購読が無ければ unavailable cause 6**。取得中に購読が消えたら取り続け、送れない分は捨てる（position の飛び）。
50. **`blocking_ms > max_op_ms` になる構成は configure で unsupported**。blocking の間は lease を数えない。
51. **rate_limit は C ≤ channels のときの上限、rate_list は 1 TLV（繰り返せば和集合）**。release(serial) は serial **以下**を解放。state 5 から
    再開した最初の区画は flags bit0。
52. **アナログの b は 1〜31**（zero は i32 のまま、trigger value u32 で足りる）。
53. **チャンネル数の u8（C、max、rate_limit の channels、max_tracks）は role(u8) に縛られるので意図的に u8** — §4 の表に。**layout の候補の
    ビット集合は u32**。i2c / spi の `errors` は u32。
54. **i2c-target**: mode 1 で未 arm のときの controller の書き込みは ACK して捨て errors を数える、mode 3 で置き場が空のときの読み出しは 0xFF、
    mode 2 の長さ byte と本文は同じトランザクション（repeated start なし）、stretch は各 byte の ACK の後、`tx_slots` = preload_tx で置いて未読の
    置き場の数（mode 3、ほかは 0）。**spi-target**: length を超えた分は捨てる（bits は実際に来た数、data は length まで）。read_rx の応答 TLV に
    `ns(u64)`（受けた時刻、任意）を予約。列の深さは describe tag 0x40 `queue_depth`。
55. **gpio set は確かめで断る以外は失敗しない（success）**。扱えない mode は unsupported + TLV channel / index（7.1-3）。
56. **理由の揃え**: i2c / spi の `length` が max_length 超 → unsupported（0 は malformed）、group bind の同じ fn の重複 → malformed、宣言に無い fn →
    unsupported、configure していない・モード不揃い・budget 超え → unavailable。
57. **空の結果・端の値**（fixture / capture）: 未割り当て channel の gpio read → unavailable(channel)、read の max = 0 → 空の成功、非リピートでの
    release → ok、未束ねの bind n = 0 → ok、state 0 の i2c / spi reset → unavailable cause 6、plan 前の query → unavailable cause 6、count = 0 の
    write / preload_tx → malformed、segments の from_serial が serial_done より先 → 空の成功。
58. registry: 各 capture / fixture の `features` ビットを enum に、uart `format` のビット、i2c / spi describe `queue_depth`、capture-group の state /
    stopped_reason、unavailable_payload に断った fn を返す tag、logic の `stopped_reason.no_free_segment` に「送らない（予約）」の注記、logic から
    analog 専用 tag を外す。

### 7.5 文書と registry の整理（書き直しのときに一緒に）

- 見直し 51〜59、本点検の 7.1-10 / 12、7.2-28、7.3-42 / 43、7.4-58 を、該当する文書を書き直すときに直す。形を変えないので凍結の後でも
  直せるが、registry の名前（生成コードに出る）は凍結前に。
- 開発ガイドの追随: host ガイド §3（boot_id は confirm から、ロック無しの Monitor の動線）、§4（max_op_ms）、§2.5（expired の扱い: 専用の例外、
  黙って open し直さない）、§5（uart の位置の規則）。probe ガイド §3.8（iProduct / subclass / protocol / HID usage）、§3.9（max_op_ms と lease）、
  boot_id の作り方。usb-identity §3 / §4 を「計画をやめた」形に書き替える。
- registry に `[usb]`（subclass 0x4F、protocol 0x45、HID usage page 0xFF4F / usage 0x45、参照 firmware の VID:PID）と `[limits]`（lease 1000〜60000、
  owner / unit_id / slot name 1〜32、インターフェース名 1〜64、max_op_ms 既定 2000、min_max_frame 64）を置き、生成コードで検査できるようにする。

### 7.6 ★ 判断の記録（原則だけでは決まらなかったもの）

| # | 決めたこと | 理由 | 別の案 |
|---|---|---|---|
| 7.1-9 | core の describe `label` は firmware の固定ラベルだけ、設定の label は get で読む | describe を set で変えない（原則 5）。host は 2 か所を合わせる手間 | describe に残し「label は例外」と書く |
| 7.1-18 | uart の位置は起動の中で戻らない（世代番号を置かない） | 実装が軽く bind の口にも同じ規則が効く。console は番号で見分けるので不要 | read の応答 TLV に generation |
| 7.3-30 | failed の形は `status, [TLV]`、固定部は (op, resolution, outcome) ごと | 成功の形を汚さない | attach / scan の先頭に status を置き形を 1 つに |
| 7.3-38 | swd の tid は scheme 2 = targetsel | 同じピンの connection を見分けるのに最小 | entry の後ろに targetsel を足す |
| 7.4-44 | mode 3 のデータに generation TLV を必須に | 「start の応答前に送り残しを捨てる」だけでは経路の遅れで守れない | 不変条件だけ書く |
