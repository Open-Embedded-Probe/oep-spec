# Open Embedded Probe — probe 開発ガイド

状態: **ガイド**（規範ではない）。probe を作る人のために、[OEP core](oep-core.ja.md) と
`oep-if-*.ja.md` が probe に求めることを満たす実務のやり方と、実際に踏んだ罠をまとめる。規範と食い違えば規範が正しい。host の側は [host 開発ガイド](host-development-guide.ja.md)。

- 最初の一歩（confirm、list、describe に答えるいちばん小さい probe とバイト列）は [はじめに](getting-started.ja.md)、probe が
  しなければならないことのチェックリストは [適合](conformance.ja.md) §1。
- probe library や board ごとの作り方と制約は、その実装のリポジトリに置く。
- `probe_frame_gap_ms` のような逆引用符の名前は、すべての数を持つ `registry/oep-v1.toml` のキー。

## 1. 開閉でリセットしない・状態を変えない

- 経路を開閉しても probe はリセットしない。DTR / RTS の変化で MCU をリセットする回路を持つボードは、host がそれを避けて開く
  （host ガイド §1）。probe は、口が開いた・閉じたことで自分から再起動しない。
- **DTR に頼らない。** DTR が下りている間は送らない USB シリアルのスタックがある。それを切って（スタックの「流れの制御を無視する」
  設定など）、host の開き方が違っても話し続けるようにする。transports §4: probe は DTR、RTS、線の状態を何の判断にも使わない。
- **経路の開閉では状態を変えない。** attach、ピン、線の状態はそのまま。資源を外すのは core §9 の寿命の規則のときだけ（明示の
  release / detach、lease の期限切れと force でのそのセッションの分）。外すときも target をリセットしない。解いたピンは設定の idle の
  状態（既定は Hi-Z）にし、駆動し続けない（core §8）。
- **起動したら、答える前にピンをしまう。** 最初の応答の前に、自分で使うchannelと設定が使用・設定を禁止するchannelを除き、空きの状態にする: 設定が idle を
  定めればその idle、そうでなければ Hi-Z（入力、プルなし）（core §8）。MCU の起動のコードや周辺回路のドライバが残したままにしない。
  firmware が動くまで、ピンは MCU のリセットの状態で、どの firmware も変えられない。誤った水準が害になる線には外付けのプルが要る
  と利用者に伝える（[安全とセキュリティ](security.ja.md) §6）。
- 開くとどうしてもリセットされる probe は、その文書で利用者にそう伝える。

## 2. 送受信のバッファ

- **宣言したwindowとmax_inflightを守る要求を保持できるようにする。** windowは見出しを含む未解決要求のmessage byte総量で、実行中の要求も数える。
  フレームの包み、下層driver、DMA/packetの保持量は別に見積もる。単にwindowより大きいringを設けることを要求しない。
  応答は順に生成して送ってよく、window内の全要求に対する最大応答の合計を一度に保持する必要はない。
- **プラットフォームの既定のバッファの大きさを、確かめずに使わない**: max_frame 1 つより小さいことが多い。
- 複数の未解決要求を受ける構成では、長い処理の間に来る適合要求を保持する（割り込み/DMA、受信のpoll、下層の保持やbackpressureなど）。
  max_inflight=1の構成ではhostは応答前に次の通常要求を送らないため、並行受信を実現するためだけの割り込み/DMAを一律に要求しない。
- **受信で 1 byte ごとに重い処理をしない。** 届いている分をまとめて読み、時計は 1 回だけ読み、本文はまとめて写す。1 byte ごとに
  時計を読むと、受信の速さが線の速さよりずっと低く頭打ちになることがある。
- **宣言した max_frame の要求を丸ごと受けられるようにする**: フレームの保持と下層から渡る量・framing処理を合わせて確認する。
  ringの大きさやcopy数は実装の方式で選ぶ。小さい構成では64byteの要求と64byteの結果用bufferを例にできるが、包みや下層driver等を含む全RAMの値ではない。
- 通知を提供する場合も有限な保持量を選ぶ。送信上限max_frame×2は必須のqueue容量ではない。
  送り始めたframeを途中で捨てたり応答を挟んだりせず、未送信の通知より応答を優先する。満たせない購読の保持量はcore §10.3に従って断る。
- **vendor bulk の OUT は packet ごとに受ける**。ZLP で終わる大きな転送として受けない: host は wMaxPacketSize の倍数の書き込みの後に
  長さ 0 の転送を続ける（transports §1）ので、ちょうど packet の境で終わる要求が次の OUT まで待たされることがある。長さ 0 の完了は
  読み飛ばす。
- 線の速さは `oep.probe.link` の source / sink の op（[リンク](../interfaces/oep-if-link.ja.md) §2）で測る。受信・送信の経路を変えたら測り直す。

内部のC構造体をwireのfield順に並べる必要はない。例えばマークのu64を先に置けばABIのpaddingを減らせる。
wireへは決められた順とlittle endianでfieldごとに符号化する。packed属性や構造体の丸ごとの送信を一律には要求しない。
マークを提供しない構成には、その記録・serial・ringを確保しない。planの置き換えも、全機能のbufferを複製せず、
既存表と受信した要求を副作用なしで照合してから、除く割当と追加する割当だけを適用できる。

## 3. OEP の口にほかのものを出さない・誰も読まない口で止まらない

- **OEP を運ぶ口にログを出さない。** ログの行はフレームを壊し、host は応答が来ないとみなす。その口ではプラットフォームのログを
  止める。
- **誰も読んでいない口への書き込みで main loop を止めない。** 開かれていない USB シリアルの口へのブロックする書き込みは、呼ぶたびに
  タイムアウトまで待ち、すべての応答と通知を遅らせうる。ブロックしない書き込みにするか、書かない。

## 4. 信頼性のない経路には CRC と再送

- USB（CDC、vendor bulk）はデータを保証するが、**USB-UART の変換チップを挟む経路は保証しない**: probe と変換チップの間の UART、
  変換チップの中、USB をネットワークで運ぶ層で、byte が落ちたり化けたりする。
- そのためシリアルの口は COBS + CRC-16/CCITT-FALSE を運ぶ（transports §1）: 壊れたフレームは捨てられ、host が送り直す（core §5.1）。
  host は「応答が来た」ことを正しさの根拠にしない。
- target の側も同じ: debug の線の 1 bit の parity は、壊れた応答の半分を通す。メモリの読み出しや flash の結果は、上位の CRC か
  読み戻しで確かめる。

## 5. UART bridge の起動時の速さ

- UART bridge の probe は、いつも `uart_bridge_boot_baud`（115200 bps）8N1、流れの制御なしで起動する（transports §4）。起動時の速さを
  設定にしない: 設定を忘れると入れなくなり、未確認の速さの自動検出は避ける。
- セッションの間だけ速くするのは port_speed（[リンク](../interfaces/oep-if-link.ja.md) §3、任意）: `oep.probe.link` を list に出し、復帰保留を含む4つの状態と戻る
  条件を実装し、その describe の ops に port_speed（0x12）と port_state（0x13）を立てる。port_stateは今の速さと状態を返す。戻り先はいつも起動時の速さ。
- USB CDC と内蔵の USB シリアルでは、線の設定は数字が渡るだけで速さに関係しない。無視する（transports §4）。

## 6. シリアルのフレーム専用の作り

口ごとに読み手と書き手を 1 つ持つ。0x00 の候補をためて COBS と CRC を検証し、壊れた候補は捨てる。
バッファがあふれても target へ転送しない。送信キューにはフレーム単位で積み、別のフレームを途中に挟まない。
ログや raw console は別の endpoint に置く（transports §4）。


## 7. probe の再起動の抑止

口を開閉しても probe が再起動しないようにする（§1）。USB スタックの再起動のきっかけ（DTR / RTS の並び、1200 bps の「touch」、vendor の
リセットの要求）をすべて切る。きっかけが firmware の外にあるとき（USB-UART の変換チップの先の自動リセットの回路）は、host が DTR と
RTS を立てて開き（host ガイド §1）、それでもリセットするなら、その probe の文書で利用者に伝える。platform 固有の設定方法は実装リポジトリに置く。

## 8. 推奨の USB の作り（VID:PID、iProduct、serial number、interface）

ネイティブ USB を持つ probe のために:

- **VID:PID**: host が自動で OEP の probe と見分けるのは、プロジェクトの USB の VID:PID `1209:4F45`（VID 0x1209、PID 0x4F45。
  registry の `usb`。transports §3）だけ。probe は oep-probe-arduino の PID-USE の条件の下でそれを使う。それで列挙しない probe は、
  利用者が名指すか口を選ぶ。USB-UART の bridge の向こうの口と、ハードウェアが記述子を決める内蔵の USB シリアルは、プロジェクトの VID:PID を
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
- USB の識別と host の選び方は [USB の識別](usb-identity.ja.md)。

## 9. ロックの奪い方に probe が答えること

host は transport の数でロックの奪い方を決める（host ガイド §6）。probe は:

- transport の一覧を正しく出す（シリアルの口が 1 つだけの probe は、そう見えるように）;
- lease が切れたらロックを空け（後始末をし、core §9）、lock_state の残り時間を正しく返す;
  持ち主の新規要求自身の処理だけをleaseの停止区間とし、応答生成から再開する。通信の送信待ちやsession_id 0の照会では止めない（core §6.1）。
  送信先が止まってもleaseの期限検査・後始末を止めない。送信とtimerの進め方は実装が選び、別threadを要求するものではない。
- `lease_min_ms`〜`lease_max_ms` の lease の要求はそのまま受け、ほかはその範囲に丸める（core §6.4）。


任意の方針判定を持つ実装は、見出しの検査後、再送のbyte記録を返す前に判定する（core §4.3）。
方針が不要な最小実装には、認証の操作・状態表・追加RAMを要求しない。

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
新しい経路には使ったことの無い index を付け、外した index は使い回さない。OEP の経路の index は fn 0 の transport と confirm の対応に使う。

**boot_id**（core §6.5）: hardware RNGがあれば乱数、不揮発記憶を使えるなら起動カウンターや保存した乱数が候補になる。
どちらも無ければ、ADCの雑音や最初の外部通信を受けた時のtimerなど、起動ごとに異なる入力を混ぜる。
起動の決まったコード位置のtimer値だけでは、再起動を識別できないことがある。生成方法の選択は規範の追加要件ではない。

**model**（0x41、任意）: 自由な文字列。同じ種類のハードウェアに同じ firmware なら同じ値にし、個体ごとに変えない。

**firmware**（0x40）: 任意の版・診断情報の文字列。describeの値は同じboot_idの間固定する（core §7.3/§7.5）。
起動時に確定した診断情報は含められるが、動作中に変わる状態は状態照会opで返す。
**chip**（0x4C、任意）: 自由な文字列。MCU の型番とリビジョン（キャプチャの記録に、どのチップで取ったかを残すのに使われる）。

**インターフェースの識別**（core §7.2）: probe が起動している間 fn は変わらない。instance は同じ (name, revision) の中で重複しない固定識別子で、欠番を許す。
firmware に定数として割り当ててよく、動的な割当表を要求しない。削除や fn 変更で残った instance を詰め直さず、削除した番号を別の論理インターフェースへ振り直さない。
保存した設定はカテゴリを (name, instance) で指し、項目の名前の意味は revision を越えて変えない（core §13.1）。既存の契約を壊す変更は revision を上げ、できれば古い revision も別の fn で出し続ける（core §2.8）。

**ピン**（core §7.4）: ピンを集合のどれにでも割り当てられる機能は role_channels を、組が決まっている機能は組ごとに channel_group を
宣言する。両方を使ってもよい。probe 自身が使う channel はどの宣言にも載せず（インターフェースに割り当てない）、配線の固定の名前は `label`（0x46）に置く。plan に
上限があれば `oep.probe.plan` の describe に plan_roles を宣言する（[plan](../interfaces/oep-if-plan.ja.md) §1）。
片方向だけのUARTは、提供するRXまたはTXのroleだけをplanで割り当てて使う。固定のRX/TX組をchannel_groupで宣言するprobeが
片方向のplanも受け付けるなら、その片方向に一致するgroupも宣言する。RX専用のprobeにはTXの宣言・実装は要らない
（[fixture](../interfaces/oep-if-fixture.ja.md) §2）。

**max_frame、window、max_inflight**（confirm、core §4.4）、経路ごと:

- max_frame: `min_max_frame`（64）以上。その長さの要求が1つ丸ごと受信の経路に入るように選ぶ（§2）。max_lengthは機能の上限で、
  blockなど分割できる操作では経路ごとのframeにも合わせる。分割できない外部RXの上限は、その操作の定義に従い全経路へ収める（core §7.4）。
- window: max_op_ms の間忙しくしている間に持てる、待っている要求の byte 数。max_frame 以上（core §7.1）。
- max_inflight: 受け付ける待ちの要求の数、1 以上（core §7.1）。再送cacheの件数とは別である。
  最後のsession_id/corrの順序状態を残せば、再送byteの記録は0件でもよい（core §5.1）。旧要求にはresult_lostを返して再実行しない。
  記録を持つときの保持メモリは、cache件数×（保持する要求/応答とmetadata）の量で選ぶ。未解決要求を受けるbufferは別に確保する。
- シリアルの口では、host の OS の受けの量が先に限られる（host ガイド §8）。window を大きくしても host の役には立たない。

**資源IDの保持**（core §9）: 1から増やすカウンターと、上限を決めた使用中の資源表で実装できる。
閉じたIDの全履歴を持つ必要はない。u32の次番号と使用中の資源表を持ち、0へのwrapを枯渇として扱えばよい。0を枯渇の印に使えば、追加のflagやu64カウンターも要らない。
session終了時は使用中の資源を解放するが、boot内の割当カウンターは戻さない。枯渇しても既存資源の操作・解放は続けられる。
IDを消費するのは番号を割り当てる作成で、すべての要求ではない。例えばplan_applyは番号を返さず、接続を維持したread/writeも番号を増やさない。
作成失敗で予約済み番号が欠番になる場合はある。同時に使える資源数と、boot中のID作成総数を分けて考える。

**max_op_ms**（0x4D、必須）: 1つの要求自身の検証・内部の再試行・実行・後始末・応答生成を含む最長の処理時間。
同じ経路・別経路の先行要求待ちと経路の転送時間は除く。save、flashのローダー、attach、scan、resetも含む。1〜`max_op_ms_max`（600000 ms）。
引数がそれを超えうる op は unsupported で断る。host は来ない応答を max_op_ms + `host_wait_add_ms` 待つので、要る分よりずっと大きく宣言しない。
confirm / list / describe / clock / keepalive / lock_stateは、max_op_ms が大きくても min(max_op_ms, core_quick_op_max_ms) 内で要求全体を処理する（core §4.4）。

**時計**（core §2.7）: 起動からの ns（u64）。同じ boot_id の間、減らず、一周しない。ハードウェアの数え器が 64 bit より狭ければ
（32 bit の µs の数え器は約 71.6 分で一周する）、一周の数でソフトウェアで広げ、一周を見逃さないだけの頻度で（main loop から）読む。
clock（core §7.6）の応答の uptime_ns は、その要求を処理する中でこの時計を読んだ値にする（前に読んだ値を使い回さない）。host はその値を、
自分が送った時と受けた時の中点に当てる。

**session_id** は host が選ぶ。probe は最後のものを覚えるだけ（core §6.1）。

## 11. probeの設定と保存

設定を持つ場合（core §13）:

- 本体が項目の一覧、値、世代、保存を持ち、持ち主（本体の channel とネットワーク、各インターフェース）は宣言、検証、適用だけをする。
  持ち主は値をメモリに持ち、普段の処理で設定の道を通らない（設定の読み書きはまれ）。
- 内容の変更をu32のgenerationで追い、getページ間の等値を保つ。内容のdigestを変更検出の保証に使わない。
- 値の数とbyte数を有限にできる。要求と既存の値を先に照合してから更新し、全状態のcloneを一律に要求しない。
- save/stateと不揮発領域は、保存を提供するときだけ必要。保存の形式は自由だが、カテゴリ、項目、keyを名前で持つ（番号を保存しない）。
  入れ子の構造（カテゴリ → 項目 → key の名前 → 値。CBOR など）は、平らな名前の約半分の大きさで済む（参考）。
- 原子的保存には2つの写しと完全性検査/commit情報などを使える。現在のgenerationとは別に内部形式の整合を確かめる。
  同じ内容が既に保存されていれば書込みを省く。
- 起動時は宣言済みの項目に当たり、名前を引けて検証を通る値だけを使い、disable、idleの順に反映する。使わなかった値は次のsaveで消える。
  部分適用と読めない容器を区別する。容器を読めない場合は不確かな設定を適用しない。
- 設定が掛かる前のpinはMCUのリセット状態にある。保存だけでは再起動の全期間の電気的状態を保証しない（[安全](security.ja.md) §6）。

## 12. target を扱う部品

target を扱う probe に共通する実装上の注意。

- **runを提供する場合**: riscv-dmのrunは、dcsrのebreakmとprv=Mを設定してhostのコードを走らせる
  （[線とデバッグ](../interfaces/oep-if-debug.ja.md) §4.4）。target固有の割込み制御などはhostの手順で扱う。
- **ブロック転送の実装方法**: 対応するdebug moduleではautoexecなどでまとめて処理できる。
  転送方法によらず、doneの計測点、書込みの再実行禁止、後始末は線とデバッグ §2/§4/§6に従う。autoexecの採用自体は適合条件ではない。
- **線の速さは、確かめたときの target のクロックでしか保証されない。** リセットで target が遅いクロックに戻ると、先に選んだ速さでは
  書き込みが化ける。リセットは最も遅い速さで行い、hart が止まってから速さを選び直す。リセットをかけながらの attach も同じで、リセットを
  放す前に最も遅い速さにする。wake が target をリセットする線では、wake を使わずに遅い速さから速めて測り直す。化けた読み出しで
  DMSTATUS が「走っている」に見えることがある: version の欄が合わない値は雑音として扱う。
- **フレームの間の線の休み方は線の定義の一部**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §3.1、§3.2、§5）で、idle_clock が許す所では target
  ごとに host が選び、rvswd では host が選ばなければ probe が target_id から決める（debug §3.1、`oep.wire.rvswd` の設定 `rest.{}` で口ごとに OFF）。線の節に従い、
  やり取りが失敗した後は線を駆動しないで休ませる（debug §2）。接続を閉じた後は、線切れでなければその休みの状態を保持する（debug §2、設定
  `hold.{}` で口ごとに OFF）。target によっては駆動が止まると数 ms でデバッグの状態を失う（CH32L103 は約 5 ms）。
- **target ごとに違う設定は、基本は host が判定する。タイミングに関わるものなどは probe の自動の判定を足せる**（core §12 規則 8）。考える順:
  1. **host から間に合うか**: 設定を誤ると数 ms 以内に target の状態が壊れるもの（例: CH32L103 は rvswd の線を high で休ませると約 1 ms で
     debug module がリセットされ、halt が外れる。CH32X035 は逆に low で休ませると attach できない）は、host が接続先を確かめてから設定を直す
     手順では間に合わない。初期設定を Web ブラウザなどから行う host は、時間の猶予が無い操作をできない。こういうものが自動の判定の候補になる。
  2. **host に知識を積ませないか**: host が接続先を確かめてから設定を変える作りは、チップごとの知識（バッドノウハウ）をすべての host に要求する。
  3. **自動の判定を足すときの条件**: 何を選んだかを host が読めるようにする（応答や一覧に出し、自動の判定をしたことが分かるように）。host の
     明示の指定を優先する。probe の設定で OFF にできるようにする（口ごとなど、判定が分かれうる単位で）。判定に使うチップの表は registry に置き、
     実装の中の隠れた知識にしない。
  判断が分かれるものは、実機の測定と host 側の利用者（ch32rv など）の意見をそろえてから、仕様の所有者が決める。
- **debugとfixtureの同時動作でだけ起きる不具合**では、処理負荷に加えて線の干渉も確認する。
  出力の強さを調整できるhardwareなら、線のタイミングを保てる範囲で弱めて比較する方法がある。
  強さを変更する機能や特定の段階を、すべてのPHY・移植へ要求するものではない。
- **問題を直したら、同じ仕組みの箇所を探す**（ほかの PHY、ほかの SoC、線を駆動する fixture、client と仮想ベンチ）。どこが大丈夫で、どこが
  未確認かを記録に残す。
- **resume と run は出し直さない**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §4.2、§4.4）。resume の要求が 2 回要る target や、すべて再開したと
  知らせない target は host が扱う: 汎用の名前のインターフェースに target 固有の知識を入れると core §12 の規則 8 に反する。
- **ブロックのループを速くする変更は、線の上のタイミングを変えうる。** 残す前に複数の target で測る。
- **キャプチャのストリーミングをするなら max_frame は 256 以上を勧める**（[キャプチャ](../interfaces/oep-if-capture.ja.md) §3.4）。データの通知の
  見出しは 17 byte で、max_frame 64 では 27%、256 で 7%、1024 で 2% になる。遅いリンクほど、データの形式 1 の events（§1.3）が効く。
  max_frame は経路ごと（core §7.1）なので、速い経路（USB の vendor bulk）だけを大きくしてよい。シリアルの口は小さいままでよい。
- **ストリーミングのバッファは、想定する host の遅れ × 最大の転送の速さ以上にする**。例: 50 ms × 20 MB/s = 1 MB。
  - 深さは configure の応答の stream_buffer（キャプチャ §3.3）で host に知らせる。
  - 足りないと、host が平均では追いついていても、読みの揺れのたびに区画を落とす。2026-10-20 の P4X（PSRAM なし、32 KB）では、20 MB/s で
    1.6 ms ぶんしかなく、同期の読み 1 本の Python の host で 15% を落とした。
  - 内部 RAM だけで深くできない probe は、保てない rate を configure / query で断る（§1.3、§3.2）。
  - host の側は、非同期の読みを複数出したままにするのが前提（例: libusb の 64 KB × 32 本）。
- **取り込みのリングを溜めとして使うなら、追い越しは隙間にする**（キャプチャ §2.2）。例: P4 の zero-copy のストリーミング
  （oep-probe-arduino d92d988）。
  - PARLIO の DMA リングを PSRAM に置き（1 MiB、40 MB/s で 26 ms ぶん）、送る stage が全部使われているあいだ、収穫は塊をリングに残して
    あとで戻る。stage へのコピーは 1 回。
  - DMA に追い越された塊は、作りかけの stage を失う前のバイトまでで閉じて送り、position を飛ばして、次の stage を追い越しの後の最初の
    バイトから始める。収穫のキューに入らなかった塊も同じ。どの区画にもまだ入っていないので、エラーにしない。
  - stream_buffer にはリングを含める。リングの最大の使用量を診断に出すと、host の遅れの見積もりに使える。
- **条件が成立した通知のバッチは出し切る**（core §10.3）。min_bytes か max_delay_ms が成り立った時点で溜まっていた分は、max_frame に分けて
  続けて送り、残りに条件を掛け直さない。
- **コンソールの送りの列**（[コンソール](../interfaces/oep-if-console.ja.md) §2）: write は列の空きに入る分をすぐ受けて答え、target へは列から mechanism の
  運び方で渡す（targetの受け取りを待ってから答えない）。writeを提供する場合の有限な列の大きさはprobeが決める。
  小さい列でもよく、hostはacceptedから未受付の残りを送る。writeなしならTX queueは不要。
- **一時的なdebug状態の後始末**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §4）: 保存する値は実行中のopだけに保持してよい。
  successの前に戻す。線の失敗や時間切れで戻せなければ失敗を返してconnection/streamを閉じ、後続opへ復元作業を持ち越さない。
- **リセットを解いた後の待ち**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §3、§4.3）: ndmreset やリセットの線を解いた後に DM が答えない間は、
  DMSTATUS を読み直して待つ（多くても max_op_ms）。この間の失敗を、線の再試行にも線切れにも数えない。
- **線の再試行は書き込みを繰り返さない**（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §2）: target のメモリへの store と host の dmi の手順を書いた後の
  確かめで線の失敗が分かったら、やり直さずに failed / partial で答え、done は失敗より前に済んだ数にする（target が受けなかったと答えた DMI の busy と
  SWD の WAIT は除く）。自分が DM とレジスタに値を置く書き込み（program buffer、abstractauto、GPR、dcsr、戻す DATA0 / DATA1）は繰り返してよい。
  connection の上の再試行と同期の取り直しでは、target をリセットしうる wake を送らない。
- **コンソールの読みの順**（[コンソール](../interfaces/oep-if-console.ja.md) §3）: その connection の riscv-dm の要求に答えた後は、次にコンソールのために DATA0 を
  読む前に DMSTATUS を読み、hart が止まっていれば読まない。
