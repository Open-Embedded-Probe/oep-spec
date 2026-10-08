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
- 口の上には、OEP の応答と一緒に生のバイト（target のコンソールなど）が流れてくる（transports §4）。フレームにならないバイト、
  CRC の合わない候補、待っていない corr の応答は雑音として捨てる。**雑音を見ても送り直さない**。応答が来ないことは待ち時間だけで
  判断し（core §4.4）、送り直しは §8 のとおり。
- 正しい COBS のフレームは、2 つの 0x00 の間に 65796 byte（65535 byte の message とその CRC-16、
  254 byte ごとに COBS の code の 1 byte）より多くを持たない。それより長くなった候補は、閉じの 0x00 を待たずに雑音として捨ててよい。
- 送るフレームは必ず前後を 0x00 で囲む。前の 0x00 が無いと、probe はフレームの頭を生のバイトとして流してしまう。
- 自分のセッションが口を持っている間、その口の生の転送は止まる（transports §4）。コンソールは OEP の read で読む。

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
- **one-shot CLI はコマンドごとに新しいセッションを開く。** 再開は無い: セッションが終わると（end、lease の期限切れ、force）、
  probe はそれが作ったものをすべて解放する（core §6.4、§9）。前のコマンドから要るものは、明示の経路で probe の上に見つける:
  同じピンへの attach はスロットが保つ接続を返し（flags bit1。その attach が運ばない idle_clock などの設定は、接続の今のままになる。
  [線とデバッグ](../interfaces/oep-if-debug.ja.md) §1）、同じ場所で同じ mechanism のコンソールの open は、閉じた後でも
  位置とマークを保ったストリームを返すので、リセット直後の最初の行が残る（[コンソール](../interfaces/oep-if-console.ja.md) §2）。
  コマンドの間も駆動し続けるピン（電源のスイッチ）は設定の plan か出力の idle にし、コマンドの間も張っておく接続はスロットにする
  （[probe の設定](../interfaces/oep-if-probe-config.ja.md)）。boot_id を probe ごとに、unit_id をキーにして覚える: open の応答の
  boot_id が違えば probe は再起動したので、覚えた fn の対応を使う前に list し直す（core §6.5）。
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
- **モニターは入力を送る間だけロックを取る**（open → write → end）。読み出しはロック不要なので、モニターがロックを握り続けると、
  別の端末の書き込みが `locked` で失敗する（開発で最もよくある組み合わせ）。
- 終わるときは end を送る（送らなくても期限で下りる）。
- **止まって走り直しうる host**（CLI、ブローカー）: 経路が閉じてもセッションは終わらない（transports §3）ので、end を送らずに止まった
  host のロックと資源は lease が切れるまで残る。session_id を probe ごと（unit_id をキー）にファイルなどに残しておき、次に走るときは
  まずその id で open し、すぐ end して、前に持っていたものを解放する（同じ id の open は送り直しとして受けられる、core §6.2）。
  その後は新しい id でセッションを開く。こうしないと、前の lease が切れるまで locked で待つことになる。

### 5.1 1 つの probe の複数の経路

- 1 つの probe が複数の経路（vendor bulk、HID、シリアルの口、TCP）を見せることがある。経路はセッションとロックを 1 つ共有する
  （transports §3）。fn 0 の describe の unit_id（ASCII の大文字と小文字を区別せずに比べる）でまとめ、`x-` で始まる unit_id ではまとめない
  （core §7.5）。
- 選べるなら vendor bulk、HID、シリアルの口の順に使う（transports §3）。シリアルの口は生のバイトも運び、受けの量にも限りがある
  （transports §4）。
- 自分のセッションの id を持つ要求は、すべて 1 つの経路で送る（transports §3）。ロック不要の要求は別の経路で送ってよい（たとえば、
  デバッガが vendor bulk を持つ間に、HID で describe と state を読む）。
- max_frame、window、max_inflight とプロトコルの revision は経路ごと（core §4.4、§7.1）: 使う経路ごとに confirm する。

### 5.2 probe を再起動する（restart）

`oep.probe.restart` の restart（[再起動](../interfaces/oep-if-restart.ja.md)）は、口を抜き差しせずに probe を起動し直す。おかしな状態になった
probe の立て直しと、host 自身の「probe が再起動した」ときの道筋の試験に使う。任意のインターフェースなので、list で `oep.probe.restart` を
見つけてから使う。その describe の restart_max_ms は、応答から同じ経路で confirm にまた答えるまでの最長の時間で、下の 5 の上限になる。
restart の前に読んでおく。

1. ロックを取る（restart はロックの要る op。session_id 0 なら session_required）。保存したい設定があれば先に save する:
   保存していない設定は再起動で無くなる（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §2）。
2. restart を送る。後ろに要求を続けない（どの経路にも）: 応答の後の probe は何も処理せず、答えない。
3. completed success の応答が来たら、その probe の経路をすべて閉じる。UART bridge で port_speed を上げていたら、起動時の速さに
   戻す（[リンク](../interfaces/oep-if-link.ja.md) §3 の host 2）。
4. 少し（目安 100 ms）待つ。probe はこの間に再起動を始める。
5. 新しく開くのと同じに開き直す（§4、transports §3 の探りの規則: 最初は confirm。UART bridge では起動時の速さ）。USB では device が bus から外れて列挙し直す:
   OS の口の名前が変わることがあるので、serial number（= unit_id）で探し直す。開けないか confirm に答えが無ければ、応答を受けてから
   restart_max_ms が過ぎるまで開き直しと confirm を繰り返す（それぞれの confirm の応答は core §4.4 のとおり待つ）。それでも正しい
   confirm の応答が無ければ、probe は無くなったものとして扱う: その probe の経路を閉じて利用者に知らせ、利用者が開き直すまで何も送らない。
   利用者が前もって頼んだ開き直し（道具の option で、閉じた後も一定の時間開き直しを続ける、など）は、利用者が開き直すことに当たる。
   UART bridge と TCP の口は閉じずに残ることもあるが、同じ手順でよい。TCP では、アドレスが変わりうるので unit_id で browse し直す（§4.1）。
6. confirm の boot_id を restart の前のものと比べる。違えば再起動した: 覚えた fn の対応、資源の番号、ストリームの位置、セッションを
   すべて捨て（core §6.5）、list し直し、要るなら新しいセッションを開く。前のセッションの id の要求は no_session で断られる。同じなら
   restart は実行されなかったものとして扱う。
7. 応答が来なかったときも 5〜6 と同じに確かめる。restart_max_ms は、restart の応答の待ちが過ぎた時から数える。restart を同じ corr で
   送り直したときは、再起動した後の probe は no_session で断る: それも再起動のしるしで、5〜6 に進む（restart_max_ms はそれを受けた時から）。

**中継する host**（transports §1 の中継のブローカー）は、restart をほかのロックの要る op と同じに中継し、応答を道具に返した後は、上と同じに
probe への経路を閉じる。ブローカーの probe への経路が無くなれば（ブローカーが閉じた、USB で列挙し直した、TCP が閉じた）ブローカーは終わり、
道具への接続も閉じる（transports §1）: 道具は新しく開くのと同じにやり直す。

再起動の後、保存した設定はどの起動とも同じに掛かる（at boot のスロットはまた attach する）。target は reset されず、止めていた hart は
止めたまま残る（[再起動](../interfaces/oep-if-restart.ja.md) §2）。

### 5.3 probe とスロットの名指し方

- **アドレス**: host が probe とスロットを文字で名指すときは `oep://<unit_id>[/<slot name>]` と書く。authority は unit_id（core §7.5、小文字）、
  path はスロットの名前（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §1.1）1 つだけ。path の無い `oep://<unit_id>` は probe 自身。
  IDE や設定のファイルが probe を覚えるときはこの形で覚える（VID:PID や口の名前ではなく）。unit_id とスロットの名前は、どちらも URL の中で
  encode の要らない文字だけを使う。
- **インターフェース**: 文字で 1 つのインターフェースを指すとき（CLI、設定のファイル、ログ）は `name#instance` と書く（instance は list の値、
  0 から。`#0` は省いてよい）。例: `oep.fixture.uart#1` は 2 つめの `oep.fixture.uart`。

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
    §6.4）。
- lease は、対話的な道具は短く（2〜3 秒）、試験のセッションのように長く握る道具は長く（10 秒、keepalive で更新）。

## 7. ブローカー

1 つの probe を同じ PC の複数の道具で同時に使うときは、host の側のブローカーが probe との 1 本のセッションを持ち、道具ごとの
要求を束ねる（corr の付け替え、道具の open / end を probe に出さない、道具が切れたらその道具の資源を外す）。probe から見える
transport とセッションは 1 つのまま。道具とブローカーの間は、仕様の TCP の形（`length(u16) message`、transports §1）を使える。セッションの
op に自分で答え、ほかを中継するブローカーは、transports §1 と core §5.2 の中継のブローカーの規則に従う（confirm の transport の index は
0xFF、client の接続ごとの corr の対応表）。自分で答えるのはセッションの op（confirm、open、end、keepalive、lock_state）だけで、fn 0 の
clock はほかの要求と同じに probe に中継する（道具が読む時刻が probe のものであるため。transports §1、core §7.7）。

## 8. 応答の対応付けと送り直し（transports §5 と core §5.2 が求めること）

- **corr が合わない応答は受け取らず、入力を読み捨てて同期し直す**（transports §5）。USB の経路によっては、取り消した転送の残りが次の
  応答として届くことがある（USB-over-IP の層を通したときに見た）。vendor bulk / HID / TCP のフレームには CRC が無いので、
  corr の照合がこの防御になる。
- **corr は要求ごとに 1 ずつ進める**（session_id 0 の要求も数える。65535 の次は 1、0 は使わない。core §4.1）。同じ corr を使うのは
  送り直しのときだけ。
- 応答が壊れたか来なかったら、**同じ corr で送り直す**（状態を変える要求も。core §5.2）。probe は覚えた応答を返すので、
  二重に実行されない。
  - result_lost: probe が応答を覚えていない（大きすぎた、表から落ちた）。実行されたかは分からないので、状態を読み直して確かめる。
  - 同じ corr の要求は、中身が違っても送り直しとして扱われ、覚えた応答が返る（core §5.2）。corr を使い回すと別の要求の応答を受けるので、
    番号付けを誤らない。
  - 立て直しの中で unsubscribe と end を送ったときは、元の要求は送り直さない。
- **送り直す回数の目安**（core は回数を決めない）:
  - 答えがまったく来ない: core §4.4 の待ちの後に 1 回。
  - シリアルの口で壊れたフレームが届いた（セッションが口を持っている間）: 待たずにすぐ、数回（例: 3 回）まで（下の「シリアルの口の壊れたフレーム」）。
- **最後の送り直しにも答えが無ければ、その経路は失敗した**（core §5.2）: その要求の結果は分からず、その経路で出ている要求もいっしょに
  失敗する。何もなかったように次の要求を送らない。COBS を含むどの種類のフレームでも、先に立て直す: 入力が静かになるのを待ち、
  自分の corr を持つ応答が返るまで confirm する（transports §5）か、口を閉じて開き直す。その confirm で boot_id が変わっていれば再起動
  （やり直す、§5）。その後、状態を変える要求を繰り返す前に状態を読む。
- **シリアルの口の壊れたフレーム**: 未解決の応答があるときに CRC の合わない候補が届いたら、それを失われた応答とみなし、待ち時間を待たずに
  同じ corr で送り直してよい（core §5.2。セッションが口を持っている間）。probe は覚えた応答か result_lost を返すので安全である。
  フロー制御の無い USB-UART の変換器は、続けて流れる probe → host のバイトをどの速さでも落としうる。負荷の下の壊れたフレーム 1 つを、
  線の失敗とみなさない。
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
| unknown_operation（0x02） | その fn にその op が無い | probe が実装していない任意の op（core §1.2）。任意の op は describe の ops（0x09）を見てから使う。ops を確かめて送らないときは、この応答と同じ失敗を報告し、呼び出し側がどちらでも 1 つのエラーを見るようにする |
| malformed（0x03） | 要求の形が誤り | 自分の符号化の誤りか、どの revision でも除かれる値。そのまま送り直さず、要求を直す。要求のバイト列をログに残す |
| unavailable（0x04） | 今の状態か今の資源ではできない | TLV を読む: cause（1 ピンが使用中、2 数の上限、3 保存の容量が足りない、4 グループに束ねられている、5 設定が持っている、6 状態が違う）、channel、fn。利用者に見せ、自分の資源を解くか順を変える。cause 5 は probe の設定（plan、disable、出力の idle、スロット）が持っているので、要求ではなく設定を変える（どれが持つかは probe の設定の get で見る）。知らない cause は不明として見せる（core §2.4） |
| window_exceeded（0x06） | window / max_inflight を超えた | この経路の probe の上限を超えて先送りした。応答を待ち、新しい corr で送り直す（core §5.2: 直した要求は新しい corr で送る） |
| no_session（0x07） | どのセッションもロックを持っていない: 自分のセッションが終わった（end、lease の期限切れ、force）か、probe が再起動した | セッションが作ったものはすべて解放された（core §9）。新しいセッションを開き、plan、attach、購読を張り直す。黙って続けない（§5）。再起動は open の boot_id で分かる |
| locked（0x08） | 別のセッションがロックを持っている | payload に残りの ms と、あれば持ち主の文字列。待つか、持ち主を添えて「使用中」とするか、利用者が頼んだときだけ force で奪う（§6） |
| session_required（0x09） | ロックの要る op の要求が session_id 0 だった | 誤り: 自分の session_id で送る |
| no_connection（0x0A） | その資源の番号を知らない | 接続やストリームが閉じたか、probe が再起動した。番号を捨て、資源を作り直す（attach、open）。長く持つ番号は一覧の op で確かめる（core §9） |
| unsupported（0x0B） | 定義にはあるが、この probe は扱えない | payload の tag が何かを示す: 0x00 = 固定部分の値、それ以外は受け取ったままの critical な TLV の tag。channel / index の TLV がどの要素かを示すことがある。describe を見て probe が宣言するものを選ぶ。そのまま送り直さない。confirm では TLV 0x01 が probe の扱える revision を示す（core §7.1） |
| result_lost（0x0C） | 送り直しの応答を覚えていない | 実行されたかは分からない: 状態を読み直す（core §5.2） |
| 0x05、0x0D、0x0E | 予約 | 失敗として扱う |

- **completed failed / partial**: payload は op が決める（wire と target では `status` と `done`、[共通部品](../interfaces/oep-if-common.ja.md) §3）。
  status の line はふつう、速さを下げて attach し直す。wait は後で `done` から続ける。fault は原因を読んで消す。timeout は上限を見直す。
  state は先に target を要る状態にする。知らない status は失敗。
- インターフェース固有の理由（0x40〜0x7F）は各インターフェースが定める。v1 には無い。

## 10. revision、TLV、知らない値

- **プロトコルの revision**: 経路の最初の confirm で扱える範囲を送り、その後は `min_rev = max_rev =` 使っている revision を送る
  （core §7.1）。rejected unsupported なら、TLV 0x01 が probe の扱える revision を示す。revision は経路ごと（TCP は接続ごと）。
- **インターフェースの revision**: list は fn ごとに (name, instance, revision) を返す。知らない revision のインターフェースは使わない
  （core §2.7）。probe は古い revision を別の fn で出してよいので、知っているほうを選ぶ。instance は (name, revision) ごとに数える
  （core §7.2）。
- **応答の読み方**: 固定部分の後ろは TLV の並び。知らない tag は読み飛ばす。繰り返さない tag は最初のものを使う。並びは要素に長さの
  無い `count × element` なので、要素は定義のとおりにフィールドごとに読む。固定の形は末尾を延ばされない。長さが定義と違う TLV の値は
  壊れている（core §2.3）。新しい情報は新しい tag で来る。応答の中で bit 7 の立った TLV は知らない tag として扱う。
- **要求の送り方**: 効かなければ意味の無い TLV か、効かないと害のある TLV（pins、速さの上限など）には critical の bit を立てる（core §2.3）。
  その tag を実装しない probe は critical なら断り、そうでなければ黙って無視する。実装する probe は bit によらず値を確かめる。
  要求の TLV の値を後ろに延ばさない（core §2.3）。繰り返さない tag を繰り返さない。
- **応答の知らない値**: 知らない resolution、outcome、status、reason は失敗。知らない kind の出来事は捨てる（seq は数える）。ほかの enum
  の知らない値（cause、scan の種類）は不明として見せる。flags の予約の bit は無視する（core §2.4）。
- **真偽値と文字列**: 0 以外の真偽値は真と読む。応答の文字列は、見せる前に制御文字と不正な UTF-8 を置き換える（core §2.1）。

## 11. 時間のかかる操作

- どの op も 1 つの応答で終わる。時間のかかる op（run、キャプチャの configure、save、attach、scan、reset）は、応答が来るまで待つ。
  待ち時間は op の引数で決まる（core §4.4。attach、scan、riscv-dm の reset は max_op_ms）。
- run の間、probe はほかの要求に答えない（[OEP core](oep-core.ja.md) §4.4）。timeout は lease と応答の待ち時間より十分短くする。
- 書き込みのように多くの要求を送る処理は、lease が切れないよう、普段の要求か keepalive でロックを保つ。

## 12. 通知

- 購読にはロックが要り、購読はロックと一緒に終わる（end、期限切れ、force。core §11.3）。監視だけの host は、代わりに bind した
  シリアルの口の生のバイトを読むか（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §1.2）、ロック不要の read の op で読みに行く。
- 購読は、通知を送り出すインターフェースの fn に、その fn 自身の op で送る: subscribe は op 0x30、unsubscribe は op 0x32（どのインターフェースでも
  同じ番号。要求は相手の fn を持たない）。その fn の describe の ops にこの 2 つが立っていなければ、その fn は通知を送らない（送っても
  unknown_operation）。同じ fn を購読し直すと購読は丸ごと置き換わり、seq は購読のたびに 0 から数える（core §11.3）。
- **role で振り分ける**（core §11.1）: corr で照らすのは応答（0x02）だけ。出来事（0x05）とデータ（0x06）は byte 1〜2 が fn。通知が
  来続けても、応答を待つ処理と入力を読む処理が期限までに終わるようにする。
- **seq** は fn ごとのフレームの通し番号（u16、一周する）。飛びは、probe の中か途中で通知が失われたこと。データではストリームの
  `position` も失われた分を示す: フレームの position が前のフレームの終わりと合わなければ、その間のバイトは失われた（core §11.2、
  [共通部品](../interfaces/oep-if-common.ja.md) §1.5）。
- **min_bytes / max_delay_ms の選び方**: データについて、probe は min_bytes がたまるか、最初のバイトから max_delay_ms が過ぎたら送る（0 はその条件を
  使わない。両方 0 ならすぐ送る）。出来事はまとめられず、先の応答の後すぐ届く（core §11.3）。まとめを大きくするとフレームが減り、遅れを短くすると待ちが減る。シリアルの口では min_bytes を
  小さく保つ（§8 の受けの量）。
- **probe の時刻の読み方**: probe の今の時刻は fn 0 の clock（op 0x04）で読む（core §7.7）。ロック不要で、session_id 0 で送れば
  セッションが無くても、ほかの道具がロックを持っていても答えが来て、セッション、ロック、lease に触れない。応答は boot_id と uptime_ns。
  1. 送る直前に自分の時計を読み（t0）、応答を受けた直後にまた読む（t1）。
  2. uptime_ns は t0 と t1 の間のどこかで読んだ probe の時計の値なので、中点 (t0 + t1) / 2 をそれに当て、不確かさを (t1 − t0) / 2 とする。
  3. 精度が要るときは clock を何度か続けて読み、t1 − t0 のいちばん短いものを使う（往復の遅れは揺れるが、短い往復ほど中点が確か）。
  4. キャプチャの前と後など時を置いて読み直すと、二つの時計のずれ（一方がどれだけ速いか）が分かる。マークや区画の時刻（probe の時計）を
     host の時刻に写すのに使う。
  5. 応答の boot_id が前と違えば probe は再起動した: それより前の uptime_ns とは比べられない（core §6.5）。
  中継のブローカーを通しても同じに使える: ブローカーは clock に自分で答えず probe に中継するので、値は probe のもので、中継の遅れは往復に
  入る（transports §1）。probe が生きているかは応答の待ち時間で、再起動は confirm、clock、open の boot_id で分かる（core §6.5）。
- 通知は購読を受けた経路に送られる。同じ session_id の open を別の経路で送ると、そちらに移る（core §6.2）。
- キャプチャの流し続けには独自の規則がある: 送る余地が無いと probe は新しい区画を丸ごと捨て、stop の前に取った分は送り続け、stop の後で
  受けた位置の終わりが status の write_pos と等しくなれば host はすべてを持っている（[キャプチャ](../interfaces/oep-if-capture.ja.md) §2.1）。
  probe は区画が終わる前にその区画のデータを送ることがある。トラックがエラーで止まったら（stopped reason 3、state 6）、status を読み、
  受けたデータのうち write_pos から先を捨てる（区画の中で落とした区画は、データではない。キャプチャ §2.2）。受けている
  間はロックを保つ。

## 13. plan とピン

- plan は fn ごと（`oep.probe.plan`、[plan](../interfaces/oep-if-plan.ja.md) §2）。plan_apply は名前を挙げた fn の割り当てだけを置き換え、ほかの fn の plan は残る。UART を受けた
  まま capture を足せる。解くときは plan_release に fn を並べる（n = 0 ならすべて）。
- ほかの fn や connection が持つピンを取ろうとすると rejected unavailable で、何も変わらない（core §8.1）。
- 解いたピンは空きの状態になる: probe の設定の idle か、Hi-Z（core §8）。治具の配線で相手の入力が浮くピン（DUT の RX につながる
  TX など）は、`oep.probe.config` の idle で pull-up の入力にして保存する（§15）。
- plan はセッションの資源で、セッションのロックが終わるとき、end、lease の期限切れ、force のどれでも解放される（core §9）。設定から入れた plan は残る。

## 14. コンソール

- 書き込みのあとのモニターは「最後の reset マークから」読む（common §1.2 の from 3）。前回の未取得のログが流れない。
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

## 15. probe の設定（`oep.probe.config`）の使い方

設定は項目の並びで、項目ごとにキーがある。set はキーごとに置き換え、unset はキーを消し、save は今の設定を丸ごと書く
（[probe の設定](../interfaces/oep-if-probe-config.ja.md)）。host は欲しい設定を自分のファイルに持ち、probe をそれに合わせる:

1. **見る**: list に `oep.probe.config` があること（無い probe は設定を扱わない）。describe で items（扱う tag）、storage（max_bytes。
   0 は保存できない）、slots_max を見る。
2. **get で今の設定を読む**（ロック不要）。get は項目を tag の順に、同じ tag の中はキーの順に、host が送ったとおりの形で（critical の bit を
   落として）返し、どのページも同じ hash を返す。ページの途中で hash が変わったら、最初から読み直す。hash の作り方は probe が決めるので、
   host は計算しない（probe の設定 §2）。
3. **自分の欲しい設定と項目ごとに比べる。同じなら何もしない。**
4. **違うとき**: セッションを開き、欲しい項目を set で送り（set はキーごとに置き換え、送らないキーは残す）、get にあって要らない
   キーを unset する。set は原子的で、どれかの項目が断られれば何も変わらない（probe の設定 §2）。
5. **要るときだけ save する**: state（ロック不要）を読み、storage_state が 1 で storage_hash が今の get の hash と等しければ、保存済みの
   設定は今の設定と同じなので save しない。違えば save を送る。保存は flash を書いて消耗させ、書く間（最長 max_op_ms）ほかの要求を止める。
   ループの中や毎回の実行で save しない。
6. **効き目を確かめる**: 自動の attach と bind のコンソールは set が終わった後に始まり、巻き戻されない。state の slot_state と bind_state
   で見る（probe の設定 §3.3）。
7. **firmware を更新した後**: state が storage_state 2（読めない）で理由 2（保存した項目が指すインターフェースが無い、revision が違う、
   bind の口がシリアルの口でなくなった）なら、保存した設定は掛かっていない。自分のファイルから set し直して save する。理由 1 は保存の
   形が読めない、理由 3 は掛けるのを断られた（資源がぶつかる）。

覚えておくこと:

- 既定値は無い: 設定していないことは何もしない（probe の設定の冒頭）。設定の plan はセッションではなく設定のもの: plan_release では
  解けず、その fn への plan_apply は断られる（[plan](../interfaces/oep-if-plan.ja.md) §2.3）。
- idle: 相手の入力が浮くピンには適切な pull の入力を選び、外部回路を制御する channel の出力は安全な level を選ぶ。出力の idle は
  ピンが空いている間ずっと、起動時にも駆動するので、保存する前に配線を確かめる。idle の項目のある channel は、count = 0 の scan と pins
  の無い attach から外れる（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §1）。
- disable: 外に出していない channel や、ほかの部品につながる channel を並べると、probe はそれを駆動しない。
- label で名付けた線は、probe の設定 §1.3 の探し方で見つかる。
- スロットの target が入れ替わっていないかは、connections の tid（target_id）で確かめる（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §2.1）。probe はスロットの target を照合しない。
- erase は保存した写しだけを消す。今の設定は次の起動まで残る。

### 15.1 Wi-Fi の設定

describe の items に wifi（0x08）があり wifi_max が載る probe は、Wi-Fi でつなぐネットワークを設定で持つ（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §1.4）。

- **passphrase は利用者に聞く**: 入力を画面に出さないプロンプトで受ける。表示しない、ログに書かない（probe の設定 §1.4）。コマンドの引数
  （シェルの履歴とプロセスの一覧に残る）や host の設定ファイルに平文で置かない。保管するなら OS の鍵の保管を使う。
- **経路**: passphrase は暗号なしで set に載る。手元の USB やシリアルの口か、信頼するネットワークの経路で送る（[安全とセキュリティ](security.ja.md) §1）。
- **並び**: index が試す順。よく使うネットワークを小さい index に置く。probe は最初につながった entry を使い、切れたら初めから試す。
- **比べ方**（§15 の 3）: get は passphrase を返さない（pass_len は、あれば 0xFF、無ければ 0）。host は ssid と passphrase の有無だけを比べ、
  passphrase は利用者が変えると言ったときだけ送る。ssid だけ変えるときは pass_len 0xFF で送ると、その index の passphrase が残る。
  entry を別の index に移すときは、passphrase をもう一度送る（0xFF は同じ index のものしか保たない）。
- **見る**: state（ロック不要）の wifi の TLV。state 2 で使っている entry、rssi、ipv4 が分かる。state 3 なら reason（1 見つからない、
  2 認証、3 アドレスが来ない）を利用者に見せる。
- TCP の経路で、使っている entry を変えると（変えた set の応答の後で）その経路も切れる。シリアルの口か USB から設定するのが確か。
  TCP からしか届かないときは、変えた後に §4.1 のやり方で probe を見つけ直す。
- 保存しなければ、再起動で消える（§15 の 5）。
