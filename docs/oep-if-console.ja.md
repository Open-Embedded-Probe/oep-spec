# OEP 標準インターフェース: コンソール v1

[English](oep-if-console.md)

状態: **規範**（2026-09-26。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md)を反映）。本体は [OEP core](oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
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
| 0x01 | open | connection(u16)、mechanism(u8)、[TLV] | stream(u16)、flags(u8: bit0 既存のストリーム)、[TLV] | 必要 |
| 0x02 | read | stream(u16)、from(u8)、arg(u64)、max(u16)、[TLV] | start(u64)、flags(u8)、len(u16)、data、[TLV] | 不要 |
| 0x03 | marks | stream(u16)、from_serial(u32) | more(u8)、count(u8)、count × (len(u8)、mark)、[TLV] | 不要 |
| 0x04 | clear | stream(u16) | — | 必要 |
| 0x05 | mark | stream(u16)、value(u8) | — | 必要 |
| 0x06 | write | stream(u16)、count(u16)、data | accepted(u16)、[TLV] | 必要 |
| 0x07 | close | stream(u16) | — | 必要 |
| 0x08 | streams | first(u8) | more(u8)、count(u8)、count × (len(u8)、stream(u16)、connection(u16)、mechanism(u8)、users(u8)、state(u8))、[TLV] | 不要 |

- read、marks、clear、mark、write は [共通部品](oep-if-common.ja.md) §1 の形（先頭に stream）。
- mechanism: 0 SDI、1 DMDATA、2 dmseq（framing は [target-console-dmseq](target-console-dmseq.ja.md)）。**mechanism の番号が方式を
  正確に決める**（版を持たない）。方式を変えるときは新しい番号（3 以降、registry に足す）にし、古い番号の意味は変えない。知らない mechanism と、
  describe の mechanisms に無い mechanism は rejected unsupported（payload `0x00`、core §4.3）。
- describe: tag 0x40 mechanisms（u8 の並び。その probe が開ける mechanism）。必ず出す。
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
- **1 つの connection に生きているストリームは 1 つ**（3 方式とも DATA0 を郵便受けにする）。別の mechanism の open は rejected
  unavailable（cause 6）。
- **ストリームの寿命は connection と同じ数え方**（[共通部品](oep-if-common.ja.md) §2）: 使っているものは、open したセッションと、
  bind で開いたスロット。close と lease の期限切れ・force は自分の分を外すだけで、全員が外れたら閉じる（mark closed、detail 1 / 2）。
  スロットの項目の置き換え・削除で外れたときは detail 3、connection が閉じたときは 4。
- probe は、ストリームを開いている間、セッションと関係なく target の出力を吸い出して貯める（dmseq は読み続けないと target が
  送信で詰まる）。
- probe がコンソールの読みを止めるのは、**その connection の riscv-dm の要求を実行している間と、hart が止まっている間**
  だけ（ほかの connection の長い要求の間も、この connection の読みは続ける。core §7.5 max_op_ms）。抽象コマンドと DATA0 を取り合わないよう、host は抽象コマンドの一連を 1 つの dmi 要求に入れる
  （[線とデバッグ](oep-if-debug.ja.md) §4.1）。「hart が止まっている」は probe が DMSTATUS で見る: host が dmi の要求の中で hart を止めても走らせても
  （debugger が dmcontrol の haltreq / resumereq を自分で書いても）、hart が走っていれば probe は読みを続ける（戻す）。probe が
  DMSTATUS を見る間隔は 20 ms 以下（host が raw で止めたあと、probe が DATA0 を読みうるのはその間だけ）。
  host は、コンソールのために riscv-dm の resume の op を使う必要はない。
- ストリームを開いた connection が失われたら、マーク link-lost（コンソールの読みの中で線切れを判定したとき）か closed（4）を付けて
  閉じる。target の自己リセット（havereset）を見たら mark restart（1）を付け、dmseq は未同期に戻す。**閉じたストリームも、同じ接続の場所（同じ wire の
  同じピンの組）で同じ mechanism が次に open されるまで読める**（read / marks。write / mark / clear は rejected unavailable）。線が
  落ちる直前の出力を回収するため。別の場所の open では消えない。
- ストリームが使う connection は、そのストリームを開いたセッション（または `oep.probe.config` のスロット）が使っているものとして数える。
- write は、方式が 1 回に運べる分（送り枠、dmseq は 2 byte、DMDATA は 3 byte）だけを受け付ける。**accepted は送り枠に入れた分で、
  target が受け取ったことは意味しない**。枠が空いていなければ accepted 0（completed failed）。残りは host が、読みの進みを見て送り直す
  （[共通部品](oep-if-common.ja.md) §1.4）。

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
