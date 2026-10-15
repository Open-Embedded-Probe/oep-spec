# Open Embedded Probe — host 開発ガイド

状態: **ガイド**（規範ではない）。host を書く人のために、[OEP core](oep-core.ja.md) と
`oep-if-*.ja.md` が求めることを満たす実務のやり方と、実際に踏んだ罠をまとめる。規範と食い違えば規範が正しい。
最初の一歩（いちばん小さい host とバイト列）は [はじめに](getting-started.ja.md)、host がしなければならないことの
チェックリストは [適合](conformance.ja.md) §2。probe 実装の使い方は、その実装のリポジトリを参照する。

節は、host が最初にすること（口を開く、フレーム、発見、セッション、断り）から、任意の設定までの順に並ぶ。製品や target に固有の手順は、それを実装する client または利用アプリケーションの文書に置く。

## 1. probe をリセットせずに開く

- **DTR と RTS を両方立てたまま開く**（多くのシリアルのライブラリの既定）。transports §4 は、口を開いている間それを立てておくことを
  host に求める。probe はどちらも判断に使わない。
- **どうしても下ろすなら、RTS を DTR より先に下ろす。** 多くのボードは DTR / RTS を自動リセットの回路につないでいて、RTS = 1・
  DTR = 0 の状態で MCU がリセットされる。DTR を先に下ろすとその状態を通る。
- 閉じるときは何もしなくてよい。
- DTR を下ろしたまま使わない: DTR が low の間は送らない USB シリアルのスタックがある（transports §4 はそのときの probe の動きを決めて
  いない）。
- probe の口を 1200 bps で開かない: 1200 bps で開いて閉じることをブートローダに入る合図にする USB スタックがいくつもある。

## 2. シリアルの口は常に COBS、フレームの外は雑音

- OS からシリアルデバイスに見える口（UART bridge、USB CDC、内蔵の USB シリアル）は、どれも COBS + CRC-16 で話す（transports §1）。
  フレームの形は経路の種類で決まり、VID:PID では選ばない。
- OEP の口はフレーム専用で、コンソールの生データを混ぜない。解けない候補と CRC 不一致は捨てる。
  正常なフレームでも待っていない corr の応答は捨てる。再送は §8 に従う。
- 正しい COBS のフレームは、2 つの 0x00 の間に 65796 byte（65535 byte の message とその CRC-16、
  254 byte ごとに COBS の code の 1 byte）より多くを持たない。それより長くなった候補は、閉じの 0x00 を待たずに雑音として捨ててよい。
- 送るフレームは必ず前後を 0x00 で囲む。前の区切りが無い候補は probe に捨てられうる。
- コンソールは OEP の read / write を使う。別の raw endpoint は明示した経路として扱う。

## 3. UART の速度

UART bridge の probe は、いつも起動時の速さ `uart_bridge_boot_baud`（115200 bps）8N1、流れの制御なしで始まる（transports §4。逆引用符の
名前は、すべての数を持つ `registry/oep-v1.toml` のキー）。port_speed（[リンク](../interfaces/oep-if-link.ja.md) §3、任意）は
セッションの間だけそれを上げる。上げるかどうか、候補、確かめ方、元に戻す基準は host が決める。必要な帯域を満たせなければ、probe のより速い
経路（ネイティブ USB）を使う。

UART bridge と、それと見分けられないシリアルの口では、どの応答の待ちにも core §4.4 の転送時間を足す。その口での最初の confirm の
応答の前は、max_frame をまだ知らない: 式には `min_max_frame`（64）を使い、その後はその口でのいちばん新しい confirm の応答の
max_frame を使う（core §4.4）。

## 4. USB の probe の見つけ方

- host が自動で OEP の probe と見分けるのは、プロジェクトの USB の VID:PID `1209:4F45`（VID 0x1209、PID 0x4F45。registry の
  `usb` の `project_vid` / `project_pid`。transports §3）だけである。probe の一覧を作るときは、この VID:PID の USB の device を並べる。
  それぞれの USB の serial number が unit_id で、開かずに区別できる。
- ほかのもので probe と見分けない: iProduct も、interface の class / subclass / protocol も、HID の usage page も使わない。これらは
  ほかの製品と偶然重なりうる。iProduct は人のための名前で、何もそれで probe を見分けない。interface の値は、probe と分かった
  device の中で口を選ぶためだけに使う（transports §3）。
- ほかの device と口は、利用者が probe を unit_id で名指したとき（USB の serial number がそれと同じ device）か、口を選んだときだけ
  開く（transports §3）。開いたら transports §3 の探りの規則で確かめる: 最初に送るのは confirm だけで、正しい confirm の応答が待ち時間の
  うちに来なければ、閉じてほかに何も送らない。
- プロジェクトの VID:PID を持てない probe がある: USB-UART の bridge の向こうの probe（bridge は自分の VID:PID と serial number で
  列挙する）と、ハードウェアが記述子を決める内蔵の USB シリアルの probe。host はこれらを自分では見つけられない: 利用者が口を
  選ぶ。confirm の後、fn 0 の describe がその probe の unit_id を返す。probe は口の名前ではなくこれで覚える（§5.3）。

### 4.1 TCP の probe の見つけ方

TCP で待ち受ける probe が自分を広告するときは、DNS-SD の service `_oep._tcp` を mDNS で広告する（transports §3。広告は probe が選ぶ）。

- `_oep._tcp.local.` を browse し、instance ごとに SRV（host の名前と port）、アドレス、TXT の `unit_id` を読む。port はいつも SRV の値を使う。
- service の名前 `oep` は IANA に登録した名前ではない。同じ名前で別のサービスが広告されうるので、見つけたものはどれも、confirm（`OEP!` の答え）と describe の unit_id で確かめてから使い、確かめられないものは候補から外す（transports §3 の探りの規則どおり）。
  仕様は port を決めない。
- 開いたら transports §3 の探りの規則のとおり、最初は confirm だけを送る。fn 0 の describe の unit_id で確かめ、TXT と違えば閉じる。
- **どれを使うか**は host が決める。目安: 利用者が unit_id で名指したら、TXT の unit_id が同じ instance を開く。名指しが無く 1 つも
  覚えていなければ、見つけた probe（unit_id と instance の名前）を並べて利用者に選ばせ、選んだ unit_id を覚える。同じ unit_id を USB と
  TCP の両方で見つけたら 1 つの probe としてまとめ（§5.1）、ふつうは USB の経路を使う（Wi-Fi の切れや遅れが無い）。
- 再起動の後や Wi-Fi のつなぎ直しの後は、アドレスが変わりうる: unit_id で browse し直す（§5.2 の 5）。
- 問い合わせは、すべての IPv4 のネットワーク接続から送る（接続ごとに送り出す口を選ぶ）。アドレス 0.0.0.0 の socket から 1 回だけ送ると、
  OS が選んだ 1 つの接続（仮想の接続のことがある）からしか出ず、ほかの接続の先の probe を見落とす。
- 広告しない probe と、mDNS が届かない所（ルーターの向こう、VPN、NAT の内側の仮想マシン）では、利用者がアドレスと port を明示する。
- 広告は同じネットワークの誰でも出せ、describe の unit_id も偽れる。TCP は信頼できるネットワークか、認証したトンネルの中でだけ使う
  （transports §1）。

## 5. session_id と発見

- open のたびに新しい、予測できない 32 bit の乱数の session_id を選ぶ。0、連番、固定値にしない（core §6.1）。
- **one-shot CLI はコマンドごとに新しいセッションを開く。** 前のセッションの connection や stream を再利用しない。
  hostに保存した配線の設定を読み、pinsと速さを明示してattachする。複数コマンドで出力や接続を保つ場合は、それらを同じセッションで実行する。
  必要なコンソール出力は end の前に read して host のログへ保存する。
  unit_id ごとに boot_id を記録し、変わったら fn の対応を list から作り直す。
- **発見の手順**: USB の device を列挙し、プロジェクトの VID:PID を持つもの（§4）と、名指した unit_id と serial
  number が同じものを開く（transports §3）。serial number が unit_id。device の中の口は interface の
  記述子で選ぶ（vendor bulk: class 0xFF / subclass 0x4F / protocol 0x45、HID: usage page 0xFF4F / usage 0x45、CDC はすべてシリアルの口）。
  開いたら最初に confirm だけを送り（応答が無ければ閉じる）、boot_id と上限を取り、describe の unit_id が serial と同じことを確かめる。
  ロック無しの監視は confirm か clock の boot_id で再起動を知る。
- **上限は使う前に確かめる。** confirm の応答では、max_frame は 64 以上、window は max_frame 以上、max_inflight は 1 以上（core §7.1）。
  fn 0 の describe では、max_op_ms は 1〜`max_op_ms_max`（600000 ms、core §7.5）で、これで応答の待ちに上限が付く。範囲を外れた値を返す
  probe は適合していないので、丸めずに値を利用者に知らせ、その経路を使わないのがよい。
- 対話型の CLI やモニターのように長く開いておくものは、keepalive か普段の要求でロックを保つ。確認のプロンプトで止まる間も
  keepalive を打ち、破壊的な手順の前ごとにセッションが生きているか（`no_session` / `locked` にならないか）を確かめる。
- **既存のstreamを読む監視はsession_id 0でよい**。そのstreamを作った所有者がsessionを保つ必要があり、監視のreadではleaseを更新しない。
  monitor自身がplan/connection/streamを作るなら、その所有sessionを利用中は保つ。writeもその所有sessionで行い、endすると作った資源と未読bufferは消える。
  複数の道具で同じ資源を使う場合はbrokerの1つの所有sessionへ束ねる。各道具がopen → write → endを送って共有資源を残せるとは仮定しない。
- 終わるときは end を送る（送らなくても期限で下りる）。
- **止まって走り直しうる host**（CLI、ブローカー）: 経路が閉じてもセッションは終わらない（transports §3）ので、end を送らずに止まった
  host のロックと資源は lease が切れるまで残る。次に走るときに前のセッションを終わらせるには、その id の open と end を
  **新しい要求**として送る（同じ id の open はセッションを保つ、core §6.2）。新しい要求の corr は、前の実行が最後に使った corr から
  1〜32767 先でなければ result_lost になる（core §4.1、§5.1）。そこで host は、session_id と一緒に、前の実行がまだ使っていない corr を
  probe ごと（unit_id をキー）にファイルなどへ残す。例えば 1024 個ずつ先へ予約し、使い切る前に次の予約を書く。次に走るときは、
  予約した corr から open と end を送り、前に持っていたものを解放してから、新しい id でセッションを開く。
  記録が無い、または読めないときは、前の lease が切れるまで待つ（lock_state の残り時間）か、利用者が明示したときだけ force で奪う。
  `x-` の unit_id ではこの記録を持たない（core §7.5）。

### 5.1 1 つの probe の複数の経路

- 1 つの probe が複数の経路（vendor bulk、HID、シリアルの口、TCP）を見せることがある。経路はセッションとロックを 1 つ共有する
  （transports §3）。fn 0 の describe の unit_id（ASCII の大文字と小文字を区別せずに比べる）でまとめ、`x-` で始まる unit_id ではまとめない
  （core §7.5）。
- 選べるなら vendor bulk、HID、シリアルの口の順に使う（transports §3）。シリアルの口は受けの量にも限りがある
  （transports §4）。
- 自分のセッションの id を持つ要求は、すべて 1 つの経路で送る（transports §3）。ロック不要の要求は別の経路で送ってよい（たとえば、
  デバッガが vendor bulk を持つ間に、HID で describe と state を読む）。
- max_frame、window、max_inflight とプロトコルの revision は経路ごと（core §4.4、§7.1）: 使う経路ごとに confirm する。

### 5.2 probe を再起動する（restart）

`oep.probe.restart` の restart（[再起動](../interfaces/oep-if-restart.ja.md)）は、口を抜き差しせずに probe を起動し直す。おかしな状態になった
probe の立て直しと、host 自身の「probe が再起動した」ときの道筋の試験に使う。任意のインターフェースなので、list で `oep.probe.restart` を
見つけてから使う。そのdescribeのrestart_max_msはprobe内部の復帰までの上限で、OSの列挙やネットワークの接続時間を含まない。
restartの前に読み、開き直しの期限はそれに外部の待ちを加えてhostが決める。

1. ロックを取る（restart はロックの要る op。session_id 0 なら session_required）。保存したい設定があれば先に save する:
   保存していない設定は再起動で無くなる（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §2）。
2. restart を送る。後ろに要求を続けない（どの経路にも）: 応答の後の probe は何も処理せず、答えない。
3. completed success の応答が来たら、その probe の経路をすべて閉じる。UART bridge で port_speed を上げていたら、起動時の速さに
   戻す（[リンク](../interfaces/oep-if-link.ja.md) §3 の host 2）。
4. 少し（目安 100 ms）待つ。probe はこの間に再起動を始める。
5. 新しく開くのと同じに開き直す（§4、transports §3 の探りの規則: 最初は confirm。UART bridge では起動時の速さ）。USB では device が bus から外れて列挙し直す:
   OS の口の名前が変わることがあるので、serial number（= unit_id）で探し直す。開けないか confirm に答えが無ければ、応答を受けてから
   hostが決めた期限まで開き直しとconfirmを繰り返す（confirmの応答はcore §4.4のとおり待つ）。restart_max_msの経過だけでは、
   外部の経路が復帰したことやprobeの違反を判断できない。期限までに正しい
   confirm の応答が無ければ、probe は無くなったものとして扱う: その probe の経路を閉じて利用者に知らせ、利用者が開き直すまで何も送らない。
   利用者が前もって頼んだ開き直し（道具の option で、閉じた後も一定の時間開き直しを続ける、など）は、利用者が開き直すことに当たる。
   UART bridge と TCP の口は閉じずに残ることもあるが、同じ手順でよい。TCP では、アドレスが変わりうるので unit_id で browse し直す（§4.1）。
6. confirm の boot_id を restart の前のものと比べる。違えば再起動した: 覚えた fn の対応、資源の番号、ストリームの位置、セッションを
   すべて捨て（core §6.5）、list し直し、要るなら新しいセッションを開く。前のセッションの id の要求は no_session で断られる。同じなら
   restart は実行されなかったものとして扱う。
7. 応答が来なかったときも5〜6と同じに確かめる。hostの開き直しの期限はrestartの応答の待ちが過ぎた時から数える。
   同じcorrのrestartがno_sessionで断られた場合も5〜6へ進み、その応答を基準に開き直しの期限を決める。

**中継する host**（transports §1 の中継のブローカー）は、restart をほかのロックの要る op と同じに中継し、応答を道具に返した後は、上と同じに
probe への経路を閉じる。ブローカーの probe への経路が無くなれば（ブローカーが閉じた、USB で列挙し直した、TCP が閉じた）ブローカーは終わり、
道具への接続も閉じる（transports §1）: 道具は新しく開くのと同じにやり直す。

再起動の後、保存した設定は通常の起動と同じに掛かる（配線の設定はhostが再適用する）。
再起動の手順はtargetのreset/resumeを意図して行わないが、ピンのリセット状態や外部回路の影響は別に確認する（[再起動](../interfaces/oep-if-restart.ja.md) §2）。

### 5.3 probeとhostの接続プロファイルの名指し方

- **アドレス**: host が probeと接続プロファイルを文字で名指すときは `oep://<unit_id>[/<profile name>]` と書く。authority は unit_id（core §7.5、小文字）、
  path はhost側の接続プロファイルの名前1 つだけ。path の無い `oep://<unit_id>` は probe 自身。
  IDE や設定のファイルが probe を覚えるときはこの形で覚える（VID:PID や口の名前ではなく）。unit_idとプロファイルの名前は、どちらも URL の中で
  encode の要らない文字だけを使う。
- **インターフェース**: 文字で 1 つのインターフェースを指すとき（CLI、設定のファイル、ログ）は `name#instance` と書く（instance は list の値、
  0 も有効で、`#0` は省いてよい）。例: `oep.fixture.uart#1` は instance=1 の `oep.fixture.uart` であり、list の2番目という意味ではない。
  revision は別に明示して保存・選択し、(name, instance, revision) を解決する。欠番なら未提供として扱う。

接続プロファイルはhostが持つ配線/速さ/target選択の記述で、probeの標準設定項目ではない。
labelを線の役目に使う場合、`nrst`、`power_hi`、`power_lo`を慣行にできる。複数の接続先にはhostのプロファイル名Sを用い、
`S.N`の設定label、単一接続先なら`N`の設定label、最後にfirmwareの`N`の順で探す。ASCIIの大小文字を区別せず、
同じ段で複数channelが見つかれば曖昧として使用しない。probeはこの名前から線を動かさない。

## 6. 排他とロックの奪い方

- **シリアルの口は必ず排他で開く**（Linux / macOS は `ioctl(TIOCEXCL)`、Windows は元から排他。transports §3）。排他でないと、応答の
  バイトが別のプロセスに渡り、経路が成り立たない。協力型のロック（`flock`。「exclusive」と呼ぶライブラリもある）は、それを見ない道具を
  止めないので、開いた後に TIOCEXCL を掛ける。root は TIOCEXCL を素通りする。
- libusb / WinUSB の claim は OS が排他する。
- **本当の排他は session_id で行う**（core §6）。ロックの奪い方は probe の transport の数（fn 0 の describe の transport）で決める。
  - **transport がシリアルの口 1 つだけの probe**: 排他で開けた時点で、前の持ち主のプロセスは口を握っていないので、open の force で
    その場で奪ってよい。
  - **transport が複数の probe**: lock_state で残り時間を読み、残りだけ待つ（上限は数秒）。持ち主が lease を更新し続けているなら、
    待たずに「使用中」とする。force は利用者が明示したときだけ使う（force は認証ではなく、TCP は信頼できる接続でだけ使う。transports §1、
    core §6.4）。
- leaseは、要求1つの欠落を再送で回復する余裕を含めて選ぶ。最後の同じSIDの新規要求から次のkeepaliveまでの間隔をH、
  core §4.4のkeepalive再送待ちをW、再送要求がprobeへ届く転送時間をT、
  所有者の要求がleaseを止めない先行処理を待つ時間の上限をQとして、H + W + T + Q + hostのスケジューリングの余裕を、受理されたleaseより十分小さくする。
  Wは min(max_op_ms, core_quick_op_max_ms) + host_wait_add_ms + 転送の時間で、最大の処理分は1000 msである。
  速い経路の対話的な道具は、例えばlease 5秒、keepalive間隔1秒から始める。遅い経路や大きいframeでは転送時間も計算し、必要ならleaseを伸ばす。
  lease_max_msでも余裕を確保できない構成では、1frameの欠落からセッションを保ったまま回復する保証はない。
  単一経路・max_inflight=1で先行処理が無ければQ=0でよい。別経路の長い照会などでQを見積もれない場合も、その保証は置かない。
  leaseはprobeの応答生成から進むため、hostが応答を受け取った時から丸ごと残っているとは仮定しない。
  送信の停滞で期限切れになっても、遅れて届くsuccessは資源の継続を保証しない。

再送で受け取るsuccessは、元の要求の結果である。leaseが既に切れていても保持した結果は返りうるが、ロックや資源は復活せず、再送でleaseも延びない（core §5.1/§9）。
復旧時にはboot_idと状態を確認する。例えば同じSIDの新しいkeepaliveで所有を確認でき、no_sessionならそのSIDは終了済みである。
再送したkeepaliveのsuccessだけで次の更新を遅らせず、新しいcorrのkeepaliveで更新する。
別SIDの新しいセッションを開いたときは以前の資源を引き継がず、必要な接続やplanを明示的に作り直す。

## 7. ブローカー

OEP へ自分で答える broker は独立した OEP の端点として動かす。list / describe / confirm、セッション、再送履歴、資源の寿命を
client 向けに実装し、上流の probe との対応は内部で管理する。core の 5 個の op だけを特別扱いする端点にはしない。
同じ資源を長く保持したい複数の道具は、broker のセッション内で処理をまとめる。client 向けの共有方針は core が決めない。



任意の方針によるunavailable cause 7は、認証した経路や在席確認などの製品条件を満たしていないことを表す（core §4.3）。
hostは同じ要求やforceを繰り返して回避せず、その製品の接続・認可手順へ進む。過去の成功応答は現在の許可の証明にしない。

## 8. 応答の対応付けと送り直し（transports §5 と core §5.1 が求めること）

- 待っていない corr の正常な応答は捨てる。長さやフレームが壊れた場合の回復は transports §5 に従う。TCP は閉じて開き直す。
  開き直した経路へは購読が移らないので、続けたい購読を subscribe し直す（§12）。
- corr は u16、session_id ごとに循環して前進する。0 を飛ばし、通常は 65535 の次を 1 にする。
  前の新規要求からの距離と、最古の未解決要求からの距離を半周32768未満に保つ。未解決要求を残して半周以上進めない。
  SID0の照会は所有するセッションの順序を進めない。全要求のcounterを単純に共用して、大量のSID0照会でセッションのcorrを半周飛ばさない。
  同じ経路では、セッションが違っても未解決番号や古い応答が残りうる番号を避ける。
  再送した要求は最初の応答で解決しても追加応答が残りうる。最後の再送コピーより後に送った別番号の応答を受け取るまで、その番号を別sessionへ渡さない。
  待っていない旧応答は捨てる。解決済み要求の再送予約を止め、経路外に保存した古いコピーを後から書き込まない。
  排出や半周の範囲を確定できなければ経路を立て直し、新しいSIDで回復する（資源解放はcore §9）。
- 再送は見出しと payload を含めて同じ byte 列を使う。変更した要求には新しい corr を振る。同じ corr で内容を変えると malformed。
- result_lost は実行済みか不明なので、再実行の前に状態を読む。再送記録の件数とbyte数には上限があり、0件も許される。
  max_inflight件の結果を必ず再取得できるとは考えない。作成した資源のIDなどを回復できなければ、所有を確認できる同じSIDのendで資源をまとめて解放するか、規則に従う新しいSIDへの切替で不明な資源を解放してから作り直す。
  result_lostの要求を新しいcorrで自動的に繰り返すと、元の資源が残ったまま2つ目を作ることがある。接続の開き直しだけでロック・資源・再送順序は初期化されない（transports §3）。
- 再送を諦めた経路の未解決要求はすべて結果不明として扱う。回復時に boot_id を確認し、資源の一覧や状態を読んでから次を判断する。
- 再送回数と間隔は host が決める。CRC 不一致の候補が届いたら、待ち時間前に同一要求を再送してよい。

- **シリアルの口の受けの量**: OS のシリアルドライバは、一度にまとまって届く量がドライバの受けの量を超えると、エラーなしに黙って
  落とすことがある（測った Linux のドライバの 1 つでは約 8 KiB の burst）。シリアルの口では、未解決の要求の応答の見込み量（同時数 ×
  フレームの上限）と購読の min_bytes を小さく（目安: 応答 6 KiB 以下、min_bytes 2 KiB 以下）保ち、大量の転送は vendor bulk を優先する。
  probe の max_inflight と window は probe の受けの上限で、host の受けの上限ではない。

## 9. 断りごとに host がすること

rejected は要求が受け付けられなかったこと、completed failed / partial は実行したが全部はうまくいかなかったこと（core §4.2）。見出し、
送り直しの表、セッションの断りはこの順で来る。それ以外の理由が 2 つ当たる要求には、probe はどれか 1 つで答える（core §4.3）: どの理由でも、
直すか諦めるかで扱う。知らない理由は失敗として扱う（core §2.4）。

| reason | 意味（core §4.3） | host がすること |
|---|---|---|
| unknown_function（0x01） | その fn が無い（payload の中で指した fn も） | 手元の fn の対応表が古いか誤り。list し直す（fn の番号は boot_id が同じ間だけ有効、core §7.2）。そのインターフェースは使わない |
| unknown_operation（0x02） | その fn にその op が無い | probe が実装していない任意の op（core §1.2）。任意の op は describe の ops（0x07）を見てから使う。ops を確かめて送らないときは、この応答と同じ失敗を報告し、呼び出し側がどちらでも 1 つのエラーを見るようにする |
| malformed（0x03） | 要求の形が誤り | 自分の符号化の誤りか、どの revision でも除かれる値。そのまま送り直さず、要求を直す。要求のバイト列をログに残す |
| unavailable（0x04） | 今の状態か今の資源ではできない | TLV を読む: cause（1 ピンが使用中、2 数・処理能力の上限、3 保存の容量が足りない、4 グループに束ねられている、5 設定が持っている、6 状態が違う）、channel、fn。利用者に見せ、自分の資源を解くか順を変える。cause 5 は probe の設定（disable、出力の idle）が持っているので、要求ではなく設定を変える（どれが持つかは probe の設定の get で見る）。知らない cause は不明として見せる（core §2.4） |
| window_exceeded（0x06） | window / max_inflight を超えた | この経路の probe の上限を超えて先送りした。応答を待ち、新しい corr で送り直す（core §5.1: 直した要求は新しい corr で送る） |
| no_session（0x07） | どのセッションもロックを持っていない: 自分のセッションが終わった（end、lease の期限切れ、force）か、probe が再起動した | セッションが作ったものはすべて解放された（core §9）。新しいセッションを開き、plan、attach、購読を張り直す。黙って続けない（§5）。再起動は open の boot_id で分かる |
| locked（0x08） | 別のセッションがロックを持っている | payload に残りの ms と、あれば持ち主の文字列。待つか、持ち主を添えて「使用中」とするか、利用者が頼んだときだけ force で奪う（§6） |
| session_required（0x09） | ロックの要る op の要求が session_id 0 だった | 誤り: 自分の session_id で送る |
| no_resource（0x0A） | その資源の番号を知らない | 接続やストリームが閉じたか、probe が再起動した。番号を捨て、資源を作り直す（attach、open）。長く持つ番号は一覧の op で確かめる（core §9） |
| unsupported（0x0B） | 定義にはあるが、この probe は扱えない | payload の tag が何かを示す: 0x00 = 固定部分の値、それ以外は受け取ったままの critical な TLV の tag。channel / index の TLV がどの要素かを示すことがある。describe を見て probe が宣言するものを選ぶ。そのまま送り直さない。confirm では TLV 0x01 が probe の扱える revision を示す（core §7.1） |
| result_lost（0x0C） | 送り直しの応答を覚えていない | 実行されたかは分からない: 状態を読み直す（core §5.1） |
| 未割当の reason | 未定義 | 失敗として扱う |

- **completed failed / partial**: payload は op が決める（wire と target では `status` と `done`、[共通部品](../interfaces/oep-if-common.ja.md) §3）。
  status の line はふつう、速さを下げて attach し直す。wait は後で `done` から続ける。fault は原因を読んで消す。timeout は上限を見直す。
  state は先に target を要る状態にする。知らない status は失敗。
- インターフェース固有の理由（0x40〜0x7F）は各インターフェースが定める。v1 には無い。

## 10. revision、TLV、知らない値

- **プロトコルの revision**: 経路の最初の confirm で扱える範囲を送り、その後は `min_rev = max_rev =` 使っている revision を送る
  （core §7.1）。rejected unsupported なら、TLV 0x01 が probe の扱える revision を示す。revision は経路ごと（TCP は接続ごと）。
- **インターフェースの revision**: list は fn ごとに (name, instance, revision) を返す。知らない revision のインターフェースは使わない
  （core §2.8）。probe は古い revision を別の fn で出してよいので、知っているほうを選ぶ。instance は (name, revision) ごとの識別子で、欠番を許す
  （core §7.2）。
- **応答の読み方**: 固定部分の後ろは TLV の並び。知らない tag は読み飛ばす。繰り返さないtagは最初のものを使い、後続も構造と既知の長さを検証する（core §2.3）。並びは要素に長さの
  無い `count × element` なので、要素は定義のとおりにフィールドごとに読む。固定の形は末尾を延ばされない。長さが定義と違う TLV の値は
  壊れている（core §2.3）。新しい情報は新しい tag で来る。応答の中で bit 7 の立った TLV は知らない tag として扱う。
- **要求の送り方**: 効かなければ意味の無い TLV か、効かないと害のある TLV（attachのreset、scanのmax_speedなど）には critical の bit を立てる（core §2.3）。
  その tag を実装しない probe は critical なら断り、そうでなければ黙って無視する。実装する probe は bit によらず値を確かめる。
  attachのpinsとmax_speedは固定部分なので、このcriticalの規則ではなく固定部分の検証で扱う。
  要求の TLV の値を後ろに延ばさない（core §2.3）。繰り返さない tag を繰り返さない。
- **応答の知らない値**: 知らない resolution、outcome、status、reason は失敗。知らない kind の出来事は捨てる（seq は数える）。ほかの enum
  の知らない値（cause、scan の種類）は不明として見せる。flags の予約の bit は無視する（core §2.4）。
- **真偽値と文字列**: 0 以外の真偽値は真と読む。応答の文字列は、見せる前に制御文字と不正な UTF-8 を置き換える（core §2.1）。

## 11. 時間のかかる操作

- どの op も 1 つの応答で終わる。時間のかかる op（run、キャプチャの configure、save、attach、scan、reset）は、応答が来るまで待つ。
  待ちはmax_op_ms + host_wait_add_ms + 転送の時間を基本にする（core §4.4）。操作が要求全体の短い上限を定める場合だけ、その上限を使う。
- 別経路の先行要求を待つ時間は処理上限へ含めない。短い上限のclock等も、別経路の長いopを待つ場合は、送信からその上限までに応答が届く保証ではない。
  別経路の未解決要求が分かるhostはその待ちも考慮し、分からない場合も、時間切れだけで再起動や二重実行を判断せずcore §5.1で復旧する。
- runの間、probeはほかの要求に答えない（[OEP core](oep-core.ja.md) §4.4）。実行・準備・後始末はmax_op_msに含まれ、所有者の要求自身の処理中はleaseを数えない。
  応答生成後の送信待ちは数える。別経路のロック不要照会や再送だけでは、所有者のleaseは延びない。
- 書き込みのように多くの要求を送る処理は、lease が切れないよう、普段の要求か keepalive でロックを保つ。
  I2C/SPIのread_rxのようにデータを消費する操作も、応答を失うと結果が不明になる。再送記録が無くresult_lostなら、そのフレームを回収できるとは限らない。
  新しいcorrでread_rxを送ると次のフレームを消費する。要求の再送と、新しいデータの読出しを区別する。

debugの高水準opで後始末が失敗すると、connectionと依存console streamが閉じ、未読の出力も失われる。
必要なログは操作の前と実行の合間にconsole readでhostへ移しておく。線の故障直前のcrashログまで回収できる保証はない。
raw dmiで抽象コマンドやresetからhalt待ちを組む場合は、待ちを含む一連を1要求に入れる（debug §4.1）。

## 12. 通知

- 購読にはロックが要り、購読はセッションと一緒に終わる。監視だけの host はロック不要の read を使う。
- 購読は、通知を送り出すインターフェースの fn に、その fn 自身の op で送る: subscribe は op 0x01、unsubscribe は op 0x02（どのインターフェースでも
  同じ番号。要求は相手の fn を持たない）。その fn の describe の ops にこの 2 つが立っていなければ、その fn は通知を送らない（送っても
  unknown_operation）。同じ fn を購読し直すと購読は丸ごと置き換わり、seq は購読のたびに 0 から数える（core §10.3）。
- **role で振り分ける**（core §10.1）: corr で照らすのは応答（0x02）だけ。出来事（0x03）とデータ（0x04）は byte 1〜2 が fn。通知が
  来続けても、応答を待つ処理と入力を読む処理が期限までに終わるようにする。
- **seq** は fn ごとのフレームの通し番号（u16、一周する）。飛びは、probe の中か途中で通知が失われたこと。データではストリームの
  `position` も失われた分を示す: フレームの position が前のフレームの終わりと合わなければ、その間のバイトは失われた（core §10.2、
  [共通部品](../interfaces/oep-if-common.ja.md) §1.5）。
- **min_bytes / max_delay_ms の選び方**: データについて、probe は min_bytes がたまるか、最初のバイトから max_delay_ms が過ぎたら送る（0 はその条件を
  使わない。両方 0 ならすぐ送る）。出来事はまとめられず、先の応答の後すぐ届く（core §10.3）。まとめを大きくするとフレームが減り、遅れを短くすると待ちが減る。シリアルの口では min_bytes を
  小さく保つ（§8 の受けの量）。
- **probe の時刻の読み方**: probe の今の時刻は fn 0 の clock（op 0x04）で読む（core §7.6）。ロック不要で、session_id 0 で送れば
  セッションが無くても、ほかの道具がロックを持っていても答えが来て、セッション、ロック、lease に触れない。応答は boot_id と uptime_ns。
  1. 送る直前に自分の時計を読み（t0）、応答を受けた直後にまた読む（t1）。
  2. uptime_ns は t0 と t1 の間のどこかで読んだ probe の時計の値なので、中点 (t0 + t1) / 2 をそれに当て、不確かさを (t1 − t0) / 2 とする。
  3. 精度が要るときは clock を何度か続けて読み、t1 − t0 のいちばん短いものを使う（往復の遅れは揺れるが、短い往復ほど中点が確か）。
  4. キャプチャの前と後など時を置いて読み直すと、二つの時計のずれ（一方がどれだけ速いか）が分かる。マークや区画の時刻（probe の時計）を
     host の時刻に写すのに使う。
  5. 応答の boot_id が前と違えば probe は再起動した: それより前の uptime_ns とは比べられない（core §6.5）。
  中継のブローカーを通しても同じに使える: ブローカーは clock に自分で答えず probe に中継するので、値は probe のもので、中継の遅れは往復に
  入る（transports §1）。probe が生きているかは応答の待ち時間で、再起動は confirm、clock、open の boot_id で分かる（core §6.5）。
- 通知は購読を受けた経路に送られる。同じ session_id の open を別の経路で送っても送り先は変わらない（core §6.2）。送り先を移すのは
  subscribe のし直しだけである（core §10.3）。経路を閉じて開き直したとき（TCP の開き直し、USB の挿し直し、§8）も、購読は閉じた
  経路へ送り続け、その分は捨てられる（transports §3）。host は新しい経路で、続けたい fn をすべて同じ条件で subscribe し直す
  （seq は 0 から。間に失った分は seq と position の飛びで分かる）。
- キャプチャの流し続けには独自の規則がある: 送る余地が無いと probe は新しい区画を丸ごと捨て、stop の前に取った分は送り続け、stop の後で
  受けた位置の終わりが status の write_pos と等しくなれば host はすべてを持っている（[キャプチャ](../interfaces/oep-if-capture.ja.md) §2.1）。
  probe は区画が終わる前にその区画のデータを送ることがある。トラックがエラーで止まったら（stopped reason 3、state 6）、status を読み、
  受けたデータのうち write_pos から先を捨てる（区画の中で落とした区画は、データではない。キャプチャ §2.2）。受けている
  間はロックを保つ。

captureの世代は同じboot内で使い回さない。0xFFFFFFFFを使い切ると、既存データの読出し・解放はできるが、新しいstartは再起動までcause 2で断られる。
再起動後はboot_idを確かめ、新しいsessionとplanから設定し直す（capture §0）。

## 13. plan とピン

- plan は fn ごと（`oep.probe.plan`、[plan](../interfaces/oep-if-plan.ja.md) §2）。plan_apply は名前を挙げた fn の割り当てだけを置き換え、ほかの fn の plan は残る。UART を受けた
  まま capture を足せる。解くときは plan_release に fn を並べる（n = 0 ならすべて）。
- ほかの fn や connection が持つピンを取ろうとすると rejected unavailable で、何も変わらない（core §8.1）。
- 解いたピンは空きの状態になる: probe の設定の idle か、Hi-Z（core §8）。治具の配線で相手の入力が浮くピン（DUT の RX につながる
  TX など）は、`oep.probe.config` の idle で pull-up の入力にして保存する（§15）。
- planはセッションの資源で、end、leaseの期限切れ、forceで解放される（core §9）。hostの配線設定は残せるが、実行中のplanを引き継がない。

## 14. コンソール

- marksを提供するconsoleでは、from 3のargにresetのkind 0x40を置いて最後のresetマークから読める（common §1.2、console §2）。
  marksを提供しない構成では、hostが保持する位置からfrom 0で読み、操作の区切りをhost側のログに記録する。
- モニターが一度閉じて戻るときは、前回読んだ位置から読む。
- 応答の start が要求した位置より進んでいたら、その差が失われた量である。表示に残す。
- 表示用の時刻は受け取った時刻を使う（probe は byte ごとの時刻を持たない）。
- **入力を送る**: write は probe の送りの列（大きさは probe が決める）に入った分を accepted で返す（[コンソール](../interfaces/oep-if-console.ja.md) §2）。
  accepted が count より少なければ、残りを少し待ってから送る（列は target が
  受け取った分だけ空く。dmseq では target の 1 つのフレームへの答えにつき 2 byte、DMDATA では 1 つの枠への答えにつき 3 byte）。accepted は target が受け取ったことでは
  ない: 届いたかはコンソールの出力（エコーなど）で見る。
- **dmseq のコンソールが答えているか**: 出力するか入力を見に行く target は、少なくとも長い待ちに短い待ちを足した時間
  （[dmseq](../interfaces/target-console-dmseq.ja.md) の「タイムアウト」）に 1 回フレームを出す。未同期のまま 3 s の間有効なフレームを
  読まなかったら、dmseq のコンソールが答えていないと利用者に伝えてよい。出力も入力の読みもしない target は何も出さないので、これは
  コンソールが無いことの証拠ではない。
- **SDI と DMDATA の限界**: この 2 つの方式は枠に番号を持たないので、線の書き込みが失われると、同じ枠が 2 回届いたり（重複）、DMDATA では
  答えに載せた入力の byte が失われたりしうる。重複も欠落も許されないなら dmseq を使う（[dmseq](../interfaces/target-console-dmseq.ja.md)）。
- **hart を止めたとき**: probe は hart が止まっている間コンソールを読まない（[コンソール](../interfaces/oep-if-console.ja.md) §3）。dmi で抽象コマンドを使って
  DATA0 / DATA1 を変えたら、hart を走らせる前に元の値を書き戻す（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §4）。

## 15. probeの設定

`oep.probe.config`はdisable/idle/labelを扱う。配線、UART、ネットワークの設定はhostまたは別の定義で管理する。

1. list/describeで対応itemsとopsを読む。saveがあればstorage.max_bytesは1以上で、無ければ保存を提供しない。
2. getのcount個の項目を読み、末尾の拡張TLVを別に読む。moreならcountをfirstへ加えて続ける。
   途中でgenerationが変われば最初から読み直す。generationはboot内の変更カウンタで、hostが計算するhashではない。
3. 欲しい内容とキーごとに比べ、同じなら何もしない。変更はロックを取り、count付きset/unsetを送る。
   外側のTLVと項目のtag bit7は別の規則なので、項目はbit7=0で送る。
4. 保存したい場合だけsaveする。stateが提供され、saved_generationが現在のgenerationと等しければ保存済み。
   内容が同じならprobeは不要な書込みを省く。eraseは保存だけを消す。
5. firmware更新後に部分適用/読めない状態になったら、getで効いている項目を確認し、保存したhost設定と比べて修復する。
   無効なlabelなどを理由に独立したdisable/idleが全て消えたと決め付けない。

idle出力はhostが去った後も空きのpinで効く。保存前に配線とlevelを確認する。
保存を提供しない最小構成ではstateも必須ではない。

## 16. wireとtargetの操作を組み合わせる

wireのattachが返したconnection番号を、対応するtargetのfnへの要求で明示する。wireのfn番号をtargetのfn番号として使わない。
接続を複数持つ場合も、保存した番号を要求ごとに選び、最後の接続を暗黙に使わない。

arm-adiの最小probeはtransferだけを提供する。read_block/write_blockがopsに無ければ、hostがAPの選択・設定・posted readの回収をtransferで組む。
ブロック操作があれば、そのmax_lengthの範囲で使う。未実装の任意操作からの組み替えと、実行した操作が失敗した後の再実行は区別する。
失敗した書き込みやdone 0はtargetへの作用が無かった保証にならないため、失敗後に別の操作で同じ書き込みを自動的に繰り返さない。
例外は、何度実行しても1回と同じ状態にしかならないと定義された群だけである（riscv-dm では hart が止まっている間の DM の作業用レジスタと、
値のほかに作用の無いレジスタの読み書き、[線とデバッグ](../interfaces/oep-if-debug.ja.md) §4.1）。落ちやすい線では、書き込みの後に同じ群で
読み戻して確かめ、確かめられなければその群をやり直す。
生のtransfer/dmiで扱うチップ固有の手順と復旧は、host側のプロジェクトが管理する。
