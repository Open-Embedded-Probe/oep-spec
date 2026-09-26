# OEP 標準インターフェース: probe の設定 v1

状態: **規範**（2026-09-26）。本体は [OEP core](oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。経緯と実験は
[シリアルの口と永続化](probe-cdc-and-persistence.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.probe.config` | 1 | probe の設定（起動モード、plan、ラベル、CDC の口に流すもの）と、その保存 |

- **既定の値は持たない。** 項目はすべて host が設定し、probe は設定されたとおりに動く。設定されていない項目については何もしない。
- 設定を扱わない probe は、このインターフェースを list に出さない。
- 設定から入れた plan と bind はセッションの資源ではない（core §9）。lease の期限切れでも外さない。
- mode、port、bind、cost など USB の構成に関わる describe は、USB を持つ probe だけが出す。

## 1. 項目

**設定 = 項目（TLV）の並び**。tag はこの文脈の空間。項目ごとに**キー**があり、同じ tag の項目はキーで見分ける。

| tag | 項目 | 値 | キー | いつ効くか |
|---:|---|---|---|---|
| 0x01 | boot_mode | mode(u8)（describe の mode の番号） | —（1 つだけ） | 次の起動から |
| 0x02 | plan | fn(u16)、role(u8)、channel(u16)（1 項目 1 割り当て） | fn（同じ fn の項目で、その fn の plan になる） | すぐ（その fn の plan_apply と同じ） |
| 0x03 | label | channel(u16)、text | channel | すぐ（core の describe の label 0x46 に出る） |
| 0x04 | bind | port(u8)、source(u8)、attach(u8)、flags(u8)、source ごとの引数 | port | すぐ |
| 0x05 | target | wire_fn(u16)、scheme(u8)、mask(n byte)、value(n byte) | wire_fn | すぐ（自動の attach の確かめに使う） |
| 0x06 | idle | channel(u16)、mode(u8: 0 Hi-Z、1 プルアップの入力、2 プルダウンの入力) | channel | すぐ（そのピンが空いている間） |

- **USB に関わる項目（boot_mode、bind）は任意の群**。USB を持たない probe は label、plan、idle だけを扱ってよい。扱う項目は
  describe の items で宣言し、宣言していない項目の set は rejected unsupported。
- **idle**: plan にも connection にも使われていないピンの状態。起動時と、そのピンが解放されるたび（core §8）に、この状態にする。
  idle が無いピンは Hi-Z。治具の配線で相手の入力が浮くピン（相手の RX につながる TX など）は、host が idle で明示し、保存する。

### 1.1 bind（CDC の口に何を流すか）

| source | 意味 | 引数 |
|---:|---|---|
| 0 | なし | — |
| 1 | `oep.fixture.uart` | fn(u16)、baud(u32)、format(u8) |
| 2 | `oep.target.console` | wire_fn(u16)、mechanism(u8)、swdio(u16)、swclk(u16)、max_speed(u32) |

- source 1: format は `oep.fixture.uart` の configure の TLV 0x01 と同じ。baud = 0 は「口の line coding が来るまで UART を動かさ
  ない」で、flags bit0 が要る。fixture.uart の bind は、plan に RX / TX がある間だけ動く。
- source 2: swdio / swclk は attach の pins と同じ組（1 本の線は swclk = 0xFFFF）、max_speed は attach の max_speed と同じ（0 は
  上限なし）。自動の attach は、この組と上限で、[線とデバッグ](oep-if-debug.ja.md) §1 の規則どおりに行う。
- source 2 の attach（**必ず明示する**）:

  | attach | 意味 |
  |---:|---|
  | 0 | host に任せる（host が attach したら、その connection でコンソールを開いて流す） |
  | 1 | 口が開かれたとき（DTR が立ったら）自動で attach する |
  | 2 | 起動時に自動で attach する |

  1 / 2 には、同じ wire_fn の項目 target が要る（無いまま set すると rejected unavailable）。自動の attach は止めない attach
  （method 0）だけで、その応答の target_id（[線とデバッグ](oep-if-debug.ja.md) §1）を target の項目と比べる: scheme が同じで、
  target_id の値と mask のビットごとの AND が value と一致したときだけコンソールを開く。**target_id が無い、scheme が違う、一致
  しないときは、コンソールを開かずに外し、describe の bind_state で知らせる。** 比べ方（どのビットを無視するか）は host が mask で
  決める（例: WCH の chip_id でリビジョンのビット [7:4] を無視するなら mask 0xFFFFFF0F）。
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
|---|---|---|---|---|
| 0x01 | get | first(u16) | more(u8)、hash(u32)、項目の並び（今の設定） | 不要 |
| 0x02 | set | 項目の並び | hash(u32) | 必要 |
| 0x03 | save | — | hash(u32) | 必要 |
| 0x04 | erase | — | — | 必要 |
| 0x05 | reboot | — | —（応答を送ってから再起動する） | 必要 |

- **set は、要求に含まれる項目のキーごとに置き換える**（含まれないキーはそのまま。何回かの set に分けて積み上げられる）。
  キーの項目を消すには、そのキーだけを持つ項目を送る（label は channel だけ、bind は port だけ、plan は fn だけ、target は wire_fn
  だけ、idle は channel だけ、boot_mode は長さ 0）。plan の項目は fn ごとにまとめて、その fn の plan を置き換える。
- 1 つの set の中で同じキー（plan は (fn, role)）が 2 回出たら、要求全体を rejected malformed。
- **set の原子性は、設定の検証と資源の予約（plan の適用、bind の確かめ）まで**。どれかが受け入れられなければ、何も変えずに
  rejected。自動の attach とコンソールを開くこと（外の状態を変えること）は、set が済んだ後に行い、その結果は describe の
  bind_state で分かる（巻き戻さない）。
- **設定は起動モードに依存しない。** bind はどのモードの口でも名指してよい（port は、どれかのモードの ports の範囲）。今のモードに
  無い口への bind は保持して何もせず、そのモードで起動したときに結ぶ。
- **hash** は今の設定の正規形の CRC-32（core §5.2 と同じ IEEE）。正規形 = 項目を tag の昇順に、同じ tag の中はキー（plan は
  (fn, role)）の昇順に並べ、TLV（tag u8、len u8、値）でつないだバイト列。tag には critical の bit を含めない（要求で critical で
  送られても外して持つ）。host は自分の欲しい設定から同じ値を計算し、get の hash と同じなら何もしない。
- **save は host の明示的な操作だけ**で、今の設定をそのまま保存する（同じ内容なら書かない）。書いている間はほかの要求に答えない。
  保存先が足りなければ rejected unavailable。erase は保存を消す（今の設定は変えない）。
- **保存には、保存したときの interface の一覧の識別値を付ける**（list の entry（fn、instance、revision、name）を fn の順につないだ
  バイト列の CRC-32）。起動時に今の一覧の識別値と違えば、保存を適用しない（fn の番号が別の機能を指しているかもしれないため。
  storage の状態は「あり・読めない」）。boot_mode だけは、組める mode なら一覧が違っても使ってよい（USB から戻れるように）。
- 起動時は、保存を今の設定にして（上の確かめを通ったとき）、idle を掛け、起動モードで列挙し、plan を適用し、bind を結ぶ。保存を
  読めないときは適用せず、describe で知らせる。
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
| 0x45 | items | 扱う項目の tag の並び（u8） |
| 0x46 | bind_state | port(u8)、state(u8: 0 待っている、1 流している、2 target が一致しない、3 attach できなかった、4 target_id が無い)。bind ごとに 1 つ |

mode の functions: bit0 vendor bulk、bit1 CDC の OEP の口、bit2 HID の OEP の口、bit3 Mass Storage（OEP の外）、bit4 DFU runtime
（OEP の外）。
