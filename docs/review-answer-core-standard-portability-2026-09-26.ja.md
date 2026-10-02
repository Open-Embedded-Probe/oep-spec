# OEP v1 コア・標準インターフェースの移植性と復旧性レビュー（2026-09-26）

状態: **記録**（規範ではない。レビューの回答と提案）。 対象は `oep-spec` 2ff1d62 の
[`oep-core.ja.md`](oep-core.ja.md) と §14 の標準インターフェース文書、`oep-probe-arduino` 3160dee、
`oep-client-python` 75ee13e。実機で確認したことは
[実機・ソースレビュー](hardware-source-review-2026-09-26.ja.md)と
[操作・テスト監査](v1-operation-test-audit-2026-09-26.ja.md)に分けた。本書は、遅さやジッタではなく、
**別 MCU で同じ要求を実装できるか、実装できない能力を host が宣言から分かるか、失敗後に安全な状態へ戻れるか**を判定する。

## 判定基準

- host が知ってよいのは target と治具の配線・電気条件、および OEP の名前・revision・`describe`・操作結果。
  probe の MCU、ペリフェラルの初期化順、DMA 番号、PIO プログラム、USB の実装詳細は知らない前提。
- 宣言は少なくとも「要求を送る前に安全な候補を絞れる」こと、動的な資源競合は拒否理由と読み戻しで扱えることが必要。
  静的宣言に全ての組合せを列挙する必要はない。
- **rejected は無変更**、completed failed / partial は進行範囲と現在の状態を知れる、応答喪失時は照会か安全な再初期化で
  立て直せることを要求する。ただし probe の電源断直前に target へ送った非冪等な書き込みの成否を一般に確定することは
  不可能であり、その場合は「不確定」と明示して target 側の知識で照合する。

## A. コアから先に点検した結果

### C1 — P1: `plan_apply` の原子性とハードウェア再構成の契約が足りない

[core §8](oep-core.ja.md) は、要求に出た fn の plan だけを原子的に置き換え、他 fn を保つと約束する。
しかし同じピンを capture と I2C/SPI で安全に共有できても、MCU によっては後から capture 側の pin 設定をすると
ペリフェラルの設定が消える。P4 実測では既存 I2C に capture plan を追加した時点で NACK、SPI では MISO が失われ、
どちらも `plan_apply` は success を返した。I2C は probe 側の再 configure / arm で復旧した。

これは「共有を禁止」して片付く問題ではない。共有できる組と、**途中の停止を許して probe が順序を組み直せる組**は異なる。
host が P4 特有の順序を持つべきでもない。core に次の二段階契約を足すのがよい。

1. 通常の plan 要求では、既存機能を一時停止する必要があれば**何も変えずに拒否**し、再構成を許せば適用できる旨、
   影響する fn と失われる可能性のある受信・区画を機械可読に返す。
2. host が許す場合、別 corr の要求に critical な「再構成・一時中断を許す」指定を付ける。probe が内部順序を決め、
   維持する fn を再設定してから success を返す。途中の欠損は status / mark / event で見えるようにする。
3. 再構成に失敗した場合、**旧状態を復元できたか、安全な停止状態になったか**を outcome と状態照会で区別する。
   `rejected` を返して旧機能だけを壊すことは許さない。

現行の `unavailable` の自由な payload だけに乗せると host が標準的に解釈できない。core の共通の補助情報として定義したい。
どの MCU でもハードウェアレベルの瞬時切替は要求せず、論理的な成功状態と中断の許諾を規定する。

### C2 — P1: 結果喪失・継承後の状態を照会できない

[core §5.2](oep-core.ja.md) は重複排除表から落ちた要求に `result_lost` を返し「状態を読み直す」とするが、
core には **plan の取得**がない。`end` 後の plan は次セッションへ移る（§9）のに、その次の host はどの fn / role / channel を
継承したか列挙できない。`lock_state` もロックだけで資源を返さない。`plan_release(n=0)` なら一掃できるが、
既存の target 配線を維持したい host には回復手段にならない。

少なくとも read-only の plan 一覧（ページング可能）と状態世代番号が必要。`plan_apply` / `plan_release` の応答に世代番号を返せば、
応答喪失後に適用済みか照合できる。接続やストリームの継承を認めるなら、それらにも列挙・識別または
「新セッションは既存資源を安全に全解放して始める」という選択肢が要る。
変更が target へ既に出たか判断不能な場合は再送を勧めず、`indeterminate` と照合手順を示す。

### C3 — P1: `rejected` / `completed failed` の失敗後状態が一般則で閉じていない

[core §4.2, §8.1](oep-core.ja.md) は「拒否なら無変更」と書く一方、実行を始めた後の
`completed failed` / `partial` について一般の後状態を定めない。特に plan の実体適用、設定の set、pin の mode 切替は、
実ハードウェアが途中で失敗しうる。現行 P4 では不正な UART plan 更新を拒否した後、以前の UART が止まる実測もある。

各状態変更 op に、拒否前チェック、実行中の失敗、応答喪失の **3 行の後状態契約**を必須にする。
一括原子を名乗る op は旧状態復元を実装・試験する。復元不能な MCU では、その op を細かく分けるか、
安全停止と状態照会を規範化して「原子的」という約束を緩める。内部で戻せないことを host の probe 別知識に転嫁しない。

### C4 — P1: `describe` はピン候補を表せるが、共有・電気的制約を表せない

[core §7.4, §8.1](oep-core.ja.md) の `role_channels` / `channel_group` は単独 fn 内の組を表す。
同時に扱える observer と driver の関係、入力専用ピン、開放電圧・許容電圧、pull / 駆動可能性は共通形式にない。
内部 DMA の組を全列挙する必要はないが、host が新しい治具を結線・計画するときに、少なくとも危険な候補と
原理的に不可能な候補を宣言で除外できるべき。GPIO の global `modes` だけではピンごとの差も表せない。

提案: `channel` に対する電気的・入出力能力の宣言（値が不明なら不明と明示）、fn 間共有の**静的な許可関係**、
実資源が足りない場合の動的 `unavailable` を分ける。電圧範囲は probe の端子の限界であり、target の安全電圧は
host の target/治具知識として扱う。静的な許可関係が無い probe でも「試して無変更で断られる」ことを保証する。

### C5 — P2: 小 RAM probe とページングの最小不変条件が未規定

core は `max_frame` / `window` / `max_inflight` を交渉するが、ゼロ不可・相互関係・最小長を明記しない。
`list` は1 entry、`describe` は1 TLV が1フレームに入ることを前提とし、名前やビットマップが長い場合の
分割・省略の規則がない。少 RAM の MCU が極小 frame を宣言したとき、host が必要な宣言を全部取得できるかは保証されない。

`max_inflight ≥ 1`、`window ≥ max_frame` または明示した別の相互関係、必須応答・最長の必須 entry に必要な
最小 `max_frame` を決める。長い bitmap は複数 TLV、長い label は省略可など、probe が小容量でも
完全な discovery を構成できる規則にする。複数ページ中に再起動・宣言変更が起きたときの検出方法も要る。

### C6 — P2: `boot_id = 0` と再発見の境界

[core §6.5](oep-core.ja.md) は boot_id=0 を「不明」と許す。この probe では再起動後に fn の対応や
資源が失われたことを、`no_session` が来るまでは判定しにくい。read-only の `list` / `describe` のページング中に
再起動すると、別の起動のページが混ざりうる。起動をまたいで同じ fn と誤認しない仕組みが必要。
boot_id が生成できない MCU には、起動ごとの乱数を強制するより、`confirm` の起動世代または
read-only ページの世代と、host の全再発見規則を設けるのが妥当。

## B. 標準インターフェースを点検した結果

| インターフェース | MCU 非依存性と宣言 | 失敗後の復旧 | 判定 |
|---|---|---|---|
| `oep.wire.rvswd` / `swio` | WCH 専用と名前で分かる。ピン組は宣言される | `wait/line/fault` と再 attach は定義あり。reset channel の候補が未宣言 | 条件つき |
| `oep.wire.swd` | ARM の線として妥当。任意 pin 組の scan 列挙に u8 上限問題 | attach / detach / line の筋はある。NRST 同時 attach は v1 に無く、その限界は明記 | 条件つき |
| `oep.target.riscv-dm` | 生の dmi で target 知識を host に置ける。RV32 hart0 の高水準 op は任意と宣言 | `done/status` は有用。ただし書込み・run の結果喪失は target 照合が必要 | 概ね可 |
| `oep.target.arm-adi` | 生の transfer は汎用。MEM-AP の前提は host が設定 | 部分転送は `done/status/ack` で分かる。結果喪失は target 側照合 | 概ね可、実機未確認 |
| `oep.target.console` | 名前は汎用だが方式と実装は DMI DATA0/1 および WCH 系の SDI 等に固定。方式の宣言も無い | 閉じた stream の read はよい。方式可否は open の試行まで不明 | 要整理 |
| `oep.fixture.gpio` | mode 集合は fn 全体で宣言。pin ごとの mode / 電気条件が不明 | `set` は順次実行だが途中失敗と応答喪失の出力状態照会がない | 要補強 |
| `oep.fixture.uart` | RX/TX 片方向は仕様上可能。format は宣言、baud 範囲は無い | configure 後の設定を読む op がなく、`result_lost` 後に判定不能。現行 probe は片方向 plan を拒否 | 要補強 |
| `oep.fixture.capture` | layout と実レートの返却は移植性に効く。query が任意で、組合せの事前確認ができない probe がある | status はあるが設定内容とエラー理由が読めない。中断・欠損の表現は要試験 | 要補強 |
| `oep.fixture.analog` | 同じ枠で複数 ADC 形態を表せる。ただし現行3台での実装・実測なし | capture と同じ。較正や入力範囲は宣言頼み | 未検証 |
| `oep.probe.config` | USB 関連は任意と明記され、非USB MCUでも label / plan / idle は可能 | get/hash と storage 状態は有用。set の資源適用失敗と自動 attach 後状態はさらに明確化が必要 | 条件つき |

現行の MCU ごとの境界も区別する。P4 は capture と I2C/SPI の同居自体は可能だが再構成の契約が欠ける。
classic ESP32 の SPI target は 3 MHz 上限を `max_clock_hz` で宣言し、20 MS/s capture は持たず 2 MS/s を宣言するので、
その速度差は仕様で扱える。RP2350 probe は capture / analog を list に出さないので、無い機能を host が要求しない形にできる。
小 RAM の MCU は `max_frame` と任意インターフェースを小さくできる設計だが、C5 の discovery 下限が決まるまでは
「コアがどの容量の MCU でも実装可能」とまでは言えない。**非対応を list/describe で表せることと、実装済みの機能を
安全に組み合わせられることは別**である。

### S1 — P1: wire の `scan(count=0)` が多数のピン組で表現できない

[debug §1](oep-if-debug.ja.md) は `count=0` を「許す全組」とし、応答の `tried` を u8 にする。
自由な SWDIO/SWCLK ピンをそれぞれ20本持つ probe は候補が400組になる。`tried` は255までで、
最初の走査が256組目以降に届いた場合の位置も、残りの組を取得する方法も定義できない。
これは特定 MCU の実装不足でなく、汎用ピン割当を認める wire 形式そのものの上限。
列挙を u16 cursor でページングするか、`count=0` は安全に有限な既定組だけと明記し、完全探索は host 指定の組にする。
ピン組の順序も role_channels の集合だけでは一意でないので定義が要る。

### S2 — P1: 「汎用 console」の名前と実体が食い違う

[console §1–3](oep-if-console.ja.md) の `oep.target.console` は debug connection を要し、
SDI / DMDATA / dmseq は DMI DATA0/1 を使う。ARM SWD や別系統の MCU に同じ名前で汎用 console を期待する host には
実装できない。これは [core §13.8](oep-core.ja.md) の「汎用名にチップ固有の処理を入れない」とも合わない。
少なくとも対応する wire/target の名前、使える mechanism、向き、最大 write を `describe` で宣言する。
より明瞭なのは、位置つきストリームを共通部品に残し、DMI mailbox の console を特化名に分けること。
物理 UART は現行どおり `oep.fixture.uart` でよい。

### S3 — P1: 宣言と非破壊の問い合わせが足りない機能

- [fixture §1](oep-if-fixture.ja.md) の `modes` は fn 全体のビット集合。GPIO ごとに実装できる mode が違う MCU では、
  host は対応しない pin/mode 組を事前に除外できない。per-channel mask を足すか、global modes は全候補 pin で保証する。
- [fixture §2](oep-if-fixture.ja.md) の UART は format は宣言するが、baud の可否・許容誤差・実 baud を非破壊で
  照会する方法がない。現行 `FixtureUart` は 1200〜2,000,000 baud を固定で判定するが、その範囲を
  `describe` に出さない。configure の戻り値だけでは、既存 stream を止めずに候補選定できない。
  さらに同実装は片方向 plan を拒否するだけでなく、configure も RX が無ければ拒否するため、
  TX 専用を仕様どおり有効にするには両方の経路を直す必要がある。
- [capture §3.5](oep-if-capture.ja.md) は「宣言にない組合せを query で確かめる」とするが、
  query は features bit0 の任意 op。query が無い probe は既存のデータを壊しうる configure で試すしかない。
  query を全 capture/analog に必須とするか、query 不在のときは宣言が完全であることを保証する。
- [debug §3](oep-if-debug.ja.md) の attach_under_reset は許す reset channel と probe の既定 reset line を
  宣言しない。host の治具情報で channel を知れても、その probe が同時 attach で扱えるかは実行まで不明。
  対応 op と channel の候補を宣言し、不可なら通常 attach / GPIO 操作への退避を明示する。

### S4 — P1: GPIO の「順次 set」と core の拒否・部分成功を整合させる

[fixture §1](oep-if-fixture.ja.md) の set は順序どおり pin を切り替えるため、reset pulse などに必要。
事前の不正 pin/mode は「何もせず rejected」とするが、途中でハードウェア設定に失敗した場合、
前の pin は既に切り替わっている。戻すと reset pulse の電気的意味が変わり、戻さなければ一括成功と見なせない。
`completed partial` に実行済み件数と失敗位置を返し、各 pin の現在 mode を照会できるようにするか、
「MCU が必ず成功させられる mode だけ宣言する」と規定する。応答喪失後に `read(level)` だけでは出力 mode を判別できない。

### S5 — P2: capture の既定値・応答・失敗理由を閉じる

[capture §3.3](oep-if-capture.ja.md) は mode / rate / samples 等を TLV として置くが、どれを省略できるか、
省略時の値、成功応答でどの actual TLV が必須かが一意でない。異なる MCU の host が `layout`、レート、区画サイズを
必ず取得できるよう、モードごとの必須 request / response と不変条件を決める。
`status.state=6` の原因、再 configure が旧区画を消すか、start/release 失敗時に何が残るかも定める。
ストリーミングは subscribe が前提なので、未購読 start を副作用なしで拒否することと、
mode 3 を宣言する probe は通知を実装することを明記する。

### S6 — P2: config の保存・復旧は前進しているが境界が残る

[config §2–3](oep-if-probe-config.ja.md) の get/hash、保存一覧 ID、保存が読めない状態の宣言は良い。
一方 set が plan と bind を即時適用するため C1/C3 と同じ再構成失敗が起きる。
`set` の拒否、適用途中失敗、自動 attach 失敗をそれぞれ独立した状態として照会できるようにする。
`save` の電源断・容量不足後は、次回起動の storage state と hash で照合する。`reboot` の応答喪失は
「応答が来なかったからもう一度 reboot」を禁止し、新しい起動の識別と get で判断する。

## C. 失敗時の立て直しを要求ごとに固定する

| 場面 | host が probe 宣言・応答だけでできるべきこと | 現状 |
|---|---|---|
| 事前に不可と分かる pin / mode / rate | `describe` と非破壊 query で別候補に切替 | fn 内 pin 組は可。pin ごとの mode、UART baud、capture query 任意など不足 |
| 資源競合・再構成が必要 | 既存状態を保った拒否を受け、影響範囲を見て許諾・再要求 | `unavailable` だけでは理由と影響 fn が共通形式で分からない |
| 実行中の失敗 | done / 現在状態 / 安全停止の有無を読んで復旧 | debug の done/status は良い。plan、GPIO、config は不足 |
| 応答の喪失 | 同 corr の再送、`result_lost` なら read-only の状態照会 | 再送はあるが plan、GPIO mode、UART 設定など照会不能 |
| lease 失効・force | 解放範囲を確認し、pin を安全な idle に戻して再開 | 一般寿命は明記。実装横断の安全状態テストが不足 |
| probe 再起動 | boot 世代を確認し、fn と全状態を再発見 | boot_id=0 とページ混在の境界が曖昧 |
| target 側の非冪等な書込み中に probe 再起動 | 結果を「不確定」とし、target 固有の readback / status で照合 | core の一般的な照合方法は原理的に提供できない。明示すべき |

## D. 先に固める規範と適合試験

1. **core**: 拒否の無変更、再構成の許諾と影響範囲、plan の照会・世代、失敗時の安全状態を先に決める。
   P4 の capture→I2C/SPI、I2C/SPI→capture、拒否・強制・故障注入を適合試験にする。
2. **core discovery**: 小 frame / 1 inflight の probe でも list/describe を完走できる最小条件と、ページ中の再起動検出を決める。
   CH32V003 相当の RAM 制約で実装して検証する。全 MCU 対応という主張はこの最小構成の実証までは留保する。
3. **標準**: wire scan の大きな候補集合、console の特化名と方式宣言、GPIO/UART/capture の欠けた宣言・query を決める。
   それぞれ宣言に無い要求・critical TLV の拒否が状態を変えない試験を置く。
4. **復旧**: 全状態変更 op で「成功、事前拒否、途中失敗、応答喪失、probe 再起動」を同じ表で試す。
   target の非冪等な副作用は、一般化できない境界として host の target 知識へ明示的に渡す。

今回の結論は、OEP の層分け自体は別 MCU に移しやすいが、**能力が無いことの宣言と、状態変更が不確かになったときの
読み戻し**がまだ十分ではない、というもの。速度のチューニングより先にこの契約を固めるべき。
