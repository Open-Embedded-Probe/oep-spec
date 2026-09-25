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
| 0x01 | open | connection(u8)、mechanism(u8)、[TLV] | stream(u8)、flags(u8: bit0 既存のストリーム) | 必要 |
| 0x02 | read | stream(u8)、from(u8)、arg(u64)、max(u16) | start(u64)、flags(u8)、data | 不要 |
| 0x03 | marks | stream(u8)、from_serial(u32) | more(u8)、count(u8)、count × mark | 不要 |
| 0x04 | clear | stream(u8) | — | 必要 |
| 0x05 | mark | stream(u8)、value(u8) | — | 必要 |
| 0x06 | write | stream(u8)、count(u16)、data | accepted(u16) | 必要 |
| 0x07 | close | stream(u8) | — | 必要 |

- read、marks、clear、mark、write は [共通部品](oep-if-common.ja.md) §1 の形（先頭に stream）。
- mechanism: 0 SDI、1 DMDATA、2 dmseq（framing は [target-console-dmseq](target-console-dmseq.ja.md)）。知らない mechanism は
  rejected unsupported（payload なし）。
- 知らない stream は rejected unavailable。
- ストリームの番号は core §9 の規則で振る（新しいストリームのたびに 1〜255 を進める）。
- revision 1 は通知を送らない（subscribe は rejected unavailable）。後から足すときは、データの payload を共通部品 §1.5 の形にする。

## 2. ストリームの規則

- **同じ (connection, mechanism) のストリームがあれば、open はそれを返す**（flags bit0。位置もマークもそのまま）。
  1 コマンド 1 プロセスの host が、続きから読めるようにするため。
- probe は、ストリームを開いている間、セッションと関係なく target の出力を吸い出して貯める（dmseq は読み続けないと target が
  送信で詰まる）。
- probe がコンソールの読みを止めるのは、**その connection の riscv-dm の要求を実行している間と、hart が止まっている間**
  だけ。抽象コマンドと DATA0 を取り合わないよう、host は抽象コマンドの一連を 1 つの dmi 要求に入れる
  （[線とデバッグ](oep-if-debug.ja.md) §4.1）。
- ストリームを開いた connection が失われたら、マーク link-lost を付けて閉じる。**閉じたストリームも、同じ mechanism で次に
  open されるまで読める**（read / marks。write / mark / clear は rejected unavailable）。線が落ちる直前の出力を回収するため。
- ストリームが使う connection は、そのストリームを開いたセッション（または bind）が使っているものとして数える。
- write は、方式が 1 回に運べる分だけを受け付ける（dmseq は 2 byte まで）。残りは host が送り直す。
