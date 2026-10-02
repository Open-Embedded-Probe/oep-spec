# OEP レビュー回答: 新規 probe / host の実装、MCU 非依存性、機能の組み合わせ

状態: **記録**（規範ではない。レビューの回答と提案、2026-09-26）。

日付: 2026-09-26。対象: review-guide が規範として挙げる core、oep-if-*。
core の作業中の更新（資源番号 u16 化、長い操作の予約化など）も確認した。仕様への提案であり、仕様本体は変更していない。
実機検証ではなく、独立した実装者が文書から同じ動作を作れるかのレビュー。前回の回答とは別に、移植性と組み合わせに焦点を絞る。

## 1. 結論

**core の基本構造は特定 MCU に閉じていない。しかし標準インターフェースには、現在の WCH 系 target と ESP32 / RP2 系 probe の
使い方を一般化しきれていない部分がある。このまま仕様だけで別の probe と汎用 host を作ると、独自解釈が必要になる。**

特に直したいのは、target 固有の判定、debug 操作の前提、機能間の資源競合、plan の更新単位、アナログのチャネル別表現である。
すべての MCU・周辺機能を標準で扱う必要はない。**対応しない機能を安全に断れて、対応する共通部分はそのまま使える**ことを目標にする。

ここでいう MCU は、probe を動かす MCU と、デバッグされる target の MCU を分けて考える。

| 新しく作るもの | 現状の主な障害 |
|---|---|
| 小容量 RAM、UART 接続だけの probe | 小フレームでの宣言・設定の分割、USB 前提の設定項目、長時間処理中の応答性 |
| ピン配置が固定された ARM SWD probe | reset の共通規則が RISC-V 用、reset 中の接続、multidrop の接続同一性 |
| RV64 / 複数 hart を扱う probe と host | 高水準操作の u32 固定、hart 選択と状態保存の契約不足 |
| UART・GPIO・capture を併用する治具 | plan の全体解除、共有ピン・DMA の競合、解除後も TX を駆動する規則 |
| チャネルごとに入力範囲が異なる ADC probe | 共通 scale、意味が実装依存の attenuation、大チャネル数で TLV 長が超過 |
| 既存コードを読まずに作る汎用 host | 任意 op・対応値の宣言、接続前の経路発見、永続設定の識別が不足 |

## 2. 優先して修正したい点

優先度 P1 は、安全な動作・相互運用・代表的な移植先を妨げるもの。P2 は、制限として明示すれば初版で残せるもの。

### R1 / P1: 汎用設定に target 固有の chip_id 判定がある

根拠: [probe-config §1.1](oep-if-probe-config.ja.md)。自動 attach 後に chip_id を読み、bit [7:4] を必ず無視し、
0 / 0xFFFFFFFF を不明として扱う。

別の MCU では、その位置が revision とは限らない。さらに、chip_id の取得場所・方法・識別体系が定義されていない。
独立した probe 実装者は、何を読み、何を比較すれば適合するか決められない。これは core の「target の知識は host」の方針とも合わない。

最小の修正は、一般の設定からこの暗黙の識別方法を外し、自動 attach を対応 backend の任意機能にすること。
共通化するなら識別方式と期待値を明示し、方式ごとに取得・比較を定義する。bit mask を追加するだけでは、取得方法の未定義は解決しない。
汎用のチップ識別スクリプト実行機構を新設する必要はない。

また bind は wire_fn だけを持ち、pins / max_speed / targetsel を保存できない。複数のピン組を持つ probe では、debug §1 が要求する
pins を自動 attach に渡せない。bind は検証済みの接続設定を参照するか、同じ安全条件を保存できる形にする。

### R2 / P1: 全 wire 共通の寿命が RISC-V のレジスタで定義されている

根拠: [debug §2](oep-if-debug.ja.md)。reset 後の havereset 確認、切断時の dmactive 維持・haltreq 解除が、ARM SWD を含む
connection 全体の規則として書かれている。

ARM 実装にはそのレジスタがない。「参照者がなくなれば閉じる」「不要な target reset を行わない」は共通部品に置き、
RISC-V の具体的な処理は riscv-dm、V00x の回復手順は該当 backend の規則へ移す。
1000 ms の無応答判定も、許容する reset / power 状態との関係を定める。数十 ms の reset を除外する記述だけでは長い reset を扱えない。

### R3 / P1: riscv-dm の生転送と、32bit target 向けの便利操作が分離されていない

根拠: [debug §4](oep-if-debug.ja.md)。memory address、run の PC・レジスタ値、step の DPC が u32。
「1 要求は 1 hart」とあるが、高水準 op がどの hart を対象とし、raw DMI の hartsel を維持するかは明示されていない。

RV64 のレジスタ値や 4 GiB 以上の番地をこれらの op では運べない。ただし **DMI の value が u32 なのは別問題で、それ自体を
RV32 限定の欠陥とするべきではない**。生 DMI で組める操作と、この便利操作の表現限界を分ける必要がある。
RISC-V 公式仕様も、32bit の実装例を 64 / 128bit 向けへ適応すること、hart 選択を前提に操作することを説明している。
参考: [RISC-V Debugger Implementation](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html)。

小さく直すなら、生 DMI を基礎にし、read_block / run 等を明示的な任意機能にする。対応するアドレス幅・レジスタ幅・対象 hart の規則を
定義し、未対応時は host が生転送へ戻れるようにする。全 probe に RV64 の高水準操作を強制する必要はない。

加えて read_block / write_block は、halt が必要か、物理/仮想のどちらの番地か、scratch GPR・progbuf・DATA・abstractauto を保存するかが
不足している。異なる実装が異なる target 状態を残すと、同じ host が安全に使えない。高速化の方式そのものより、前提と副作用を定めたい。

### R4 / P1: PC が変わらないことを「未実行」と判定して再実行する

根拠: [debug §4.2、§4.4](oep-if-debug.ja.md)。resume の一部と run は、DPC が開始位置から動かなければ resume を出し直す。

一度走り、処理を行って同じ位置で停止した場合にも DPC は等しくなる。run では loader の副作用を二度起こし得る。
step の説明自体も「PC が同じでも実行済み」のケースを認めている。
RISC-V の標準的な resume 確認は resumeack に基づく。参考: [公式仕様の Running](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html)。

標準動作では PC の一致だけで再実行しない。特定 target の不具合回避なら、その条件を明示した限定的な処理にする。
また reset method の「PFIC など」は共通の具体的手順にならないため、host 側の手順か名前付きの固有機能へ分ける。

### R5 / P1: plan と直接 attach の間に、共通の資源競合規則がない

根拠: [core §7.4、§8](oep-core.ja.md)、[debug §1](oep-if-debug.ja.md)。plan は各インターフェースが検証する。
debug の pins は plan を通さず指定できる。

GPIO と SWD が同じピンを出力として取得する場合、双方の個別検証だけなら通り得る。別ピンでも、UART と capture が同じ DMA / timer を
必要とする MCU がある。個々のピン候補だけでは併用の可否は表せない。

最低限、「すべての資源取得は既存の plan・connection・永続 bind と競合確認し、失敗時は既存機能を変更しない」を共通契約にする。
どの DMA を使うかまで host へ公開する必要はない。共有入力など安全な併用は、実装が明示的に許す場合だけ許可すればよい。

### R6 / P1: plan が probe 全体で一つ、解除も全体なので機能を追加しにくい

根拠: [core §8](oep-core.ja.md)。適用済み plan があれば新しい plan_apply は unavailable。

UART ログを受信中に空きピンで capture を追加するにも、UART を含む plan を解除して作り直す必要がある。
永続設定から入れた plan と、一時的な host の計測を組み合わせる場合も同じ問題になる。

plan の識別番号を増やすことが唯一の解ではない。**変更する instance だけを原子的に追加・置換・解除し、無関係な instance は維持する**
方式でも足りる。基本単位を fn にするなら、同じ instance の別 fn が plan を共有する規則との整合を取る。
初版で全体 plan を残すなら、「独立機能の無停止追加はできない」という制限を明記する。

### R7 / P1: UART の plan 解放後も TX を high に駆動する

根拠: [fixture §2](oep-if-fixture.ja.md)、[core §8](oep-core.ja.md)。TX は plan を解いた後も high に保つ。

所有権を返したはずのピンに駆動責任が残る。次に GPIO の low 出力や open-drain バスへ渡すとき、誰が UART の駆動を解除するのかが
決まっていない。特に外付けバッファや pin mux のある probe では、単なる GPIO の上書きでは済まない。

idle high は UART が所有している間の規則にする。解放時は原則 high-Z、または基板が宣言する安全状態へ戻し、次の所有者へ確実に渡す。
雑音対策に必要な pull-up と、解放後も能動駆動することは分ける。

### R8 / P1: アナログの frontend と換算がチャネル別に完結しない

根拠: [capture §1.2、§3.3、§3.5](oep-if-capture.ja.md)。frontend は role ごとに attenuation を指定できるが、
応答 scale は zero / scale_nv の一組で、どの role の換算かを持たない。attenuation 自体も「実装の値」。

異なる入力範囲・ゲイン・校正値を持つ ADC チャネルを同時に取得すると、一つの換算式では正しく表示できない。
また host が probe の SDK enum を知っていないと、候補の数値を入力範囲として説明できない。

scale は role をキーに返す。frontend の候補は opaque な番号でもよいが、番号に対応する物理入力範囲や倍率を宣言する。
全チャネル共通の設定しか扱えない probe は、その制限を宣言して異なる指定を断ればよい。
特殊な ADC packing をすべて標準化する必要はなく、基本形式への詰め直しか別形式を許す現在の方針は維持できる。

### R9 / P1: 宣言上の大きさと TLV / フレーム上限が合っていない

根拠: [core §2.2、§7.3](oep-core.ja.md)、[capture §3.3](oep-if-capture.ja.md)、[probe-config §1、§2](oep-if-probe-config.ja.md)。

- アナログ timing の value 長は `1 + 4 + 4*C`。C=63 で 257 byte、C=64 で 261 byte となり、len(u8) の最大 255 を超える。
  アナログ role 0〜63 をすべて使う構成を現在の形式では記述できない。
- 保存 plan は一つの TLV に `n * 5` byte。51 割り当てで 255 byte、52 で超過する。通常の plan_apply は複数 TLV なのに、保存時に
  別の小さい上限が生じる。
- label は同じ tag の項目を set ごとに全部置換するため、ラベル群を数フレームに分けて蓄積できない。

TLV 全体を大きくするより、チャネル情報は role ごと、または base/count 付きに分割可能にし、設定はキー単位で更新・削除できる形が小さい。
configure 応答も、必要な情報が一フレームに収まる最大構成を宣言するか、結果取得をページ化する。
小容量 probe に全チャネル対応を要求する話ではなく、対応すると宣言した構成を必ず wire 上で表せるようにする話である。

### R10 / P1: SWD の接続同一性と reset 操作が不足している

根拠: [debug §1、§5](oep-if-debug.ja.md)。既存線への attach は同じ connection を返す一方、SWD は targetsel を受け付ける。

同じピン上の target A に接続済みで target B を指定した場合、既存 connection を返すのか、切り替えるのか、拒否するのか決まっていない。
接続の同一性に targetsel を含め、異なる指定は明示的に拒否して detach を要求するだけでも安全になる。

また SWD は attach_under_reset を持たない。汎用 GPIO を提供しない固定デバッグ端子の probe では、NRST を制御しながら接続する
標準の経路がない。GPIO と複数要求を組み合わせる場合も、reset 解放と halt の間の時間は host の往復遅延に依存する。
任意の reset 制御・reset 下接続を wire 側に用意するのがよい。全 probe への必須化は不要。
参考として CMSIS-DAP は nRESET の制御・監視を SWD/JTAG のピン操作として持つ。
[DAP_SWJ_Pins](https://arm-software.github.io/CMSIS_5/5.8.0/DAP/html/group__DAP__SWJ__Pins.html)。

## 3. 制約を明示するか、仕様を補いたい点

### R11 / P2: 「省略できる機能」と「対応値」の見つけ方を揃える

[core §7.4](oep-core.ja.md) に features はあるが、debug / fixture / console では対応 op・GPIO mode・UART format・console mechanism の
宣言が十分に定義されていない。capture の宣言は比較的具体的で、この方向へ揃えるとよい。

小さい probe は GPIO の pull-down、UART の全 format、高水準 debug op などを実装しなくてよい。その代わり、最低限必須の操作と
任意操作、値の対応範囲、安全に試してよい問い合わせを各インターフェースで決める。全機能を表す巨大な共通 schema は不要。
channel_group の「完全一致」は RX のみ / TX のみを別 group に列挙すれば表せるが、その手順と role の個数制約も明示したい。

SDI / DMDATA は [console §1](oep-if-console.ja.md) に方式名はあるが、dmseq と違い、この規範から実装できる framing の参照がない。
現行コードを読まなくても同じ方式を実装できる短い定義または規範参照が必要である。

### R12 / P2: 永続設定の識別と原子性の範囲

[core §7.2](oep-core.ja.md) の fn は起動中だけ安定するのに、[probe-config](oep-if-probe-config.ja.md) は plan / bind / target の fn を保存する。
firmware 更新後に番号を振り直した際、旧 fn が別機能を指しても検知する規則がない。
安定した機能・実体のキーで保存するか、宣言構成の識別値が変わったら適用しない規則が必要。数値 fn のまま無条件に復元しない。

set の「何も変えない」は、設定検証・資源予約には適用できるが、attach 後の target 状態や消費済み console 出力までは巻き戻せない。
設定の commit と外部接続の activation を分け、後者の失敗状態を取得できるようにする。
describe で自動 attach の不一致を知らせるという本文に対応する status の wire 定義も補いたい。

USB を持たない probe が label / plan 保存だけ実装できるよう、USB mode / port / bind は任意の設定群と明示する。
USB 固有の設定が存在すること自体は問題ではなく、一般設定の利用条件にしないことが重要である。

### R13 / P2: 独自拡張にも「target の知識を入れない」を絶対適用するか

[core §13](oep-core.ja.md) は独自インターフェースにも、チップごとの flash 手順などを入れない規則を適用する。
これは MCU 移植の障害というより、専用量産治具・vendor 固有の高速書き込みなどを OEP 上に追加できる範囲の制約である。

汎用の標準インターフェースを chip database から独立させる方針は維持したい。一方、独自名の任意機能まで禁じるかは分けて判断する。
許可するなら、固有の高速操作を追加しても既存の生転送を置き換えず、非対応 host が無視できる形にする。

### R14 / P2: 小さい同期実装の限界と host の接続開始条件

[core §3、§4.4、§10](oep-core.ja.md) と [debug §4.4](oep-if-debug.ja.md) を合わせると、長い操作を予約に戻しても、run の無期限待ち自体は残る。
単一ループの probe がその間応答できない場合、keepalive / force / 復旧をどう扱うかが不足する。
非同期 activity を直ちに戻す必要はないが、長時間処理中も制御要求を処理するのか、有限時間に制限するのか、lease の扱いを決めたい。

独立 host 向けには USB の OEP interface / endpoint / HID usage の識別を transport binding として定義するか、外部指定が前提と明記する。
confirm の前に必要な接続条件は、confirm / describe だけでは発見できない。
max_frame も「probe が受け取る上限」と「host が壊れた応答と判断する上限」に使われているため、双方向共通か別々かを定義する。

## 4. 現在の方向性を維持してよいところ

- 名前と revision で発見し、fn を固定しない構造。新しい MCU のために core の機能一覧を増やす必要がない。
- role_channels と channel_group の併用。自由な pin mux と固定ピンの両方を扱える。
- 実レートと layout を probe が返す capture。ESP32 / RP2 の native packing に完全一致させる必要がない。
- 実装できない機能を list に出さないこと、生転送を host 側のチップ知識と組み合わせること。
- 外部クロック・多段トリガ等を基本機能から切り出すこと。初版を万能化する必要はない。

WCH 専用の rvswd / swio があることや、例に ESP32 が多いこと自体は欠陥ではない。
問題は、その条件が名前付きの機能境界を越えて、他の target や共通操作にも必須になっている箇所である。

## 5. 最小限の見直し順序と確認シナリオ

1. R1〜R4: chip 固有の知識と、生転送 / 任意の高水準操作を分離する。
2. R5〜R7: 資源取得・競合・解放を揃え、無関係な機能を止めずに変更できる単位を決める。
3. R8〜R10: channel 別の物理量、分割可能な情報、接続同一性を定める。
4. R11〜R14: 最小適合条件と接続開始条件を補い、独立実装で照合する。

その際は、既存 probe の正常系だけでなく、次を仕様テストにする。

- UART-only / 小フレームの probe で、宣言と設定を最後まで読み書きする。
- UART を受信し続けたまま、別ピンの capture を追加・解除し、UART のデータと設定が維持される。
- GPIO / SWD / 永続 bind が競合する場合、取得に失敗しても既存のピン状態が変わらない。
- raw DMI のみの実装で、高水準 debug op が使えなくても host が基本操作を続けられる。
- 異なる hart、同じ SWD ピンの異なる targetsel が、意図しない既存接続に混同されない。
- loader が実行後に同じ PC で停止しても、再実行されない。
- 異なるゲインの ADC 2 チャネルを正しく換算でき、64 チャネル分の情報も符号化できる。
- firmware 更新で fn の割当てが変わっても、旧設定で別機能を自動駆動しない。

core の u16 資源番号化などはレビュー中も更新されていたため、関連文書の一時的な u8 / u16 不一致は独立の設計欠陥として数えていない。
固める前には全 op 表・共通部品・生成物の同期確認が必要である。また u16 を同じ boot 中に再利用しない方式は安全性を改善する一方、
長期稼働では 65535 回の生成後に枯渇する。許容する運用制限か、generation / epoch を導入するかは別途判断したい。

総じて、**新しい MCU のために例外を増やすより、「標準の小さな共通部分」「宣言できる制限」「明示的な固有機能」を分ける修正が有効**。
今の構造を全面的に捨てる必要はなく、既存実装に暗黙に含まれている前提を、この三つに置き直す段階だと評価する。
