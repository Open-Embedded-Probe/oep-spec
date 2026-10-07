Status: **applied**（2026-10-07）。WireSkein が全体（§11 を含む）を確かめ、例のバイトをすべて独立に再現して承認した。規範の文は
[capture](../interfaces/oep-if-capture.ja.md) §5（multirate、59c5459）、§1.1（w を 1〜128 の任意の整数に、66c49e7）、§2.2（区画の中で
落としたら区画を出さない、0b9a058）。番号は `registry/oep-v1.toml` の `oep.fixture.logic`、vector は `tests/vectors/multirate.json`、
`logic_layout.json`、`ops.json`。この文書は判断の記録として残し、規範ではない（試作の測った値は理由としてここにだけ置く）。

規範に入れるときに文で補ったこと: §11.2 の出さない区画では status の write_pos をその区画の先頭のままにする。rate_range の min_hz でも
保てない multirate の設定は rejected unsupported（multirate の tag）。min_d は 1 以上の値として読む（1 ≤ min_d ≤ max_d）。
ストリーミングの区画も、短い区画を除き L の倍数の base sample にする。

入力: 外部レビュー [§12.8](external-spec-review-2026-10-06.ja.md)、capture §1〜§4（f64ce92 の configure / query の契約、74cf946 の §3.6）、
core §13、ESP32-P4 の試作（§1）、WireSkein と wch-protocols-e4 の回答。

**守るもの**: この機能のきっかけになった probe の、raw のレートでの処理量。layout の判断はすべてここから来る（§5）。

## 0. 結論（要約）

- **新しいインターフェースを作らない。** capture §3.6 が `oep.fixture.logic` の configure（要求と応答）と describe に残した
  TLV 0x60〜0x7F を使う、logic の**別の定義**にする。layout と違う data の形は、自分の応答の TLV（block）で示す（§3.6）。
- 要求は **multirate（0x60、繰り返す、host は critical の bit を付ける）**。1 つでもあれば multirate で取る。応答は layout（0x51、
  D = 1 のチャネルの分）と **block（0x60）**。describe は **multirate（0x60）** で扱えることを宣言する。
- op、状態、区画の情報、世代、read、release、segments のページング、出来事、capture-group の bind は**変えない**。
  samples、pretrigger、trigger_index、rate は **base sample**（全チャネルを同時に見るレート）で数える。
- 方針は 3 つ: **sample**（D = 1 が raw、D > 1 が点を選ぶ）、**any_active**、**edge_latch**（2 bit）。
- block = **D = 1 の部分**（基本の layout と同じ w / pos、sample-major、L サンプル）＋**縮約の部分**（役割の順に bit で詰める）。
  それぞれ byte の境目から始まり、0 の padding はそれぞれの末尾だけ。

## 1. ESP32-P4 の試作（調べた結果）

`oep-probe-arduino` には無い（`main`、`l103-investigate`、`spi-classic-fix`、`origin/release` のどれにも無い。`src/OepCaptureGroup.cpp` の
`any_active` は組の状態の変数で無関係）。`~/dev_oep` のほかの repo にも無い。試作は **`~/dev_wch/wch-protocols/experiments/`** にある:

| 実験 | 内容 |
|---|---|
| E105 `codec.py` | 意味の基準になる Python の reference codec（encode / decode / budget） |
| E114 | host が渡す descriptor から組む generic codec、ACCEPT / REJECT |
| E115 | 縮約チャネルを群ごとの bit 行列の転置で取り出す（速さ） |
| E117〜E121 | 正規ライブラリの公開 API への移植、soak（16 ch: 3 raw＋hold/8＋12 hold/64 を 60 Msps でバイト一致） |

- **D**: `log2 D`（u8）。2 の冪で 1〜128。2 の冪でない D は遅い経路になる。
- **descriptor**: 16 byte の header＋`budget_mbps`（u16）＋チャネルごとに 4 byte `gpio, mode, log2 D, phase | polarity<<7`
  （mode 0 raw、1 decimate_hold、2 any_active、3 edge_latch）。最大 16 チャネル。
- **block**: 128 base sample。raw チャネルを sample-major に F bit ずつ詰めた部分 → 縮約チャネルを bit で隣接させて連結 → block の末尾だけ
  byte に padding。区画もトリガも無く、ストリーミングだけ。
- **予算**: 形式、PARLIO（≤ 160 MHz）、raw 入力の帯域、codec の上限、host の USB 予算で断る。codec の上限は方針の組み合わせで大きく
  変わるので、descriptor ごとに device の上で符号化して測る。
- **edge_latch の不具合**: bucket の内側の遷移だけを数えていた。bucket の境目で始まり中で終わる pulse は消え、bucket 全体を覆う
  pulse は level 1、edge 0 になった。この提案は境目も数える（§4.4）。

## 2. 置き場と番号

- `oep.fixture.logic`（revision 1）の別の定義。名前も revision も増えない。対象の系統はどの系統にも使う。
- 番号は §3.6 が残した範囲から: 要求 0x60、応答 0x60、describe 0x60。0x61〜0x7F は残す。analog には入れない。

## 3. 何が変わり、何が変わらないか

**変わらない**: op の表と番号、ロック、状態の遷移、モード、区画の情報の形（37 byte）、世代、read / release / segments（共通部品 §1.3 の
ページング）、出来事（segment、stopped、triggered と generation）、ストリーミングのデータと TLV generation、capture-group、
区画の中の連続の約束（§2.2: 区画の中は連続で、穴のある区画は無い）。query、force、subscribe / unsubscribe が任意なのも同じ。

**変わる**（multirate の TLV があるときだけ）:

| 項目 | 基本 | multirate |
|---|---|---|
| rate / actual_rate | サンプルのレート | base rate |
| samples、pretrigger、actual_samples、trigger_index | サンプルの数 | base sample の数 |
| 応答の layout（0x51） | 全チャネル | D = 1 のチャネルだけ（0 本もある） |
| 応答の block（0x60） | 無し | 必ず返す |
| データ | §1.1 | §5 の block |
| トリガ | サンプルで評価 | 縮約の前の base sample で評価（どの方針の役割でも） |

## 4. TLV

### 4.1 describe

| tag | 名前 | 値 |
|---|---|---|
| 0x60 | multirate | policies(u32: bit p = 方針 p を扱う。bit 0 は立つ)、min_d(u32: 1)、max_d(u32)、pow2(u8: 1 = その範囲の 2 の冪だけ、0 = その範囲の全部の整数) |

- この TLV が無い fn は multirate を扱わない。
- rate_range、channels、trigger は base rate、base sample で読む。mode（0x40）の max_samples は基本の layout での上限で、
  multirate の上限は応答の actual_samples が正（宣言は目安、§3.5）。
- **予算の数は宣言しない**。host が設定を選ぶ目安は次の式で、規範は応答:
  1 block のバイト数 `B = ceil(L·w / 8) + ceil(R / 8)`（C = 0 なら第 1 項は 0）、`R = Σ_c (L / D_c) · b_c`（縮約のチャネルの和。b_c は sample と any_active が 1、
  edge_latch が 2）。ストリーミングの payload は `actual_rate · B / L` byte/s。

### 4.2 configure / query の要求

| tag | 名前 | 値 | 送るか |
|---|---|---|---|
| 0x60 | multirate | role(u8)、policy(u8)、d(u32)、param(u32)。役割ごとに 1 つ。繰り返す | 任意。1 つでもあれば multirate。**host は critical の bit を付ける**（0xE0） |

- critical にする理由: 扱わない probe が知らない TLV として無視すると、基本の layout で黙って取ってしまう。critical なら
  rejected unsupported（受け取ったままの tag 0xE0）。扱う probe は bit 7 によらず同じに扱う（core §2.3）。
- multirate の TLV の無い plan の役割は `policy 0、d 1、param 0`（raw）。
- param: sample では phase（0 ≤ phase < d）。any_active と edge_latch では active の極性（0 = active-low、1 = active-high）。
  any_active と edge_latch は phase を持たない（区間はいつも区画の base sample 0 に揃う）。
- mode、rate、samples、segments、trigger、pretrigger の契約（§3.3）は**そのまま**。数は base sample で読む。
- 断り（core §2.3、§4.3。要求全体を断り、何も変えない）:

| 要求 | 断り |
|---|---|
| d = 0、sample で phase ≥ d、any_active / edge_latch で d = 1 か param > 1、同じ role に 2 つ | malformed |
| 予約の policy（3 以上）、宣言の policies に無い policy、宣言に無い d | unsupported（受け取ったままの tag） |
| plan に無い role | unavailable（cause 6） |
| describe に multirate の無い fn | unsupported（受け取ったままの tag。critical のとき） |

- any_active / edge_latch の d = 1 を除くのは、D = 1 の部分を「点のレベル」だけにするため（any_active の d = 1 は raw と同じ値、
  edge_latch の d = 1 はレベルの列から分かる）。
- **トリガ**は、役割の方針によらず縮約の前の base sample で評価する。
- **rate**: §3.3 の「rate_range の中で実現できる最も近い値」のまま。応答は、その方針の組み合わせ、チャネル数、モードで probe が保てる
  最も高い rate（求めた rate 以下）を返す。それをどう見つけるか（組み合わせごとに測る、余裕をどれだけ取るか）は実装が決める。
  host は configure か query に rate = max_hz を送れば、その組み合わせの最高の base rate を知る。query は時間がかかることがある。
- **samples**: probe は L の倍数にする（切り上げ、上限を超えれば L の倍数で切り下げ）。actual_samples が正（§3.3 のまま）。

### 4.3 configure / query の応答

| tag | 名前 | 値 |
|---|---|---|
| 0x51 | layout | 基本と同じ形 w(u8)、C(u8)、pos[C](u8)。C と pos は **D = 1 のチャネル**（役割の順）だけ。D = 1 が無ければ C = 0（w は 1） |
| 0x60 | block | L(u32)。1 block の base sample の数 |

- 「success はその対象の行をすべて返す」（§3.3）は変わらない: multirate でも layout を返し、block を足す。
- w の値は基本と同じ（§11.1 の後は 1〜128 の任意の整数。3 本の raw なら w = 3 で詰められる）。probe は D、phase、極性を変えない（扱えなければ断る）ので、記述は返し直さない。
- L の規則: L ≥ 1、どのチャネルの d でも割り切れる。選び方は probe の自由。B の上限は決めない（host は start の前に B を計算できる）。

### 4.4 方針（registry の enum `multirate_policy`）

区画の base sample n のレベルを x(n) と書く。チャネルの値 k（区画の中で 0 から数える）:

| 値 | 名前 | ビット数 | 値 k |
|---:|---|---:|---|
| 0 | sample | 1 | x(k·D + phase) |
| 1 | any_active | 1 | 区間 `[k·D, (k+1)·D)` に x(n) = active が 1 つでもあれば active、無ければその反対 |
| 2 | edge_latch | 2 | bit 0 = x((k+1)·D − 1)（区間の最後のレベル）。bit 1 = 区間の中に、n ≥ 1 で x(n−1) ≠ active かつ x(n) = active の n がある |

- edge_latch の遷移は**前の base sample からの変化**。区間の最初の base sample は前の区間の最後と比べる（block の境目をまたいでも同じ）。
  区画の base sample 0 は何とも比べない（そこで遷移は無い）。
- 値 k は、それが頼る区間（sample は 1 点、any_active と edge_latch は D 点）が全部区画の中（samples 未満）にあるときだけ存在する。
  stop で短くなった区画の末尾の、D に満たない区間は捨てる。区間を短くして値を作らない。
- any_active / edge_latch の値は区間の要約で、位置と長さを表さない。不確かさは D base sample で、別の値を足さない。

**WireSkein への写し方**: `tick_hz = num / den`（actual_rate）。sample → `bits`、`step = D`、`phase = phase`。
any_active → `interval-any`、edge_latch → `interval-latch`、どちらも `step = D`、`phase = 0`、極性はそのまま。区画の start_ns が時刻の基準。

## 5. データの layout

### 5.1 block

区画のストリーム（§1 の定義のまま）は、区画の position から始まる block の並び。block b は区画の base sample `[b·L, (b+1)·L)` を表し、
格子は区画ごとに base sample 0 から始まる。1 つの block は 2 つの部分からなる:

1. **D = 1 の部分**: 応答の layout（w、C、pos）で、block の L 個の base sample を §1.1 の規則（§11.1 の後の形）のとおりに置いたもの。L·w ビット。
   L·w が 8 の倍数でなければ、次の byte の境目まで 0 のビットで埋める。長さは `ceil(L·w / 8)` バイトで、基本の layout が L サンプルに
   出すものと同じ。C = 0 なら 0 バイト。
2. **縮約の部分**: D = 1 の部分の直後の byte から。縮約のチャネルを**役割の番号の小さい順**に、各チャネル `L / D_c` 個の値を値 0 から、
   **チャネルの間を空けずに** bit で詰める（ストリームのビットの定義どおり LSB から）。チャネル c の値 j は、この部分のビット
   `off_c + j · b_c` から b_c ビット（off_c は前のチャネルの `(L / D) · b` の和。edge_latch は値の bit 0 が低い方）。合計 R ビットの後ろを、
   次の byte の境目まで 0 で埋める。長さ `ceil(R / 8)` バイト。

- 0 で埋めるのは 2 か所（それぞれの部分の末尾）だけ。D = 1 の部分の中の、どの pos にも当たらないビットは基本どおり未定義。
- 完全な block はどれも B バイト。block b は区画の先頭から `b · B` バイト目。block b の値 j はチャネルの値 `b · (L / D_c) + j`。

理由（試作の作者の見積もり）: raw チャネルを 1 チャネル 1 面にすると、P4 の codec の費用は 3〜4 倍になる（E105 では sample-major の方が
3〜4 分の 1 の時間）。チャネルごとに byte の境目に揃えると、バイトが無駄になる（試作の例で 25 B に対して 32 B）か、L を 1024 まで
上げることになり、USB の 512 B の stage に合わなくなる。

### 5.2 区画の最後の block

- 区画の samples が L の倍数でないとき、最後の block は `r = samples mod L` 個の base sample を表す。D = 1 の部分は r サンプルぶん
  （`ceil(r·w / 8)` バイト、末尾は 0 で埋める）。縮約の部分は、§4.4 の「値が存在する」規則で決まる数の値を同じ順で詰める:
  sample は `max(0, ceil((r − phase) / D))`、any_active と edge_latch は `floor(r / D)`。末尾は 0 で埋める（R = 0 なら 0 バイト）。
- 区画のバイト数 = `floor(samples / L) · B` ＋ 最後の block のバイト数。区画の情報に新しいフィールドは要らない。
- samples が L の倍数でない区画は、stop かエラーで短くなった区画（flags bit1）と、pretrigger が足りずに短くなった最初の区画（§3.3）だけ。
  区画の長さの規則は基本と同じ。
- 区画の中は連続（§2.2）なので、block は区画の中で欠けない。host は segments で区画の position と samples を読み、区画ごとに復号する。

### 5.3 例

4 チャネル、L = 32:

| 役割 | 記述 | 置き場 |
|---|---|---|
| 0 | any_active、D 32、active-low | 縮約: 1 値（ビット 0） |
| 1 | raw（TLV を送らない） | D = 1: pos 0 |
| 2 | raw（TLV を送らない） | D = 1: pos 1 |
| 3 | sample、D 4、phase 1 | 縮約: 8 値（ビット 1〜8） |

応答の layout は w 2、C 2、pos [0, 1]。D = 1 の部分 64 ビット = 8 バイト、縮約の部分 R = 9 ビット = 2 バイト（ビット 9〜15 は 0）。B = 10。
ワンショット、samples 96、base sample 72 で stop した（samples 72、flags bit1、r = 8）。入力（区画の base sample n）:

- 役割 0: n = 13 と 70 で 0。ほかは 1。
- 役割 1: n = 0〜4、20〜23、32〜63 の偶数、64〜65 で 1。
- 役割 2: n = 8〜11、33、66〜71 で 1。
- 役割 3: n = 2〜9、26〜31、32〜63、68〜71 で 1。

| block | D = 1 の部分 | 縮約の部分 |
|---|---|---|
| 0（n 0〜31） | `55 01 AA 00 00 55 00 00` | `0C 01`（役割 0 の値 0、役割 3 の値 `0x86` を 1 ビットずらす） |
| 1（n 32〜63） | `19 11 11 11 11 11 11 11` | `FF 01`（役割 0 の値 1、役割 3 の値 `0xFF`） |
| 2（r = 8） | `A5 AA` | `02`（役割 0 は値なし、役割 3 は n = 65、69 の 2 値 `0, 1`） |

```text
55 01 AA 00 00 55 00 00 0C 01  19 11 11 11 11 11 11 11 FF 01  A5 AA 02
```

（23 バイト。n = 70 の役割 0 の pulse は、捨てた区間にある。）

configure の要求の TLV:

```text
40 01 00 01                                  mode 1
42 04 00 00 E1 F5 05                         rate 100 000 000
43 04 00 60 00 00 00                         samples 96
E0 0A 00 00 01 20 00 00 00 00 00 00 00       multirate: role 0, any_active, d 32, active-low
E0 0A 00 03 00 04 00 00 00 01 00 00 00       multirate: role 3, sample, d 4, phase 1
```

応答の TLV: `50 08 00 00 E1 F5 05 01 00 00 00`（actual_rate 100 MHz）、`51 04 00 02 02 00 01`（layout w 2、C 2、pos 0 1）、
`60 04 00 20 00 00 00`（block L 32）、`52 04 00 60 00 00 00`（actual_samples 96）、`56 04 00 00 00 00 00`（blocking_ms 0）。

**L·w が 8 の倍数でない例**: 役割 0 raw、役割 1 sample D 4 phase 0、L = 4、w 1。D = 1 の部分は 4 ビット＋0 の 4 ビットで 1 バイト、
縮約の部分は 1 ビット＋0 で 1 バイト、B = 2。samples 8、役割 0 は n = 0〜2 と 5 で 1、役割 1 は n = 0 で 1:
`07 01 02 00`。

**w = 3 の例**（§11.1 の後）: 役割 0〜2 raw（pos 0、1、2）、役割 3 sample D 4 phase 0、役割 4 any_active D 2 active-low、L = 4。
D = 1 の部分は 12 ビット＋0 の 4 ビットで 2 バイト、縮約の部分は 3 ビット（役割 3 が 1、役割 4 が 2）＋0 で 1 バイト、B = 3。samples 8。
入力: 役割 0 は n = 0〜2、5 で 1。役割 1 は n = 1、3 で 1。役割 2 は n = 7 で 1。役割 3 は n = 0、4、5 で 1。役割 4 は n = 2 だけ 0:
`59 04 03  08 08 07`。

**edge_latch の例**: 役割 0 だけ、edge_latch、D 8、active-high、L = 16（C = 0、layout `51 02 00 01 00`）。B = 1（4 ビット＋0）。samples 48。
入力: n = 0〜2、8〜10、16〜23、30〜33 で 1。

| 区間 | n | 値（bit1 edge、bit0 level） | 理由 | 試作 |
|---|---|---|---|---|
| 0 | 0〜7 | `00` | n = 0 は何とも比べない | `00` |
| 1 | 8〜15 | `10` | 境目の n = 8 で立ち上がる（n = 7 と比べる） | `00`（消える） |
| 2 | 16〜23 | `11` | 区間全体を覆う。n = 16 は block の境目（n = 15 と比べる） | `01`（edge 無し） |
| 3 | 24〜31 | `11` | n = 30 で立ち上がる | `11` |
| 4 | 32〜39 | `00` | n = 32 は block の境目をまたいだ pulse の続き（立ち上がりではない） | `00` |
| 5 | 40〜47 | `00` | | `00` |

```text
08 0F 00
```

（試作の数え方では `00 0D 00`。）

## 6. 区画の情報、通知、capture-group

- 区画の情報の形と意味は基本と同じ。samples は base sample の数、start_ns は base sample 0 の時刻、trigger_index は base sample の番号、
  flags bit2 は 1 base sample 周期以上の遅れ。triggered の trigger_index も base sample。
- 区画の中でデータを落としたときの扱いも基本のまま（§2.2 の連続の約束と §11.2: 穴のある区画は出さず、エラーで止まる）。
- capture-group: 変えない。multirate で configure した logic の fn も、今のまま bind でき、trigger_track にできる。「最も近いサンプル」は
  このトラックでは最も近い base sample。pretrigger もそのトラックの base sample で数える。

## 7. 規範の文の置き場所と registry

- capture に **§5 multirate（`oep.fixture.logic` の別の定義）** を足す。§3.6 の一覧に「チャネルごとの縮約: §5」を足す。
- registry の `oep.fixture.logic`: `tlv.configure` に `multirate = 0x60`、`tlv.configure_answer` に `block = 0x60`、`tlv.describe` に
  `multirate = 0x60`、`enum.multirate_policy`（sample 0、any_active 1、edge_latch 2）。

## 8. 足す vector

ops.json（logic の fn、describe に multirate を持つ fake）:

1. describe: multirate `policies 0x00000007、min_d 1、max_d 128、pow2 1`。
2. configure: §5.3 の要求と応答（バイトつき。layout は D = 1 の 2 本、block）。query は同じ応答で状態を変えない。
3. 断り: d = 0、sample で phase = d、any_active で param 2、edge_latch で d 1、同じ role に 2 つ → malformed。policy 3 → unsupported
   （tag 0xE0）。d = 3（pow2 の宣言）、d = 256 → unsupported。plan に無い role → unavailable 6。multirate を宣言しない fn に 0xE0 →
   unsupported（tag 0xE0）。
4. samples 72 → actual_samples 96（L 32 の倍数）。
5. 重い組み合わせで rate = max_hz → actual_rate が下がる（fake の上限で固定した値）。
6. segments: 短い区画（samples 72、flags bit1）。trigger_index が any_active の役割の base sample。

data の vector（例 `tests/vectors/multirate.json`。入力は役割ごとの base sample のレベル、記述、w / pos、L、samples、期待するバイト）:

7. §5.3 の 4 チャネルの例（23 バイト）。
8. L·w が 8 の倍数でない（`07 01 02 00`）。w = 3 の raw 3 本と縮約（`59 04 03 08 08 07`）。
9. D = 1 が無い（C = 0）。
10. 縮約のチャネルが byte をまたぐ（§5.3 の役割 3）と、縮約の部分の末尾の 0。
11. sample の phase ≠ 0 で、最後の block の `ceil((r − phase)/D)` が 0 と 1 になる r。
12. any_active active-high、D 8。
13. edge_latch: 区間の境目で始まる pulse、区間全体を覆う pulse、block の境目をまたぐ pulse、区画の base sample 0 の 1（edge 無し）
    （§5.3 の `08 0F 00` を 4 つに分ける）。
14. pretrigger が足りずに短くなった最初の区画と、続く区画（格子が区画ごとに始まる）。

capture-group:

15. multirate の logic と analog を bind、trigger_track が multirate の logic。

## 9. 2 の冪でない D

試作では遅い経路になる。それは実装の性質で、規範は変えない: その probe は describe の pow2 = 1 で 2 の冪だけを宣言する。

## 10. 決めたこと（問いを閉じた）

1. **新しいインターフェースにしない**: logic の 0x60 を使う。
2. **query は任意のまま**。query は時間がかかることがある。
3. **pretrigger が足りないときの区画の長さは基本と同じ**。格子は区画ごとに始まる。
4. **rate**: 応答は probe が保てる最も高い rate。見つけ方と余裕は実装が決める。
5. **予算の数を describe に置かない**。目安の式と応答で足りる。
6. **D = 1 は基本の layout、縮約は bit で詰める**（§5.1。P4 の処理量を守る）。D = 1 の部分の末尾は 0 で埋め、縮約の部分は byte の境目から。
7. **B の上限を決めない**。
8. `tick_hz` は有理数: num / den をそのまま写す（WireSkein）。
9. any_active / edge_latch は phase を持たない（WireSkein）。
10. 短い区画の末尾の、D に満たない区間は捨てる（WireSkein）。
11. D の宣言は min_d / max_d / pow2 で足りる（WireSkein）。2 の冪でない D の遅さは pow2 で表す（§9）。
12. **edge_latch を規範にする**: 遷移は前の base sample からの変化、区間の最初は前の区間の最後と比べ（block をまたいでも）、区画の
    base sample 0 は比べない（wch-protocols-e4）。
13. 区画の中で落としたデータは基本の規則のまま（§2.2）。基本に 1 文を足す（§11.2）。
14. **基本の w を 1〜128 の任意の整数にする**（§11.1）。

残る問いは無い。

## 11. 基本の logic の変更（適用済み: §11.1 は 66c49e7、§11.2 は 0b9a058）

### 11.1 w を 1〜128 の任意の整数にする

守るもの: raw チャネルの帯域。3 本の probe が w = 4 で 33% 余分に払わない。

- §1.1 の値の表: `w` の範囲を「1, 2, 4, 8, 16, 32, 64, 128 のどれか」から **「1〜128 の整数」** にする。probe は今までどおり 2 の冪を選んでよい。
- 規則 1〜4 はそのまま（サンプル i はストリームのビット `i·w` から、チャネル k はビット `i·w + pos[k]`、区画は `ceil(N·w / 8)` バイト）。
  ストリームのビット j は、すでに §1 の冒頭で「バイト `floor(j / 8)` のビット `j mod 8`」と定めてある。
- 規則 5 を次の 1 文に置き換える: **「w が 8 の倍数のとき、サンプルは `w/8` バイトの little endian の整数と同じになる（§1 のビットの定義から
  出る結果で、別の規則ではない）。」** w < 8 の「1 バイトに 8/w サンプル」の文は消す（w = 3 ではサンプルがバイトをまたぐ。並びは
  ビットの定義だけで決まる）。
- 例の表に 1 行足す:

| 構成 | w | pos | 中身 |
|---|---|---|---|
| 3 ビットずつ詰める probe、**3 本** | 3 | [0, 1, 2] | サンプル i はビット 3i〜3i+2。8 サンプルが 3 バイト。サンプル 2 はバイト 0 のビット 6〜7 とバイト 1 のビット 0 |

- vector（基本の logic）: w 3、pos [0, 1, 2]、N 8。ch0 はサンプル 0〜2、5 で 1、ch1 は 1、3 で 1、ch2 は 7 で 1 → `59 84 80`。
- multirate の vector: §5.3 の w = 3 の例（`59 04 03 08 08 07`。L·w = 12 で 8 の倍数でない）。
- registry: layout の w の注記を「1〜128」に。configure の応答の layout の形（w(u8)）は変わらない。

### 11.2 区画の中で落としたら、その区画を出さない

§2.2 の「区画の中は連続を約束する」の後に 1 文足す:

**「probe が区画を連続に保てない（区画の中のデータを落とした）とき、その区画をデータとして出さない。トラックはエラーで止まる（state 6、
stopped reason 3 error、error 2）。」**

- 合う番号: enum `error` の **2 置き場**（storage）。取り込みのキューやリングがあふれてデータを落とした場合で、status の flags bit0
  「probe の中でデータを落とした（取り込みのキューやリングがあふれた）」と同じ原因。DMA やペリフェラルが失敗して落としたなら、今までどおり
  **1 DMA / ペリフェラル**。新しい番号は要らない。
- ストリーミングで**送る**余地が無くて捨てる分（§2.1 のストリーミングの規則 1）は、これと別: 区画を丸ごと捨て、次の区画の flags bit0
  （押し出された）で表す今の規則のまま。区画の中に穴は作らない。
- vector: 取り込みのあふれを起こす fake で、stopped（reason 3、error 2）、status の state 6 と flags bit0、その区画が segments に出ないこと。

