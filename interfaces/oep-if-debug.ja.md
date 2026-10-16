# OEP インターフェース: 線とデバッグ v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。本体は [OEP core](../docs/oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§2 debug の
connection、§3 status）。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.wire.rvswd` | 1 | 2 線の RVSWD で RISC-V の DM につなぐ | DM に 2 線の RVSWD で届く RISC-V の target |
| `oep.wire.swio` | 1 | 1 線の SWIO で RISC-V の DM につなぐ | DM に 1 線の SWIO で届く RISC-V の target |
| `oep.wire.swd` | 1 | ARM の SWD で ADI につなぐ | SWD の DP を持つ ARM の target |
| `oep.target.riscv-dm` | 1 | RISC-V Debug Module の操作 | RISC-V Debug Module を持つ RISC-V の target |
| `oep.target.arm-adi` | 1 | ARM ADI（DP / AP）の操作 | ADI を持つ ARM の target |

- `oep.wire.*` は connection を作り、`oep.target.*` は connection の上で target を操作する。target を扱うインターフェースは
  attach の前から list に出し、connection の無い要求は rejected no_resource。
- connections 以外の op はすべてロックが要る。
- 最小のwireはattach/detach/connectionsと1接続だけでよく、scan・複数接続・consoleを要求しない。
  targetのflash手順、メモリ配置、チップの識別子の解釈はhostの知識として扱う。probeが実装する高水準の操作は、宣言したtarget操作の範囲に限る。
  connectionはwireのpin/target選択を保持し、各target要求が先頭のconnection番号でその接続を選ぶ。wireとtargetのfn番号が一致する必要はない。

## 0. 本書の wire が共有する規則、別の wire が定めるもの

本書の `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd` は:

1. op 0x10 scan、0x11 attach、0x12 detach、0x13 connections、0x14 holds を §1〜§2.2 の意味で使う（wire は 0x15 から op を足してよい）。attach、detach、connections、holds は必須。scan は任意で、ops で宣言する;
2. §1 と §2 に従う。swdio / swclk は「ピンの役 1 / 2 の channel」と読み替える;
3. `oep.target.*` のインターフェースが使う [共通部品](oep-if-common.ja.md) §2 の connection を作る。

別のwireを定義するときは、次を明記する。本書の2ピンのattachやconnectionsの要素の固定形は、一律には要求しない。
使う役割数・接続先の選択が異なるwireは、別の名前と固定形をcore §12に従って定義してよい。

- ピンの役と、速さの選び方;
- wake / 設定の手順と、それが target をリセットしうるか（§2）、scratch のレジスタ（§1）;
- やり取りと、やり取りの間の線の休み方（§2）;
- 「見つかった」の基準と、scan_kind の値;
- 共通target_idを採用する場合のscheme（§1の空間から）と、線切れの見え方;
- その connection を受ける `oep.target.*` のインターフェースと、コンソールを使えるかどうか。

## 1. attach の規範（本書の3つのwire）

- **速さを確かめる前の書き込み.** 線の速さを確かめ終えるまで、probe が target に書くのは次だけである:
  1. その wire の節が定める wake / 設定の手順（たとえば wake のパターン、line reset、target の選択、または debug module が答える前に要る
     設定のレジスタ）。wire の最も遅い速さで送る;
  2. connection が RISC-V の DM に届く wire での dmactive。DMCONTROL がすでに dmactive = 1 と読めないときだけ（この書き込みは haltreq を下ろす）。
- **速さの確かめ方.** 可変速のwireは読むだけで速さを選ぶ。scratchを定めるwireは、選んだ速さで書き込みの道も確かめる。書いて読み戻してよいのは、その wire の節が
  空きの scratch（debug のコマンドが走っていない間、target のどこも使わないレジスタ）と名指した debug module のレジスタと、その wire の節が
  それを空けるための書き込みと名指したものだけである。確かめる前に各 scratch のレジスタを読み、確かめた後にその値を書き戻す。書いたものが
  読み戻らない速さは使わない。復元できなければattachはcompleted failedで終え、connectionを作らない。
  scratchを持たないwireと固定速のwireの確認方法は、それぞれの節で定める。
- 速さを確かめる前に、これ以外のものを target に書かない（速さの合わない書き込みは、化けた値を target のレジスタに書きうる）。
- **ピンの組**: describe の channel_group / role_channels が候補を宣言する。
  attachの固定部分は`method(u8)、swdio(u16)、swclk(u16)、max_speed(u32)`。短い固定部分はrejected malformed。
  probe は未指定の配線を探したり、既存の connection を選んだりしない。
- **scan は任意の有限探索**: host は count ≥ 1 の候補の組を明示する。count 0 は rejected malformed。
  role_channels だけを宣言する場合は役 1 × 役 2 の候補を host が作り、同じ channel を二度使わない。
  応答の tried は要求の先頭から試した数。候補が残る間は 1 以上。host は未試行の候補を次の要求に載せる。
  同じ候補を重複して載せる要求は malformed。skip や probe 内部の暗黙の候補一覧は持たない。
- 宣言が許さない組は unsupported。使用中のピンを含む組は unavailable（cause 1）、disable または出力 idle のピンなら cause 5。
  scanのunavailable/unsupportedの診断TLV 0x40 index（u8）は、要求の候補の0起点の番号を任意に示す。これは各wireの固有tagである。
  scan は候補全体を副作用の前に検証する。実行中の connection のピンを探索に使わない。
  試したピンは各候補の後で空きの状態に戻す。探索自体は connection を作らない。
- **時間**: attach と scan の応答は、max_op_ms（core §7.5）のうちに返す。速さの探索と再試行をいつ諦めるかは probe が決める。attach で
  どの速さも使えなければ、応答は status line の completed failed。host の待ちは core §4.4 に従う。
- **同時に持てる接続の数**: wire のインターフェースは describe の max_connections（tag 0x40、u8）で宣言する。宣言が無ければ 1。
  ロックは probe に 1 つのまま（接続ごとのロックは無い）。
- **attach は新しい connection を作る。** 既存の接続へ暗黙に加わらない。既存の接続のピンを含む場合は unavailable（cause 1）。
  host は取得済みの番号を使うか、明示的に detach して作り直す。
- 接続数の上限を超える attach は unavailable（cause 2）。probe は空きを作るために別の接続を閉じない。
- 失敗したattachはconnectionを作らず、既存のprobe資源を変えない。新しく試したピンは空きの状態へ戻す。
  targetへ届いた書込みやresetの効果は取り消せるとは限らない。
- `speed_hz` は probe が選んだ線の速さ（1 ビットの周期の逆数の目安）。
- max_speed（u32 Hz）: probeはこれを超える速さを選ばない。0はmalformed。probeのmin_clock_hzより小さければunsupported
  （attachは固定部分の印0、scanはmax_speedのtag）。scanでは任意TLV 0x01で与える。
- **scan が書くもの**: 「速さを確かめる前の書き込み」の 1 と 2 だけで、「見つかった」の識別子を読むためである。scan は書き込みの道を
  確かめず、scratch のレジスタに書かない。max_speed の無い scan は、その wire の最も遅い速さで試す。max_speed のある scan は、attach と同じく
  max_speed 以下で読むことで速さを選んでよい。dmactive は立てたまま残す。「見つかった」は DMSTATUS.version が 2 以上で 15 でないこと（0 = DM が無い、1 = このインターフェースが
  扱わない版、15 = 適合しない DM）。swd は DPIDR が読めたこと。外れた組のピンは core §8 の
  空きの状態に戻す。
- **target の識別子**: attach の応答の後ろに、probe が読めた target の識別子を TLV 0x01 target_id（scheme(u8)、値）で付けてよい。
  scheme は識別子の取り方。target_id の scheme の番号は probe 全体で 1 つの空間である（registry `[common.enum.target_id_scheme]`:
  1 その debug module の DMI 0x7F の u32、2 swd の DPIDR）。各 wire は、どの scheme を使うかを書く。probe は読めなかったとき（scheme が「無い」と定める値だったときを含む）
  は付けない。値の意味（どのビットが系統で、どれがリビジョンか）は host が知っている。probe は解釈しない。
  このscheme空間への追加はOEPがregistryで割り当てる。独自インターフェースは自己の固定形/TLVで独自の識別情報を返してよく、
  共通target_idを採用しない機能にこのscheme空間を要求しない（core §12）。

## 2. connection の寿命（本書の3つのwire）

[共通部品](oep-if-common.ja.md) §2 に加えて:

- **reset後のDMの待ち**: attachのreset線またはreset opのndmresetを解いた後、DMSTATUSが線からの応答を得るまで読み直して待つ。
  attachではwireの最も遅い速さで読む。待ちの間だけwireのwake/設定手順（§1）を送り直してよい。
  待ちと後始末を含め要求全体のmax_op_msのうちに終える。hostの待ちはcore §4.4。
- **detach は connection と、その上の stream を解放する。** force の TLV は持たない。
- **target の reset では connection を閉じない**。probe は、reset の後も同じ connection で使えるように保つ（wire ごとの手順は
  §4.6 など、target を扱うインターフェースの節）。
- **1 つの要求の中の再試行**: probe は 1 つの要求の中で線を再試行してよい（どれだけ続けるかは probe が決め、遅い速さでの再試行を含む）。
  諦めたら、その要求を status line で終える。それだけでは線切れと決めない。再試行の間の遅い速さは一時的で、connection の speed_hz は変えない。
- **書き込みを繰り返さない**: target のメモリへの store（store を起こす書き込みを含む）と host の dmi の要求の手順は、target に届いたかもしれない後には、
  probe の線の再試行で繰り返さない（target が受けなかったと答えたもの、DMI の busy と SWD の WAIT は繰り返してよい）。probe 自身が debug module と
  レジスタに値を置く書き込み（同じ値をもう一度書いても何も起こらないもの: program buffer、abstractauto、GPR、dcsr、戻す DATA0 / DATA1）は繰り返してよく、
  ほかの書き込み（hart を走らせる resumereq など）は store と同じく繰り返さない。繰り返さない書き込みで失敗した要求は completed failed / partial で答え、
  done はそれより前に済んだ手順か語の数にする。probe 自身の読み出しは繰り返すことがある。
- **target の状態を変えない**: connection がある間、probe が自分の判断で行う線の再試行と同期の取り直しは、target の状態を変えない。wake / 設定の手順が
  target をリセットしうる wire では、connection の上でそれを送るのは attach と、reset（attach の reset TLV、riscv-dm の reset の op）の中だけである。
- **線切れ**: ある connection の操作が線からの応答無しで失敗し続け（status line。要求の中でもコンソールの読みの中でも）、その間にその connection で
  成功した操作が無いとき、probe はその connection の線が切れたと決めてよい（いつ決めるかは probe が決める。reset の線を保っている間とそれを解いた直後は、
  target が答えないことがある）。probe が要求の中で線切れと決めたら、その要求に status line で答えてから connection を閉じる。
- **線切れの判定は、要求の中かコンソールの読みの中でだけ行う**。status line だけでは connection が閉じたことにならない: host は connections で確かめる。
  コンソールの読みの中で判定したらconnectionとstreamを閉じる。閉じる際に、後から読めないマークは作らない。
- **線が応えない間の線**（電気的な安全）: やり取りとは、wire の節が定める 1 つの frame か packet、または 1 回の wake pattern で、節がその直前に求める
  線の level を含む。線からの応答無しで失敗したやり取り（上の線切れに数える失敗）から、その線でやり取りが成功するまで、または connection を失うまで、
  probe はやり取りの間、その線を放した状態で休ませ、やり取りの最中だけ駆動する（再試行の 1 回 1 回もやり取り）。放した状態とは駆動しない状態で、
  pull 無しか、その connection でのその線の休みの level に向けた pull とする。idle_clock 1（low）を使う connection のクロックの線では、
  pull 無しか pull-down で、pull-up にはしない。やり取りがまた成功したら、probe は次のやり取りの前に connection の休み方（クロックの線は
  idle_clock の level、データの線はその休み方: rvswd は §3.1、swio は §3.2、swd は §5）に戻す。やり取りが成功している間の、やり取りの間の休み方は wire の節が定めるとおりで、この規則では変わらない。
- **connectionを閉じる手順はtargetをreset/resumeしない**。外部回路によるtargetの状態変化までは保証しない。
- **閉じた後の線（保持）**: 線切れ以外で connection が閉じたら（detach、セッションの end / lease の期限切れ / force、core §9）、probe はその線のピンを
  その connection の休みの状態（rvswd は §3.1 の休ませ方、swio は §3.2、swd は §5）で駆動したまま**保持**する。target によっては、線が駆動されなくなると
  数 ms でデバッグの状態を失う（CH32L103 は約 5 ms で halt を失い、hart がリセットされる）。host から間に合わないので probe が自動で保つ
  （core §12 規則 8）。
  - **OFF にできる**: 設定 `wire-hold`（[設定](oep-if-probe-config.ja.md) §1、key はその口の SWDIO の channel）が off なら保持せず、core §8 の空きの状態にする。
    項目が無ければ on。ピンに設定の idle か disable があれば、保持せずにそれに従う。
  - **保持は空きの状態の一種**（core §8）: 保持中のピンは、どのインターフェースも空きのピンと同じに取れる（attach、plan、scan。保持を理由に cause 1
    にも cause 5 にもしない）。取ったインターフェースが線を引き継ぎ、その組の保持は終わる。attach は wake から始め（2 本とも high から始まる）、
    休ませ方はその接続で決め直す（§3.1）。口の target が差し替わっていても同じである。
  - **保持が終わるとき**: ピンが取られた、`wire-hold` が off になった、そのピンに idle か disable の項目が置かれた、probe が再起動した。終わったピンは
    空きの状態にする。
  - **線切れでは保持しない**: 線切れで閉じたら、上の「線が応えない間の線」のとおり駆動せず、空きの状態にする。
  - **見える**: 保持中の口は holds（§2.2）で読める。保持は connection ではなく、connections には出ない。

### 2.2 holds（保持中の口の一覧）

```text
要求: first(u8)
応答: more(u8)、count(u8)、count × entry、[TLV]（core §2.3）
entry: swdio(u16)、swclk(u16)、rest(u8)
```

- そのインターフェースが §2 の保持で駆動している口を、first 番目から 1 フレームに入る分だけ返す（ページは §2.1 と同じ）。ロックなしで使える。
- swio は swclk = 0xFFFF。rest は rvswd ではその休ませ方（idle_clock の値: 0 high、1 low）、ほかの wire では 0。
- connection が閉じたら、その組の channel は core §8 の空きの状態になる（idle_clock の駆動もやめる）。

**connection と hart の状態機械**:

| 出来事 | connection | hart | ストリーム |
|---|---|---|---|
| detach / end / lease 切れ / force | 解放 | 触らない | 解放 |
| 線切れ | 解放 | — | 解放 |
| targetの自己リセット | 保つ | targetの状態 | 保つ（marks提供時はrestart mark） |
| probeの再起動 | 無効 | 手順ではreset/resumeしない。ピンのリセット状態による変化は保証しない | 無効 |

- （参考、安全）セッションの終わり（end、lease の期限切れ、force）は hart に触らない: hart を止めたまま host が死ぬと、target は止まったままになる（デバッガの
  detach と違い、走り出さない）。target が何を制御していてもそうである。host が去った後に target を走らせたい host は、end の前に resume する。

### 2.1 connections（接続の一覧）

```text
要求: first(u8)
応答: more(u8)、count(u8)、count × entry、[TLV]（core §2.3）
entry: connection(u32)、swdio(u16)、swclk(u16)、speed_hz(u32)、tid_scheme(u8)、tid_len(u8)、tid
```

- そのインターフェースの生きている接続を、作られた順に first 番目から 1 フレームに入る分だけ返す。more = 1 なら続きがあり、host は
  first に受け取った数を足してもう一度聞く。ロックなしで使える。
- tidはattach時に読んだtarget_id（無ければtid_scheme 0、tid_len 0）。swdはtid_scheme 2、tid_len 4、tidはDPIDR。
  swdでTARGETSELを指定したentryには、応答TLV 0x01 selected_target（entry_index(u8)、targetsel(u32)）を付ける。
  entry_indexはこのページの0起点の番号。このTLVはentryごとに繰り返せる。必要なTLVまで1frameに入るentryだけ返す。
  selectorはhostが与えた選択値で、読出した識別子と区別する。指定無しと値0の指定も区別する。

## 3. `oep.wire.rvswd` / `oep.wire.swio`

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (kind(u8)、swdio(u16)、swclk(u16)、id(u32))、[TLV] | 必要 | 任意 |
| 0x11 | attach | method(u8: 0 止めない / 1 止める)、swdio(u16)、swclk(u16)、max_speed(u32)、[TLV] | connection(u32)、id(u32)、flags(u8)、speed_hz(u32)、[TLV] | 必要 | 必須 |
| 0x12 | detach | connection(u32)、[TLV] | — | 必要 | 必須 |
| 0x13 | connections | first(u8) | §2.1 | 不要 | 必須 |
| 0x14 | holds | first(u8) | §2.2 | 不要 | 必須 |

- swio の組は swclk = 0xFFFF（1 本の線。swclk ≠ 0xFFFF は宣言が許さない組で、scan でも attach でも §1 のとおり rejected unsupported）。rvswd と swio の scan の entry の kind は 1（riscv-dm）、
  idはscan、attachともDMSTATUS。その connection を使うのは `oep.target.riscv-dm` と `oep.target.console`。
- method 0は必須。method 1はdescribeのfeatures bit0（attach_halt）を宣言するときだけ提供する。
  提供しないmethodと未知のmethodはunsupported（固定部分の印0）。method 1はhartselを0にし、hart 0が止まってhaltreqを下ろせた場合だけ成功。
- **attach の flags**（3 線共通、registry の `attach_flags`）: bit0 保留中の havereset を確認応答した（riscv）、bit1 未割当、
  bit2 dormantから起こした（swd）、bit3 probeがhart 0の停止を確認した（0は未確認）。
  method 0に、hart選択の変更や停止状態の確認は要求しない。dpc TLVは任意のRV32診断値で、bit3が立ち、読めた場合だけ付ける。
- **wake / 設定の手順**（§1 の 1）: rvswd: wake のパターン（§3.1）、続けて DMI 0x7E と DMI 0x7D にそれぞれ 0x5AA50400 を書く。その組を 2 回。
  swio: DMI 0x7E と DMI 0x7D にそれぞれ 0x5AA50400 を書く。その組を 2 回。両方の線のフレームは §3.1 と §3.2。
- **scratch**（§1）: PROGBUF0（DMI 0x20）。それを空ける書き込み: ABSTRACTAUTO（DMI 0x18）= 0。これは戻さない（前のセッションが残した autoexec は、
  アクセスのたびに走る）。
- **reset をかけながらの attach**: TLV 0x04 reset（critical: `channel(u16)、hold_ms(u16)`）を付けると、probe はリセットの線（channel）を
  hold_ms 保ってから離す。method 1 なら離しながら halt を打ち続け、できるだけ早く止める（flags bit3、dpc TLV）。**最初の命令の前で
  止まる保証は無い**（reset の線の解放から halt が効くまでに走った分がある）。reset の直後の位置で
  止める保証が要るときは、riscv-dm の reset mode 1（ndmreset を haltreq を保ったまま解く）を使う。method 0はhalt要求を出さない。任意の機能で、role_channels の role 3（reset）で宣言する。持たない probe は reset の TLV を rejected unsupported で断る（受け取ったままの tag、0x84、core §2.3）。使用中のピンとの競合は reset 前に断る。hold_ms は
  core の max_op_ms の対象。
- resetの線を離した後の待ちは§2。DMが答えてから速さを確認する（§1）。
- **reset の線に既定は無い**: どの線を reset に使うかは host が毎回 channel で明示する（線を取り違えた reset は target や治具を
  壊しうる）。probe が reset に使ってよい channel は describe の role_channels の role 3（reset）で宣言する。宣言していない
  channel は、何も実行せずに rejected unsupported（受け取ったままの tag、0x85）。今ある plan や接続が持つ channel は、core §8.1 の取り合いとして rejected
  unavailable。idle が出力の channel は、§1 のとおり rejected unavailable。**reset の線はオープンドレインで low に引き、離すときは引くのをやめて core §8 の空きの状態にする**（外部の reset ボタンや
  ほかの driver と短絡しない）。channel は op の間だけ持つ。持たない probe では、host は `oep.fixture.gpio` の解放と attach をまとめて
  送って再試行する。

TLV（wire の一族で 1 つの空間。rvswd、swio、swd は、この表のうち自分が使うものを同じ番号で使う。core §2.5 の 4）:

| op | tag | 名前 | 値 |
|---|---:|---|---|
| scan | 0x01 | max_speed | u32 Hz（無ければその wire の最も遅い速さ） |
| scan、attach（swd だけ） | 0x02 | targetsel | u32。§3 の swd |
| scan、attach（rvswd だけ） | 0x03 | idle_clock | u8。線を休ませる間の SWCLK: 0 = high、1 = low。attach では critical で、無ければ probe が target_id から決める（§3.1）。scan では scan の間の休ませ方（省略時は high、下） |
| attach | 0x04 | reset | channel(u16)、hold_ms(u16)。critical。上 |
| attach の応答 | 0x01 | target_id | scheme(u8)、値 |
| attach の応答 | 0x02 | dpc | u32。任意。hart 0が止まっている（flags bit3）ときのRV32 dpc |
| attach の応答（rvswd だけ） | 0x03 | idle_clock | u8。その接続が使う休ませ方（0 high、1 low）。rvswd は必ず付ける |
| connections の応答（rvswd だけ） | 0x02 | idle_clock | entry_index(u8)、idle_clock(u8)。rvswd は entry ごとに付ける（§2.1 の selected_target と同じ数え方） |

pin の role（1 swdio、2 swclk、3 reset）、scan の kind（1 riscv-dm、2 arm-adi）、attach の method（0 止めない、1 止める）、attach の flags のビットも
一族で 1 つの空間である。swio は swclk を持たないので role 1 と 3 を使う。

これらの wire が使う target_id の scheme（`target_id_scheme`、probe で 1 つの空間、§1）: 1 = DMI のアドレス 0x7F を読んだ u32（長さ 4）。0 と 0xFFFFFFFF は「無い」（付けない）。
2 = swdのDPIDR（u32、長さ4）。

### 3.1 RVSWD のフレーム

線は 2 本、SWDIO（ピンの役割 1）と SWCLK（ピンの役割 2）。probe は SWCLK をいつも駆動する。SWDIO は読み出しのデータの間を除いて駆動し、
線を使っている間は SWDIO にプルアップを保つ（どちらも駆動しないとき、線が high に読めるように）。

**ビットの区切り。** T は半周期。1 つのビットの区切りは、SWCLK low を T、続けて SWCLK high を T である。
- probe が送るビット: probe は、その区切りを始める SWCLK の立ち下がりで SWDIO をそのビットにし（2 本が同時に変わる）、次の立ち下がりまで保つ。
  target は立ち上がりでそれを読む。
- target が送るビット: target は立ち下がりの後に SWDIO を変える。probe は low の半分の終わり、立ち上がりの直前に SWDIO を読む。

**条件**（SWCLK が high の間に SWDIO が変わるのはここだけ）:
- START: 2 本とも high を T 以上、続けて SWCLK を high のまま SWDIO が下がる。最初のビットの区切りは T 後に始まる。
- STOP: SWDIO low のビットの区切り 1 つ、続けて SWCLK を high のまま SWDIO が上がる。その後 2 本とも T 以上 high のまま。

**フレーム**: DMI のアクセス 1 回。値は最上位ビットから送る。フレームはビットの区切り 53 個。

| 欄 | 区切り | 駆動する側 | 値 |
|---|---:|---|---|
| START | — | probe | |
| address | 7 | probe | DMI のアドレス |
| direction | 1 | probe | 1 書き込み、0 読み出し |
| ヘッダのパリティ | 1 | probe | address、direction とこのビットの 1 の数を偶数にする |
| aux 1 | 5 | probe | 1、0、1、0、1 |
| data | 32 | probe（書き込み）、target（読み出し） | 32 bit の値 |
| data のパリティ | 1 | data と同じ側 | data とこのビットの 1 の数を偶数にする |
| aux 2 | 5 | probe | 1、0、1、1、1 |
| STOP | 1 | probe | STOP の SWDIO low のビットの区切り |

- **向きの切り替え**（読み出し）: probe は、aux 1 の最後の区切りの立ち上がりの後、SWCLK が high の間に SWDIO の駆動をやめ、最初の data の区切りが
  余分な区切り無しに続く。data のパリティの区切りの立ち上がりの後、probe は SWDIO を再び high に駆動し、aux 2 が余分な区切り無しに続く。target が SWDIO を
  駆動するのは、data と data のパリティの 33 個の区切りの間だけである。
- data のパリティが合わない読み出しは、失敗した読み出しである（§2 のとおり再試行する）。書き込みに確認応答は無い: 書く経路は読み戻しでしか確かめられない（§1）。
- **休ませ方**（フレームの間）: idle_clock 0 では 2 本とも high のまま。idle_clock 1 では SWCLK low、SWDIO high で、どちらも probe が駆動する。フレームは 2 本
  とも high から始まる: idle_clock 1 では、START の T 以上前に、SWDIO high のまま SWCLK が上がる。
- **休ませ方の決め方**: 必要な休ませ方は target の系統で決まり、系統どうしで逆になる（CH32L103 は high で休むと約 1 ms で debug module がリセットされ、
  CH32X035 は low で休むと attach できない）。どちらにも安全な既定は無い。attach は 2 本とも high から始まるので、どの系統でも target_id
  （scheme 1、DMI 0x7F）までは読める。host から接続先を確かめて直すのでは間に合わないので、probe の自動の判定を置く（core §12 規則 8）。
  休ませ方は次の順で決める:
  1. attach の idle_clock の TLV（host の明示）があれば、それ;
  2. 無ければ、その SWCLK の channel の設定 `rvswd-rest`（[設定](oep-if-probe-config.ja.md) §1）が high か low なら、それ（自動の判定を OFF にした口）;
  3. 無いか auto なら自動の判定: probe は wake から target_id を読むまでを high で行い、読んだ target_id の bit 31〜20（系統、registry
     `oep.wire.rvswd` の `target_id_family`）が `idle_low_family` にあれば low、無ければ（target_id が読めないときも）high にする。
  どの場合も、使う休ませ方を attach の応答と connections の TLV idle_clock で返す（自動の判定をしたことが host に分かる）。
  1 つの接続の休ませ方は 1 つで、接続の間は変えない。変えるには detach して attach し直す（生きた接続のピンへの attach は §1 のとおり断られる）。
  系統の表は target の知識なので registry に置き、各実装が名前で引く（系統の追加は registry の変更）。
  method 0 の attach（素通しを含む、[設定](oep-if-probe-config.ja.md) §1.2）も同じに決める。

**wake のパターン**（wake / 設定の手順の最初の部分、§3）:

1. 2 本とも high に駆動して 20 µs 以上;
2. SWDIO high のビットの区切り 100 個;
3. SWDIO low のビットの区切り 1 個;
4. SWCLK が high の間に SWDIO が上がる（STOP の条件）;
5. 最初のフレームの前に、2 本とも high を 20 µs 以上。

- **wake / 設定の手順の速さ**: T は 500 ns 以上、かつ 1 / (2 × max_speed) 以上。probe が dmactive を書くとき（§1 の 2）、その直後に同じ T で設定の組
  （DMI 0x7E、続けて DMI 0x7D）をもう 2 回書いてよい。これらの書き込みは wake / 設定の手順の一部である。
- **速さの選び方**: probe は、DMSTATUS の読み出しで、一番遅い T から短い方へ進めて T を選ぶ（§1）。
- wake のパターンは、target のデバッグの口だけでなく target そのものをリセットしうる（§2 の、target の状態を変えない再試行の規則が掛かる）。

### 3.2 SWIO のフレーム

線は 1 本、SWDIO（ピンの役割 1）。休んでいるときは high。probe は、送るとき線を high にも low にも駆動する。線を使っている間、probe は線に
プルアップを保つ。フレームの間、線は high で休む: probe が high に駆動するか、そのプルアップに放す。そこで high に駆動してよいのは、target が答えている間だけ。やり取りが失敗してからは、線をプルアップに放し、high に駆動しない（§2、線が答えない間の線）。

**probe が送るビットの区切り**: 線を low、続けて high。

| 区切り | low | その後の high |
|---|---|---|
| 1 | 240 から 310 ns | 240 から 270 ns |
| 0 | 840 から 1060 ns | 240 から 270 ns |


**target が送るビットの区切り**（読み出しの区切り）: probe は線を 240 から 270 ns low に駆動し、駆動をやめる。target は、線を low に保って 0 を、
上がるにまかせて 1 を送る。probe は、自分が作った立ち下がりから 520 から 600 ns 後に線を読む（high = 1、low = 0）。その後、線がまた high に読めるまで
待つ。100 µs 以内に high に読めなければ、その読み出しは失敗である。high になったら、probe は次の区切りの前に線を 130 ns 以上 high に駆動する。
low の駆動をやめた後と、0 を読んだ後に、probe は 1 回 30 ns 以下だけ線を high に駆動してよい（充電のパルス。プルアップを通る立ち上がりを
短くするため）。

**フレーム**: DMI のアクセス 1 回。最上位ビットから、区切り 41 個:

- 書き込み: START（1 の区切り）、7 bit の DMI のアドレス、direction 1、続けて probe が送る data の区切り 32 個;
- 読み出し: START（1 の区切り）、7 bit の DMI のアドレス、direction 0、続けて読み出しの区切り 32 個。

- パリティ、確認応答、STOP は無い。読み出しが見つけられるのは high に戻らない線だけで、違うビットは見つけられない。
- probe は、フレームのすべての区切りを上の時間の中に保つ（フレームを何にも割り込ませない）。フレームの後、次のフレームの前に、線は 8 µs 以上
  high のまま。
- **速さ**: ビットの時間は決まっているので、probe は速さを選ばない。describe の min_clock_hz で、0 の区切りの速さ（1 / (その low + その high)）を宣言する。
  attachのspeed_hzもこの値。max_speedがこれより低ければunsupported（§1）。scratchの確認はこの固定速で行う。

## 4. `oep.target.riscv-dm`

要求の先頭は connection(u32)。

- **必須のopはdmiだけ**。halt、resume、reset、read_block、write_block、run、stepは任意で、describeのopsで宣言する
  （core §1.2、§7.4）。read_block と write_block は組で持つ。host は、任意の op が
  無くても dmi で同じことを組める。
- **dmi 以外の op（高水準の op）の範囲**: RV32 の hart 0 だけを扱う（番地、レジスタの値、pc は u32）。probe は高水準の op の中で
  DMCONTROL の hartsel を 0 にし、**0 にして返す**（host が dmi で選んだ hartsel は、その dmi の要求の中だけ）。ほかの hart は
  host が dmi で扱う。

**opの後始末**: 高水準opのsuccessは、下表の後始末がすべて済んだ場合だけ返す。
戻すのは、そのopが一時的に使った値である。hostが求めたhalt/resume/resetやメモリへの書込みの効果は残る。
raw dmiに、probe自身の復元や追加の読み書きを挟まない。

失敗時も、要求全体のmax_op_msのうちに後始末を試みる。戻す必要のある値やhaltreqを戻せない場合は、
completed failed / partialを返してから、そのconnectionと依存streamを閉じる（共通部品 §2）。
statusは後始末の失敗を表し、doneは済んだ手順・語の数のまま。targetが元の状態とは保証しない。
read_block / write_block は、後始末が失敗した場合も done > 0 なら partial、done = 0 なら failed とする。
全語の転送が済んだ done = count > 0 の場合も partial であり、転送の完了だけでは success にしない。
復旧のためのreset/resumeは行わず、次のopやセッション終了まで復元を持ち越す表も要求しない。
hostは必要ならattachし直し、targetの状態を確かめて復旧する。

| op | probe が触るもの | 応答の前に |
|---|---|---|
| halt | haltreq | allhaltedを確かめてからhaltreqを下ろす。待ち切れたときも下ろすことを試みる |
| resume | haltreq = 0、resumereq = 1 を 1 回 | 何も覚えず、何も戻さない |
| step | dcsr.step、DATA0 / DATA1（dcsr の読み書き）、haltreq | dcsr.step を下ろし、DATA1、DATA0 を戻し、haltreq を下ろす。hart をもう一度止められなければ、応答が step_left を示す（§4.2） |
| reset | haltreq、ndmreset、havereset の確認応答 | ndmresetを解き、haveresetを確認応答し、haltreqを下ろす。mode 1のhartは止めたまま |
| read_block / write_block | GPR（s0、s1、a0、a1）、DATA1 / DATA0、abstractauto、program buffer、sysbus | GPR、DATA1、DATA0、abstractauto を戻す。program buffer と SBCS / SBADDRESS は戻さない（host が使うなら設定し直す） |
| run | pc、host が指定した GPR、dcsr（ebreakm、prv）、haltreq | **host の指示どおりに変えたまま返す**（host の責任）。abstractauto と haltreq は戻す |
| dmi | host が書いたもの | 何も触らず、何も戻さない（host が DATA を使ったら host が戻す） |
| コンソールの読み | DATA0 / DATA1 | [コンソール](oep-if-console.ja.md) §3 のとおり |

戻す値は、その op の中で読んだ「触る前の値」。高水準の op の中で DM の状態（abstractcs.busy の解除、allhalted、allresumeack）をどれだけ待つかは
probe が決める（max_op_ms のうち）。待ち切れなかったときの status は各 op の節のとおり（halt は timeout、resume / step は state）。DMI の busy は
probe の中で再試行し、諦めたら status wait（§6 の WAIT と同じ）。

**DATA0 と DATA1**: コンソールの方式（[コンソール](oep-if-console.ja.md) §3）は DATA0 / DATA1 を target との郵便受けに使う。probe は、自分の op で
使った DATA0 / DATA1 をsuccessの応答の前に戻す（失敗時は上の後始末の規則）。host は、dmi の要求で抽象コマンドなどを使って DATA0 / DATA1 を変えたら、hart を走らせる前に、
変える前の値を書き戻す。

| op | 名前 | 要求（connectionの後ろ） | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | dmi | n(u16)、n個の手順 | done(u16)、status(u8)、nvals(u16)、nvals × value(u32)、[TLV] | 必要 | 必須 |
| 0x11 | halt | — | status(u8)、[TLV] | 必要 | 任意 |
| 0x12 | resume | — | status(u8)、[TLV] | 必要 | 任意 |
| 0x13 | reset | mode(u8)、[TLV] | status(u8)、flags(u8)、pc(u32)（mode 1ではdpc）、[TLV] | 必要 | 任意 |
| 0x14 | read_block | address(u32)、count(u16)、[TLV] | done(u16)、status(u8)、done × word(u32)、[TLV] | 必要 | 任意（writeと組） |
| 0x15 | write_block | address(u32)、count(u16)、count個の語、[TLV] | done(u16)、status(u8)、[TLV] | 必要 | 任意（readと組） |
| 0x16 | run | pc(u32)、timeout_ms(u32)、n(u8)、n × (regno(u16)、value(u32))、n_out(u8)、n_out × regno(u16)、[TLV] | status(u8)、stopped(u8)、dpc(u32)、elapsed_us(u32)、nvals(u8)、nvals × value(u32)、[TLV] | 必要 | 任意 |
| 0x17 | step | — | status(u8)、moved(u8)、dpc_before(u32)、dpc_after(u32)、[TLV] | 必要 | 任意 |

空の結果と端の値: dmi の n = 0 は success、done 0。dmi の max_reads / max_us = 0 は 1 回読む。run の n_out に同じ regno が 2 回あれば
そのまま 2 回返す。

### 4.1 dmi

| kind | 手順 | 引数 | 応答に足す値 |
|---:|---|---|---|
| 0x01 | 書く | address(u8)、value(u32) | — |
| 0x02 | 読む | address(u8) | 読んだ値(u32) |
| 0x03 | 読む回数を上限に待つ | address(u8)、mask(u32)、value(u32)、max_reads(u16) | 最後に読んだ値(u32) |
| 0x04 | 待ち | wait_us(u32) | — |
| 0x05 | 時間を上限に待つ | address(u8)、mask(u32)、value(u32)、max_us(u32) | 最後に読んだ値(u32) |

- 知らないkindでは引数の長さを推測せず、その位置で検証を止め、要求全体をrejected unsupported（固定部分の印0）で断る。
  それより前の手順も実行しない。知っているkindの引数が短い場合はmalformed。probeは手順を全部確かめてから実行する。
- **done は最後まで済んだ手順の数**（失敗したときは、失敗した手順の 0 起点の番号）。値を足すのは 0x02 / 0x03 / 0x05 だけ。
  `nvals` は応答に入っている値の数（最初の done 個の手順のうち値を足す手順の数に、失敗した手順が 0x03 / 0x05 で待ち切れた
  （status timeout）なら 1 を足したもの）。線の不良などで読めずに失敗した手順は値を足さない。
- 実行前に、値を返す手順の数をrとして成功応答の固定結果`10 + 4×r`byteがその経路のmax_frameへ収まることを確認する。
  収まらなければunsupported（固定部分の印0）で断り、DMIへアクセスしない（core §4.4）。診断用の任意TLVは収まる分だけ付ける。
- 0x04 の手順の wait_us と 0x05 の手順の max_us の和は max_op_ms を超えてはならない（rejected unsupported）。0x03 の手順は時間ではなく回数で抑える。
  この和は明示的な待ちの量であり、内部の再試行・転送・後始末を含む要求全体の上限ではない。host の待ちは core §4.4 に従う。
  走っている間に要求が max_op_ms に達したら、probe はその手順で要求を終え、status timeout で答える（done = その手順の番号）。
- **同じconnectionのconsole streamを開いているhostは、抽象コマンドの一連（data1 / data0 の書き込み、command、data0 の読み）を1つのdmi要求に入れる**（probe が
  要求の間にコンソールの読みを挟んでも壊れない。`oep.target.console` §3）。
- **同じ場合、haltreq / haveresetを扱う一連の手順も、待ちの手順を使って1つのdmi要求に入れる**。
  例えばresetしてhaltを待つ場合は、haltreqを保ったresetの解除とhaveresetの確認応答、停止の確認、haltreqの解除までを同じ要求で行う。
  consoleの読みが要求の間にhaveresetを確認応答するとDMCONTROLを書き、haltreqを下ろすため、要求をまたいでその保持に頼らない。
  同じconnectionのconsole streamを閉じ、hostが競合する別のtarget操作を挟まなければ、raw手順を複数のdmi要求へ分けてよい。
  この分割に原子性はなく、session終了や通信失敗で途中まで作用した場合はhostが状態を確認して復旧する。
- **やり直してよい群**（[共通部品](oep-if-common.ja.md) §3 の例外）: hart が止まっている間に host が送る dmi の群で、書き込みが次だけのものは、
  何度実行しても target を 1 回実行したときと同じ状態にしか変えない。host は、その群の結果を確かめられなかったとき（応答が無い、status line /
  wait / timeout、host が群に入れた確かめ（DMSTATUS の読み、読み戻し）が合わない）、新しい corr で群全体をやり直してよい。
  1. ABSTRACTCS への cmderr の消去と、DATA0 / DATA1 への書き込み;
  2. aarsize 2（32 bit）、transfer 1、postexec 0 の access register で、値のほかに作用を持たないレジスタ（GPR、dpc、dcsr）を読むもの（write 0）、
     または同じ群でその前に DATA0 へ置いた値を書くもの（write 1）。
  ほかの書き込み（メモリ、ほかの CSR、program buffer の実行、abstractauto、haltreq / resumereq / ndmreset）を含む群はやり直さない。
  hart が止まっている間、probe はコンソールのために DATA0 / DATA1 を使わない（[コンソール](oep-if-console.ja.md) §3）ので、やり直しが郵便受けと
  ぶつかることは無い。やり直しの回数と間隔は有限にし、群の書き込みが置いた DATA0 / DATA1 は §4 のとおり hart を走らせる前に戻す。
  （参考）書き込みの後に同じ群で読み戻すと、前後の DMSTATUS の読みが通る線のちらつき（書き込み 1 つの取りこぼし）も見つけられる。

### 4.2 halt、resume、step

- **halt**は、すでに止まっていればhaltreqを下ろしてok。待ってもallhaltedが見えなければ、haltreqを下ろすことを試み、status timeoutで答える。
  下ろせない場合は§4の後始末の失敗として扱う。
- **resume** は haltreq = 0、resumereq = 1 を 1 回書く。ok は「hart が debug mode を出た」ことで、DMSTATUS の allresumeack（または
  allrunning で halted でない）で判断する。resumereq は出し直さない。待っても見えなければ status state。
  - （参考）target によっては、これで足りない（allresumeack を立てない target がすぐ breakpoint で止まり直す、1 回の resumereq で出ない
    ことがある）。その扱い（dpc を読んで、動いていなければもう一度 resume する、など）は target を知っている host が行う。
- **step** は dcsr.step を立てて resume を 1 回だけ出し、戻ったら dcsr.step を下ろす。dpc が動かなくても失敗にしない（status ok、moved = 0。自分自身へ
  跳ぶ命令は正しく進んでも dpc が同じなので、host が命令を読んで判断する）。prv は変えない。
  hart が debug mode に戻らなければ、probe は haltreq を立てて待つ。hart が止まれば、dcsr.step を下ろし、
  DATA1 / DATA0 を戻して status state で答える。止まらなければ、haltreq を下ろし、応答の TLV 0x01 step_left
  （長さ0）を付けてstatus stateで答える。dcsr.stepが立ったままかもしれず、hartは走っている。
  後始末を完了できないためconnectionを閉じる。hostはattachし直して止め、dcsr.stepを下ろす。
- step の moved、dpc_before、dpc_after は status ok のときだけ意味を持つ。ok でなければ、probe はどれも 0 にし、host は読まない（hart が
  止まっていれば、host は dpc を dmi で読む）。

### 4.3 reset

| mode | 意味 |
|---:|---|
| 0 | 走らせる |
| 1 | 最初の命令の前で止める（haltreq を保ったまま ndmreset を解く） |

応答:

| フィールド | 意味 |
|---|---|
| flags bit0 | 要求したmodeの状態を確認した（mode 0は走っている、mode 1は止まっていてdpcが読めた） |
| pc | flags bit0が立ったmode 1ではdpc。ほかは0 |

- mode 0と1だけを定める。ほかはunsupported（固定部分の印0）。successはflags bit0が立ち、後始末も済んだ場合だけ。
  flags bit0は後始末の成功を意味しない。満たさなければcompleted failed（形は同じ。statusは
  止まらない/走らない = timeout、DMが応えない = line、cmderr = fault）。待ちと後始末はmax_op_msのうちに行う。
- ndmresetを解いた後の待ちは§2。DMが答えなければstatus lineのcompleted failed。必要な後始末が済まなければconnectionを閉じる（§4）。
- flags のほかの bit は 0。reset の後は havereset を確認応答し、haltreq を下ろす（mode 1 は止めたまま）。

reset は ndmreset を使う。**reset の op はリセットの線を動かさない**: リセットの線が動くのは、attach の reset TLV（§3）か、host が自分で治具のインターフェースを使うときだけ。

### 4.4 run

- host のローダーを呼ぶためのもの。probe は dcsr の ebreakm と prv = M を立て、pc から走らせ、止まるのを待つ。**probe は run を
  出し直さない**（止まった位置が開始位置のままでも、走って戻った場合と区別できない）。hostもdpcだけで未実行と判断しない。
  dpcは停止位置の情報として扱い、再実行してよいことをtarget固有の状態などで確認できる場合だけ、新しい要求を送る。
  **デバッガの continue には使わない**（prv と ebreakm を変える）。
- timeout_ms が core の max_op_ms を超えれば rejected unsupported。要求全体は準備と後始末を含め max_op_ms のうちに終える。
  timeout_ms は実行の待ちの上限であり、要求全体の残り時間がそれより短い場合は、その残り時間の中で停止と後始末を試みる。
  host の待ちは core §4.4 に従い、timeout_ms だけから決めない。
  止まったらstopped = 1（後始末も済んだ場合はsuccess）。上限に達したら probe は hart を止めてから dpc と値を読み、stopped = 0、status timeout、outcome
  failed で返す（dpc と値はすべて有効）。止められなければ stopped = 2、status timeout、outcome failed、nvals = 0（dpc は無効）。
  走らせる前の準備（レジスタ、dcsr、pcの設定）が失敗したら、probeはresumeを出さずにstopped = 3、statusはその失敗、outcome failed、
  nvals = 0（dpc は無効）で返す。応答の形はいつも同じ（`run_stopped`: 0 時間切れで止めた、1 止まった、2 止められなかった、3 走らせなかった）。
  無効な dpc は 0。
- **elapsed_us** は、probe が hart を走らせた書き込み（resumereq）から、止まったのを見た（stopped 1）、上限で止めた（0）、止めるのを
  諦めた（2）ときまでの、probe が測った時間（µs）。stopped 3 では 0。
- regno は RISC-V の抽象レジスタ番号（a0 = 0x100A）。

### 4.5 read_block、write_block

- 語（32 bit）単位。8 / 16 bit のアクセスは dmi の手順で組む。
- **1 回の長さ**: read_block / write_block を持つ probe は、describe の共通 tag max_length（core §7.4）を必ず出す。単位は **byte 数**
  （4 の倍数）。hostはread_blockのcountを`min(max_length, max_frame − 8) / 4`以下、write_blockのcountを
  `min(max_length, max_frame − 20) / 4`以下の整数にする。readの8byteは応答の見出し5 + done 2 + status 1、writeの20byteは
  要求の見出し10 + connection 4 + address 4 + count 2である。大きい経路を小さい経路の転送量へ一律に制限しない。
  必要な結果がframeへ収まらない要求は実行前にunsupportedで断る（core §4.4）。count × 4 が max_length を超えれば rejected unsupported（payload `0x00`）。count = 0 は
  success、done 0。4 の倍数でない address は rejected malformed。
- **読みの意味**: read_block は target のバスを通して読む。probe の側に写しを持たない（直前の write_block、dmi、run で target が
  書いたものを反映する）。
- **前提**: hart が止まっていること（止まっていなければ status state）。番地は、止まっている hart が M モードで使う番地。

### 4.6 RISC-V の connection の扱い

- attach は保留中の havereset を先に確認応答する（確認応答するまで DMSTATUS の halt / running を固定する DM がある）。
- **haveresetの自動確認応答**は高水準のopとコンソールの読みで行う。raw dmiのopには追加の読み書きや確認応答を挟まず、hostが指定した手順だけを実行する。
  同じconnectionにdmseqのconsole streamがある場合、自動確認応答の後はそのstreamを未同期へ戻す。
  console streamがありmarksを提供する場合はrestart（kind 0x41、detail 1）のマークを付ける。
  probe自身のreset opによるhaveresetの確認応答の後も、存在するdmseq streamだけを未同期へ戻す。consoleを提供しないprobeに同期状態やマークの保持は要求しない。
  reset opが成功した場合はreset（kind 0x40、detail 1）を1つ付け、同じresetについてrestartを重ねない。
  attach時にはstreamが無いためマークを付けない。marksを提供しないfnにはマークの保持を要求しない。
  hostがraw dmiでtargetをresetしたりhaveresetを確認応答したりする場合、必要なconsoleの同期初期化はstreamのclose/openで明示する。

## 5. `oep.wire.swd`

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | scan | count(u8)、count × (swdio(u16)、swclk(u16))、[TLV] | tried(u8)、count(u8)、count × (kind(u8)、swdio(u16)、swclk(u16)、id(u32))、[TLV] | 必要 | 任意 |
| 0x11 | attach | method(u8: 0だけ。ほかはunsupported、固定部分の印0)、swdio(u16)、swclk(u16)、max_speed(u32)、[TLV] | connection(u32)、id(u32)、flags(u8)、speed_hz(u32)、[TLV] | 必要 | 必須 |
| 0x12 | detach | connection(u32)、[TLV] | — | 必要 | 必須 |
| 0x13 | connections | first(u8) | §2.1 | 不要 | 必須 |
| 0x14 | holds | first(u8) | §2.2 | 不要 | 必須 |

- scanのkindは2 = arm-adi。idはscan、attachともDPIDR。要求と応答の形は§3と同じ。
- scanのTLVは0x01 max_speed、0x02 targetsel。attachのTLVは0x02 targetsel、0x04 reset（任意、§3）。
- **wake / 設定の手順**（§1 の 1）: JTAG から SWD への切り替え、dormant からの wake、与えられたときの TARGETSEL。swd は scratch のレジスタを名指さない。
- **速さの確認**: max_speed以下でDPIDRの読みがACK OKと正しいパリティで終わる速さを選ぶ。
  scratchの書込み/読戻しは行わない。読出しとACKだけでは書込みデータの正しさを保証しないため、
  target固有の書込み確認はhostが必要に応じてtransferで行う。
- attach は JTAG から SWD への切り替えを試し、答えがなければ dormant から起こす（flags bit2）。電源投入（CTRL/STAT の CDBGPWRUPREQ /
  CSYSPWRUPREQ）は host が DP の書き込みで行う。
- **線と packet**: この wire の線は SWDIO（ピンの役 1）と SWCLK（ピンの役 2）の 2 本で、Arm Debug Interface（ADIv5 / ADIv6）の SWD の手順を使う。
  probe は SWCLK を常に駆動する。packet とは、その手順の 1 つの SWD packet で、要求、確認応答、手順がそれに与えるデータの相を、それらの
  turnaround のサイクルとともに含む。packet の 1 つ 1 つと、line reset、JTAG から SWD への切り替え、dormant からの wake の手順の 1 つ 1 つが、§2 の 1 つのやり取りである。
- **idle サイクル**: probe は、どの packet の後にも、また上の手順の 1 つ 1 つの後にも、少なくとも 8 回の idle サイクルを刻む: SWDIO を probe が
  low に駆動したクロックのサイクルである。これはそのやり取りの一部である（§2）。
- **休み方**（やり取りの間）: SWDIO は probe が low に駆動し、SWCLK は high に駆動する。
- **probe が線の駆動をやめる前に**（detach などで connection が閉じるとき、probe がピンを放すとき、または §2 の「線が応えない間の線」の
  放した状態にするとき）、最後の packet の後の 8 回の idle サイクルを刻み、target がその packet を終えられるようにする。
- **targetsel（TLV 0x02、u32）はcriticalで送る**（multidropのときだけ。無視されると別のtargetにattachするため）。
  connectionは指定の有無と値を保持する。v1では同じピンの組に1接続だけを持ち、targetselが同じでも違っても、
  そのピンを含むattachはunavailable（cause 1）。切替えはdetach後にattachする。
  scan は targetsel なしで試す（TARGETSEL が要る multidrop の
  target は scan に出ない。scan の TLV 0x02 targetsel で 1 つだけ指定して試せる）。
- swdのconnectionにはコンソールは乗らない。

## 6. `oep.target.arm-adi`

要求の先頭は connection(u32)。transferは必須。read_block/write_blockは組で提供する任意opで、opsに宣言する。
最小の実装はtransferだけでよく、hostがAPの選択、CSW/TARの設定、posted readの回収を生の転送で組む。
read_block/write_blockはその手順をprobe内でまとめるための操作で、提供しなければunknown_operation。任意opのためのfeaturesは追加しない。

| op | 名前 | 要求（connectionの後ろ） | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | transfer | n(u16)、n個の転送: req(u8: bit0 APnDP、bit1 RnW、bit2-3 A[3:2]、bit4-7は0)と、書込みならvalue(u32) | done(u16)、status(u8)、ack(u8)、nvals(u16)、nvals × value(u32)、[TLV] | 必要 | 必須 |
| 0x11 | read_block | address(u32)、count(u16)、[TLV] | done(u16)、status(u8)、done × word(u32)、[TLV] | 必要 | 任意（writeと組） |
| 0x12 | write_block | address(u32)、count(u16)、count個の語、[TLV] | done(u16)、status(u8)、[TLV] | 必要 | 任意（readと組） |

- ack は最後の転送の生の ACK（`swd_ack`: 線の順で bit0 が最初。OK = 1、WAIT = 2、FAULT = 4。無応答は status line）。req の bit4-7 が
  0でなければ、その位置で検証を止め、要求全体をrejected unsupported（固定部分の印0）で断る。それより前の転送も実行しない。
  知っているreqの書き込みのvalueが短い場合はmalformed。nvals は読んだ値の数（最初の done 個の転送のうち読み出しの数）。
  n = 0 は success で、done 0、status ok、ack 0（転送が 1 つも無ければ ack は 0）、nvals 0。
- transfer は生の転送で、AP の読み出しが 1 つ遅れて返るのもそのまま（host が RDBUFF か次の AP の読み出しで受け取る）。
  WAIT は probe の中で再試行し、諦めたら status wait。FAULT で止まるので、host は ABORT で sticky を消す。
- 実行前に、読み出す転送の数をrとして成功応答の固定結果`11 + 4×r`byteがその経路のmax_frameへ収まることを確認する。
  収まらなければunsupported（固定部分の印0）で断り、線へ転送しない（core §4.4）。診断用の任意TLVは収まる分だけ付ける。
- read_block / write_blockを提供する場合の1回の長さと読みの意味は riscv-dm（§4.5）と同じ: describe の max_length（byte 数、4 の倍数）を必ず出し、
  count × 4 がそれを超えれば rejected unsupported（payload `0x00`）。hostは同節のread/writeそれぞれの式で、その経路のframeへ収まるcountを選ぶ。
  read_block は target のバスを通して読み、probe の側に写しを持たない。
- read_block / write_block は今の MEM-AP の TAR / DRW を使う。SELECT と CSW（32 bit、単一増加）は host が先に設定する。probe は
  TAR の自動の増加が保証される範囲（ADI）を越えるところで TAR を書き直し、1 つ遅れる読み出しを並べ直す。**CPUの停止状態は問わない**（MEM-APはCPUが走っていても読める）。
  **done は probe が送った語の数**で、target が受けた保証ではない（posted write の FAULT は後の転送で見える）。TAR は進めたままにし、
  SELECT / CSW は変えない（§4 の不変条件の arm 版: probe は host が設定したものを変えない）。

## 7. 参照する仕様

この文書の OEP のメッセージは、本文だけで定まる。RVSWD と SWIO のフレームは §3.1 と §3.2 が定める。target を動かすのに使うもの:

| インターフェース | 仕様 | 使う部分 |
|---|---|---|
| `oep.wire.swd`、`oep.target.arm-adi` | Arm Debug Interface Architecture Specification, ADIv5.2 と ADIv6.0 | SWD のパケット、turnaround、line reset、JTAG から SWD への切り替え、dormant からの wake、TARGETSEL。DP と AP のレジスタ。MEM-AP の TAR、DRW、CSW |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.target.riscv-dm` | RISC-V Debug Specification 0.13.2 と 1.0（DMSTATUS.version 2 と 3） | DMI のレジスタ（DMCONTROL、DMSTATUS、ABSTRACTCS、COMMAND、ABSTRACTAUTO、DATA0、DATA1、PROGBUF0、SBCS、SBADDRESS）、抽象コマンド、program buffer、dcsr、dpc、havereset |
