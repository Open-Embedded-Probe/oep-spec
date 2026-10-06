# OEP インターフェース: リンク v1

[English](oep-if-link.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.link` | 1 | 経路を試し（線の試験）、セッションの間だけ UART bridge の口の速さを上げる（port_speed） | どの系統にも使う |

- `oep.probe.link` は任意のインターフェースである。port_speed を持つ probe はこれを list に出す。線の試験だけのために出してもよい。probe が
  list に出す `oep.probe.link` は高々 1 つ。
- その op は、port_speed が変える口の速さのほか、probe の状態を変えない。

## 1. 操作

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x01 | source | length(u32)、[TLV] | len(u16)、data、[TLV] | 不要 | 必須 |
| 0x02 | sink | count(u16)、data、[TLV] | — | 不要 | 必須 |
| 0x03 | port_speed | baud(u32)、step(u8: 0 試す、1 決める、2 戻す)、verify_ms(u16)、[TLV] | baud(u32: 実際に掛かる速さ)、[TLV] | 必要 | 任意 |

port_speed は任意で、describe の ops で宣言する（core §1.2、§7.4）。それを持たない probe は unknown_operation で答える。

## 2. 線の試験（source、sink）

source と sink は経路の速さを測るためのもの。状態を変えない。

- **source**: data は len バイトで、k バイト目（k は 0 から）は k & 0xFF。len は length と、要求の来た経路の max_frame（core §4.4）から 7
  （応答の見出し 5 と len 2）を引いた値の、小さいほう。length 0 なら len 0。
- **sink**: count の後ろに、値が任意の count バイトが続く。count が後ろに続くバイトより大きければ rejected malformed。応答は completed success で、
  payload は空。
- host はその応答を、ほかの要求と同じように待つ（core §4.4）。confirm のようには繰り返さない。

## 3. port_speed

port_speed は、UART bridge の口で、セッションの間だけリンクの速さを起動時の速さ（115200 bps、transports §4）より上げる。probe の
fixture UART の速さは別（そのインターフェースの configure と設定）。この節が決めるのは**握手**である。どの速さを試すか、通ったとみなす基準、
使っている間に戻す基準は host が決める（[host 開発ガイド](../docs/host-development-guide.ja.md) §17）。

**probe**

- 対象は、要求の来た経路が transport kind 1（UART bridge）の口のときだけ。ほかの経路からの port_speed は rejected unavailable（cause 6）。
- UART が作れる最も近い速さが要求と `port_speed_tolerance_pct`（2 %）より大きく違えば rejected unsupported。応答の baud は実際に掛けた速さ。
  step 0（試す）の verify_ms 0 は rejected malformed。step 1（決める）と step 2（戻す）では verify_ms に意味は無く、どの値も受ける。
- 状態は口ごとに **起動時 / 試し / 決めた** の 3 つ。
  - **試す**（step 0、起動時の状態で受ける）: 応答を今の速さで送り終えてから、応答の baud に切り替えて**試し**になる。verify_ms を
    この要求の値で始める。
  - **決める**（step 1、試しの状態で、同じ baud、新しい速さで受ける）: **決めた**になる。
  - **戻す**（step 2、試し・決めたのどちらでも）: 応答（baud は起動時の速さ）を今の速さで送ってから起動時の速さに戻る。
  - 状態に合わない step（起動時の状態で決める、決めた後に決める、起動時の状態で戻す、試し・決めたの口で試す、試している baud と違う baud で
    決める）は rejected unavailable（cause 6）。probe は同時に 1 つの口だけ上げる: 上げている口がある間の、別の口の試すも rejected unavailable（cause 6）。
- **probe が自分で起動時の速さに戻る条件**（戻ったことは知らせない）:
  1. 試しのまま verify_ms が過ぎた。
  2. 決めた後、その口に正常なフレームが `port_speed_idle_ms`（3000 ms）来ない。正常なフレームを受けた時と応答を送った時から数え直す（要求を実行して
     いる間は進まない。lease と同じ、core §6.1）。
  3. セッションが終わった（end、lease の期限切れ、force で持ち主が替わった）。end と force は応答を送ってから戻る。
- 試しと決めるの間、セッションの資源とロックは変わらない。生の転送（transports §4）はセッションの間止まっている。

**host**

1. 試すの応答を受けたら、要求した baud（作れなければ応答の baud）に切り替え、`port_speed_switch_wait_ms`（20 ms）以上待ってから、新しい速さで
   次の要求を送る。
2. 戻すの応答、end の応答、または応答の後に probe が再起動する op の応答（probe は起動時の速さで起動し直す）を受けたら、起動時の速さに切り替える。
