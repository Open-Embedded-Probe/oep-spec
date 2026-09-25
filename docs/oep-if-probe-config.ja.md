# OEP 標準インターフェース: probe の設定 v1

状態: **規範**（2026-09-26）。本体は [OEP core](oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。経緯と実験は
[シリアルの口と永続化](probe-cdc-and-persistence.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.probe.config` | 1 | probe の設定（起動モード、plan、ラベル、CDC の口に流すもの）と、その保存 |

- **既定の値は持たない。** 項目はすべて host が設定し、probe は設定されたとおりに動く。設定されていない項目については何もしない。
- 設定を扱わない probe は、このインターフェースを list に出さない。
- 設定から入れた plan と bind はセッションの資源ではない（core §9）。lease の期限切れでも外さない。

## 1. 項目

**設定 = 項目（TLV）の並び**。tag はこの文脈の空間。同じ tag を複数置く項目（label、bind）がある。

| tag | 項目 | 値 | いつ効くか |
|---:|---|---|---|
| 0x01 | boot_mode | mode(u8)（describe の mode の番号） | 次の起動から |
| 0x02 | plan | n × (fn(u16)、role(u8)、channel(u16)) | すぐ（plan_release + plan_apply と同じ） |
| 0x03 | label | channel(u16)、text | すぐ（core の describe の label 0x46 に出る） |
| 0x04 | bind | port(u8)、source(u8)、attach(u8)、flags(u8)、source ごとの引数 | すぐ |
| 0x05 | target | wire_fn(u16)、chip_id(u32) | すぐ（自動の attach の確かめに使う） |

### 1.1 bind（CDC の口に何を流すか）

| source | 意味 | 引数 |
|---:|---|---|
| 0 | なし | — |
| 1 | `oep.fixture.uart` | fn(u16)、baud(u32)、format(u8) |
| 2 | `oep.target.console` | wire_fn(u16)、mechanism(u8) |

- source 1: format は `oep.fixture.uart` の configure の TLV 0x01 と同じ。baud = 0 は「口の line coding が来るまで UART を動かさ
  ない」で、flags bit0 が要る。fixture.uart の bind は、plan に RX / TX がある間だけ動く。
- source 2 の attach（**必ず明示する**）:

  | attach | 意味 |
  |---:|---|
  | 0 | host に任せる（host が attach したら、その connection でコンソールを開いて流す） |
  | 1 | 口が開かれたとき（DTR が立ったら）自動で attach する |
  | 2 | 起動時に自動で attach する |

  1 / 2 には項目 target が要る（無いまま set すると rejected unavailable）。自動の attach は止めない attach（method 0）だけで、
  直後に target の chip_id を読み、項目 target と違えばコンソールを開かずに外して describe で知らせる。**比べるときは bit [7:4]
  を無視する**（シリコンのリビジョン）。**chip_id が 0 か 0xFFFFFFFF なら「分からない」として、自動の attach を断る。**
- いったん開いたコンソールは、口が閉じられても読み続ける。コンソールが使う connection は bind が使っているものに数える
  （[共通部品](oep-if-common.ja.md) §2）。connection を失ったら、bind は次の合図（attach 0 は host の attach、1 は次に口が
  開かれたとき、2 は次の起動）まで待つ。
- flags: bit0 口の line coding（baud、data bits、parity、stop bits）を fixture.uart に写す（最後に来た設定が勝つ。OEP の
  configure も同じ UART を掛け直す）。ほかの bit は 0（立っていれば rejected unsupported）。
- **口に流すのは、口が開かれている間（DTR）に来たバイトだけ**。閉じている間に来たバイトはストリーム（OEP の read）にだけ残る。
  口から来たバイトは、source 1 なら TX に、source 2 なら console の write に、相手が受け取れる分だけ渡す（残りは口に残る）。
  ストリームが口より丸ごと先に行ったら、口は一番古いバイトまで飛ぶ。
- DTR / RTS / 1200 baud の touch は、attach 1 の合図（DTR）のほかには何もしない（target の reset に使わない）。CDC は AT コマンド
  なし（bInterfaceProtocol 0）で宣言する。

## 2. 操作

| op | 名前 | 要求 | 応答 | ロック |
|---:|---|---|---|---|
| 0x01 | get | first(u16) | more(u8)、hash(u32)、項目の並び（今の設定） | 不要 |
| 0x02 | set | 項目の並び | hash(u32) | 必要 |
| 0x03 | save | — | hash(u32) | 必要 |
| 0x04 | erase | — | — | 必要 |
| 0x05 | reboot | — | —（応答を送ってから再起動する） | 必要 |

- **set は、要求に含まれる tag の項目をすべて置き換える**（含まれない tag はそのまま）。同じ tag の項目を消すには、その tag を
  値の長さ 0 で 1 つ送る。**set は全体で原子的**（plan が受け入れられても bind が結べなければ plan も元に戻し、何も変えない）。
- 1 つの set の中で同じキー（label の channel、bind の port）が 2 回出たら、要求全体を rejected malformed。
- **設定は起動モードに依存しない。** bind はどのモードの口でも名指してよい（port は、どれかのモードの ports の範囲）。今のモードに
  無い口への bind は保持して何もせず、そのモードで起動したときに結ぶ。
- **hash** は今の設定の正規形の CRC-32（core §5.2 と同じ IEEE）。正規形 = 項目を tag の昇順に、同じ tag の中は最初のキー（label は
  channel、bind は port）の昇順に並べ、TLV（tag u8、len u8、値）でつないだバイト列。tag には critical の bit を含めない（要求で
  critical で送られても外して持つ）。host は自分の欲しい設定から同じ値を計算し、get の hash と同じなら何もしない。
- **save は host の明示的な操作だけ**で、今の設定をそのまま保存する（同じ内容なら書かない）。書いている間はほかの要求に答えない。
  保存先が足りなければ rejected unavailable。erase は保存を消す（今の設定は変えない）。
- 起動時は、保存があればそれを今の設定にして、起動モードで列挙し、plan を適用し、bind を結ぶ。保存を読めないときは適用せず、
  describe で知らせる。
- **describe の mode には、probe が実際に組める構成だけを出す。** set は describe に無い mode を rejected unsupported で断る。
  firmware が変わって保存の boot_mode が組めなくなったときは、probe は保存から boot_mode を外して、自分の選ぶモードで起動し直す
  （USB から戻れなくならないように）。保存の hash が変わるので、host はそれで気づく。

## 3. describe

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | mode | index(u8)、functions(u8)、ports(u8: データの CDC の口の数)、name（text）。モードごとに 1 つ |
| 0x41 | current_mode | 今の mode(u8)、次の起動の mode(u8) |
| 0x42 | port | port(u8)、USB の interface 番号(u8)。今のモードの口だけ |
| 0x43 | storage | 保存できる最大 byte(u32、0 = 保存なし)、保存の状態(u8: 0 なし / 1 あり・適用済み / 2 あり・読めない)、保存の hash(u32)、save の最長時間(u32 ms)、reboot から再列挙までの最長時間(u32 ms) |
| 0x44 | cost | ports(u8)、OEP の probe → host の上限の目安(u32 byte/s) |

mode の functions: bit0 vendor bulk、bit1 CDC の OEP の口、bit2 HID の OEP の口、bit3 Mass Storage（OEP の外）、bit4 DFU runtime
（OEP の外）。
