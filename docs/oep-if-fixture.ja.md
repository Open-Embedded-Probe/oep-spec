# OEP 標準インターフェース: fixture v1

状態: **規範**（2026-09-26）。本体は [OEP core](oep-core.ja.md)、共通部品は [共通部品](oep-if-common.ja.md)（§1 位置つきの
ストリーム）。番号の唯一の定義は `registry/oep-v1.toml`。キャプチャは [キャプチャ](oep-if-capture.ja.md)。

| 名前 | revision | 役割 | plan の role |
|---|---:|---|---|
| `oep.fixture.gpio` | 1 | ピンを駆動し、読む | 1 = 線 |
| `oep.fixture.uart` | 1 | UART の送受信 | 1 = RX、2 = TX |

どちらも plan（core §8）で割り当てたチャンネルだけを扱う。

## 1. `oep.fixture.gpio`

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | set | n(u8)、n × (channel(u16)、mode(u8)) | — | 必要 |
| 0x02 | read | n(u8)、n × channel(u16) | n × level(u8: 0 / 1) | 不要 |

| mode | 意味 |
|---:|---|
| 0 | 入力（浮き） |
| 1 | 入力、プルアップ |
| 2 | 入力、プルダウン |
| 3 | 出力 low |
| 4 | 出力 high |
| 5 | オープンドレイン low（引く） |
| 6 | オープンドレインの解放（外部または target のプルアップで high） |

- 並びは要求の順に 1 つずつ行う（NRST を引いてから離す、などを 1 要求で送れる）。
- 割り当てていないチャンネルや扱えない mode があれば、何もせず rejected unavailable（payload にその位置 u8）。
- plan を解いたら、そのチャンネルは入力に戻る。

## 2. `oep.fixture.uart`

ストリームは fn に 1 本。

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | configure | baud(u32)、[TLV] | baud(u32、実際の値) | 必要 |
| 0x02 | read | from(u8)、arg(u64)、max(u16) | start(u64)、flags(u8)、data | 不要 |
| 0x03 | marks | from_serial(u32) | more(u8)、count(u8)、count × mark | 不要 |
| 0x04 | clear | — | — | 必要 |
| 0x05 | mark | value(u8) | — | 必要 |
| 0x06 | write | count(u16)、data | accepted(u16) | 必要 |

- op 0x02〜0x06 は [共通部品](oep-if-common.ja.md) §1 の形（stream の byte なし）で、`oep.target.console` と同じ番号。
- configure の TLV 0x01 format（u8）: bit0-1 データ長（0 = 8、1 = 7）、bit2-3 パリティ（0 なし、1 偶数、2 奇数）、bit4 ストップ
  ビット（0 = 1、1 = 2）。無ければ 8N1。
- 受信は configure から plan を解くまで、セッションに関係なく貯める。configure をやり直しても貯めた分と位置はそのまま
  （境目が要るなら host が mark を付ける）。
- **TX の線は、configure の前と plan を解いた後も UART の休止（high）に保つ**（相手の受信が雑音を拾わないため。core §8 の「解放 = 入力」の例外）。
- revision 1 は通知を送らない（subscribe は rejected unavailable）。後から足すときは、データの payload を共通部品 §1.5 の形にする。
