# Open Embedded Probe — 経路とフレーム（OEP transports）v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作る。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](versioning.ja.md) §6）。
この文書は、OEP のメッセージをどう運ぶかを定める: 経路とそのフレーム、host が probe の口を見つけて開くやり方（USB の見分け方、探りの規則、口の選び方）、
1 つの probe の複数の経路、シリアルの口を生のバイトと共用すること、長さつきのフレームの区切りの立て直し、host の待ちが数える転送の時間。
メッセージ、セッション、そのほかは [OEP core](oep-core.ja.md) が定める。この文書は本体の層に属し、本体の適合（core §1.2）とプロトコルの
revision（core §7.1）はこの文書も含む。番号の唯一の定義は `registry/oep-v1.toml`。

## 1. フレーム

経路の種類は 2 つに分かれる。**シリアルの口（serial port）** は OS からシリアルデバイスに見える経路（UART bridge = probe の
UART を USB-UART の変換チップで出したもの、USB CDC、内蔵の USB シリアル）で、OEP とシリアルの生のバイトを同じ口で運ぶ（§4）。
ほかの経路（USB の vendor bulk、HID、TCP）は OEP だけを運ぶ。

| 経路 | フレーム |
|---|---|
| シリアルの口（UART bridge、USB CDC、内蔵の USB シリアル） | COBS + CRC-16、0x00 で区切る（下） |
| USB の vendor bulk、TCP | `length(u16) message`。CRC なし。length 0 は予約（keepalive。読み飛ばす）。vendor bulk では 1 回の転送に複数のフレームが入ってよく、フレームが転送をまたいでもよい |
| USB の HID（vendor 定義の report） | vendor bulk の長さつきのバイト列を report で運ぶ: report = `count(u16)`、その列の count バイト、埋め（report の大きさは HID の記述子のとおり）。規則は下 |

- **HID の report**: 向きごとに、report は 1 つのバイト列を運ぶ。
  1. report の OEP のバイトは、count の後ろの count バイトである。向きごとに report の順につなげると、1 つの長さつきのバイト列になる。
     vendor bulk と同じ列（`length(u16) message`）である。
  2. フレームは report をまたいでよく、1 つの report があるフレームの終わりと次のフレームの始まりを持ってよい。送る側はフレームごとに新しい report から始めてよい。
     受ける側はそれに頼らない。
  3. count が 0 の report は空で、読み飛ばす。
  4. 送る側は埋めを 0 にする。受ける側は、埋めをその値によらず無視する。
  5. OEP の HID の interface は、report ID を宣言しないか、その input の report と output の report が使う report ID を 1 つ宣言する。宣言するときは、
     両方向のすべての report がそれで始まり、count はその後ろから数える。受ける側は、別の ID で始まる report を捨てる。
  6. §2 の途切れの規則はこの列に掛かる: フレームが途中で、report が 200 ms（`probe_frame_gap_ms`）来ないとき、probe は
     途中のフレームを捨て、列の次のバイトを長さの始まりとして読む。host は §5 で立て直す。
  7. count が report に入る量（report の長さ − 2、report ID があれば − 3）より大きい report は捨て、受ける側は列が壊れたとして
     扱う: 200 ms 途切れるまで入力を捨てる。max_frame より大きい長さ（下）と同じ。
- **COBS のフレーム**: message の後ろに CRC-16/CCITT-FALSE（多項式 0x1021、初期値 0xFFFF、反転なし、"123456789" → 0x29B1）を
  little endian で付け、COBS（254 byte のブロックに分ける標準の形）で符号にし、**前後を 0x00 で囲んで送る**（`0x00 <COBS> 0x00`）。
  probe も host も前の 0x00 を省かない。最後のブロックが 254 byte の data を持つ（code 0xFF）とき、符号にする側は後ろに空のブロックを付けず、解く側は
  付いた形も付かない形も受ける。空のフレーム（0x00 の連続）は読み飛ばす。
- **host の受け方（COBS）**: 口を開いた直後から最初の 0x00 までと、0x00 から次の 0x00 までを、どちらもフレームの候補として解く
  （開く前に送られたバイトや、開いた直後に落ちたバイトで前の 0x00 が届かないことがある）。解けない候補、CRC の合わない候補、
  role か corr の合わないフレーム（core §11.1）は、シリアルの生のバイト（雑音）として捨てる。
- **USB の束ね方**（vendor bulk）: host は、書き込みの長さが wMaxPacketSize の倍数なら長さ 0 の転送を続ける。probe は、送り
  終えて後ろに続かないとき、最後の転送が wMaxPacketSize の倍数なら、長さ 0 の転送を送るか最後の 1 byte を別の転送に分ける。
  続きがすぐ来るときは倍数のままでよい。
- **max_frame より大きい長さ**: probe はそのフレームと、次に `probe_frame_gap_ms` 途切れるまでの入力を捨て、次のフレームを待つ。応答は送らない。TCP では代わりに接続を閉じる。HID では、これは列から読んだ長さに掛かる（report の count は上の規則 7）。
- どのフレームを使うかは経路の種類だけで決まる（VID:PID で選ばない）。
- **TCP は、信頼できるローカルの接続か、認証したトンネルの内側でだけ使う。** OEP は認証を持たない（core §6.4 の force を含む）。
  1 つの probe を複数の host で使うときは、ブローカーが 1 つのセッションに束ねる（probe の規則がブローカーに何を求めるかは次の項目）。
- **OEP の要求に自分で答える端点は probe である**。何が運び、後ろに何があるかによらない（たとえば TCP で OEP を出し、別のデバッガを動かすプログラム）。probe の規則はすべてそれに掛かる。要求を OEP の probe に中継するだけのブローカーは、その probe に対しては host である。
- **セッションの op に自分で答える中継のブローカー**で、ほかの要求をすべて 1 つの OEP の probe に中継するものは、自分の describe を持たない: それが中継する fn 0 の describe は probe のもの。自分で答えるセッションの op は confirm、open、end、keepalive、lock_state の 5 つだけである。fn 0 の clock（core §7.7）はそれに含まれない: ブローカーは clock をほかの要求と同じく probe に中継し、client はその応答を core §4.4 のとおりに待つ。confirm の transport TLV では index 0xFF（「describe に無い」）を返す。probe に対しては host である。それらのセッションの op の規則はすべて、その応答に掛かる。
- **中継のブローカーの probe への経路が無くなったとき**（USB で device が bus から外れた、TCP の接続が閉じた、ブローカーが probe への経路を閉じた）: ブローカーは終わる: client の接続をすべて閉じる。client は、経路が閉じたときと同じに、新しく開くのと同じやり方でやり直す。
- **TCP の経路**: TCP で待ち受ける probe は、待ち受けの socket 1 つを fn 0 の describe の経路 1 つとして並べる（kind 6、interface 0xFF）。その socket で受けた接続はどれも、confirm の transport TLV でその index を返す。§3、core §4.4、core §7.1、core §11.4 が経路ごとに掛ける規則（セッションの要求は 1 つの経路で、max_frame / window / max_inflight、使っている revision、通知の送り先）は、受けた接続ごとに別々に掛かる。
  probe が待ち受ける TCP の port と、host が TCP の probe を見つける方法は、この仕様の外である。

## 2. フレームの送り方

- host は **1 つのフレームを 1 回の書き込みで送り**、フレームの途中で `probe_frame_gap_ms` 止めない。
- シリアルの口、vendor bulk、HID では、フレームの途中で 200 ms（`probe_frame_gap_ms`）入力が途切れたら、probe は読み取りを最初からやり直す。**TCP ではやり直さない。** TCP は区切りを失わず、流れの壊れた TCP の接続は閉じる。

## 3. 複数の経路

- probe は OEP の制御を複数の経路で受けてよい。**複数の経路はセッションとロックを 1 つ共有する**。どの経路から来た要求も同じ
  ものとして扱い、応答はその要求の来た経路に返す。通知は subscribe が来た経路に送る（core §11.4）。
- **1 つのセッションの id を持つ要求は 1 つの経路で送る**（core §5.2 の順序の判定が経路の遅れで誤らないため）。session_id 0 の要求は
  別の経路から送ってよい。host が 1 つのセッションの要求を 2 つの経路から送ったときの誤判定は host の責任で、probe は確かめない。
- host は、同じ probe に複数の経路があれば vendor bulk、HID、シリアルの口の順に試す（シリアルの口は生のバイトの転送にも
  使われる、§4）。probe の経路の一覧は fn 0 の describe の transport（core §7.5）で分かる。
- **USB の OEP の probe の見分け方**: host が知らない device の中から OEP の probe を自動で見分けるのは、**プロジェクトの USB の
  VID:PID `1209:4F45` で列挙する device** だけである（VID 0x1209、PID 0x4F45。registry の `usb` の `project_vid` / `project_pid`）。ほかの値で
  OEP の probe を自動で見分けることはない。それ以外は、利用者が probe を名指すか口を選ぶ（次の 2 つの項目）。device の
  文字列 iProduct は表示のための自由な文字列で、host は見分けに使わない。interface の文字列も表示のためのもので、見分けには使わない。
- **名指した probe**: 利用者が probe を unit_id で名指したとき、host は、serial number
  がその unit_id と同じ USB の device を、見分けずに開いてよい。開いた後は下の探りの規則に従い、confirm の後に送る fn 0 の describe の
  unit_id が名指した値と同じときだけ、その device をその probe として使う。違えば host はその device を閉じ、ほかに何も送らない。ここでの比べ方（unit_id と
  serial number、unit_id どうし）は、英字の大文字と小文字を区別しない（serial number を大文字で見せる OS や道具があるため。unit_id
  は core §7.5 の文字だけなので、区別しなくても別の値が同じにはならない）。
- **ほかの device とシリアルの口**: 上の 2 つに当たらない USB の device とシリアルの口は、host が自分で扱い方を持つものか、利用者が
  明示して選んだものだけを開く。
- **探りの規則**: host が見分けずに開く device と口（名指した device、利用者の選んだ口、host が自分で扱う device）では、
  host が最初に送るのは confirm（core §7.1）だけである（core §5.2 の 1 回の送り直し、registry の `resend_max` を含む）。confirm の待ち時間
  （core §4.4。confirm には引数で決まる時間が無いので 1000 ms（`host_wait_add_ms`）と転送の時間）が過ぎても正しい confirm の応答が来なければ（送り直したときは、送り直した
  confirm の待ち時間が過ぎても来なければ）、host はその device か口を閉じ、ほかに何も送らない。ただし UART bridge（transport の
  kind 1）の口では、送り直しの代わりに §4 の「上げた速さの後」のとおり confirm を繰り返す（送るのは confirm だけで、その間に正しい応答が来なければ閉じる）。正しい confirm の応答とは、送った
  confirm と同じ corr の completed で、payload が core §7.1 の形（`OEP!` で始まる）のものをいう。正しい応答が来た device と口は OEP の
  probe として扱う。
- **口の選び方**: OEP の probe と分かった device（プロジェクトの VID:PID、名指した device、正しい confirm の応答が来た device）の中の
  口は、interface の記述子で選ぶ: CDC（ACM）はすべてシリアルの口（§4。どれも OEP を受ける）、**bInterfaceClass 0xFF、
  bInterfaceSubClass 0x4F ('O')、bInterfaceProtocol 0x45 ('E') の interface の bulk IN / OUT の組**は vendor bulk、**usage page 0xFF4F、
  usage 0x45 の HID** は HID（registry の `usb`）。probe は vendor bulk と HID をこの形で出し、それぞれ高々 1 つしか出さない。host は、
  この class / subclass / protocol と usage page / usage だけで device を OEP の probe とは決めない。ほかの class 0xFF の interface
  （内蔵の USB シリアルのデバッグの機能、WebUSB など）はこの subclass / protocol を持たないので掴まない。ほかの機能（DFU、Mass Storage など）は
  OEP の外。
- **USB の serial number は unit_id**（core §7.5）: probe が serial を選べる口（CDC、vendor bulk、HID を自分で出す device）では、serial number を
  unit_id そのものにする（core §7.5 の不変性）。host は開かずに個体を見分けられ（名指した probe を探せる）、どの経路の describe とも同じ値に
  なる。serial を選べない口（内蔵の USB シリアル、USB-UART の変換チップ）は、host が経路を外から指定し、describe で unit_id を確かめる。
- **max_frame は両方向の上限**: probe は max_frame を超える message を送らず、host は max_frame を超える message を送らない。
- **confirm の前**: どの probe も 64 byte（registry の `min_max_frame`）までの message を受ける（confirm の max_frame は 64 以上）。
  host は confirm の応答を受けるまで、64 byte を超える message を送らない。host は probe から長さ 65535 byte までの message を
  受けられるようにする。
- host は、OS が許すところでは、シリアルの口と HID を排他で開く（Linux では tty に TIOCEXCL）。
- HID を出す probe は、output の report を、interrupt OUT の endpoint でも SET_REPORT（Output）でも受ける。
- vendor bulk を出す probe は、できれば（SHOULD）その interface に Microsoft OS 2.0 の compatible ID `WINUSB` を付ける。

## 4. シリアルの口の共用

シリアルの口は、OEP のフレームと生のバイト（target のコンソールなど）を同じ口で運ぶ。probe はどの口でもいつでも OEP を受ける
（口を OEP 専用にする設定や、起動の型は持たない）。

- **UART bridge の回線**: データ 8 bit、パリティなし、ストップ 1 bit、フロー制御なし。起動時の速さは **115200 bps**（registry の `uart_bridge_boot_baud`）。port_speed（[リンク](../interfaces/oep-if-link.ja.md) §3）が変えるのは速さだけ。
- **上げた速さの後**: UART bridge の口を開く host は、port_speed を使うかどうかにかかわらず、起動時の速さで正しい confirm の応答が来なければ、
  あきらめる前にそこで `port_speed_idle_max_ms` + `host_wait_add_ms` の間 confirm を繰り返す（前の host が上げた速さは
  それまでに起動時の速さに戻る、[リンク](../interfaces/oep-if-link.ja.md) §3）。
- **USB のシリアルの口**（USB CDC、内蔵の USB シリアル）: probe は、host がどんな line coding を設定しても OEP を受けて送り、line coding を何にも掛けない。
- **制御線**: probe は、OEP を受けるか送るかを DTR、RTS、回線の状態で決めない。host は口を開いている間 DTR と RTS を立てておく（UART bridge はそれを probe のリセットにつないでいることがある）。
- **probe の受け方**: 0x00 が来たら次の 0x00 までためて解く。解けて CRC が合えば OEP の要求。解けない、CRC が合わない、または
  次の 0x00 の前に 200 ms 途切れた（§2）ときは、ためた分（前の 0x00 を含む）を生のバイトとして扱う。候補を閉じた 0x00 は
  次の候補の始まりになる。**0x00 だけで中身の無い候補**（フレームの閉じの 0x00 の後に何も来ないとき、0x00 の連続）は区切りで
  あり、200 ms 途切れても生のバイトにしない。0x00 の外で来たバイトはすぐ生のバイトとして扱う。
- **生のバイトの行き先**: probe がその口に結んだ流れ（どの流れを結ぶかは probe の設定が決める。結んでいなければ捨てる）。
  （参考）上の受け方により、0x00 の後に来た生のバイトは、次の 0x00 が来るか入力が 200 ms 途切れたときに初めて結んだ流れに届く。だから結んだ流れは
  文字の流れに向く。0x00 を含む二進の流れは、0x00 ごとに最長 200 ms 遅れる。
- **probe の送り方**: 応答と通知は `0x00 <COBS> 0x00`。1 つの口の送信は 1 つの書き手が行い、フレームの途中に生のバイトを挟ま
  ない（フレームは生のバイトより先に出してよく、生のバイトどうしの順は保つ）。
- **生の転送を止める口**: ロックを持つセッションの要求（その session_id を持つ要求。ロックを取った open も含む）が 1 つでも
  来た口では、そのセッションが終わる（end、lease の期限切れ、force で奪われる）まで、probe は生のバイトを送らず、口から来た
  生のバイトを捨てる。ロックの要らない要求だけが来た口と、ほかの経路でセッションが動いている口は止めない。
- host は、生のバイトの中に正しいフレームに見えるものが偶然現れても、role と corr の照合（core §11.1）で捨てる。
  （参考）この照合は、わざと作ったフレームは止めない。生の転送が止まっていない口では、target の出力が、CRC の合ったフレームで、
  未解決のロックなしの要求の corr を持つものを含みうる（corr は 1 ずつ進むので予測できる）。host はそれを応答として受ける。応答の中身を信じる必要のある host は、
  生の転送が止まった口（上のとおり、自分のセッションの要求が届いた後）か、長さつきのフレームの口で要求を送る。

## 5. 区切りの立て直し（長さつきのフレーム）

長さつきのフレーム（vendor bulk、HID、TCP）で、host は、corr の合わない応答、あり得ない長さ（max_frame を超える）、途中で
止まったフレーム（続きが 200 ms 来ない。TCP を除く: TCP ではフレームの途中の休みは普通のことで、host はそのフレームを読み続ける、§2）を見たら、入力が静かになるまで読み捨て、confirm を送って自分の corr の応答が返ることを
確かめてから再開する。通知が流れ続けて入力が静かにならないときは、
unsubscribe と end を確かめずに送ってよい（二度実行しても害がない）。COBS のフレームは CRC で壊れたものを捨てられるので、
この手順は要らない。

立て直しの confirm の前と、長さつきのフレームの口を開いて最初の confirm の前には、host は、その口に最後に書いてから `probe_frame_gap_ms` より長く待つ（probe が途中のフレームを捨てるまで）。TCP では、代わりに接続を閉じて新しく開いてもよい（長すぎる長さの後は、probe が閉じている、§1）。

## 6. host の待ちの転送の時間

host が応答を待つ時間（core §4.4）には、次の転送の時間を足す。転送の時間は UART bridge 以外では 0。UART bridge では (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud 秒で、L はその要求のフレームの線の上の長さ、baud は口の今の速さ。その経路で confirm の応答を受け取るまで、host は max_frame として `min_max_frame`（64）を使う。その後は、そこでのいちばん新しい confirm の応答の max_frame を使う。シリアルの口が UART bridge かどうか分からない host（たとえば fn 0 の describe で経路の種類を読む前、core §7.5）は、そのシリアルの口でこの転送の時間を数え、baud は自分がその口に設定した速さとする。

## 7. 参照する仕様

OEP のフレームと message は、この文だけで定まる。USB の経路を出す probe は、次にも従う:

| 仕様 | 使う部分 |
|---|---|
| Universal Serial Bus Specification, Revision 2.0 | 列挙、device と interface の記述子、serial number の文字列、bulk 転送と長さ 0 のパケット（§1、§3） |
| USB Class Definitions for Communications Devices 1.2 とその PSTN subclass（CDC ACM） | USB CDC のシリアルの口の CDC ACM の機能: その interface、line coding、制御線（§3、§4） |
| Device Class Definition for HID 1.11 | vendor 定義の input と output の report、report ID、SET_REPORT（§1、§3） |
| Microsoft OS 2.0 Descriptors Specification | vendor bulk の interface の compatible ID `WINUSB`（§3） |
