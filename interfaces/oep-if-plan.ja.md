# OEP インターフェース: plan v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作る。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.plan` | 1 | どのインターフェースのどの役（role）に、どの channel を使うかの割り当て（plan） | どの系統にも使う |

- **plan の role** は、インターフェースの文書が plan を通して割り当てると定める role である（その role の番号と、選べるピンの宣言 role_channels /
  channel_group は、そのインターフェースの文書と describe が決める、core §7.4）。要求の引数でピンを選ぶ role（線の attach の pins など）は
  plan の role ではない。
- plan の role を持つインターフェースを list に出す probe は、`oep.probe.plan` を list に出す。plan の role を持つインターフェースが 1 つも
  無い probe は、出さない。probe が list に出す `oep.probe.plan` は高々 1 つ。
- plan はセッションの資源である（core §9）。ただし保存した設定が入れた plan（§2.3）は除く。

## 1. 操作

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x01 | plan_apply | role_assignment の TLV の並び | — | 必要 | 必須 |
| 0x02 | plan_release | n(u8)、n × fn(u16) | — | 必要 | 必須 |

describe（core §7.4 の共通の tag のほか）:

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | plan_roles | u32。plan が一度に持てる role_assignment の数（すべての fn の合計。設定の plan を含む）。上限のある probe は必ず出す |

## 2. plan

plan は **fn ごと**に持つ。

### 2.1 plan_apply

- 要求は role_assignment の TLV（0x10、critical の 0x90 で送る: fn(u16)、role(u8)、channel(u16)。繰り返す）の並び。1 つの割り当ての見分けは
  (fn, role, channel)（同じ role に複数の channel を持つ機能がある。gpio など）。
- **要求に出てくる fn の割り当てだけを原子的に置き換え**、ほかの fn の plan はそのまま保つ。置き換える fn の今の割り当てを外したものとして、
  各インターフェースが副作用なしで確かめ（core §8.1 の取り合いの確かめを含む）、全部が受け入れたときだけ適用する。1 つでも断れば、
  何も変えずに rejected（置き換えるはずだった fn の今の plan も残る）。
- **割り当ての数**: 置き換えた後の割り当ての合計（すべての fn。設定の plan を含む）が plan_roles を超える plan_apply（と設定の set）は、何も変えずに
  rejected unavailable（cause 2。資源が足りない。core §8.1 と同じ断り方。要求の形は正しいので malformed ではない）。
- 応答は completed success で、payload は無い。

### 2.2 plan_release

- `n(u8)、n × fn(u16)`。挙げた fn の plan を解く（n = 0 はすべての fn）。plan の無い fn は無視する。
- 応答は completed success で、payload は無い。

### 2.3 設定の plan

保存した設定（[probe の設定](oep-if-probe-config.ja.md) の plan の項目）が入れた fn の plan は、セッションのものではなく、設定だけが変える。
plan_release はその fn を解かずに無視し（n = 0 でも）、plan_apply がその fn を挙げたら何も変えずに rejected unavailable（cause 5、core §8.1 の
ピンの取り合いと同じ断り方）。設定の plan を変える・外すのは、設定の set（とその保存）で行う。こうしないと、保存した設定と実際の割り当てが
食い違う。

### 2.4 ピン

- 解いたピンは、どの道で解いても（plan_release、plan_apply による置き換え、core §9 のセッションの終わりでの後始末）、core §8 の空きの状態にする。
  インターフェースは、解いた後もピンを自分の駆動のまま残してはならない。
- plan を取ってもピンの電気の状態は変わらない（core §8）。ピンは、それを持つインターフェースが使い始めるまで空きの状態を保つ。どの操作で使い始める
  かは、各インターフェースの文書が定める（plan そのもので使い始めるインターフェースもある）。
- idle が出力（mode 3 / 4）の channel への plan をインターフェースの文書が断るときの断り方は core §8。
- セッションの終わりで plan が外れると、ピンは plan_release と同じく空きの状態になる。target の線を plan で保っていた場合、target の状態が変わりうる。

### 2.5 断り方

plan_apply（core §4.3 の順）:

| 状況 | reason |
|---|---|
| 形の誤り、同じ (fn, role, channel) が 2 回、fn 0 を挙げた | malformed |
| fn が無い | unknown_function |
| role がそのインターフェースに無い（plan の role でない）、channel が role_channels の候補に無い、channel_group のどれにも一致しない | unsupported（tag 0x90） |
| plan_roles を超える、ピンや資源の取り合い（core §8.1）、設定の plan の fn、インターフェースが断る出力の idle | unavailable（cause 2 / 1 / 5） |

plan_release: 形の誤り（n と後ろの fn の数が合わない）は malformed。
