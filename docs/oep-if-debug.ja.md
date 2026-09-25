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
- すべての op はロックが要る。

## 1. attach の規範（全 wire）

- probe は、線の速さを確かめ終えるまで target に書き込まない（読むだけで速さを選ぶ）。速さの合わない書き込みは、化けた値を
  target のレジスタに書きうる。
- **ピンの組**:
  - probe が使える組は describe の共通タグ（core §7.4）で宣言する。決まった組は channel_group、どのピンにも割り当てられる
    なら role_channels。役の番号は `pin_role`（1 = SWDIO、2 = SWCLK）。
  - scan の要求は試す組の並び。**count = 0 は probe が許すすべての組**。応答の組は、そのまま attach の pins に渡せる。
  - attach / attach_under_reset は pins（TLV 0x03、critical）で組を指定する。pins が無ければ、許す組が 1 つだけならその組、
    2 つ以上なら rejected unavailable（host が選ぶ）。
  - **許していない組は、何も実行せずに rejected unavailable**（scan は要求の中に 1 つでもあれば全体を断る）。
  - 1 つの wire のインターフェースの connection は 1 つ。生きている connection と違う組の attach は rejected unavailable。
- **すでに attach している線への attach は、その connection をそのまま返す**（flags bit1）。method = 1 なら、動いていれば
  止め、止まっていれば何もしない。method = 0 は動いている hart に触れない。既存の connection が max_speed より速ければ、
  probe はその connection の速さを max_speed 以下に下げて返す。下げられない probe は、扱えない TLV の値として扱う
  （core §2.3）。
- `speed_hz` は probe が選んだ線の速さ（1 ビットの周期の逆数の目安）。
- max_speed（TLV 0x01、u32 Hz）: probe はこれを超える速さを選ばない。host は critical で送る。

## 2. connection の寿命

[共通部品](oep-if-common.ja.md) §2 に加えて:

- **detach は、その host のセッションの分を外すだけ**。ほかに使っているものがあれば connection は閉じない。detach の TLV 0x01
  force（長さ 0、critical で送る）で、使っているものがあっても閉じる。
- **target の reset（riscv-dm の reset、NRST）では connection を閉じない**（probe は havereset を確認応答して保つ）。
- 線が切れたとみなすのは、最遅の速さで再試行しても **1000 ms 続けて応答が無い**とき。reset の直後や DM の立ち上がりの間の
  数十 ms は数えない。
- **probe は connection を閉じるときもデバッグモジュールを reset しない**（dmactive を残し、haltreq などを下ろす）。reset すると
  DATA0 の dmseq のフレームが消え、次に開いたコンソールが target のタイムアウトまで待たされる。
- probe 自身の自動の attach（`oep.probe.config` の bind）も使っているものの 1 つで、host の attach はその connection に加わる
  （flags bit1）。

## 3. `oep.wire.rvswd` / `oep.wire.swio`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | count(u8)、count × (kind(u8)、swdio(u16)、swclk(u16)、DMSTATUS(u32)) |
| 0x02 | attach | method(u8: 0 止めない / 1 止める)、[TLV] | connection(u8)、DMSTATUS(u32)、flags(u8)、speed_hz(u32) |
| 0x03 | detach | connection(u8)、[TLV] | — |
| 0x04 | attach_under_reset | channel(u16、0xFFFF = probe の既定値)、hold_ms(u16)、[TLV] | connection(u8)、dpc(u32)、speed_hz(u32) |

- swio の組は swclk = 0xFFFF（1 本の線）。scan の kind は 0x01 = riscv-dm。値は生の値。
- attach の flags: bit0 保留中の havereset を確認応答した、bit1 既存の connection。
- attach は保留中の havereset を先に確認応答する（V00x の DM は確認応答まで DMSTATUS の halt / running を固定する）。
- attach_under_reset は任意の op（持たない probe は unknown_operation）。リセットの線（channel。probe が許可したものだけ）を
  保持して attach し、離しながら halt を打ち続ける。持たない probe では、host は `oep.fixture.gpio` の解放と attach をまとめて
  送って再試行する。

TLV:

| op | tag | 名前 | 値 |
|---|---:|---|---|
| attach、attach_under_reset | 0x01 | max_speed | u32 Hz |
| attach、attach_under_reset | 0x03 | pins | swdio(u16)、swclk(u16) |
| detach | 0x01 | force | 長さ 0 |

## 4. `oep.target.riscv-dm`

要求の最初の byte は connection。

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
- **resume** の ok は「hart が一度でも debug mode を出た」こと。probe は、allresumeack が立てば出し直さない。allresumeack を
  立てない target では dpc が変われば出し直さない。dpc が変わらず止まったままなら出し直す。出し直しても出なければ status
  state。host は breakpoint の上から continue するときは先に step で 1 命令進める。
- **step** は dcsr.step を立てて resume を 1 回だけ出す。dpc が動かなくても失敗にしない（status ok、moved = 0。自分自身へ
  跳ぶ命令は正しく進んでも dpc が同じなので、host が命令を読んで判断する）。hart が debug mode に戻らないときは status state。
  prv は変えない。

### 4.3 reset

| mode | 意味 |
|---:|---|
| 0 | 走らせる |
| 1 | 走らせて、実行を確認する |
| 2 | 最初の命令の前で止める（haltreq を保ったまま ndmreset を解く） |

TLV 0x01 method（u8）: 0 probe が選ぶ、1 ndmreset、2 target のシステムリセット（PFIC など）。

### 4.4 run

- host のローダーを呼ぶためのもの。probe は dcsr の ebreakm と prv = M を立て、pc から走らせ、止まるのを待つ。止まった位置が
  開始位置のままなら、走らなかったとみなして resume を出し直す。**gdb の continue には使わない**（prv と ebreakm を変える）。
- timeout_ms の 0xFFFFFFFF は上限なし。止まったら stopped = 1（success）。上限に達したら probe は hart を止めてから dpc と値を
  読み、stopped = 0、status timeout、outcome failed で返す（dpc と値はすべて有効）。止められなければ completed failed と
  payload `status(u8)` だけ。
- regno は RISC-V の抽象レジスタ番号（a0 = 0x100A）。

### 4.5 read_block、write_block

語（32 bit）単位。8 / 16 bit のアクセスは dmi の手順で組む。

## 5. `oep.wire.swd`

| op | 名前 | 要求 | 応答 |
|---:|---|---|---|
| 0x01 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | count(u8)、count × (kind(u8)、swdio(u16)、swclk(u16)、DPIDR(u32)) |
| 0x02 | attach | [TLV] | connection(u8)、DPIDR(u32)、flags(u8: bit0 dormant から起こした、bit1 既存の connection)、speed_hz(u32) |
| 0x03 | detach | connection(u8)、[TLV] | — |

- scan の kind は 0x02 = arm-adi。
- attach の TLV: 0x01 max_speed、0x02 targetsel（u32、multidrop のときだけ）、0x03 pins。detach の TLV: 0x01 force。
- attach は JTAG から SWD への切り替えを試し、答えがなければ dormant から起こす。電源投入（CTRL/STAT の CDBGPWRUPREQ /
  CSYSPWRUPREQ）は host が DP の書き込みで行う。
- attach_under_reset は持たない。

## 6. `oep.target.arm-adi`

要求の最初の byte は connection。

| op | 名前 | 要求（connection の後ろ） | 応答 |
|---:|---|---|---|
| 0x01 | transfer | n(u16)、n 個の転送: req(u8: bit0 APnDP、bit1 RnW、bit2-3 A[3:2]) と、書き込みなら value(u32) | done(u16)、status(u8)、ack(u8)、読んだ値の並び |
| 0x02 | read_block | address(u32)、count(u16) | done(u16)、status(u8)、done 個の語 |
| 0x03 | write_block | address(u32)、count(u16)、count 個の語 | done(u16)、status(u8) |

- ack は最後の転送の生の ACK。読んだ値は、最初の done 個の転送のうち読み出しの数だけ。
- transfer は生の転送で、AP の読み出しが 1 つ遅れて返るのもそのまま（host が RDBUFF か次の AP の読み出しで受け取る）。
  WAIT は probe の中で再試行する。FAULT で止まるので、host は ABORT で sticky を消す。
- read_block / write_block は今の MEM-AP の TAR / DRW を使う。SELECT と CSW（32 bit、単一増加）は host が先に設定する。probe は
  1 KiB の境界ごとに TAR を書き直し、1 つ遅れる読み出しを並べ直す。
