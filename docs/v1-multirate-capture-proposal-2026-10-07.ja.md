# チャネルごとに縮約するロジックキャプチャの提案（2026-10-07）

Status: **proposal**（非規範）。利用者と WireSkein の確認を待つ。採れば、規範の文は [capture](../interfaces/oep-if-capture.ja.md) に新しい節（§5 の案）として入れ、
番号は `registry/oep-v1.toml` に足す。core の freeze 条件ではなく、`oep.fixture.logic` の wire は変えない。

入力: 外部レビュー [§12.8](external-spec-review-2026-10-06.ja.md)、今の capture（§1〜§4）と registry の capture の項目、core §13、
ESP32-P4 の試作（§1）、WireSkein の回答（下の 4 点）。

WireSkein の回答の要約:

1. `.wireskein` はキャプチャごとに `tick_hz` を 1 つ、チャネルごとに `step` と `phase` を持つ（サンプル k = tick の phase + k·step）。
   `base_rate = tick_hz`、`D = step`、`phase = phase` でそのまま入る。
2. 点を選ぶもの（raw、decimate_hold）は今の `bits` 形式で入る。any_active / edge_latch は区間の要約なので、新しい形式
   `interval-any`（区間 k = tick `[phase + kD, phase + (k+1)D)` に 1 bit、active の極性つき）と後で `interval-latch`（2 bit）を作る。
   不確かさは D から決まる。照合では pulse の有無とレベルを確かめられ、周波数と duty は確かめない。
3. 初版は raw / decimate_hold / any_active。D は一般の整数、probe は扱える D を宣言する。block は L base sample、block の中は
   役割の順、チャネルごとに byte 境界。単一レートの interleaved layout と混ぜない。トリガは base sample で評価する。
4. 別のインターフェースにする。capture-group で束ねられること。

## 0. 結論（要約）

- 名前 **`oep.fixture.logic-multirate`**、revision 1、対象の系統: どの系統にも使う。
- op、状態、区画、read、release、通知は `oep.fixture.logic` と同じ。違うのは configure / query の中身、describe の 2 つの TLV、
  データの layout、数え方（サンプル数、pretrigger、trigger_index はすべて **base sample** で数える）。
- 縮約の方針は 2 つだけ: **sample**（点を選ぶ。D = 1 が raw、D > 1 が decimate_hold）と **any_active**。edge_latch は番号だけ予約する。
- チャネルの記述は `role(u8) policy(u8) d(u32) param(u32)`。param は sample では phase、any_active では極性。
- データは L base sample の block の並び。block の中は役割の順に、チャネルごとに 1 枚の面（plane）を byte 境界で置く。
  最後の不完全な block は、区画の samples（base sample の数）だけから長さが決まる。**区画の情報の形は変えない。**
- 予算は describe に置かない（置くのは保存の大きさだけ）。組み合わせが重ければ probe は実際の base rate を下げて答え、configure / query の応答が正。

## 1. ESP32-P4 の試作（調べた結果）

`oep-probe-arduino` には無い（`main`、`l103-investigate`、`spi-classic-fix`、`origin/release` のどれにも `any_active` /
`edge_latch` / `decimate` の実装は無い。`src/OepCaptureGroup.cpp` の `any_active` は組の状態の変数で無関係）。
`~/dev_oep` のほかの repo にも無い。試作は **`~/dev_wch/wch-protocols/experiments/`** にある:

| 実験 | 内容 |
|---|---|
| E105 `codec.py` | 意味の基準になる Python の reference codec（encode / decode / budget） |
| E114 | host が渡す descriptor から組む generic codec、ACCEPT / REJECT |
| E115 | 縮約チャネルを群ごとの bit 行列の転置で取り出す（速さ） |
| E117〜E121 | 正規ライブラリの公開 API への移植、soak（16 ch: 3 raw＋hold/8＋12 hold/64 を 60 Msps でバイト一致） |

**D の表し方**: `log2 D`（u8）。D は 2 の冪で 1〜128（`log2d > 7` は `decimation_range` で断る）。raw は D = 1 だけ。

**descriptor**: 16 byte の header（command、rate、blocks、flags、チャネル数）＋ `budget_mbps`（u16）＋チャネルごとに 4 byte
`gpio, mode, log2 D, phase | polarity<<7`。mode は 0 raw、1 decimate_hold、2 any_active、3 edge_latch。最大 16 チャネル。

**方針の意味**（E105 `codec.py`）:

- raw / decimate_hold: bucket `[kD, (k+1)D)` の中の位置 `phase` の 1 点。
- any_active: bucket の中に active level が 1 度でもあれば active level、無ければその反対（active-low なら AND、active-high なら OR）。
- edge_latch: 2 bit。bit0 = bucket の最後のレベル、bit1 = bucket の**内側**で active への遷移があったか。前の bucket の最後から
  この bucket の最初への遷移は数えない。

**block の layout**: 128 base sample で固定。block の中は「raw チャネルを sample-major に F bit ずつ詰めた部分 → 縮約チャネルの面を
**bit で隣接**させて連結 → block の末尾だけ byte に padding」。E115 からは縮約チャネルを (mode, D, phase, 極性) の群の順に並べ替え、
並び順を応答の `order=` で host に返す。区画もトリガも無く、ストリーミングだけ（端数の block は作らない）。

**予算と判定**: device は物理幅、block の大きさ、payload / padding の bit 数、raw 入力の帯域、wire の帯域を返し、
形式、PARLIO の制約（≤ 160 MHz）、raw 入力の帯域、codec の上限、host が渡す USB 予算で断る。codec の上限は表では決められず
（方針の組み合わせで 10 倍違う: 16 ch hold で 47.9 Msps/core、edge_latch ×12 で 14.3）、descriptor を受けるたびに device の上で
8,192 block を符号化して測り、その係数倍を上限にしている。

**この提案との違い**（§11 の問いにつながる）:

| 項目 | 試作 | 提案 |
|---|---|---|
| D | `log2 D`、1〜128 | u32 の整数。probe が扱う集合を宣言 |
| 方針 | raw / hold / any / edge | sample（raw は D = 1）/ any_active。edge_latch は予約 |
| block | 128 で固定 | probe が L を選んで応答で返す |
| raw チャネル | sample-major の先頭部分 | ほかと同じく 1 チャネル 1 面 |
| 面の並びと詰め方 | 群の順、bit で隣接 | 役割の順、チャネルごとに byte 境界 |
| 端数 | 無し | 最後の block の規則（§5.3） |
| edge の定義 | bucket の内側だけ | 予約。採るときは境界の遷移も数える（§10） |
| 予算 | device の bench と host の予算で ACCEPT / REJECT | describe は保存の大きさだけ。応答の実際の rate が正 |

## 2. 名前、revision、系統

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.fixture.logic-multirate` | 1 | ロジック（1 トラック）、チャネルごとに縮約して保存する | どの系統にも使う |

- core §13 規則 1: 名前は host が何に使うかで切る。基本の logic を広げず、任意の機能を別の名前のインターフェースにする（capture §3.6、§13.1 の 4）。
- 同じ probe が `oep.fixture.logic` と両方を出してよい（別の fn）。どちらも聞くだけなので、ピンの共有は capture §1 の規則のまま。
- **logic と同じ番号の tag は、同じ形で同じ意味**（数え方が base sample になることだけが違う）。違う形のものには新しい番号を使う。
  両方を実装する probe と host が、同じ番号を違う形で読まないため。

## 3. 操作

op の番号、要求と応答の固定部分、ロック、状態の遷移、区画、世代、read、release、通知は **capture §2〜§3.4 と同じ**。違いだけを書く。

| op | 名前 | logic との違い |
|---:|---|---|
| 0x01 | configure | 設定の TLV（§4.2）。応答の TLV（§4.3） |
| 0x02 | start / 0x03 stop / 0x04 force / 0x05 status | 無し |
| 0x06 | read | 無し（位置はバイト位置。§5 の layout のバイト） |
| 0x07 | segments | 形は無し。samples、trigger_index は base sample（§6） |
| 0x08 | release | 無し |
| 0x09 | query | **必須**（logic では任意） |
| 0x0A | calibration | 無い（unknown_operation、logic と同じ） |
| 0x30 / 0x32 | subscribe / unsubscribe | 無し（任意、両方とも持つか持たない） |

- query を必須にする理由: 受けられるかは方針の組み合わせで大きく変わり（§1）、describe では言い切れない。host はロックなしで、
  今の設定を壊さずに組み合わせを試せる必要がある。configure と同じ判定を、設定せずに返すだけなので、実装の量はほとんど増えない。
- 状態と通知（segment、stopped、triggered、ストリーミングのデータと TLV generation）は logic と同じ。
- 役割（plan）: 役割 k = チャネル k（0〜127）。チャネルの順は役割の番号の小さい順（capture §3.1 と同じ）。

## 4. TLV

### 4.1 describe

| tag | 名前 | 値 | logic との関係 |
|---|---|---|---|
| 0x09 | ops | core §7.4。force、subscribe / unsubscribe は持つときだけ。query は必ず立てる | 同じ |
| 0x06 | features | revision 1 はビットを定めない（予約、0） | 同じ |
| 0x41 | rate_range | min_hz(u32)、max_hz(u32)、exact(u8)。**base rate** の範囲 | 同じ形 |
| 0x44 | channels | max(u8) | 同じ |
| 0x45 | trigger | types(u32)、max_pretrigger(u32、base sample) | 同じ形 |
| 0x60 | policies | u32 のビット集合。bit p = 方針 p を扱う（§4.4。bit 0 は必ず立つ） | 新 |
| 0x61 | decimation | min_d(u32)、max_d(u32)、pow2(u8: 1 = その範囲の 2 の冪だけ、0 = その範囲の全部の整数)。min_d は 1 | 新 |
| 0x62 | storage | mode(u8)、max_bytes(u32: 1 区画のデータのバイト数の最大)、max_segments(u32)。モードごとに 1 つ繰り返す | 新（logic の 0x40 mode の代わり） |

- logic の 0x40 mode（max_samples）は使わない。チャネルごとに 1 base sample あたりのビット数が違うので、サンプル数では保存の大きさを言えない。
- **予算の式**（host が設定を選ぶための目安。規範はこの式ではなく応答）: 1 block のバイト数
  `B = Σ_c ceil((L / D_c) · b_c / 8)`（b_c は方針の値のビット数、sample と any_active は 1）。1 区画に置ける base sample は概ね
  `floor(max_bytes / B) · L`。ストリーミングの payload は `actual_rate · B / L` byte/s。L は configure の応答で分かるので、
  host は query で L と実際の rate を得てから式を使う。
- **describe に置かないもの**: 取り込みの帯域、codec の処理能力、wire の帯域。試作では方針の組み合わせで 10 倍変わり、1 つの数で
  宣言すると誤る。probe はそれを configure / query の実際の rate（§4.3）で表す。

### 4.2 configure / query の要求

| tag | 名前 | 値 | logic との関係 |
|---|---|---|---|
| 0x40 | mode | u8: 1 ワンショット、2 リピート、3 ストリーミング | 同じ |
| 0x42 | rate | rate_hz(u32)。**base rate**（全チャネルを同時に見るレート） | 同じ形 |
| 0x43 | samples | u32。1 区画の **base sample** の数（pretrigger を含む） | 同じ形 |
| 0x44 | segments | u32 | 同じ |
| 0x45 | trigger | type(u8)、role(u8)、value(u32) | 同じ形 |
| 0x46 | pretrigger | u32（base sample） | 同じ形 |
| 0x60 | channel | role(u8)、policy(u8)、d(u32)、param(u32)。役割ごとに 1 つ。繰り返す | 新 |

- channel の無い役割は `policy 0、d 1、param 0`（raw）。channel を 1 つも送らなければ、全チャネルが raw。
- param: policy 0（sample）では phase（0 ≤ phase < d）、policy 1（any_active）では極性（0 = active-low、1 = active-high）。
- 断り方（core §2.3 と §4.3 のとおり。要求全体を断り、何も変えない）:

| 要求 | 断り |
|---|---|
| d = 0、sample で phase ≥ d、any_active で param > 1、同じ role の channel が 2 つ | malformed |
| 予約の policy（2 以上。2 は edge_latch に予約）、宣言の policies に無い policy、宣言の decimation に無い d | unsupported（受け取ったままの tag） |
| plan に無い role の channel | unavailable（cause 6） |

- **トリガ**はどの役割でも、その役割の方針によらず **縮約の前の base sample** で評価する（any_active / 32 で保存する CS の
  1 base sample の pulse でトリガできる）。trigger_index と triggered の trigger_index は base sample の番号。
- **rate**: logic の規則（rate_range の中で実現できる最も近い値）に 1 つ足す: 方針の組み合わせ、チャネル数、モードのために求めた rate を
  保てないとき、probe は保てる最も高い rate を使う（求めた rate より低い）。rate_range の外は今までどおり unsupported（tag 0x42）。
  host は query に rate = max_hz を送れば、その組み合わせで出せる最高の base rate を 1 往復で知る。
- **samples**: probe は L の倍数に切り上げ、保存の上限を超えれば L の倍数で切り下げる。actual_samples が正（logic と同じく、送った値を仮定しない）。

### 4.3 configure / query の応答

| tag | 名前 | 値 | logic との関係 |
|---|---|---|---|
| 0x50 | actual_rate | num(u32)、den(u32)。base rate | 同じ |
| 0x52 | actual_samples | u32（base sample、L の倍数） | 同じ形 |
| 0x53 | actual_segments | u32 | 同じ |
| 0x56 | blocking_ms | u32 | 同じ |
| 0x61 | block | L(u32)。block の base sample の数 | 新 |

- logic の 0x51 layout（w、pos）は使わない。チャネルの面の位置は L と要求の channel から決まり、probe は D、phase、極性を変えない
  （扱えなければ断る）ので、応答で返し直さない。
- L の規則: L ≥ 1、どのチャネルの d でも割り切れる。L の選び方は probe の自由。**目安**（非規範）: どのチャネルでも `L / d` が 8 の倍数に
  なる L を選べば、byte 境界の padding は 0 になる（§5.2）。

### 4.4 方針（registry の enum `policy`）

| 値 | 名前 | 値のビット数 | チャネル c の値 k（区画の中で 0 から数える） |
|---:|---|---:|---|
| 0 | sample | 1 | base sample `k·D + phase` のレベル |
| 1 | any_active | 1 | base sample `[k·D, (k+1)·D)` に active のレベルが 1 つでもあれば active のレベル、無ければその反対 |
| 2 | （予約: edge_latch） | 2 | §10 |

- sample の D = 1 が raw、D > 1 が試作の decimate_hold。any_active の D = 1 は raw と同じ値になる。
- any_active の区間は区画の base sample 0 に揃う（phase を持たない）。値の時刻の意味は「その区間のどこかで active だった」だけで、
  位置と長さは表さない。不確かさは D base sample で、別の値を足さない。
- 値 k は、それが頼る base sample（sample は 1 つ、any_active は D 個）が全部区画の中（samples 未満）にあるときだけ存在する。

**WireSkein への写し方**: `tick_hz = actual_rate`（num / den）。sample → `bits`、`step = D`、`phase = phase`。
any_active → `interval-any`、`step = D`、`phase = 0`、極性はそのまま。区画の start_ns がキャプチャの時刻の基準。

## 5. データの layout

### 5.1 block

- 区画のストリーム（capture §1 の「ストリーム」と「ストリームのビット j」の定義のまま）は、block の並び。block b は区画の
  base sample `[b·L, (b+1)·L)` を表す。
- 1 つの block の中は、チャネルの面を**役割の番号の小さい順**に置く。チャネル c の面は `n_c` 個の値を、値 0 から面の先頭の
  ビット 0（LSB）から詰め、`ceil(n_c · b_c / 8)` バイト。値 j はその面のビット `j · b_c` から `b_c` ビット。
- 面の最後のバイトで値の後ろに残るビット（padding）は、probe が 0 にし、host は読まない。
- 完全な block では `n_c = L / D_c`。block b の中の値 j は、チャネルの値 `k = b · (L / D_c) + j`（§4.4）。
- 完全な block のバイト数 B は全部同じ（§4.1 の式）。block b は区画の先頭から `b · B` バイト目に始まる。

### 5.2 最後の block

- 区画の samples が L の倍数でないとき（stop、エラーで途中で終わった短い区画: flags bit1）、最後の block は
  `r = samples mod L` 個の base sample を表す不完全な block になる。
- その block の各チャネルの値の数は、§4.4 の「値が存在する」規則で決まる: sample は `max(0, ceil((r − phase) / D))`、
  any_active は `floor(r / D)`。面の並びと詰め方は完全な block と同じで、値の無いチャネルの面は 0 バイト。
- 区画のバイト数 = `floor(samples / L) · B` ＋ 不完全な block のバイト数。host は samples と L と channel から計算する。
- 区画の情報に新しいフィールドは要らない（r は samples から決まる）。

### 5.3 区画と block の揃え方（logic との違い）

- **区画の samples は、短い区画（flags bit1）のほかは actual_samples に等しく、L の倍数である。** リピートの次の区画とストリーミングの
  区切りは、いつも block の境目で始まる。縮約チャネルの値の間隔は、区画の境目をまたいでも D のまま。
- **pretrigger が足りないとき**（トリガが早く立った）、区画を短くせず、トリガより後ろのサンプルを多く取って samples を保ち、trigger_index を
  小さくする（logic は区画を短くする）。理由: 短くすると samples が L の倍数でなくなり、その後に続く区画とストリームの block の格子がずれる。
- **ストリーミング**: 区画はすべて完全な block の並びなので、start からのバイト位置 p は block `floor(p / B)` に入る（最後の短い区画の
  不完全な block だけが例外）。probe がデータを捨てるときは block 単位で捨てる（position の飛びは B の倍数）。host は segments を
  読まずに、position だけで block の境目が分かる。

### 5.4 例

3 チャネル、L = 32:

| 役割 | channel | 面のバイト数（完全な block） |
|---|---|---|
| 0 | sample、D 1、phase 0（raw。channel を送らない） | 32 値 → 4 |
| 1 | sample、D 4、phase 0 | 8 値 → 1 |
| 2 | any_active、D 32、active-low | 1 値 → 1（bit 1〜7 は padding の 0） |

B = 6。ワンショット、samples 96 を求め、base sample 72 で stop した（samples 72、flags bit1、r = 8）。入力（区画の base sample n）:

- 役割 0: n = 0〜4、20〜23、32〜63 の偶数、64〜65 で 1。ほかは 0。
- 役割 1: n = 2〜8、26〜31、32〜63、68〜71 で 1。ほかは 0。
- 役割 2: n = 13 と 70 で 0。ほかは 1。

| block | 役割 0 | 役割 1 | 役割 2 |
|---|---|---|---|
| 0（n 0〜31） | `1F 00 F0 00` | `86`（n = 4、8、28 で 1 → 値 1、2、7） | `00`（n = 13 に active） |
| 1（n 32〜63） | `55 55 55 55` | `FF` | `01`（active 無し） |
| 2（不完全、r = 8） | `03`（8 値） | `02`（値は n = 64、68 の 2 つ） | 無し（`floor(8/32) = 0`。n = 70 の pulse は値に入らない） |

区画のストリーム（14 バイト）:

```text
1F 00 F0 00 86 00  55 55 55 55 FF 01  03 02
```

トリガを「役割 2 の立ち下がり（type 2、value 1）」、pretrigger 13 にした場合、区画は n = 13 のトリガで trigger_index 13（base sample）。
役割 2 は any_active / 32 で保存していても、トリガは base sample で見る。

configure の要求の TLV（役割 0 は既定なので送らない）:

```text
40 01 00 01                                  mode 1
42 04 00 00 E1 F5 05                         rate 100 000 000
43 04 00 60 00 00 00                         samples 96
60 0A 00 01 00 04 00 00 00 00 00 00 00       role 1, sample, d 4, phase 0
60 0A 00 02 01 20 00 00 00 00 00 00 00       role 2, any_active, d 32, active-low
```

応答の TLV の例: `50 08 00 00 E1 F5 05 01 00 00 00`（100 MHz）、`61 04 00 20 00 00 00`（L 32）、`52 04 00 60 00 00 00`（actual_samples 96）、
`53 04 00 01 00 00 00`、`56 04 00 00 00 00 00`。

## 6. 区画の情報

**形は変えない**（capture §2 の 37 byte のまま）。意味だけ:

| フィールド | 意味 |
|---|---|
| samples | 区画の base sample の数（§5.2 の最後の block はここから決まる） |
| start_ns | 区画の base sample 0 の時刻の推定値 |
| trigger_index | トリガが立った base sample の番号 |
| flags bit2 | 予定の時刻を 1 **base sample** 周期以上過ぎて取ったサンプルがある |

position、generation、serial、flags bit0 / bit1 は logic と同じ。

## 7. capture-group との関係

- `oep.fixture.logic-multirate` の fn をトラックとして bind できる。tracks（describe 0x40）に並べる。
- trigger_track にできる。条件はそのトラックの trigger（base sample で評価）。
- 「全トラックの trigger_index を、そのトラックでその時刻に最も近いサンプルにする」は、このトラックでは**最も近い base sample**。
  pretrigger もそのトラックの base sample で数える。
- モードを揃える、束ねている間の configure / start / stop / force の断り、世代、start の応答の generation は今のまま。
- capture §4.1 の文の変更（1 行）: bind の対象「`oep.fixture.logic` / `oep.fixture.analog` の fn」を、**「capture §3 の op と状態を持つ
  トラックのインターフェース（`oep.fixture.logic`、`oep.fixture.analog`、`oep.fixture.logic-multirate`）の fn」**にする。
  freeze の前なので capture-group の revision は変えない。

## 8. 規範の文の置き場所

capture の文書に **§5 `oep.fixture.logic-multirate`** を足す（logic、analog、capture-group と同じ文書。op と状態を §3 から参照できる）。
冒頭の表に 1 行足す。registry には `[[interface]] name = "oep.fixture.logic-multirate"` を足し、op は logic と同じ表、
`tlv.configure` に channel 0x60、`tlv.configure_answer` に block 0x61、`tlv.describe` に policies 0x60 / decimation 0x61 / storage 0x62、
`enum.policy`（sample 0、any_active 1）、`reserved` に policy 2（edge_latch）と tlv.configure_answer 0x51、tlv.describe 0x40。

## 9. 足す vector

ops.json（`oep.fixture.logic-multirate` の fn）:

1. describe: ops に query、policies `0x00000003`、decimation `1, 128, pow2 1`、storage。
2. configure: §5.4 の要求と応答（バイトつき）。query は同じ応答で、状態を変えない。
3. 断り: d = 0 → malformed。sample で phase = d → malformed。any_active で param 2 → malformed。同じ role に 2 つ → malformed。
   policy 2 → unsupported（tag 0x60）。tag 0xE0（critical）で policy 2 → unsupported（tag 0xE0）。d = 3（pow2 の宣言）→ unsupported。
   d = 256（max_d 128）→ unsupported。plan に無い role → unavailable cause 6。
4. samples 72 を求める → actual_samples 96（L 32 の倍数に切り上げ）。
5. rate = max_hz に重い組み合わせ → actual_rate が下がる（fake の probe の上限で固定した値）。
6. segments: 短い区画（samples 72、flags bit1）。trigger_index が any_active の役割の base sample。

新しい data の vector（例 `tests/vectors/multirate.json`。入力は役割ごとの base sample のレベルの列、channel、L、samples、期待するバイト）:

7. §5.4（完全な block 2 つと不完全な block）。
8. any_active active-high、D = 8。
9. sample の phase ≠ 0（D 4、phase 3）。不完全な block で `ceil((r − phase)/D)` が 0 と 1 になる r。
10. `L / D` が 8 の倍数でない（padding が 0 であること）。
11. D = L のチャネル、r < D で値 0 個。

capture-group:

12. logic-multirate と analog を bind（成功）、trigger_track が logic-multirate。
13. ストリーミングで position が B の倍数で飛ぶ（fake で確かめる。バイトの vector ではない）。

## 10. edge_latch（予約、後の revision）

番号（policy 2）だけを予約する。採るときの案:

- 2 bit。値 k のビット `2j` = 区間 `[kD, (k+1)D)` の最後の base sample のレベル、ビット `2j+1` = 区間の中のどこかの base sample で
  active のレベルへの遷移があった。
- **遷移は前の base sample からの変化で数える。区間の最初の base sample では、前の区間の最後の base sample と比べる**（区画の base sample 0
  だけは比べない）。試作は区間の内側だけを数えるので、区間の境目で始まって区間の中で終わる pulse（前の区間の最後は inactive、
  この区間の最初は active、最後は inactive）を見落とす。
- WireSkein の `interval-latch` と合わせて vector を作ってから入れる。

## 11. 問い

利用者へ:

1. **raw チャネルも面にする**（試作は raw を sample-major の先頭部分に詰める）。1 つの layout で済むが、P4 の codec では raw の bit 転置の
   費用が増えうる（試作の fast 部は約 5 cycle/sample で、費用の大半）。採るなら、P4 で「raw も面にした」場合の bench を測ってから決めたい。
   測った結果が重ければ、代わりに「D = 1 のチャネルは block の先頭に logic §1.1 の w / pos の形で置く」を考える（layout が 2 つになる）。
2. **pretrigger が足りないとき区画を短くしない**（§5.3）。logic と違う。logic も同じにするか（logic の区画の長さが一定になり、少し単純になる）。
3. **重い組み合わせでは probe が rate を下げて答える**（断らない）。logic の「最も近い rate」の延長と見てよいか。
4. **query を必須にする**（logic では任意）。
5. **describe に予算の数（ストリーミングの payload の上限など）を置かない**。host は query に max_hz を送って知る。
6. 名前 `oep.fixture.logic-multirate` でよいか。

WireSkein へ:

7. `actual_rate` は num / den（整数でないことがある）。`tick_hz` は有理数を持てるか。
8. any_active の区間は区画の base sample 0 に揃え、phase を持たない（`interval-any` の phase は常に 0）。phase のある区間が要る用途はあるか。
9. 不完全な最後の block で、区間が欠ける any_active の値を出さない（§4.4）。末尾の D − 1 base sample の情報が落ちる。区間を短くして出す方がよいか。
10. D の宣言は `min_d、max_d、pow2` の 1 つ。{1, 8, 64} のような飛び飛びの集合を持つ probe は表せない（その probe は範囲を狭めるか、
    query で断る）。足りるか。
11. L の上限を決めるか（host の block の buffer）。今は u32 で probe の自由。
12. 1 つの区画の中で、チャネルごとに `.wireskein` の 1 チャネルにする写し方（§4.4 の最後）で、照合の許容（step で広げる）に足りないものはあるか。
