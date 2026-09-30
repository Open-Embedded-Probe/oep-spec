# OEP 標準インターフェース: 線とデバッグ v1

状態: **規範**（2026-09-26）。本体は [OEP core](oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§2 debug の
connection、§3 status）。番号の唯一の定義は `registry/oep-v1.toml`。名前の置き方の理由は
[能力の名前の階層](capability-name-hierarchy.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.wire.rvswd` | 1 | WCH の 2 線（RVSWD）で RISC-V の DM につなぐ |
| `oep.wire.swio` | 1 | WCH の 1 線（SWIO、CH32V00x）で RISC-V の DM につなぐ |
| `oep.wire.swd` | 1 | ARM の SWD で ADI につなぐ |
| `oep.target.riscv-dm` | 1 | RISC-V Debug Module の操作 |
| `oep.target.arm-adi` | 1 | ARM ADI（DP / AP）の操作 |

- `oep.wire.*` は connection を作り、`oep.target.*` は connection の上で target を操作する。target を扱うインターフェースは
  attach の前から list に出し、connection の無い要求は rejected no_connection。
- **target の系統（チップの型）は宣言しない。** チップごとの知識（flash の書き方、DM の癖）は host が持つ。
- connections のほかの op はすべてロックが要る。

## 1. attach の規範（全 wire）

- probe は、線の速さを確かめ終えるまで target に書き込まない（読むだけで速さを選ぶ）。速さの合わない書き込みは、化けた値を
  target のレジスタに書きうる。
- **ピンの組**:
  - probe が使える組は describe の共通タグ（core §7.4）で宣言する。決まった組は channel_group、どのピンにも割り当てられる
    なら role_channels。役の番号は `pin_role`（1 = SWDIO、2 = SWCLK）。
  - scan の要求は試す組の並び。**count = 0 は probe が許すすべての組**。応答の組は、そのまま attach の pins に渡せる。
  - role_channels で宣言した線では、許す組は「role 1 の候補 × role 2 の候補（1 本の線は role 1 だけ）で、同じ channel を 2 度
    使わないもの」。count = 0 の並びは swdio の昇順、その中で swclk の昇順とし、**今ほかのもの（plan、ほかの線の接続、設定の
    資源）が持っている channel を含む組は並べない**（count = 0 は動かしてよい組だけを試す）。組を並べた要求に、持たれている
    channel があれば、§8.1 のとおり全体を rejected unavailable。
  - 線は、生きている接続が使っている組の channel を持つ（接続が無くなれば放す）。持っている間、その channel を plan や設定が
    取ろうとすれば rejected unavailable（core §8.1）。
  - scan の応答の `tried` は、要求の並び（count = 0 なら上の count = 0 の並び。channel_group の線では describe に出した順）の
    先頭から試し終えた組の数。1 回に試すのは多くても 255 組（tried は u8）。見つかった組で応答が 1 フレームに入らなくなりそう
    なら、probe はそこで止める。**1 回の応答に時間を掛けすぎるときも、probe は途中で止めてよい**（目安 500 ms。応答が遅れると
    host の時間切れになる。bit-bang で 1 組ずつ試す probe は、全部の組に数秒かかる）。tried ≥ 1 なら、host は続きを送る。組を並べた要求で tried が並びの数より少なければ、host は残りの組でもう一度 scan を送る。
  - **count = 0 の続き**: count = 0 の要求は TLV skip（0x01、u16）で、count = 0 の並びの先頭から飛ばす数を渡せる（無ければ 0）。
    host は skip に今までの tried の和を渡して続け、**tried = 0 が返ったら終わり**。並びは要求のときの持たれ方で決まるので、
    途中で plan などが変われば、組が抜けたり重なったりしうる（host は scan の間ほかを変えない）。count > 0 に skip を付けた
    要求は rejected malformed。
  - attach / attach_under_reset は pins（TLV 0x03、critical）で組を指定する。pins が無ければ、その線の生きている接続が 1 つ
    だけならその組（既存の接続に乗る。スロットが持っている接続でもよい）、生きている接続が無く許す組が 1 つだけならその組、
    それ以外（生きている接続が 2 つ以上、または接続が無く許す組が 2 つ以上）は rejected unavailable（host が選ぶ）。
  - **許していない組は、何も実行せずに rejected unavailable**（scan は要求の中に 1 つでもあれば全体を断る）。
- **同時に持てる接続の数**: wire のインターフェースは describe の max_connections（tag 0x40、u8）で宣言する。宣言が無ければ 1。
  ロックは probe に 1 つのまま（接続ごとのロックは無い）。
- **scan と生きている接続**: 生きている接続の組は、scan で線を初めからやり直さず、その接続で読んだ値（DMSTATUS など）で見つかった
  組として返す（動いている接続を scan で壊さない）。
- **席が埋まっているときの scan**: max_connections の接続が生きている間、scan で試せるのは生きている接続の組だけである（ほかの組を
  試すには、線をその接続から離すことになる）。ほかの組を並べた要求は、何も実行せずに rejected unavailable。count = 0 の並びは
  生きている接続の組だけになる。
- **席の規則**: 生きている接続と違う組への attach（attach_under_reset を含む）は、席が空いていれば新しい connection を作る。席が埋まっていれば、使っているものが
  スロットだけ（host のセッションが使っていない、[共通部品](oep-if-common.ja.md) §2）の接続のうち最も古く作られたものを閉じて席を
  空ける。そういう接続が無ければ rejected unavailable。閉じた接続に載っていたストリームは、接続を失ったときと同じく閉じる。
  違う wire のインターフェースどうしのピンの取り合いは core §8.1 のとおり断る。
- **すでに attach している線への attach は、その connection をそのまま返す**（flags bit1）。method = 1 なら、動いていれば
  止め、止まっていれば何もしない。method = 0 は動いている hart に触れない。既存の connection が max_speed より速ければ、
  probe はその connection の速さを max_speed 以下に下げて返す。下げられない probe は、扱えない TLV の値として扱う
  （core §2.3）。
- `speed_hz` は probe が選んだ線の速さ（1 ビットの周期の逆数の目安）。
- max_speed（TLV 0x01、u32 Hz）: probe はこれを超える速さを選ばない。host は critical で送る。
- **target の識別子**: attach の応答の後ろに、probe が読めた target の識別子を TLV 0x10 target_id（scheme(u8)、値）で付けてよい。
  scheme は識別子の取り方で、wire ごとに registry が定める。probe は読めなかったとき（scheme が「無い」と定める値だったときを含む）
  は付けない。値の意味（どのビットが系統で、どれがリビジョンか）は host が知っている。probe は解釈しない。

## 2. connection の寿命（全 wire）

[共通部品](oep-if-common.ja.md) §2 に加えて:

- **detach は、その host のセッションの分を外すだけ**。ほかに使っているものがあれば connection は閉じない。detach の TLV 0x01
  force（長さ 0、critical で送る）で、使っているものがあっても閉じる。
- **target の reset では connection を閉じない**。probe は、reset の後も同じ connection で使えるように保つ（wire ごとの手順は
  §4.6 など、target を扱うインターフェースの節）。
- 線が切れたとみなすのは、最遅の速さで再試行しても **1000 ms 続けて応答が無い**とき。probe が reset を出している間、reset の線を
  probe が保っている間（plan、attach_under_reset）、その解放から target の debug が戻るまでの時間は数えない。それより長く応答
  しない target（電源を切った、長い reset を外から掛けた）は、切れたとみなしてよい。
- **probe は connection を閉じるとき、target の状態を必要以上に変えない**（target を reset しない。止めていた hart は、閉じる前の
  host の操作のままにする）。
- probe 自身の自動の attach（`oep.probe.config` のスロット）も使っているものの 1 つで、host の attach はその connection に加わる
  （flags bit1）。

### 2.1 connections（接続の一覧）

```text
要求: —
応答: count(u8)、count × (len(u8)、entry)（core §2.3）
entry: connection(u16)、swdio(u16)、swclk(u16)、speed_hz(u32)、users(u8)、slot(u8)、tid_scheme(u8)、tid_len(u8)、tid
```

- そのインターフェースの生きている接続を、作られた順に返す。ロックなしで使える。
- users: bit0 host のセッションが使っている、bit1 スロットが使っている（自動の attach か bind のコンソール）。
- slot は、その接続がスロットの接続（`oep.probe.config` §1.1）ならスロットの番号、そうでなければ 0xFF。
- tid は attach のときに読めた target_id（無ければ tid_scheme 0、tid_len 0）。swd は tid_scheme 0（DPIDR は attach の応答で返る）。

## 3. `oep.wire.rvswd` / `oep.wire.swio`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (len(u8)、kind(u8)、swdio(u16)、swclk(u16)、DMSTATUS(u32)) |
| 0x02 | attach | method(u8: 0 止めない / 1 止める)、[TLV] | connection(u16)、DMSTATUS(u32)、flags(u8)、speed_hz(u32) |
| 0x03 | detach | connection(u16)、[TLV] | — |
| 0x04 | attach_under_reset | channel(u16)、hold_ms(u16)、[TLV] | connection(u16)、dpc(u32)、speed_hz(u32) |
| 0x05 | connections | — | §2.1（ロック不要） |

- swio の組は swclk = 0xFFFF（1 本の線）。scan の kind は 0x01 = riscv-dm。値は生の値。
- attach の flags: bit0 保留中の havereset を確認応答した、bit1 既存の connection。
- attach_under_reset は任意の op（持たない probe は unknown_operation）。リセットの線（channel）を保持して attach し、離しながら
  halt を打ち続ける。
- **reset の線に既定は無い**: どの線を reset に使うかは host が毎回 channel で明示する（線を取り違えた reset は target や治具を
  壊しうる）。probe が reset に使ってよい channel は describe の role_channels の role 3（reset）で宣言する。宣言していない
  channel は、何も実行せずに rejected unavailable。今ある plan や接続が持つ channel も、§8.1 の取り合いとして rejected unavailable。持たない probe では、host は `oep.fixture.gpio` の解放と attach をまとめて
  送って再試行する。

TLV:

| op | tag | 名前 | 値 |
|---|---:|---|---|
| scan（count = 0 だけ） | 0x01 | skip | u16。count = 0 の並びの先頭から飛ばす組の数 |
| attach、attach_under_reset | 0x01 | max_speed | u32 Hz |
| attach、attach_under_reset | 0x03 | pins | swdio(u16)、swclk(u16) |
| attach、attach_under_reset（rvswd だけ） | 0x04 | idle_clock | u8。線を休ませる間の SWCLK: 0 = high（無いときと同じ）、1 = low。host は critical で送る |
| detach | 0x01 | force | 長さ 0 |
| attach、attach_under_reset の応答 | 0x10 | target_id | scheme(u8)、値 |

target_id の scheme（rvswd / swio）: 1 = WCH の DM の DMI 0x7F を読んだ u32。0 と 0xFFFFFFFF は「無い」（付けない）。

- **線の設定は target の性質で、host が持つ**: 線の速さの上限（max_speed）と休ませ方（idle_clock）は、target（チップ）が
  求めるものである（例: CH32L103 は SWCLK が high で休むと debug の線を reset し、reset 直後の遅いクロックでは 1 MHz を超えると
  書き込みの確かめが落ちる、2026-09-23〜25）。probe はそれを既定値として持たない。host が attach ごとに渡し、host 無しで attach する
  スロットは、スロットの項目に同じ値を持つ（[probe の設定](oep-if-probe-config.ja.md) §1.1）。
- 既存の connection への attach で idle_clock が今と違えば、probe はその connection の休ませ方を替えて返す。替えられない probe は、
  扱えない TLV の値として扱う（core §2.3）。

## 4. `oep.target.riscv-dm`

要求の先頭は connection(u16)。

- **必須の op は dmi、halt、resume**。reset、read_block / write_block、run、step は任意で、describe の features で宣言する
  （bit0 read_block / write_block、bit1 run、bit2 reset、bit3 step）。宣言していない op は unknown_operation。host は、任意の op が
  無くても dmi で同じことを組める。
- **dmi 以外の op（高水準の op）の範囲**: RV32 の hart 0 だけを扱う（番地、レジスタの値、pc は u32）。probe は高水準の op の中で
  DMCONTROL の hartsel を 0 にする。ほかの hart と RV64 は、host が dmi で扱う（DMI の値が u32 なのは DMI の形で、RV32 に限る
  意味ではない）。dmi の中で host が選んだ hartsel は、次の高水準の op までしか保たれない。

| op | 名前 | 要求（connection の後ろ） | 応答 |
|---:|---|---|---|
| 0x01 | dmi | n(u16)、n 個の手順 | done(u16)、status(u8)、値の並び |
| 0x02 | halt | — | status(u8) |
| 0x03 | resume | — | status(u8) |
| 0x04 | reset | mode(u8)、[TLV] | status(u8)、flags(u8)、attempts(u8)、pc(u32)（mode 2 では dpc） |
| 0x05 | read_block | address(u32)、count(u16) | done(u16)、status(u8)、done 個の語 |
| 0x06 | write_block | address(u32)、count(u16)、count 個の語 | done(u16)、status(u8) |
| 0x07 | run | pc(u32)、timeout_ms(u32)、n(u8)、n × (regno(u16)、value(u32))、n_out(u8)、n_out × regno(u16)、[TLV] | status(u8)、stopped(u8)、dpc(u32)、elapsed_us(u32)、n_out × value(u32) |
| 0x08 | step | — | status(u8)、moved(u8)、dpc_before(u32)、dpc_after(u32) |

### 4.1 dmi

| kind | 手順 | 引数 | 応答に足す値 |
|---:|---|---|---|
| 0x01 | 書く | address(u8)、value(u32) | — |
| 0x02 | 読む | address(u8) | 読んだ値(u32) |
| 0x03 | 読む回数を上限に待つ | address(u8)、mask(u32)、value(u32)、max_reads(u16) | 最後に読んだ値(u32) |
| 0x04 | 待ち | us(u32) | — |
| 0x05 | 時間を上限に待つ | address(u8)、mask(u32)、value(u32)、max_us(u32) | 最後に読んだ値(u32) |

- kind 0x10〜0x1F は、番地を u32 にした同じ手順に予約する。知らない kind は長さが分からないので、要求全体を rejected
  malformed にする（probe は手順を全部確かめてから実行する）。
- **done は最後まで済んだ手順の数**（失敗したときは、失敗した手順の 0 起点の番号）。値を足すのは 0x02 / 0x03 / 0x05 だけ。
  値の個数は、最初の done 個の手順のうち値を足す手順の数に、失敗した手順が 0x03 / 0x05 で待ち切れた（status timeout）なら 1 を
  足したもの。線の不良などで読めずに失敗した手順は値を足さない。
- 1 つの要求は 1 つの hart の操作。タイミングと線の立て直しが要るもの（リセット、回復）は部品の op にする。
- **host は抽象コマンドの一連（data1 / data0 の書き込み、command、data0 の読み）を 1 つの dmi 要求に入れる**（probe が
  要求の間にコンソールの読みを挟んでも壊れない。`oep.target.console` §2）。

### 4.2 halt、resume、step

- **halt** は、すでに止まっていれば何もせず ok。
- **resume** の ok は「hart が debug mode を出た」ことで、DMSTATUS の allresumeack（または allrunning で halted でない）で判断する。
  resumereq は 1 回だけ出し、出し直さない。見えなければ status state。
  - target によっては、これで足りない（allresumeack を立てない target がすぐ breakpoint で止まり直す、1 回の resumereq で出ない
    ことがある）。その扱い（dpc を読んで、動いていなければもう一度 resume する、など）は target を知っている host が行う。
- **DATA0 / DATA1 は target のものとして返す**: hart が止まっている間に probe が abstract command（read_block など）で
  DATA0 / DATA1 を使うと、target がそこに出していた語（dmseq などのコンソールのフレームや答え）が消え、target は resume の後、
  自分の語が無いのを沈黙と読んでタイムアウトまで待つ（X035、別の client の halt → read_block → resume の後にコンソールが
  数秒黙った、2026-09-30）。probe は、hart が止まったのを最初に見たとき（halt、またはすでに止まっていた hart への halt）の
  DATA0 / DATA1 を覚えておき、resume（と step）で hart を走らせる前に、DATA1、DATA0 の順に書き戻す。reset（reset の op、
  attach_under_reset）は target を始めからやり直させるので、覚えた値を捨てる。host が raw の DMI（dmi の op）で走らせた
  ときは書き戻さない（probe は覚えた値を捨てる）。
- **step** は dcsr.step を立てて resume を 1 回だけ出す。dpc が動かなくても失敗にしない（status ok、moved = 0。自分自身へ
  跳ぶ命令は正しく進んでも dpc が同じなので、host が命令を読んで判断する）。hart が debug mode に戻らないときは status state。
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

- outcome success の条件は、mode 0 と 2 では flags bit0、mode 1 では bit1。満たさなければ completed failed（形は同じ）。
- flags のほかの bit は 0。

TLV 0x01 method（u8）: 0 probe が選ぶ、1 ndmreset。2 は予約（target のシステムリセットには共通の手順が無いので、host が dmi で
組む）。

### 4.4 run

- host のローダーを呼ぶためのもの。probe は dcsr の ebreakm と prv = M を立て、pc から走らせ、止まるのを待つ。**probe は run を
  出し直さない**（止まった位置が開始位置のままでも、走って戻った場合と区別できない）。走らなかったかどうかは host が dpc で
  判断し、ローダーを二度走らせてよいときだけやり直す。**gdb の continue には使わない**（prv と ebreakm を変える）。
- timeout_ms は有限（0xFFFFFFFF は rejected unsupported）。run の応答を返すまで、probe はほかの要求に答えない（lease は応答の
  後から数える）。host は、lease と応答の待ち時間より十分短い timeout を使う。止まったら stopped = 1（success）。上限に達したら
  probe は hart を止めてから dpc と値を読み、stopped = 0、status timeout、outcome failed で返す（dpc と値はすべて有効）。
  止められなければ completed failed と payload `status(u8)` だけ。
- regno は RISC-V の抽象レジスタ番号（a0 = 0x100A）。

### 4.5 read_block、write_block

- 語（32 bit）単位。8 / 16 bit のアクセスは dmi の手順で組む。
- **1 回の長さ**: read_block / write_block を持つ probe は、describe の共通 tag max_length（core §7.4）を必ず出す。単位は **byte 数**
  （4 の倍数）で、count × 4 はこれを超えない（超えれば rejected malformed）。
- **読みの意味**: read_block は target のバスを通して読む。probe の側に写しを持たない（直前の write_block、dmi、run で target が
  書いたものを反映する）。保証するのは probe の側だけで、target 自身の cache や prefetch の像は範囲の外（host のチップの知識の側）。
- **前提**: hart が止まっていること（止まっていなければ status state）。番地は、止まっている hart が M モードで使う番地。
- **副作用**: probe は GPR、program buffer、DATA のレジスタを使ってよい。ただし **hart を走らせる前（resume、step）に、止まって
  いた間に使った GPR を、止まったときの値に戻す**（DATA は §4.2 のとおり）。host が何も保存しなくても、halt → read_block →
  resume で target の状態は変わらない。戻さないと、target は止まった場所によってはレジスタを壊されて走り続ける（X035、
  sketch のループに 10 ms おきの halt → read_block → resume を 109 回挟むと sketch が死んだ、2026-09-30）。program buffer は
  戻さない（target は使わない）。abstractauto は 0 に戻す。reset は覚えた値を捨てる（§4.2 と同じ）。
- run（§4.4）は host の指定したレジスタで host のローダーを走らせるもので、その間に変わった GPR、dcsr は戻さない（host の責任）。
  run の前に block の op が使った GPR は、run の後の resume で戻す。

### 4.6 RISC-V の connection の扱い

- attach は保留中の havereset を先に確認応答する（V00x の DM は確認応答まで DMSTATUS の halt / running を固定する）。
- target の reset（reset の op、NRST）の後、probe は havereset を確認応答して、同じ connection を保つ。
- **probe は connection を閉じるときもデバッグモジュールを reset しない**（dmactive を残し、haltreq などを下ろす）。reset すると
  DATA0 の dmseq のフレームが消え、次に開いたコンソールが target のタイムアウトまで待たされる。

## 5. `oep.wire.swd`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (len(u8)、kind(u8)、swdio(u16)、swclk(u16)、DPIDR(u32)) |
| 0x02 | attach | [TLV] | connection(u16)、DPIDR(u32)、flags(u8: bit0 dormant から起こした、bit1 既存の connection)、speed_hz(u32) |
| 0x03 | detach | connection(u16)、[TLV] | — |
| 0x05 | connections | — | §2.1（ロック不要） |

- scan の kind は 0x02 = arm-adi。
- scan の TLV: 0x01 skip（§1）。attach の TLV: 0x01 max_speed、0x02 targetsel（u32、multidrop のときだけ）、0x03 pins。
  detach の TLV: 0x01 force。
- attach は JTAG から SWD への切り替えを試し、答えがなければ dormant から起こす。電源投入（CTRL/STAT の CDBGPWRUPREQ /
  CSYSPWRUPREQ）は host が DP の書き込みで行う。
- **connection の同一性には targetsel を含める**。同じピンの組の生きている connection と targetsel（無しを含む）が違う attach は
  rejected unavailable（host が先に detach する）。同じなら、その connection をそのまま返す。
- attach_under_reset と reset の線の操作は、revision 1 では持たない。NRST は `oep.fixture.gpio` で動かす（reset の解放と attach の
  間は host の往復の遅れに依存する）。固定のデバッグ端子の probe 向けに、reset の線を扱う任意の op を後から足す（revision を
  変えずに足せる）。

## 6. `oep.target.arm-adi`

要求の先頭は connection(u16)。

| op | 名前 | 要求（connection の後ろ） | 応答 |
|---:|---|---|---|
| 0x01 | transfer | n(u16)、n 個の転送: req(u8: bit0 APnDP、bit1 RnW、bit2-3 A[3:2]) と、書き込みなら value(u32) | done(u16)、status(u8)、ack(u8)、読んだ値の並び |
| 0x02 | read_block | address(u32)、count(u16) | done(u16)、status(u8)、done 個の語 |
| 0x03 | write_block | address(u32)、count(u16)、count 個の語 | done(u16)、status(u8) |

- ack は最後の転送の生の ACK。読んだ値は、最初の done 個の転送のうち読み出しの数だけ。
- transfer は生の転送で、AP の読み出しが 1 つ遅れて返るのもそのまま（host が RDBUFF か次の AP の読み出しで受け取る）。
  WAIT は probe の中で再試行する。FAULT で止まるので、host は ABORT で sticky を消す。
- read_block / write_block の 1 回の長さと読みの意味は riscv-dm（§4.5）と同じ: describe の max_length（byte 数、4 の倍数）を必ず
  出し、count × 4 はこれを超えない。read_block は target のバスを通して読み、probe の側に写しを持たない。
- read_block / write_block は今の MEM-AP の TAR / DRW を使う。SELECT と CSW（32 bit、単一増加）は host が先に設定する。probe は
  1 KiB の境界ごとに TAR を書き直し、1 つ遅れる読み出しを並べ直す。
