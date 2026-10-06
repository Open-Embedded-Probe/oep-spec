# Open Embedded Probe — probe 開発ガイド

[English](probe-development-guide.md)

状態: **ガイド**（規範ではない。2026-10-06 にその日の規範の文に合わせて更新）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。probe を作る人のために、[OEP core](oep-core.ja.md) と
`oep-if-*.ja.md` が probe に求めることを満たす実務のやり方と、実際に踏んだ罠をまとめる。規範と食い違えば規範が正しい。host の側は [host 開発ガイド](host-development-guide.ja.md)。

- 最初の一歩（confirm、list、describe に答えるいちばん小さい probe とバイト列）は [はじめに](getting-started.ja.md)、probe が
  しなければならないことのチェックリストは [適合](conformance.ja.md) §1。
- 参照のライブラリの上で probe を作る案内は、ライブラリの側にある:
  [getting started](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/getting-started.ja.md)、
  [writing a probe](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/writing-a-probe.ja.md)、例の
  `examples/01.Basics/MinimalProbe`（oep-probe-arduino）。
  節の番号は 2026-10-06 に付け直した。古い番号と新しい番号の対応はその記録の冒頭。
- `probe_frame_gap_ms` のような逆引用符の名前は、すべての数を持つ `registry/oep-v1.toml` のキー。

## 1. 開閉でリセットしない・状態を変えない

- 経路を開閉しても probe はリセットしない。DTR / RTS の変化で MCU をリセットする回路を持つボードは、host がそれを避けて開く
  （host ガイド §1）。probe は、口が開いた・閉じたことで自分から再起動しない。
- **DTR に頼らない。** DTR が下りている間は送らない USB シリアルのスタックがある。それを切って（スタックの「流れの制御を無視する」
  設定など）、host の開き方が違っても話し続けるようにする。transports §4: probe は DTR、RTS、線の状態を何の判断にも使わない。
- **経路の開閉では状態を変えない。** attach、ピン、線の状態はそのまま。資源を外すのは core §9 の寿命の規則のときだけ（明示の
  release / detach、lease の期限切れと force でのそのセッションの分）。外すときも target をリセットしない。解いたピンは設定の idle の
  状態（既定は Hi-Z）にし、駆動し続けない（core §8）。
- **起動したら、答える前にピンをしまう。** 最初の応答の前に、`reserved` でないすべての channel を空きの状態にする: 設定が idle を
  定めればその idle、そうでなければ Hi-Z（入力、プルなし）（core §8）。MCU の起動のコードや周辺回路のドライバが残したままにしない。
  firmware が動くまで、ピンは MCU のリセットの状態で、どの firmware も変えられない。誤った水準が害になる線には外付けのプルが要る
  と利用者に伝える（probe の設定 §5）。
- 開くとどうしてもリセットされる probe は、fn 0 の describe で `resets_on_open` を宣言する（core §7.5）。

## 2. 送受信のバッファ

- **受信バッファは、宣言した window（受け付けてまだ処理していない要求の byte 数）より大きくする。** 送信バッファは、window 分の要求に
  対する応答の合計より大きくする。足りないと、probe が長い処理（flash のローダー、scan）をしている間に届いた byte がこぼれる。
- **プラットフォームの既定のバッファの大きさを、確かめずに使わない**: max_frame 1 つより小さいことが多い。
- 長い処理の間も受信する（割り込みや DMA で受ける、処理を分けて受信の poll を回す）。
- **受信で 1 byte ごとに重い処理をしない。** 届いている分をまとめて読み、時計は 1 回だけ読み、本文はまとめて写す。1 byte ごとに
  時計を読むと、受信の速さが線の速さよりずっと低く頭打ちになることがある。
- **宣言した max_frame の要求を丸ごと受けられるようにする**: フレームのバッファと、その下の受信の ring（下の層が 1 回に置く量の
  2 倍以上）。足りないとフレームの途中がこぼれ、以後の区切りがずれる。
- **vendor bulk の OUT は packet ごとに受ける**。ZLP で終わる大きな転送として受けない: host は wMaxPacketSize の倍数の書き込みの後に
  長さ 0 の転送を続ける（transports §1）ので、ちょうど packet の境で終わる要求が次の OUT まで待たされることがある。長さ 0 の完了は
  読み飛ばす。
- 線の速さは `oep.probe.link` の source / sink の op（[リンク](../interfaces/oep-if-link.ja.md) §2）で測る。受信・送信の経路を変えたら測り直す。

## 3. OEP の口にほかのものを出さない・誰も読まない口で止まらない

- **OEP を運ぶ口にログを出さない。** ログの行はフレームを壊し、host は応答が来ないとみなす。その口ではプラットフォームのログを
  止める。
- **誰も読んでいない口への書き込みで main loop を止めない。** 開かれていない USB シリアルの口へのブロックする書き込みは、呼ぶたびに
  タイムアウトまで待ち、すべての応答と通知を遅らせうる。ブロックしない書き込みにするか、書かない。

## 4. 信頼性のない経路には CRC と再送

- USB（CDC、vendor bulk）はデータを保証するが、**USB-UART の変換チップを挟む経路は保証しない**: probe と変換チップの間の UART、
  変換チップの中、USB をネットワークで運ぶ層で、byte が落ちたり化けたりする。
- そのためシリアルの口は COBS + CRC-16/CCITT-FALSE を運ぶ（transports §1）: 壊れたフレームは捨てられ、host が送り直す（core §5.2）。
  host は「応答が来た」ことを正しさの根拠にしない。
- target の側も同じ: debug の線の 1 bit の parity は、壊れた応答の半分を通す。メモリの読み出しや flash の結果は、上位の CRC か
  読み戻しで確かめる。

## 5. UART bridge の起動時の速さ

- UART bridge の probe は、いつも `uart_bridge_boot_baud`（115200 bps）8N1、流れの制御なしで起動する（transports §4）。起動時の速さを
  設定にしない: 設定を忘れると入れなくなり、生のバイトと OEP が混ざる口では速さの自動の検出は危うい。
- セッションの間だけ速くするのは port_speed（[リンク](../interfaces/oep-if-link.ja.md) §3、任意）: `oep.probe.link` を list に出し、3 つの状態と戻る
  条件を実装し、その describe の ops に op 0x03 を立てる。戻り先はいつも起動時の速さ。
- USB CDC と内蔵の USB シリアルでは、線の設定は数字が渡るだけで速さに関係しない。無視する（transports §4）。

## 6. シリアルの口の共用の作り

transports §4 の規則を守るための作り:

- **受信**: 口ごとに 1 つの読み手。0x00 の外のバイトはすぐ生のバイトの行き先（bind、[probe の設定](../interfaces/oep-if-probe-config.ja.md) §1.2）へ
  渡し、0x00 から次の 0x00 までを候補としてためる。候補が解けないか CRC が合わない、または入力が `probe_frame_gap_ms` 途切れたら、
  ためた分を生のバイトとして渡す。候補のバッファは max_frame の COBS の長さ + 2 を持つ。あふれそうになったら、その時点で中身を生の
  バイトとして渡す。
- **送信のキュー**: 口ごとに 1 つ。単位はフレーム丸ごとか、生のバイトの塊（64 byte 程度）。1 つの書き手が単位を割らずに出す。
  フレームは塊より先に出してよい。塊は位置つきのストリームから読むので、口が詰まっても捨てずに待てる（位置を進めないだけ）。
  endpoint がフレームを口に直接書き、別の処理が同じ口に生のバイトを書く形にしない: シリアルのドライバの多くは呼び出しの単位でしか
  排他しない。
- **口には OEP と bind の流れのほかは出さない**（§3）。

## 7. probe の再起動の抑止

口を開閉しても probe が再起動しないようにする（§1）。USB スタックの再起動のきっかけ（DTR / RTS の並び、1200 bps の「touch」、vendor の
リセットの要求）をすべて切る。きっかけが firmware の外にあるとき（USB-UART の変換チップの先の自動リセットの回路）は、host が DTR と
RTS を立てて開き（host ガイド §1）、それでもリセットするなら probe は `resets_on_open` を宣言する。例: ESP32 の USB-Serial/JTAG の口は、chip-reset-disable のビットを
立てないと DTR / RTS の並びでチップをリセットする。arduino-esp32 の TinyUSB の CDC（`USBCDC`）は `enableReboot(false)` で再起動しなくなる。

## 8. 推奨の USB の作り（VID:PID、iProduct、serial number、interface）

ネイティブ USB を持つ probe のために:

- **VID:PID**: host が自動で OEP の probe と見分けるのは、プロジェクトの USB の VID:PID `1209:4F45`（VID 0x1209、PID 0x4F45。
  registry の `usb`。transports §3）だけ。probe は oep-probe-arduino の PID-USE の条件の下でそれを使う。それで列挙する probe は
  fn 0 の describe の discoverable を 1 にする（別の口から開いた host にも分かる）。そうでない probe は 0 を返し、利用者が名指すか
  口を選ぶ。USB-UART の bridge の向こうの口と、ハードウェアが記述子を決める内蔵の USB シリアルは、プロジェクトの VID:PID を
  持てない。
- **iProduct** は人のための名前で、何もそれで probe を見分けない（transports §3）。
- **serial number は unit_id**（transports §3）。利用者が unit_id で名指した probe は、host がこれで探す。
- device の中の口は transports §3 のとおり: CDC はすべてシリアルの口。vendor bulk は class 0xFF / subclass 0x4F / protocol 0x45 の
  interface の bulk の組（Microsoft OS 2.0 の compatible ID `WINUSB` を付ける）。HID は usage page 0xFF4F / usage 0x45 で、出力の
  report を interrupt OUT と SET_REPORT の両方で受ける。vendor bulk と HID はそれぞれ多くて 1 つ。
- よい組は **vendor bulk（OEP）、HID（OEP）、CDC（シリアルの口）**:
  - vendor bulk は host の主な、速い経路;
  - HID は、他の道具が vendor や CDC を握っていても読め、ドライバも要らず、ロック不要の発見（describe、設定の get と state）に向く;
  - CDC は IDE や端末から見えるシリアルの口。OEP も受けるが（transports §4）、主にはコンソールを流す。
- 出している経路をすべて fn 0 の describe（transport の tag）に並べ、どの経路でも同じ unit_id を返す。
- 参照の probe の今の USB の形: [USB の識別](usb-identity.ja.md)。

## 9. ロックの奪い方に probe が答えること

host は transport の数でロックの奪い方を決める（host ガイド §6）。probe は:

- transport の一覧を正しく出す（シリアルの口が 1 つだけの probe は、そう見えるように）;
- lease が切れたらロックを空け（後始末をし、core §9）、lock_state の残り時間を正しく返す;
- `lease_min_ms`〜`lease_max_ms` の lease の要求はそのまま受け、ほかはその範囲に丸める（core §6.4）。

## 10. 識別子と宣言の選び方

**unit_id**（fn 0 の describe 0x42、core §7.5）: `a-z 0-9 -` の 1〜`unit_id_max_bytes`（32）byte。個体ごとに違い、個体の値だけから
作り、どの経路でも、どの firmware の版と profile でも同じで、接尾辞を付けない。probe が serial number を選べる所では USB の serial
number と等しい（transports §3）。

| 元にするもの | 利点 | 欠点 |
|---|---|---|
| チップの固有の番号を小文字の 16 進で | 保存が要らない。全消去や書き直しでも変わらない | describe や USB の serial number を読める誰にでも、チップの工場の番号を見せる（[安全とセキュリティ](security.ja.md) §8）。128 bit の番号で 32 文字を使い切る |
| 初回の起動で作って保存した乱数 | チップのことを何も見せない | 保存が要る。その保存を全消去すると個体が新しい識別になり、host の記録と名指しのアドレスが外れる |
| `x-` で始まる何か | どちらも無い probe 用 | 一意でない: host はそれでまとめず、名指さず、何のキーにもしない（core §7.5） |

16 進の数字は小文字で書く: host は大文字と小文字を区別せずに比べるが、`A-F` は使える文字に無い。

**transport の index**（core §7.5）: 0 から、経路ごとに 1 つ。同じ model の firmware の版をまたいで、経路ごとの index を変えない。
新しい経路には使ったことの無い index を付け、外した index は使い回さない。保存した bind はシリアルの口を index で指す（probe の設定
§1.2）。

**model**（0x41）: 小文字の `a-z 0-9 -`、1〜`model_max_bytes`（32）byte。同じ種類のハードウェアに同じ firmware なら同じ値で、個体ごとに
変えない。プロジェクトのものでない model は、作り手の逆ドメイン名の `.` を `-` にしたもので始める（`com-example-probe1`）。

**firmware**（0x40）: 自由な文字列（ふつうは版）。**chip**（0x4C、任意）: `<part> v<revision>`。part は `a-z 0-9` の 1〜24 文字、
revision は数字に任意の `.数字` の組。revision が分からなければ part だけ。

**インターフェースとその順**（core §7.2）: probe が起動している間 fn は変わらない。同じ (name, revision) の instance は fn の昇順に
数え、保存した設定はインターフェースを (name, instance, revision) で指す: 同じ名前のインターフェースの順を firmware の版をまたいで
変えない。インターフェースの固定部分を変えるときは revision を上げ、できれば古い revision も別の fn で出し続ける（core §2.7）。

**ピン**（core §7.4）: ピンを集合のどれにでも割り当てられる機能は role_channels を、組が決まっている機能は組ごとに channel_group を
宣言する。両方を使ってもよい。probe 自身が使う channel は `reserved`（0x44）に、配線の固定の名前は `label`（0x46）に置く。plan に
上限があれば `oep.probe.plan` の describe に plan_roles を宣言する（[plan](../interfaces/oep-if-plan.ja.md) §1）。

**max_frame、window、max_inflight**（confirm、core §4.4）、経路ごと:

- max_frame: `min_max_frame`（64）以上。その長さの要求が 1 つ丸ごと受信の経路に入るように選ぶ（§2）。max_length のような
  インターフェースの上限は、要求と応答が max_frame に収まるようにする。
- window: max_op_ms の間忙しくしている間に持てる、待っている要求の byte 数。max_frame 以上（core §7.1）。confirm の応答がこの範囲を
  外れた経路を host は使わない。
- max_inflight: 受け付ける待ちの要求の数、1 以上（core §7.1）。送り直しの表は応答と一緒に少なくとも max_inflight 個を持つ（core §5.2）。メモリは
  max_inflight × 覚える最大の応答。覚える応答の大きさに上限を置いてよい（それより大きい応答の送り直しは result_lost になる）。
- シリアルの口では、host は待つ応答の量を `host_serial_inflight_max_bytes` 以下に保つ（transports §4）。window を大きくしても host の
  役には立たない。

**max_op_ms**（0x4D、必須）: 1 つの要求にかかる最長の時間。save と flash のローダーも含む。1〜`max_op_ms_max`（600000 ms。
0 かそれより大きく宣言する probe を host は使わない、core §4.4）。引数がそれを超えうる op は unsupported で
断る。host は来ない応答を max_op_ms + `host_wait_add_ms` 待つので、要る分よりずっと大きく宣言しない。

**boot_id**（core §6.5）: 起動のたびに新しい値。次の好ましい順に取る: ハードウェアの乱数。不揮発の記憶に置き、起動ごとに変える値
（数え上げ、または保存した乱数）。どちらも無ければ、起動ごとに変わる値を混ぜたもの（初期化していない RAM、ADC の変換の雑音、
最初の USB や UART の動きが来たときに読んだ止まらないタイマー）。起動のコードの決まった場所で読んだタイマーは毎回同じ値を返し、
そうした値ではない。定数にしない。毎回同じになるライブラリの既定のままにもしない。

**時計**（core §2.6a）: 起動からの ns（u64）。同じ boot_id の間、減らず、一周しない。ハードウェアの数え器が 64 bit より狭ければ
（32 bit の µs の数え器は約 71.6 分で一周する）、一周の数でソフトウェアで広げ、一周を見逃さないだけの頻度で（main loop から）読む。
clock（core §7.7）の応答の uptime_ns は、要求を受けた後、応答を組み立てる直前にこの時計を読んだ値にする。host はその値を、
自分が送った時と受けた時の中点に当てる。

**session_id** は host が選ぶ。probe は最後のものを覚えるだけで、決して返さない（core §6.4）。

## 11. probe の設定と保存

`oep.probe.config` を list に出す probe のために（[probe の設定](../interfaces/oep-if-probe-config.ja.md)）:

- **項目は tag ごとの一つの形で持つ**（critical の bit は落とす）。hash は正規形で計算する（probe の設定
  §2）。自分の hash を `tests/vectors/probe_config_hash.json` で確かめる。
- **save は丸ごと置き換え、途中で電源が落ちても前の保存か新しい保存のどちらかが読める**（probe の設定 §2）。作り方の例:
  - 2 つの写し（A / B）。それぞれに通し番号と CRC を付ける: 新しい写しを古いほうに書き、確かめ、起動時は正しい写しのうち通し番号の
    大きいほうを使う;
  - 1 つの値を原子的に置き換えるキーと値の保存: 保存の形全体を 1 つの値として持つ。
  中身が保存と同じなら書かない（probe の設定 §2）。不要な save を送る host がいても flash を消耗させない。
- **保存は、項目が指す fn ごとに (name, instance, revision) を持ち**、起動時に今の fn に書き換える。どれかが無いか revision が違う、
  または保存した bind の口がもうシリアルの口でなければ、保存全体を掛けない（読めない、理由 2）。
- **起動の順**: 保存を今の設定にし、disable、idle（出力は強さと一緒に）、plan、uart を掛けてから、at boot の attach を始め、bind を
  つなぐ（probe の設定 §2、§3.1）。
- **max_bytes**（describe 0x40）は、いつでも保存できる正規形の長さ。識別子の表に要る分を引いて宣言する。
- **安全**: 保存した設定は、起動のたびに host なしで線を駆動する。掛かる前のピンは MCU のリセットの状態にある（probe の設定 §5）。
  レベルを誤ると害のある線には、それだけで安全な level を保つ外付けの pull が要ることを利用者に伝える。
- **boot_reset の保持の時間**は `slot_retry_reset_hold_ms`（20 ms）に決まっている。もっと長い保持の要るボードのために後から足すなら、
  slot をキーにした新しい項目の tag にする（core §2.3: 新しい項目の tag は OEP の伸び方の一つ）。revision は変わらない。

## 12. target を扱う部品

参照の probe から取った一般の決まり。

- **止まるまで走らせる**: host が渡したコードを走らせる前に、どの特権のモードでも ebreak が debug モードに入るようにする debug の制御の
  bit を立て、いちばん強い特権のモードで走らせる。最後の ebreak が trap のベクタに飛ばずに止まるようにするため。割り込みは host が
  渡すレジスタで止める。
- **連続した語**: ブロックの読み書きには debug module の autoexec を使い、それが残すアドレスで実行の回数を数える（取りこぼしや
  二重の実行を見つけるため）。
- **線の速さは、確かめたときの target のクロックでしか保証されない。** リセットで target が遅いクロックに戻ると、先に選んだ速さでは
  書き込みが化ける。リセットは最も遅い速さで行い、hart が止まってから速さを選び直す。リセットをかけながらの attach も同じで、リセットを
  放す前に最も遅い速さにする。wake が target をリセットする線では、wake を使わずに遅い速さから速めて測り直す。化けた読み出しで
  DMSTATUS が「走っている」に見えることがある: version の欄が合わない値は雑音として扱う。
- **フレームの間の線の休み方は線の定義の一部**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §3.1、§3.2、§5）で、idle_clock が許す所では target
  ごとに host が選ぶ。線の節に従い、やり取りが失敗した後は線を駆動しないで休ませる（debug §2）。
- **debug の線は、線のタイミングが許すいちばん弱い出力の強さで駆動する。** debug の線の鋭いエッジは、隣の fixture の線に乗る（コンソールを
  読む間、近くの SPI や UART の target が bit を落とす・ずらす）。どの PHY、どの移植でも設定する。線と fixture の線の強さは probe が
  決める（fixture §1.1）。
- **debug の線が忙しいときだけ壊れる fixture** は、CPU より先に線のエッジを疑う。線が休んでいるときと忙しいときで同じ手順を回し、まず
  出力の強さを見て、直ったかは前後を同じ手順で測る。
- **問題を直したら、同じ仕組みの箇所を探す**（ほかの PHY、ほかの SoC、線を駆動する fixture、client と fake）。どこが大丈夫で、どこが
  未確認かを記録に残す。
- **resume と run は出し直さない**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §4.2、§4.4）。resume の要求が 2 回要る target や、すべて再開したと
  知らせない target は host が扱う: 汎用の名前のインターフェースに target 固有の知識を入れると core §13 の規則 8 に反する。
- **ブロックのループを速くする変更は、線の上のタイミングを変えうる。** 残す前に複数の target で測る。
- **コンソールの送りの列**（[コンソール](../interfaces/oep-if-console.ja.md) §2）: write は列の空きに入る分をすぐ受けて答え、target へは列から mechanism の
  運び方で渡す（target の受け取りを待ってから答えない）。send_queue は 64 以上で、1 行のコマンドが 1 回の write に入る大きさを選ぶ
  （max_frame から write の要求の見出しと固定部分を引いた分より大きくしても、1 回の write には入らない）。
- **リセットを解いた後の待ち**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §3、§4.3）: ndmreset やリセットの線を解いた後に DM が答えない間は、
  DMSTATUS を読み直して `reset_settle_ms`（700 ms）まで待つ。この間の失敗を、線の再試行の 200 ms にも線切れにも数えない。

## 13. 参照の firmware が宣言する値（規範が選び方を任せる所）

- **model**（core §7.5、0x41）: チップの名前をハイフンなしの小文字で（`esp32p4`、`esp32`、`rp2040`、`rp2350`）。Arduino の profile の
  名前と同じ。
- **max_op_ms**（0x4D）: 10000（registry の `[reference]`）。
- **chip**（0x4C）: 型番とリビジョン。例 `esp32p4 v1.3`、`rp2350 v2`。
- **unit_id**: チップの固有の番号を小文字の 16 進で。
- **UART bridge の起動時の速さ**: `uart_bridge_boot_baud`（§5）。
