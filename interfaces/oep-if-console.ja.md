# OEP インターフェース: コンソール v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
ストリーム、§2 debug の connection）。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.target.console` | 1 | target のコンソール（debug の connection の上のストリーム） | どの系統にも使う（方式ごとに、その方式を持つ target） |

UART の素通しは `oep.fixture.uart`（[fixture](oep-if-fixture.ja.md)）で、同じストリームの形を使う。

## 1. 操作

ストリームは debug の connection の上に方式（mechanism）を指定して開く。fn はインターフェースに 1 つで、ストリームは番号で指す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x10 | open | connection(u16)、mechanism(u8)、[TLV] | stream(u16)、flags(u8: 0、未割当)、[TLV] | 必要 |
| 0x11 | read | stream(u16)、from(u8)、arg(u64)、max(u16)、[TLV] | start(u64)、flags(u8)、len(u16)、data、[TLV] | 不要 |
| 0x12 | marks | stream(u16)、from_serial(u32) | more(u8)、count(u8)、count × mark、[TLV] | 不要 |
| 0x13 | clear | stream(u16) | — | 必要 |
| 0x14 | mark | stream(u16)、value(u8) | — | 必要 |
| 0x15 | write | stream(u16)、count(u16)、data | accepted(u16)、[TLV] | 必要 |
| 0x16 | close | stream(u16) | — | 必要 |
| 0x17 | streams | first(u16) | more(u8)、count(u8)、count × (stream(u16)、connection(u16)、mechanism(u8))、[TLV] | 不要 |

この表の op はすべて必須（core §1.2）。方式は describe の mechanisms で宣言する。

- read、marks、clear、mark、write は [共通部品](oep-if-common.ja.md) §1 の形（先頭に stream）。
- mechanism: 0 SDI、1 DMDATA、2 dmseq（framing は [target-console-dmseq](target-console-dmseq.ja.md)）。**mechanism の番号が方式を
  正確に決める**（版を持たない）。知らない mechanism と、
  describe の mechanisms に無い mechanism は rejected unsupported（payload `0x00`、core §4.3）。
- describe: tag 0x40 mechanisms（u8 の並び。その probe が開ける mechanism）。必ず出す。
- 知らない stream は rejected no_resource（core §4.3）。別の種類の資源の番号（connection の番号を stream に）は rejected unavailable
  cause 6。arm-adi（swd）の connection への open も rejected unavailable cause 6（[線とデバッグ](oep-if-debug.ja.md) §5）。
- ストリームの番号（u16）は core §9 に従い、同じ boot_id の間は再利用しない。
- streams は生きているストリームだけを作成順に返す。first は u16。閉じた stream への要求は no_resource。

## 2. ストリームの規則

- open はセッション所有の新しい stream を作る。同じ connection に使用中の mechanism があれば unavailable（cause 6）。
  閉じた stream の番号、バッファ、位置やマークを再び使わない。
- close、connection の解放、セッションの終了で stream とそのバッファ・送信列を解放する。
  失う前に必要な出力を host が read で読み、ログへ保存する。
- stream が生きている間、probe は target の出力を吸い出してバッファへ貯める。
- target の自己リセットを検出したら restart mark を付け、dmseq を未同期へ戻す。

- **送りの列**: probe は、host → target を運ぶ mechanism（1、2）のストリームごとに、送りの列を持つ（大きさは probe が決める）。
  write は data を先頭から、列の空きに入る分だけ列の終わりに入れる。**accepted は列に入れたバイトの数**（count と列の空きの小さい方）で、
  target が受け取ったことは意味しない。accepted 0（completed failed）は、列が満ちているときだけ（mechanism 0 は §3.1）。
  0 < accepted < count は completed partial。残り（data の accepted 番目から）は host が後で送る（列は probe が target に渡した分だけ空く）
  （[共通部品](oep-if-common.ja.md) §1.4）。
- probe は列の先頭から、mechanism の運び方で target に渡す: dmseq は 1 つのフレームへの答えに 2 byte まで
  （[dmseq](target-console-dmseq.ja.md) の host の規則 5）、DMDATA は 1 つの枠への答えに 3 byte まで（§3.2）。どちらも、列にある分が
  それより少なければその全部を載せる。答えに載せたバイトは列から出る。列のバイトの順は write で受け取った順のままである。
- 列は、ストリームが閉じたときに捨てる（閉じたストリームへの write は rejected no_resource）。clear は読みのバッファだけを捨て、列には触れない。

## 3. 方式（mechanism）

mechanism 0、1、2 は debug module の DATA0（DMI 0x04）と DATA1（0x05）を郵便受けに使う。hart は止めない。probe は DATA0 を読んで、方式の
規則で受け取る。

- **mechanism 0〜2 の中では、1 つの connection に生きているストリームは 1 つ。** そのうちの別のものの open は rejected unavailable（cause 6）。
- probe は、**その connection の riscv-dm の要求を実行している間と、hart が止まっている間**（DMSTATUS の anyhalted が 1）は、コンソールのために
  DATA0 / DATA1 を読み書きしない。probe は、その connection の riscv-dm の要求に答えた後、次にコンソールのために DATA0 を読む前に DMSTATUS を読む。
  hart がまた走れば、probe は読みを再開する。抽象コマンドの一連の扱いは [線とデバッグ](oep-if-debug.ja.md) §4.1。

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
  （DATA0 を最後に）。位置が n 以上のバイトの値は何でもよい。
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
