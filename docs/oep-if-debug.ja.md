# OEP 標準インターフェース: 線とデバッグ v1

[English](oep-if-debug.md)

状態: **規範**（2026-09-26。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md)を反映）。本体は [OEP core](oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§2 debug の
connection、§3 status）。番号の唯一の定義は `registry/oep-v1.toml`。名前の置き方の理由は
[能力の名前の階層](capability-name-hierarchy.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.wire.rvswd` | 1 | 2 線の RVSWD で RISC-V の DM につなぐ |
| `oep.wire.swio` | 1 | 1 線の SWIO で RISC-V の DM につなぐ |
| `oep.wire.swd` | 1 | ARM の SWD で ADI につなぐ |
| `oep.target.riscv-dm` | 1 | RISC-V Debug Module の操作 |
| `oep.target.arm-adi` | 1 | ARM ADI（DP / AP）の操作 |

（参考）RVSWD と SWIO は、WCH の RISC-V の MCU が持つ 2 線と 1 線のデバッグの線である。target_id の scheme 1 の registry の名前 `wch_dmi_7f` も、WCH のデバッグモジュールから来ている。

- `oep.wire.*` は connection を作り、`oep.target.*` は connection の上で target を操作する。target を扱うインターフェースは
  attach の前から list に出し、connection の無い要求は rejected no_connection。
- **target の系統（チップの型）は宣言しない。** チップごとの知識（flash の書き方、DM の癖）は host が持つ。
- connections のほかの op はすべてロックが要る。

## 1. attach の規範（全 wire）

- probe は、線の速さを確かめ終えるまで target に書き込まない（読むだけで速さを選ぶ）。速さの合わない書き込みは、化けた値を
  target のレジスタに書きうる。
- **ピンの組**:
  - probe が使える組は describe の共通タグ（core §7.4）で宣言する。決まった組は channel_group、どのピンにも割り当てられる
    なら role_channels。役の番号は `pin_role`（1 = SWDIO、2 = SWCLK、3 = reset）。
  - scan の要求は試す組の並び。**count = 0 は probe が許すすべての組**。応答の組は、そのまま attach の pins に渡せる。
  - role_channels で宣言した線では、許す組は「role 1 の候補 × role 2 の候補（1 本の線は role 1 だけ）で、同じ channel を 2 度
    使わないもの」。count = 0 の並びは swdio の昇順、その中で swclk の昇順とし、**今ほかのもの（plan、ほかの線の接続、設定の
    資源）が持っている channel を含む組は並べない**（count = 0 は動かしてよい組だけを試す）。組を並べた要求に、持たれている
    channel があれば、§8.1 のとおり全体を rejected unavailable。
  - **idle の項目がある channel**: count = 0 の並びと、pins の無い attach の候補からは、ほかのものが持つ channel と無効にした channel に加えて、
    probe の設定に **idle の項目**がある channel（mode を問わない、[probe の設定](oep-if-probe-config.ja.md) §1）をすべて外す。
    そういう channel を明示した要求（組を並べた scan、attach の pins）は、idle が入力（mode 0〜2）なら受ける。
    idle が出力（mode 3 / 4）なら rejected unavailable（cause 5、その channel、holder_kind 7 = 設定の idle）。
  - （参考）count = 0 は空いている候補のピンを順に全部動かす。利用者の同意なしに、host は配線を知らない治具へ count = 0 を送らない。
  - 線は、生きている接続が使っている組の channel を持つ（接続が無くなれば放す）。持っている間、その channel を plan や設定が
    取ろうとすれば rejected unavailable（core §8.1）。
  - scan の応答の `tried` は、要求の並び（count = 0 なら上の count = 0 の並び。channel_group の線では describe に出した順）の
    先頭から試し終えた組の数。1 回に試すのは多くても 255 組（tried は u8）。見つかった組で応答が 1 フレームに入らなくなりそう
    なら、probe はそこで止める。**scan の予算（下）で次の組を始められないときも、probe はそこで止める**
    （少なくとも 1 組は試す）。tried ≥ 1 なら、host は続きを送る。組を並べた要求で tried が並びの数より少なければ、host は残りの組でもう一度 scan を送る。
  - **count = 0 の続き**: count = 0 の要求は TLV skip（0x01、u16）で、count = 0 の並びの先頭から飛ばす数を渡せる（無ければ 0）。
    host は skip に今までの tried の和を渡して続け、**tried = 0 が返ったら終わり**。**並びに組が残っていれば、probe は少なくとも 1 組は
    試す**（tried ≥ 1。tried = 0 は並びを使い切ったときだけ）。並びは要求のときの持たれ方で決まるので、
    途中で plan などが変われば、組が抜けたり重なったりしうる（host は scan の間ほかを変えない）。count > 0 に skip を付けた
    要求は rejected malformed。
  - attach は pins（TLV 0x03、critical）で組を指定する。pins が無ければ、その線の生きている接続が 1 つ
    だけならその組（既存の接続に乗る。スロットが持っている接続でもよい）、生きている接続が無く許す組が 1 つだけならその組、
    それ以外（生きている接続が 2 つ以上、または接続が無く許す組が 2 つ以上）は rejected unavailable（host が選ぶ）。
  - **許していない組は、何も実行せずに rejected unavailable**（scan は要求の中に 1 つでもあれば全体を断る）。
- **attach の予算**: 1 つの attach の応答に probe が掛ける時間は多くても 1000 ms（registry `limits.attach_budget_ms`）で、速さの探索とその再試行を含み、
  reset TLV の hold_ms は含まない。その間にどの速さも使えなければ、応答は status line の completed failed。
- **scan の予算**: probe は、scan の要求が届いてから 500 ms（`limits.scan_budget_ms`）より後に組を始めない（少なくとも 1 組は試す）。
  1 組の試しは attach の予算で抑える。したがって 1 つの scan の応答は多くても `scan_budget_ms` + `attach_budget_ms` かかる。
- どちらの予算も max_op_ms で頭打ちにする。host の待ちは、これらを引数の時間として数える（core §4.4）。
- **同時に持てる接続の数**: wire のインターフェースは describe の max_connections（tag 0x40、u8）で宣言する。宣言が無ければ 1。
  ロックは probe に 1 つのまま（接続ごとのロックは無い）。
- **scan と生きている接続**: 生きている接続の組は、scan で線を初めからやり直さず、その接続で読んだ値（DMSTATUS など）で見つかった
  組として返す（動いている接続を scan で壊さない）。
- **席が埋まっているときの scan**: max_connections の接続が生きている間、scan で試せるのは生きている接続の組だけである（ほかの組を
  試すには、線をその接続から離すことになる）。ほかの組を並べた要求は、何も実行せずに rejected unavailable。count = 0 の並びは
  生きている接続の組だけになる。
- **席の規則**: 生きている接続と違う組への attach は、席が空いていれば新しい connection を作る。席が埋まっていれば、使っているものが
  スロットだけ（host のセッションが使っていない、[共通部品](oep-if-common.ja.md) §2）の接続のうち最も古く作られたものを閉じて席を
  空ける。そういう接続が無ければ rejected unavailable。閉じた接続に載っていたストリームは、接続を失ったときと同じく閉じる。
  違う wire のインターフェースどうしのピンの取り合いは core §8.1 のとおり断る。
- **すでに attach している線への attach は、その connection をそのまま返す**（flags bit1）。method = 1 なら、動いていれば
  止め、止まっていれば何もしない。method = 0 は動いている hart に触れない。既存の connection が max_speed より速ければ、
  probe はその connection の速さを max_speed 以下に下げて返す。下げられない probe は、扱えない TLV の値として扱う
  （core §2.3）。
- `speed_hz` は probe が選んだ線の速さ（1 ビットの周期の逆数の目安）。
- max_speed（TLV 0x01、u32 Hz）: probe はこれを超える速さを選ばない。**attach では必須**（無ければ rejected malformed）、critical で
  送る。probe の min_clock_hz より小さければ rejected unsupported（tag 0x01）。scan にも付けられる（無ければ probe の最も遅い速さで
  試す）。pins と idle_clock は任意で、送るときは critical。
- **scan が target に書くのは dmactive だけ**（DMSTATUS を読むため）。dmactive は立てたまま残す（§4.6 と同じ。下ろすと DATA0 の
  コンソールのフレームが消える）。「見つかった」は DMSTATUS.version が 2 か 3（swd は DPIDR が読めた）。外れた組のピンは core §8 の
  空きの状態に戻す。max_speed が無い scan は、probe が安全と考える遅い速さで試す（attach と同じ探索をしてよい。swd のように読んで
  選べない線は probe の決めた遅い固定値）。
- **target の識別子**: attach の応答の後ろに、probe が読めた target の識別子を TLV 0x10 target_id（scheme(u8)、値）で付けてよい。
  scheme は識別子の取り方で、wire ごとに registry が定める。probe は読めなかったとき（scheme が「無い」と定める値だったときを含む）
  は付けない。値の意味（どのビットが系統で、どれがリビジョンか）は host が知っている。probe は解釈しない。
- **search_retries**: どの wire の attach の応答にも TLV 0x12 search_retries（u16、任意）を付けてよい: speed_hz の速さを確かめるまでに
  失敗した速さの探索の試行の数（0 = 最初の試行で通った。0xFFFF = 65535 以上）。host はこれを記録して、切れかけの線を見てよい。

## 2. connection の寿命（全 wire）

[共通部品](oep-if-common.ja.md) §2 に加えて:

- **detach は、その host のセッションの分を外すだけ**。ほかに使っているものがあれば connection は閉じない。detach の TLV 0x01
  force（長さ 0、critical で送る）で、使っているものがあっても閉じる。
- **target の reset では connection を閉じない**。probe は、reset の後も同じ connection で使えるように保つ（wire ごとの手順は
  §4.6 など、target を扱うインターフェースの節）。
- **1 つの要求の中の再試行**: probe が 1 つの要求の中で線の再試行に使うのは多くても 200 ms（registry `limits.wire_retry_ms`）で、遅い速さでの
  再試行を含む。使い切ったら、その要求を status line で終える。それだけでは線切れと決めない。attach（と scan の 1 組）の速さの探索は、
  代わりに §1 の attach の予算で抑える。再試行の間の遅い速さは一時的で、connection の speed_hz は変えない。
- **線切れ**: 線が切れたとするのは、ある connection の操作が線からの応答無しで失敗し続けて（status line。要求の中でもコンソールの読みの中でも）
  **実時間で 1000 ms**（`limits.wire_lost_ms`）たち、その間にその connection で成功した操作が無いとき。probe が reset を出している時間、
  reset の線を保っている時間（plan、attach の reset TLV）と、それを解いてからの 1000 ms は数えない。probe が要求の中で線切れと決めたら、
  その要求に status line で答えてから connection を閉じる。
- **線切れの判定は、要求の中かコンソールの読みの中でだけ行う**（idle な connection は監視しない。at boot のスロットの生存確認は
  [probe の設定](oep-if-probe-config.ja.md) §3.1）。status line だけでは connection が閉じたことにならない: host は connections で確かめる。
  コンソールの読みの中で判定したら、mark link-lost を付けて閉じる。
- **probe は connection を閉じるとき、target の状態を必要以上に変えない**（target を reset しない。止めていた hart は、閉じる前の
  host の操作のままにする）。
- connection が閉じたら、その組の channel は core §8 の空きの状態になる（idle_clock の駆動もやめる）。

**connection と hart の状態機械**:

| 出来事 | connection | hart | ストリーム |
|---|---|---|---|
| detach | その host のセッションの分を外す。ほかに使うものが無ければ閉じる | 触らない | connection が閉じれば閉じる（mark closed 4） |
| detach(force) | 閉じる（線が落ちたときと同じ扱い。at boot のスロットは retry） | 触らない | 閉じる（mark detach、closed 4） |
| end | 何も変えない（資源は次のセッションに移る、core §9） | 触らない | 変えない |
| lease 切れ / force で奪われる | セッションの分を外す。スロットが使っていれば残る | **触らない**（止まっていれば止まったまま。host は attach(method 0) + resume で戻す） | セッションの分を外す（mark closed 2） |
| 線が切れた | 閉じる | — | 閉じる（mark link-lost、closed 4） |
| target の自己リセット（havereset） | 保つ（確認応答、§4.6） | target の状態 | 保つ（mark restart 1） |
| 2 つめのセッションの attach | 同じ connection に加わる（flags bit1） | method のとおり | 同じ (connection, mechanism) なら同じストリーム |
| probe の再起動 | 無くなる | DM は dmactive を残す | 無くなる |
- probe 自身の自動の attach（`oep.probe.config` のスロット）も使っているものの 1 つで、host の attach はその connection に加わる
  （flags bit1）。

### 2.1 connections（接続の一覧）

```text
要求: first(u8)
応答: more(u8)、count(u8)、count × (len(u8)、entry)、[TLV]（core §2.3）
entry: connection(u16)、swdio(u16)、swclk(u16)、speed_hz(u32)、users(u8)、slot(u8)、tid_scheme(u8)、tid_len(u8)、tid
```

- そのインターフェースの生きている接続を、作られた順に first 番目から 1 フレームに入る分だけ返す。more = 1 なら続きがあり、host は
  first に受け取った数を足してもう一度聞く。ロックなしで使える。
- users: bit0 host のセッションが使っている、bit1 スロットが使っている（自動の attach か bind のコンソール）。
- slot は、その接続がスロットの接続（`oep.probe.config` §1.1）ならスロットの番号、そうでなければ 0xFF。
- tid は attach のときに読めた target_id（無ければ tid_scheme 0、tid_len 0）。swd は tid_scheme 2 = targetsel(u32)（multidrop で無ければ
  0）で、同じピンの組で targetsel の違う connection を見分ける。DPIDR は attach の応答で返る。

## 3. `oep.wire.rvswd` / `oep.wire.swio`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (len(u8)、kind(u8)、swdio(u16)、swclk(u16)、id(u32))、[TLV] |
| 0x02 | attach | method(u8: 0 止めない / 1 止める。ほかは rejected malformed)、[TLV] | connection(u16)、id(u32)、flags(u8)、speed_hz(u32)、[TLV] |
| 0x03 | detach | connection(u16)、[TLV] | — |
| 0x04 | — | 予約（旧 attach_under_reset。attach の reset TLV になった） | |
| 0x05 | connections | first(u8) | §2.1（ロック不要） |

- swio の組は swclk = 0xFFFF（1 本の線。scan で swclk ≠ 0xFFFF は rejected malformed）。scan の kind は `scan_kind`: 1 = riscv-dm、
  2 = arm-adi。`id` は線の種類が決める生の識別子（riscv-dm は DMSTATUS、arm-adi は DPIDR）。
- **attach の flags**（3 線共通、registry の `attach_flags`）: bit0 保留中の havereset を確認応答した（riscv）、bit1 既存の connection、
  bit2 dormant から起こした（swd）、bit3 hart が止まっている（応答の TLV 0x11 dpc が有効）。
- **reset をかけながらの attach**: TLV 0x05 reset（critical: `channel(u16)、hold_ms(u16)`）を付けると、probe はリセットの線（channel）を
  hold_ms 保ってから離す。method 1 なら離しながら halt を打ち続け、できるだけ早く止める（flags bit3、dpc TLV）。**最初の命令の前で
  止まる保証は無い**（reset の線の解放から halt が効くまでに走った分がある。[リンクの計測](link-measurements.ja.md) §3）。reset の直後の位置で
  止める保証が要るときは、riscv-dm の reset mode 2（ndmreset を haltreq を保ったまま解く）を使う。method 0 なら走ったまま attach する。任意の機能で、持たない probe は rejected unsupported（tag 0x05）。既存の connection に reset TLV を付けた
  attach は、その target を reset してから同じ connection を返す（reset の op の NRST と同じ扱い: mark reset detail 3）。hold_ms は
  core の max_op_ms の対象。
- **reset の線に既定は無い**: どの線を reset に使うかは host が毎回 channel で明示する（線を取り違えた reset は target や治具を
  壊しうる）。probe が reset に使ってよい channel は describe の role_channels の role 3（reset）で宣言する。宣言していない
  channel は、何も実行せずに rejected unsupported（tag 0x05）。今ある plan や接続が持つ channel は、§8.1 の取り合いとして rejected
  unavailable。**reset の線はオープンドレインで low に引き、離すときは引くのをやめて core §8 の空きの状態にする**（外部の reset ボタンや
  ほかの driver と短絡しない）。channel は op の間だけ持つ。持たない probe では、host は `oep.fixture.gpio` の解放と attach をまとめて
  送って再試行する。

TLV:

| op | tag | 名前 | 値 |
|---|---:|---|---|
| scan | 0x01 | max_speed | u32 Hz（無ければ probe の最も遅い速さ） |
| scan（count = 0 だけ） | 0x02 | skip | u16。count = 0 の並びの先頭から飛ばす組の数 |
| scan（rvswd だけ） | 0x04 | idle_clock | u8。scan の間の休ませ方（下） |
| attach | 0x01 | max_speed | u32 Hz。**必須**、critical |
| attach | 0x03 | pins | swdio(u16)、swclk(u16)。critical |
| attach（rvswd だけ） | 0x04 | idle_clock | u8。線を休ませる間の SWCLK: 0 = high（無いときと同じ）、1 = low。critical。rvswd 以外に 1 を送れば rejected unsupported（tag 0x04） |
| attach | 0x05 | reset | channel(u16)、hold_ms(u16)。critical。上 |
| detach | 0x01 | force | 長さ 0。critical |
| attach の応答 | 0x10 | target_id | scheme(u8)、値 |
| attach の応答 | 0x11 | dpc | u32（RV64 は 8 byte）。hart が止まっている（flags bit3）ときの dpc |
| attach の応答 | 0x12 | search_retries | u16、任意。§1 |

target_id の scheme（`target_id_scheme`）: 1 = DMI のアドレス 0x7F を読んだ u32（長さ 4）。0 と 0xFFFFFFFF は「無い」（付けない）。
2 = swd の targetsel（u32、connections の entry だけに使う。錠には使わない）。scheme ごとの値の長さは registry に持つ
（スロットの錠の mask / value の長さの確かめに使う）。

- **線の設定は target の性質で、host が持つ**: 線の速さの上限（max_speed）と休ませ方（idle_clock）は、target（チップ）が
  求めるものである（SWCLK の休ませ方で debug の線が reset される target、reset 直後の遅いクロックで速さの上限が下がる target がある。
  [リンクの計測](link-measurements.ja.md) §3）。probe はそれを既定値として持たない。host が attach ごとに渡し、host 無しで attach する
  スロットは、スロットの項目に同じ値を持つ（[probe の設定](oep-if-probe-config.ja.md) §1.1）。scan でも同じ TLV を受ける（そういう
  target を scan で壊さず見つけるため）。
- 既存の connection への attach で idle_clock が今と違えば、probe はその connection の休ませ方を替えて返す。替えられない probe は、
  扱えない TLV の値として扱う（core §2.3）。

## 4. `oep.target.riscv-dm`

要求の先頭は connection(u16)。

- **必須の op は dmi、halt、resume**。reset、read_block / write_block、run、step は任意で、describe の features で宣言する
  （bit0 read_block / write_block、bit1 run、bit2 reset、bit3 step）。宣言していない op は unknown_operation。host は、任意の op が
  無くても dmi で同じことを組める。
- **dmi 以外の op（高水準の op）の範囲**: RV32 の hart 0 だけを扱う（番地、レジスタの値、pc は u32）。probe は高水準の op の中で
  DMCONTROL の hartsel を 0 にし、**0 にして返す**（host が dmi で選んだ hartsel は、その dmi の要求の中だけ）。ほかの hart と RV64 は、
  host が dmi で扱う（DMI の値が u32 なのは DMI の形で、RV32 に限る意味ではない）。RV64 の番地は、後から read_block / write_block の
  critical TLV 0x01 `address_hi(u32)` で足す（予約。registry の reserved）。

**op の境界の不変条件**: **probe は、op の応答を返したあと、target の状態を持ち越さない**。op の中で使ったものは応答の前に戻す。
host が raw の DMI（dmi の op）で何をしても、host が途中で死んでも（lease 切れ、force）、probe が戻し忘れるものは無い。

| op | probe が触るもの | 応答の前に |
|---|---|---|
| halt | haltreq | allhalted を見る。**止まっている間、haltreq を立てたままにしてよい**（保つか下ろすかは probe が決め、host から見える動作は同じ。保つ理由は [リンクの計測](link-measurements.ja.md) §3）。resume / step / reset / detach と connection を閉じるときに下ろす |
| resume | haltreq = 0、resumereq = 1 を 1 回 | 何も覚えず、何も戻さない |
| step | dcsr.step、DATA0 / DATA1（dcsr の読み書き） | dcsr.step を下ろし、DATA1、DATA0 を戻す |
| reset | haltreq、ndmreset、havereset の確認応答 | havereset を確認応答。mode 0 / 1 は haltreq を下ろす。mode 2 は止めたままで、halt と同じく haltreq を保ってよい。mode 1 の内部の halt は step と同じく戻す |
| read_block / write_block | GPR（s0、s1、a0、a1）、DATA1 / DATA0、abstractauto、program buffer、sysbus | GPR、DATA1、DATA0、abstractauto を戻す。program buffer と SBCS / SBADDRESS は戻さない（host が使うなら設定し直す） |
| run | pc、host が指定した GPR、dcsr（ebreakm、prv）、haltreq | **host の指示どおりに変えたまま返す**（host の責任）。abstractauto と haltreq は戻す |
| dmi | host が書いたもの | 何も触らず、何も戻さない（host が DATA を使ったら host が戻す） |
| console の読み（§4.6） | DATA0 / DATA1 | hart が止まっている間は読まない |

戻す値は、その op の中で読んだ「触る前の値」。高水準の op の中で DM の状態（abstractcs.busy の解除、allhalted、allresumeack）を待つ
上限は、1 つの待ちにつき 100 ms。過ぎたときの status は各 op の節のとおり（halt は timeout、resume / step は state）。DMI の busy は
probe の中で 100 回まで再試行し、使い切れば status wait（§6 の WAIT と同じ）。

| op | 名前 | 要求（connection の後ろ） | 応答 |
|---:|---|---|---|
| 0x01 | dmi | n(u16)、n 個の手順 | done(u16)、status(u8)、nvals(u16)、nvals × value(u32)、[TLV] |
| 0x02 | halt | — | status(u8)、[TLV] |
| 0x03 | resume | — | status(u8)、[TLV] |
| 0x04 | reset | mode(u8)、[TLV] | status(u8)、flags(u8)、attempts(u8)、pc(u32)（mode 2 では dpc）、[TLV] |
| 0x05 | read_block | address(u32)、count(u16)、[TLV] | done(u16)、status(u8)、done × word(u32)、[TLV] |
| 0x06 | write_block | address(u32)、count(u16)、count 個の語、[TLV] | done(u16)、status(u8)、[TLV] |
| 0x07 | run | pc(u32)、timeout_ms(u32)、n(u8)、n × (regno(u16)、value(u32))、n_out(u8)、n_out × regno(u16)、[TLV] | status(u8)、stopped(u8)、dpc(u32)、elapsed_us(u32)、nvals(u8)、nvals × value(u32)、[TLV] |
| 0x08 | step | — | status(u8)、moved(u8)、dpc_before(u32)、dpc_after(u32)、[TLV] |

空の結果と端の値: dmi の n = 0 と read_block / write_block の count = 0 は success、done 0。4 の倍数でない address は rejected
malformed。dmi の max_reads / max_us = 0 は 1 回読む。run の timeout_ms = 0 は rejected malformed。n_out に同じ regno が 2 回あれば
そのまま 2 回返す。止まっていない hart への write_block / read_block は status state。

### 4.1 dmi

| kind | 手順 | 引数 | 応答に足す値 |
|---:|---|---|---|
| 0x01 | 書く | address(u8)、value(u32) | — |
| 0x02 | 読む | address(u8) | 読んだ値(u32) |
| 0x03 | 読む回数を上限に待つ | address(u8)、mask(u32)、value(u32)、max_reads(u16) | 最後に読んだ値(u32) |
| 0x04 | 待ち | wait_us(u32) | — |
| 0x05 | 時間を上限に待つ | address(u8)、mask(u32)、value(u32)、max_us(u32) | 最後に読んだ値(u32) |

- kind 0x10〜0x1F は、番地を u32 にした同じ手順に予約する。知らない kind は長さが分からないので、要求全体を rejected
  malformed にする（probe は手順を全部確かめてから実行する）。
- **done は最後まで済んだ手順の数**（失敗したときは、失敗した手順の 0 起点の番号）。値を足すのは 0x02 / 0x03 / 0x05 だけ。
  `nvals` は応答に入っている値の数（最初の done 個の手順のうち値を足す手順の数に、失敗した手順が 0x03 / 0x05 で待ち切れた
  （status timeout）なら 1 を足したもの）。線の不良などで読めずに失敗した手順は値を足さない。
- 0x04 の手順の wait_us と 0x05 の手順の max_us の和は max_op_ms を超えてはならない（rejected unsupported）。0x03 の手順は時間ではなく回数で抑える。
  走っている間に要求が max_op_ms に達したら、probe はその手順で要求を終え、status timeout で答える（done = その手順の番号）。
- 1 つの要求は 1 つの hart の操作。タイミングと線の立て直しが要るもの（リセット、回復）は部品の op にする。
- **host は抽象コマンドの一連（data1 / data0 の書き込み、command、data0 の読み）を 1 つの dmi 要求に入れる**（probe が
  要求の間にコンソールの読みを挟んでも壊れない。`oep.target.console` §2）。

### 4.2 halt、resume、step

- **halt** は、すでに止まっていれば何もせず ok。allhalted を 100 ms 待ち、見えなければ status timeout。
- **resume** は haltreq = 0、resumereq = 1 を 1 回書く。ok は「hart が debug mode を出た」ことで、DMSTATUS の allresumeack（または
  allrunning で halted でない）で判断する。resumereq は出し直さない。100 ms 待っても見えなければ status state。
  - target によっては、これで足りない（allresumeack を立てない target がすぐ breakpoint で止まり直す、1 回の resumereq で出ない
    ことがある）。その扱い（dpc を読んで、動いていなければもう一度 resume する、など）は target を知っている host が行う。
- **DATA0 / DATA1 は target のもの**: hart が止まっている間に probe が abstract command（read_block など）で DATA0 / DATA1 を
  使うと、target がそこに出していた語（dmseq などのコンソールのフレームや答え）が消え、target は resume の後、自分の語が無いのを
  沈黙と読んでタイムアウトまで待つ（[リンクの計測](link-measurements.ja.md) §3）。だから、DATA0 / DATA1 を使う op はそれを**自分の応答の前に**戻す（§4 の
  表）。probe は op をまたいで何も覚えない。
- **step** は dcsr.step を立てて resume を 1 回だけ出し、戻ったら dcsr.step を下ろす。dpc が動かなくても失敗にしない（status ok、moved = 0。自分自身へ
  跳ぶ命令は正しく進んでも dpc が同じなので、host が命令を読んで判断する）。hart が 100 ms 以内に debug mode に戻らないときは status state。
  prv は変えない。

### 4.3 reset

| mode | 意味 |
|---:|---|
| 0 | 走らせる |
| 1 | 走らせて、実行を確認する |
| 2 | 最初の命令の前で止める（haltreq を保ったまま ndmreset を解く） |

応答:

| フィールド | 意味 |
|---|---|
| flags bit0 | 要求した mode の状態に達した（mode 0 / 1 は走っている、mode 2 は止まっている） |
| flags bit1 | pc を読んで実行を確かめた（mode 1 だけ） |
| flags bit2 | reset の手順をやり直した |
| flags bit3 | 確認のための halt / resume が失敗した |
| attempts | 行った reset の手順の回数（1 から） |
| pc | mode 1 で確かめた pc、mode 2 では dpc。ほかは 0 |

- outcome success の条件は、mode 0 と 2 では flags bit0、mode 1 では bit1。満たさなければ completed failed（形は同じ。status は
  止まらない / 走らない = timeout、DM が応えない = line、cmderr = fault）。ndmreset を解いてから hart が止まる / 走るのを待つ上限は
  1 回の手順につき 100 ms、手順のやり直し（flags bit2）は 1 回まで。
- flags のほかの bit は 0。reset の後は havereset を確認応答し、haltreq を下ろす（mode 2 は止めたまま）。

TLV 0x01 method（u8）: 0 probe が選ぶ、1 ndmreset。2 は予約（target のシステムリセットには共通の手順が無いので、host が dmi で
組む）。

### 4.4 run

- host のローダーを呼ぶためのもの。probe は dcsr の ebreakm と prv = M を立て、pc から走らせ、止まるのを待つ。**probe は run を
  出し直さない**（止まった位置が開始位置のままでも、走って戻った場合と区別できない）。走らなかったかどうかは host が dpc で
  判断し、ローダーを二度走らせてよいときだけやり直す。**デバッガの continue には使わない**（prv と ebreakm を変える）。
- timeout_ms は 1〜core の max_op_ms（0 は rejected malformed、超えれば rejected unsupported）。run の応答を返すまで、probe はこの
  connection のほかの要求に答えない（実行中は lease を数えない、core §6.1。ほかの connection のコンソールの読みは続ける）。
  止まったら stopped = 1（success）。上限に達したら probe は hart を止めてから dpc と値を読み、stopped = 0、status timeout、outcome
  failed で返す（dpc と値はすべて有効）。止められなければ stopped = 2、status timeout、outcome failed、nvals = 0（dpc は無効）。
  応答の形はいつも同じ（`run_stopped`: 0 時間切れで止めた、1 止まった、2 止められなかった）。
- regno は RISC-V の抽象レジスタ番号（a0 = 0x100A）。

### 4.5 read_block、write_block

- 語（32 bit）単位。8 / 16 bit のアクセスは dmi の手順で組む。
- **1 回の長さ**: read_block / write_block を持つ probe は、describe の共通 tag max_length（core §7.4）を必ず出す。単位は **byte 数**
  （4 の倍数）。probe は max_length を、read_block の応答（見出し 5 + done 2 + status 1 + 語）と write_block の要求（見出し 10 +
  connection 2 + address 4 + count 2 + 語）がどちらも自分の max_frame に収まる値で宣言する（max_frame − 24 以下。これより小さく宣言してよい）。host は count を
  max_length から決め、max_frame から計算しない。count × 4 が max_length を超えれば rejected unsupported（payload `0x00`）。count = 0 は
  success、done 0。4 の倍数でない address は rejected malformed。
- **読みの意味**: read_block は target のバスを通して読む。probe の側に写しを持たない（直前の write_block、dmi、run で target が
  書いたものを反映する）。保証するのは probe の側だけで、target 自身の cache や prefetch の像は範囲の外（host のチップの知識の側）。
- **前提**: hart が止まっていること（止まっていなければ status state）。番地は、止まっている hart が M モードで使う番地。
- **副作用**: probe は GPR、program buffer、DATA のレジスタ、sysbus を使ってよい。ただし **応答を返す前に、使った GPR、DATA1、
  DATA0、abstractauto を、使う前の値に戻す**（§4 の表）。host が何も保存しなくても、halt → read_block → resume で target の状態は
  変わらない。戻さないと、target は止まった場所によってはレジスタを壊されて走り続ける。resume の時に戻す方式は、間に host の raw DMI が
  入ると戻し損ねる（[リンクの計測](link-measurements.ja.md) §3）。program buffer と SBCS / SBADDRESS は戻さない（host が使うなら設定し直す）。
- run（§4.4）は host の指定したレジスタで host のローダーを走らせるもので、その間に変わった GPR、dcsr は戻さない（host の責任）。

### 4.6 RISC-V の connection の扱い

- attach は保留中の havereset を先に確認応答する（確認応答するまで DMSTATUS の halt / running を固定する DM がある。
  [リンクの計測](link-measurements.ja.md) §3）。
- target の reset（reset の op、attach の reset TLV）の後、probe は havereset を確認応答して、同じ connection を保つ。
- **havereset を見たら**（要求の中でも、コンソールの読みの中でも）確認応答し、コンソールの dmseq の状態を未同期に戻し、その connection
  のストリームに mark restart（detail 1）を付ける。
- **probe は connection を閉じるときもデバッグモジュールを reset しない**（dmactive を残し、haltreq などを下ろす）。reset すると
  DATA0 の dmseq のフレームが消え、次に開いたコンソールが target のタイムアウトまで待たされる。

## 5. `oep.wire.swd`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (len(u8)、kind(u8)、swdio(u16)、swclk(u16)、id(u32))、[TLV] |
| 0x02 | attach | method(u8: 0 だけ。1 は rejected unsupported)、[TLV] | connection(u16)、id(u32)、flags(u8)、speed_hz(u32)、[TLV] |
| 0x03 | detach | connection(u16)、[TLV] | — |
| 0x04 | — | 予約 | |
| 0x05 | connections | first(u8) | §2.1（ロック不要） |

- scan の kind は 2 = arm-adi、id は DPIDR。要求と応答の形は §3 と同じ（3 線で 1 つの形）。
- TLV は §3 と同じ番号: scan 0x01 max_speed、0x02 skip、0x06 targetsel（下）。attach 0x01 max_speed（必須）、0x02 targetsel、
  0x03 pins、0x05 reset（持たない probe は rejected unsupported）。detach 0x01 force。attach の応答 0x10 target_id、0x12 search_retries（§1）。
- **speed の選び方**: SWD は読んで速さを選べないので、`min(max_speed, describe の max_clock_hz)` で始める。
- attach は JTAG から SWD への切り替えを試し、答えがなければ dormant から起こす（flags bit2）。電源投入（CTRL/STAT の CDBGPWRUPREQ /
  CSYSPWRUPREQ）は host が DP の書き込みで行う。§2 の再試行では、line reset と dormant 起こしをやり直す。
- **targetsel（TLV 0x02、u32）は critical で送る**（multidrop のときだけ。無視されると別の target に attach するため）。**connection の
  同一性には targetsel を含める**。同じピンの組の生きている connection と targetsel（無しを含む）が違う attach は rejected unavailable
  （host が先に detach する）。同じなら、その connection をそのまま返す。scan は targetsel なしで試す（TARGETSEL が要る multidrop の
  target は scan に出ない。scan の TLV 0x06 targetsel で 1 つだけ指定して試せる）。
- **意図した非対称**（revision 1）: arm-adi には halt / resume / step / reset / run が無い（host が transfer で組む）。swd の connection
  にはスロット・錠・コンソールが乗らない（`oep.probe.config` の slot の wire_fn に swd は使えず、swd の connection への console の
  open は rejected unavailable cause 6）。connections の entry の tid は scheme 2（targetsel）で、錠には使わない。

## 6. `oep.target.arm-adi`

要求の先頭は connection(u16)。

| op | 名前 | 要求（connection の後ろ） | 応答 |
|---:|---|---|---|
| 0x01 | transfer | n(u16)、n 個の転送: req(u8: bit0 APnDP、bit1 RnW、bit2-3 A[3:2]、bit4-7 は 0) と、書き込みなら value(u32) | done(u16)、status(u8)、ack(u8)、nvals(u16)、nvals × value(u32)、[TLV] |
| 0x02 | read_block | address(u32)、count(u16)、[TLV] | done(u16)、status(u8)、done × word(u32)、[TLV] |
| 0x03 | write_block | address(u32)、count(u16)、count 個の語、[TLV] | done(u16)、status(u8)、[TLV] |

- ack は最後の転送の生の ACK（`swd_ack`: 線の順で bit0 が最初。OK = 1、WAIT = 2、FAULT = 4。無応答は status line）。req の bit4-7 が
  0 でなければ rejected malformed。nvals は読んだ値の数（最初の done 個の転送のうち読み出しの数）。
- transfer は生の転送で、AP の読み出しが 1 つ遅れて返るのもそのまま（host が RDBUFF か次の AP の読み出しで受け取る）。
  WAIT は probe の中で 100 回まで再試行し、使い切れば status wait。FAULT で止まるので、host は ABORT で sticky を消す。
- read_block / write_block の 1 回の長さと読みの意味は riscv-dm（§4.5）と同じ: describe の max_length（byte 数、4 の倍数、要求も応答も
  max_frame に収まる値）を必ず出し、count × 4 がそれを超えれば rejected unsupported（payload `0x00`）。host は max_length から count を
  決める。read_block は target のバスを通して読み、probe の側に写しを持たない。
- read_block / write_block は今の MEM-AP の TAR / DRW を使う。SELECT と CSW（32 bit、単一増加）は host が先に設定する。probe は
  1 KiB の境界ごとに TAR を書き直し、1 つ遅れる読み出しを並べ直す。**hart の状態は問わない**（MEM-AP は走っていても読める）。
  **done は probe が送った語の数**で、target が受けた保証ではない（posted write の FAULT は後の転送で見える）。TAR は進めたままにし、
  SELECT / CSW は変えない（§4 の不変条件の arm 版: probe は host が設定したものを変えない）。64 bit の AP の番地は riscv-dm と同じ
  TLV 0x01 `address_hi` で後から足す（予約）。
