# OEP 標準インターフェース: コンソール v1

[English](oep-if-console.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
ストリーム、§2 debug の connection）。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.target.console` | 1 | target のコンソール（debug の connection の上のストリーム） |

UART の素通しは `oep.fixture.uart`（[fixture](oep-if-fixture.ja.md)）で、同じストリームの形を使う。

## 1. 操作

ストリームは debug の connection の上に方式（mechanism）を指定して開く。fn はインターフェースに 1 つで、ストリームは番号で指す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | open | connection(u16)、mechanism(u8)、[TLV] | stream(u16)、flags(u8: bit0 既存のストリーム)、[TLV] | 必要 |
| 0x02 | read | stream(u16)、from(u8)、arg(u64)、max(u16)、[TLV] | start(u64)、flags(u8)、len(u16)、data、[TLV] | 不要 |
| 0x03 | marks | stream(u16)、from_serial(u32) | more(u8)、count(u8)、count × mark、[TLV] | 不要 |
| 0x04 | clear | stream(u16) | — | 必要 |
| 0x05 | mark | stream(u16)、value(u8) | — | 必要 |
| 0x06 | write | stream(u16)、count(u16)、data | accepted(u16)、[TLV] | 必要 |
| 0x07 | close | stream(u16) | — | 必要 |
| 0x08 | streams | first(u8) | more(u8)、count(u8)、count × (stream(u16)、connection(u16)、mechanism(u8)、users(u8)、state(u8))、[TLV] | 不要 |

この表の op はすべて必須（core §1.2）。方式は describe の mechanisms で宣言する。

- read、marks、clear、mark、write は [共通部品](oep-if-common.ja.md) §1 の形（先頭に stream）。
- mechanism: 0 SDI、1 DMDATA、2 dmseq（framing は [target-console-dmseq](target-console-dmseq.ja.md)）。**mechanism の番号が方式を
  正確に決める**（版を持たない）。方式を変えるときは新しい番号（3 以降、registry に足す）にし、古い番号の意味は変えない。知らない mechanism と、
  describe の mechanisms に無い mechanism は rejected unsupported（payload `0x00`、core §4.3）。
- describe: tag 0x40 mechanisms（u8 の並び。その probe が開ける mechanism）。必ず出す。
- describe: tag 0x41 send_queue（u16、byte）。ストリームごとの送りの列（§2）の大きさで、64 以上（registry の `console_send_queue_min_bytes`）。
  mechanisms に 1 か 2（host → target を運ぶ mechanism）があれば必ず出す。どちらも無ければ出さない。
- 知らない stream は rejected no_connection（core §4.3）。別の種類の資源の番号（connection の番号を stream に）は rejected unavailable
  cause 6。arm-adi（swd）の connection への open も rejected unavailable cause 6（[線とデバッグ](oep-if-debug.ja.md) §5）。
- ストリームの番号（u16）は core §9 の規則で振る（probe で 1 つの空間、1 から進めて一周する。同じ場所の再 open は番号を消費しない、§2）。
- **streams** は生きているストリームと、閉じたがまだ読めるストリームの一覧（`stream_state`: 0 open、1 closed）。作られた順に first 番目から
  1 フレームに入る分を返し、more = 1 なら続きがある（connections と同じ形）。users は bit0 host の
  セッション、bit1 スロット（bind）。ロック無しの host（監視）が番号を得るための op。
- 閉じたストリームへの close は何もせず成功。
- revision 1 は通知を送らない（subscribe は rejected unsupported）。後から足すときは、データの payload を core §11.2 の形にする。

## 2. ストリームの規則

- **同じ (connection, mechanism) のストリームがあれば、open はそれを返す**（flags bit0。位置もマークもそのまま）。
  1 コマンド 1 プロセスの host が、続きから読めるようにするため。閉じたストリームの場所（同じ wire の同じピンの組）で同じ mechanism を
  open したときも、**同じ番号で再び開く**（位置とマークは続き、mark attach、flags bit0）。別の mechanism の open で古い方は消える。
- **各 mechanism が定めるもの**: open できる connection の種類、使う target の資源、1 つの connection にほかの mechanism と合わせて生きている
  ストリームをいくつ持てるか、probe が読みを止めるとき、target の状態を確かめる頻度（mechanism 0〜2 は §3）。
- **ストリームの寿命は connection と同じ数え方**（[共通部品](oep-if-common.ja.md) §2）: 使っているものは、open したセッションと、
  bind で開いたスロット。close と、セッションのロックの終わり（end、lease の期限切れ、force）は自分の分を外すだけで、全員が外れたら
  閉じる（mark closed、close の後は detail 1、セッションが終わったときは 2）。セッションが終わるとき、probe はそのストリームの分を connection
  の分より先に外す。そのため、最後に使っていたのがそのセッションだったストリームは、connection も閉じるときでも detail 2 で閉じる。
  スロットの項目の置き換え・削除で外れたときは detail 3、connection が閉じたときは 4。
- **コンソールのストリームはセッションのものではなく、場所と mechanism ごとの probe のもの**（core §9）。セッションの終わりはその分を外すが、
  閉じたストリームは、同じ場所で同じ mechanism が次に open されるまで読め、その open は古い番号を位置とマークごと返す（下）。そのため
  1 コマンド 1 プロセスの host も最初の行を失わない: あるコマンドがコンソールを開き、target をリセットして終わる。ストリームは閉じるが、
  読んだものは保つ。次のコマンドの同じ場所と mechanism での open がそれを返し、リセットのマークから読む。
- probe は、ストリームを開いている間、セッションと関係なく target の出力を吸い出して貯める（dmseq は読み続けないと target が
  送信で詰まる）。
- ストリームを開いた connection が失われたら、マーク link-lost（コンソールの読みの中で線切れを判定したとき）か closed（4）を付けて
  閉じる。target の自己リセット（havereset）を見たら mark restart（1）を付け、dmseq は未同期に戻す。**閉じたストリームも、同じ接続の場所（同じ wire の
  同じピンの組）で同じ mechanism が次に open されるまで読める**（read / marks。write / mark / clear は rejected unavailable）。線が
  落ちる直前の出力を回収するため。別の場所の open では消えない。
- ストリームが使う connection は、そのストリームを開いたセッション（または `oep.probe.config` のスロット）が使っているものとして数える。
- **送りの列**: probe は、host → target を運ぶ mechanism（1、2）のストリームごとに、describe の send_queue の大きさの送りの列を持つ。
  write は data を先頭から、列の空きに入る分だけ列の終わりに入れる。**accepted は列に入れたバイトの数**（count と列の空きの小さい方）で、
  target が受け取ったことは意味しない。accepted 0（completed failed）は、列が満ちているときだけ（mechanism 0 は §3.1）。
  0 < accepted < count は completed partial。残り（data の accepted 番目から）は host が後で送る（列は probe が target に渡した分だけ空く）
  （[共通部品](oep-if-common.ja.md) §1.4）。
- probe は列の先頭から、mechanism の運び方で target に渡す: dmseq は 1 つのフレームへの答えに 2 byte まで
  （[dmseq](target-console-dmseq.ja.md) の host の規則 5）、DMDATA は 1 つの枠への答えに 3 byte まで（§3.2）。どちらも、列にある分が
  それより少なければその全部を載せる。答えに載せたバイトは列から出る。列のバイトの順は write で受け取った順のままである。
- 列は、ストリームが閉じたときに捨てる（閉じたストリームへの write は rejected unavailable）。clear は読みのバッファだけを捨て、列には触れない。
- （参考）列を持つのは、1 回の write が 2〜3 byte しか受け付けないと、1 行のコマンドに 2〜3 byte ごとの要求が要るため。1 つの要求の往復が
  長い経路（UART の変換器を通る口）ではコマンドが遅くなり、コマンドの前に用意したキャプチャの窓にもコマンドが間に合わない。

## 3. 方式（mechanism）

mechanism 0、1、2 は debug module の DATA0（DMI 0x04）と DATA1（0x05）を郵便受けに使う。hart は止めない。probe は DATA0 を読んで、方式の
規則で受け取る。

- **mechanism 0〜2 の中では、1 つの connection に生きているストリームは 1 つ。** そのうちの別のものの open は rejected unavailable（cause 6）。
  arm-adi の connection では開かない（rejected unavailable cause 6）。
- probe がコンソールの読みを止めるのは、**その connection の riscv-dm の要求を実行している間と、hart が止まっている間**
  だけ（ほかの connection の長い要求の間も、この connection の読みは続ける。core §7.5 max_op_ms）。抽象コマンドと DATA0 を取り合わないよう、host は抽象コマンドの一連を 1 つの dmi 要求に入れる
  （[線とデバッグ](oep-if-debug.ja.md) §4.1）。「hart が止まっている」は probe が DMSTATUS で見る: host が dmi の要求の中で hart を止めても走らせても
  （debugger が dmcontrol の haltreq / resumereq を自分で書いても）、hart が走っていれば probe は読みを続ける（戻す）。probe が
  DMSTATUS を見る間隔は 20 ms 以下（registry の `console_dmstatus_poll_ms`。host が raw で止めたあと、probe が DATA0 を読みうるのはその間だけ）。
  host は、コンソールのために riscv-dm の resume の op を使う必要はない。

| mechanism | 名前 | 向き | 定義 |
|---:|---|---|---|
| 0 | SDI | target → host | 下の 3.1 |
| 1 | DMDATA | 両方向 | 下の 3.2 |
| 2 | dmseq | 両方向 | [target-console-dmseq](target-console-dmseq.ja.md)（通番と CRC つき） |

### 3.1 SDI

mechanism 0 はこの郵便受けの並びだけで、connection の線には依らない。target から host へバイトを運ぶ。

- **郵便受けの中のバイト**: バイト 0 は DATA0 の bit 8〜15、バイト 1 は bit 16〜23、バイト 2 は bit 24〜31。バイト 3 は DATA1 の bit 0〜7、バイト 4
  は bit 8〜15、バイト 5 は bit 16〜23、バイト 6 は bit 24〜31。DATA0 の下位 byte（bit 0〜7）は長さ L。
- **target** は 1 回に n バイト（n = 1〜7）を送る: DATA0 を読んで 0 になるまで待ち、DATA1（バイト 3〜6）を書き、次に DATA0 = n | バイト 0〜2 << 8 を書く
  （DATA0 を最後に）。位置が n 以上のバイトの値は何でもよい。target がどれだけ待つか、あきらめたバイトをどうするかは、target が
  決める。
- **probe** は DATA0 を読む。L が 1〜7 なら DATA1 も読み、バイト 0〜L − 1 をその順に受け取り、次に DATA0 に 0 を書く（受け取った印）。
  L が 0 なら何も無い。L が 8 以上なら、その word は枠ではない: probe は受け取らず、DATA0 も書かない（読み捨てない）。
- host → target の向きは無い（送りの列を持たず、write は何も受け付けない: accepted 0、completed failed）。

### 3.2 DMDATA

mechanism 1 はこの郵便受けの並びだけで、connection の線には依らない。両方向にバイトを運び、両側は DATA0 を交代で
使う。

- **状態の byte** は DATA0 の下位 byte（bit 0〜7）。bit 7 は T: 1 = **target の枠**（target が書いた）、0 = probe が書いた、または開始時の
  0。bit 0〜5 は L = バイトの数 + 4。bit 6 は 0 を書き、読む側は無視する。
- **郵便受けの中のバイト**: SDI（§3.1）と同じ位置: バイト 0〜2 は DATA0 の bit 8〜31、バイト 3〜6 は DATA1。
- **target** は DATA0 の bit 7 が 0 のときだけ DATA0 を書く。自分の枠は、空の枠も、probe が答えるまで書き換えない。
  - n バイト（n = 1〜7）を送るときは、DATA0 の bit 7 が 0 になるまで待ち、その word の答え（下）を受け取り、n が 4 以上なら DATA1（バイト 3〜6）を
    書き、次に DATA0 = 0x80 | (n + 4) | バイト 0〜2 << 8 を書く（DATA0 を最後に）。位置が n 以上のバイトの値は何でもよい。
  - 送らずに入力を求めるときは、DATA0 の bit 7 が 0 になるまで待ち、その word の答えを受け取り、次に DATA0 = 0x84 を書く（**空の枠**、
    L = 4: 「郵便受けは probe の番」）。そのあとは、ほかの枠と同じく probe の答え（DATA0 の bit 7 が 0 になる）を待つ。
  - **答えの受け取り**: bit 7 = 0 で L が 5〜7 の word は、target へのバイトを L − 4 個運ぶ（バイト 0〜L − 5）。0 の word と、bit 7 = 0 のほかの
    word は何も運ばない。
  - target がどれだけ待つか、あきらめたバイトをどうするかは、target が決める。
- **probe** は DATA0 を読む。
  - bit 7 が 0 なら何もしない: その word は、target がまだ置き換えていない自分の答えか、0。probe は bit 7 = 0 の word の上に書かない。
  - bit 7 が 1 で L が 5〜11 なら、n = L − 4 バイトを受け取る: バイト 0〜2（n の分まで）はその word から、n が 4 以上ならバイト 3〜n − 1
    は DATA1 から（DATA1 は DATA0 の後に読む）。それから答える。
  - bit 7 が 1 で L が 4 なら、枠は空（バイトを運ばない）。probe はそれに答える。
  - bit 7 が 1 で L が 0〜3 か 12〜63 なら、その word は target の枠ではなく、バイトを運ばない（多くは probe やほかの debugger が
    残した値。たとえば 0xffffffff）。probe は DATA0 に 0 を書いて消し、その上に入力を載せない（送りの列のバイトは出さない）。
  - **答え**: target の枠 1 つにつき DATA0 をちょうど 1 回書く。送りの列（§2）にバイトがあれば、n = 列のバイトの数と 3 の小さい方として、
    DATA0 = (n + 4) | バイト 0〜n − 1 << 8（バイト 0〜n − 1 は列の先頭の n バイト。bit 7 = 0。位置が n 以上のバイトは 0）で、その n バイトは
    列から出る。列が空なら DATA0 = 0。probe は DATA1 を書かない。

## 4. 参照する仕様

この文書の OEP のメッセージは、本文だけで定まる。target を動かすのに使うもの:

| 仕様 | 使う部分 |
|---|---|
| RISC-V Debug Specification 0.13.2 と 1.0（DMSTATUS.version 2 と 3） | debug module の DATA0（DMI 0x04）、DATA1（DMI 0x05）、DMSTATUS（allhalted、allrunning、havereset）と、DATA0 と DATA1 も使う抽象コマンド |
