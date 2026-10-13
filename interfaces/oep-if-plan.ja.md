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
- plan はセッションの資源である（core §9）。保存した割り当ての再適用はHostが明示的に行う。

## 1. 操作

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x10 | plan_apply | role_assignment の TLV の並び | — | 必要 | 必須 |
| 0x11 | plan_release | n(u8)、n × fn(u16) | — | 必要 | 必須 |

describe（core §7.4 の共通の tag のほか）:

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | plan_roles | u32。plan が一度に持てる role_assignment の数（すべての fn の合計）。上限のある probe は必ず出す |

## 2. plan

plan は **fn ごと**に持つ。

### 2.1 plan_apply

- 要求は role_assignment の TLV（0x10: fn(u16)、role(u8)、channel(u16)。繰り返す）の並び。1 つの割り当ての見分けは
  (fn, role, channel)（同じ role に複数の channel を持つ機能がある。gpio など）。
- **要求に出てくる fn の割り当てだけを原子的に置き換え**、ほかの fn の plan はそのまま保つ。置き換える fn の今の割り当てを外したものとして、
  各インターフェースが副作用なしで確かめ（core §8.1 の取り合いの確かめを含む）、全部が受け入れたときだけ適用する。1 つでも断れば、
  何も変えずに rejected（置き換えるはずだった fn の今の plan も残る）。
- 同じ(fn, role, channel)のまま残る割り当ては解放も再取得もせず、ピンのlevel・向き・プル・強さと機能の状態を保つ。
  取り除く割り当てだけを解放し、追加する割り当てだけを取得する。割り当ての集合が変わらないfnは何もしない。
  変更するfnの機能が動作中なら、そのインターフェースの定義に従いunavailable（cause 6）で断る。
  別fnに束ねられている資源の変更はunavailable（cause 4）。原子性は要求全体の受け付けと状態の更新についての契約であり、
  複数ピンの電気的な切替を同時にする要求ではない。
- **割り当ての数**: 置き換えた後の割り当ての合計（すべての fn）が plan_roles を超える plan_applyは、何も変えずに
  rejected unavailable（cause 2。資源が足りない。core §8.1 と同じ断り方。要求の形は正しいので malformed ではない）。
- 応答は completed success で、payload は無い。

### 2.2 plan_release

- `n(u8)、n × fn(u16)`。挙げたfnのplanを解く（n = 0はすべてのfn）。存在するfnにplanが無ければ無視する。
  対象を全部確かめてから解放する。存在しないfnはunknown_function、別fnに束ねられて解放できないものはunavailable（cause 4）で、要求全体を何も変えずに断る。
  セッションの終了ではcore §9に従い依存資源を先に解放するため、この拒否によって後始末を止めない。
- 応答は completed success で、payload は無い。

### 2.3 ピン

ピンの取得・解放・空きの状態はcore §8に従う。§2.1で残す割り当てには解放の処理を行わない。
使い始める操作と、設定が駆動する出力のピンを取れるかは、採用するインターフェースが定める。

### 2.4 断り方

plan_apply（core §4.3 の順）:

| 状況 | reason |
|---|---|
| 形の誤り、同じ (fn, role, channel) が 2 回、fn 0 を挙げた | malformed |
| fn が無い | unknown_function |
| role がそのインターフェースに無い（plan の role でない）、channel が role_channels の候補に無い、channel_group のどれにも一致しない、個別機能が定める役割の個数・ピンの組を満たさない | unsupported（受け取ったままの tag） |
| plan_roles を超える、ピンや資源の取り合い（core §8.1）、インターフェースが断る出力の idle | unavailable（cause 2 / 1 / 5） |
| 変更対象が動作中、別fnに束ねられている | unavailable（cause 6 / 4） |

plan_release: 形の誤り（n と後ろの fn の数が合わない）は malformed。
