# OEP 標準インターフェース: コンソール v1

状態: **規範**（2026-09-26）。本体は [OEP core](oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
ストリーム、§2 debug の connection）。番号の唯一の定義は `registry/oep-v1.toml`。考え方と理由は
[コンソールのストリーム](console-stream.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.target.console` | 1 | target のコンソール（debug の connection の上のストリーム） |

UART の素通しは `oep.fixture.uart`（[fixture](oep-if-fixture.ja.md)）で、同じストリームの形を使う。

## 1. 操作

ストリームは debug の connection の上に方式（mechanism）を指定して開く。fn はインターフェースに 1 つで、ストリームは番号で指す。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | open | connection(u16)、mechanism(u8)、[TLV] | stream(u16)、flags(u8: bit0 既存のストリーム) | 必要 |
| 0x02 | read | stream(u16)、from(u8)、arg(u64)、max(u16) | start(u64)、flags(u8)、data | 不要 |
| 0x03 | marks | stream(u16)、from_serial(u32) | more(u8)、count(u8)、count × mark | 不要 |
| 0x04 | clear | stream(u16) | — | 必要 |
| 0x05 | mark | stream(u16)、value(u8) | — | 必要 |
| 0x06 | write | stream(u16)、count(u16)、data | accepted(u16) | 必要 |
| 0x07 | close | stream(u16) | — | 必要 |

- read、marks、clear、mark、write は [共通部品](oep-if-common.ja.md) §1 の形（先頭に stream）。
- mechanism: 0 SDI、1 DMDATA、2 dmseq（framing は [target-console-dmseq](target-console-dmseq.ja.md)）。知らない mechanism と、
  describe の mechanisms に無い mechanism は rejected unsupported（payload なし）。
- describe: tag 0x40 mechanisms（u8 の並び。その probe が開ける mechanism）。必ず出す。
- 知らない stream は rejected unavailable。
- ストリームの番号（u16）は core §9 の規則で振る（新しいストリームのたびに 1 から進め、同じ boot_id の間は再利用しない）。
- revision 1 は通知を送らない（subscribe は rejected unavailable）。後から足すときは、データの payload を共通部品 §1.5 の形にする。

## 2. ストリームの規則

- **同じ (connection, mechanism) のストリームがあれば、open はそれを返す**（flags bit0。位置もマークもそのまま）。
  1 コマンド 1 プロセスの host が、続きから読めるようにするため。
- probe は、ストリームを開いている間、セッションと関係なく target の出力を吸い出して貯める（dmseq は読み続けないと target が
  送信で詰まる）。
- probe がコンソールの読みを止めるのは、**その connection の riscv-dm の要求を実行している間と、hart が止まっている間**
  だけ。抽象コマンドと DATA0 を取り合わないよう、host は抽象コマンドの一連を 1 つの dmi 要求に入れる
  （[線とデバッグ](oep-if-debug.ja.md) §4.1）。「hart が止まっている」は probe が DMSTATUS で見る: host が dmi の要求の中で hart を止めても走らせても
  （debugger が dmcontrol の haltreq / resumereq を自分で書いても）、hart が走っていれば probe は読みを続ける（戻す）。
  host は、コンソールのために riscv-dm の resume の op を使う必要はない。
- ストリームを開いた connection が失われたら、マーク link-lost を付けて閉じる。**閉じたストリームも、同じ接続の場所（同じ wire の
  同じピンの組）で同じ mechanism が次に open されるまで読める**（read / marks。write / mark / clear は rejected unavailable）。線が
  落ちる直前の出力を回収するため。別の場所の open では消えない。
- ストリームが使う connection は、そのストリームを開いたセッション（または `oep.probe.config` のスロット）が使っているものとして数える。
- write は、方式が 1 回に運べる分だけを受け付ける（dmseq は 2 byte まで）。残りは host が送り直す。

## 3. 方式（mechanism）

どれも debug module の DATA0（DMI 0x04）と DATA1（0x05）を郵便受けに使う。hart は止めない。probe は DATA0 を読んで、方式の
規則で受け取る。

| mechanism | 名前 | 向き | 定義 |
|---:|---|---|---|
| 0 | SDI | target → host | 下の 3.1 |
| 1 | DMDATA | 両方向 | 下の 3.2 |
| 2 | dmseq | 両方向 | [target-console-dmseq](target-console-dmseq.ja.md)（通番と CRC つき） |

### 3.1 SDI（WCH の SDI printf）

- target は DATA0 が 0 になるのを待ち、DATA1 = バイト 3〜6、DATA0 = 長さ（1〜7）| バイト 0〜2 << 8 を書く（little endian、
  DATA0 を最後に書く）。
- probe は DATA0 の下位 byte が 1〜7 なら、DATA1 も読んで、長さの分のバイトを受け取り、DATA0 に 0 を書く（受け取った印）。
  下位 byte が 0 は何も無い。8 以上は枠ではない（読み捨てない）。
- host → target の向きは無い（write は何も受け付けない: accepted 0、completed failed）。

### 3.2 DMDATA（minichlink の framing）

- DATA0 の下位 byte が状態の byte。bit 7 = 1 は target の枠、下位 6 bit は長さ + 4。
- target の枠（bit 7 = 1）で長さ + 4 が 5 以上なら、DATA1 も読んで長さ（1〜7）の分を受け取る（並びは SDI と同じ）。4 は target の
  空の枠（「郵便受けは host の番」）。
- probe は target の枠 1 つにちょうど 1 回答える: 送るバイトがあれば DATA0 = (n + 4) | バイト 0〜2 << 8（n は 1〜3、bit 7 = 0）、
  無ければ DATA0 = 0。bit 7 が 0 の word（host の枠がまだ取られていない、または答えたばかり）には書かない。
- 空の枠は、次の読みでもそのままのときだけ答える（target が空の枠を置いた直後に本当の枠を重ねることがあり、すぐ答えると
  その枠を消す）。
