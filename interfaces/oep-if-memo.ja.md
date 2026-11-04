# OEP インターフェース: メモ欄 v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.memo` | 1 | host が probe に名前つきの小さなデータを置き、後で読み出す | どの系統にも使う |

- host が、probe ごとの記録（つないだ target、治具の配線、試験の準備など）を probe 自身に置いておくためのもの。probe を別の host へ
  つなぎ替えても、記録が probe について行く。
- `oep.probe.memo` は任意のインターフェースである。probe が list に出す `oep.probe.memo` は高々 1 つ。
- **probe はメモ欄を使わない**: probe は置かれたデータを読まず、意味を持たせず、どの動作もメモ欄の中身で変えない。OEP のどの規則も
  メモ欄の中身に頼らない。probe の振る舞いを決める値は設定（core §13）に置く。設定とメモ欄は別のもので、互いの保存、量、規則に効かない。
- **持ち主の区別は無い**: オブジェクトは名前だけで決まる。どの host のどの道具でも、同じ名前は同じオブジェクトを指す。

## 1. オブジェクト

メモ欄はオブジェクトの集まりで、オブジェクトは名前、データ、crc を持つ。

- **名前**: text（core §2.1）で 1〜64 byte。probe は名前をバイト列のまま比べる（大文字と小文字、正規化を区別しない読み替えをしない）。
  文字の種類は制限しない。
- **データ**: 0〜max_object byte のバイト列。probe はデータの形を知らない。
- **crc**: u32。host が書くときにデータ全体の CRC-32 を置き、probe は書き終えたときにそれを確かめて、データと一緒に持つ。読むときは
  持っている値を返す。CRC-32 は CRC-32/ISO-HDLC（多項式 0x04C11DB7、初期値 0xFFFFFFFF、入力と出力を反転、最後に 0xFFFFFFFF と XOR、
  "123456789" → 0xCBF43926。zlib の crc32 と同じ）。長さ 0 のデータの crc は 0。

describe（core §7.4 の共通の tag のほか）:

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | max_object | u32。**必須**。1 以上。オブジェクトのデータの最大の長さ（byte） |
| 0x41 | max_objects | u32。**必須**。1 以上。同時に持てるオブジェクトの数 |

- probe は、名前が 64 byte でデータが max_object byte のオブジェクトを、max_objects 個まで同時に持てることを保証する。宣言は保証なので、
  宣言より多く持てても、宣言より少なくしか持てない probe にはしない。
- 下限は定めない。host は宣言を読んで、足りなければメモ欄を使わない。

## 2. 操作

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x10 | list | first(u16)、prefix(text、0〜64 byte)、[TLV] | more(u8)、count(u8)、count × (name(text)、size(u32)、crc(u32))、[TLV] | 不要 | 必須 |
| 0x11 | read | name(text)、offset(u32)、max(u16)、[TLV] | size(u32)、crc(u32)、len(u16)、data、[TLV] | 不要 | 必須 |
| 0x12 | write | name(text)、size(u32)、offset(u32)、crc(u32)、len(u16)、data、[TLV] | —、[TLV] | 必要 | 必須 |
| 0x13 | delete | name(text)、[TLV] | —、[TLV] | 必要 | 必須 |

text はどれも `len(u8)、bytes` の形で置く。

### 2.1 list

- 名前が prefix で始まるオブジェクトを並べる（prefix が空ならすべて）。並びの順は probe が決める。オブジェクトを足すか消すまで、順は変わらない。
- first はその順で何番目（0 から）から返すか。count は応答に入れた数で、応答が要求の来た経路の max_frame（core §4.4）に収まるだけ入れる。
  more は、その後ろにまだ当てはまるオブジェクトがあれば 1、無ければ 0。host は first に count を足して続きを読む。
- size はデータの長さ、crc はそのオブジェクトの持つ crc（§1）。書きかけのオブジェクト（§2.3）は並べない。

### 2.2 read

- name のオブジェクトのデータを、offset から最大 max byte 返す。返す len は、max、size から offset を引いた値、要求の来た経路の max_frame に
  収まる長さの、いちばん小さいもの。offset が size 以上なら len は 0。
- size と crc はオブジェクト全体の値（§1）。host は全部を読んだら、データの CRC-32 を crc と比べる（§3）。
- name のオブジェクトが無ければ rejected no_resource。書きかけのオブジェクト（§2.3）も無いものとして扱う。

### 2.3 write

1 つのオブジェクトを、1 回か、offset の順に並んだ何回かの write で書く。

- **始め**: offset 0 の write が、name のオブジェクトの書き込みを始める。そのとき前のデータは捨てる（同じ名前のオブジェクトがあれば、
  その中身はこの時点で失われてよい）。書き込みが終わるまで、そのオブジェクトは書きかけで、list にも read にも現れない。
- **続き**: offset が 0 でない write は、書きかけのオブジェクトの続きである。name、size、crc は始めの write と同じ値、offset はそれまでに
  受け取った byte の数でなければならない。そうでなければ rejected unavailable（cause 6、wrong_state）で、書きかけのものは変えない。
- **終わり**: 受け取った byte の数が size になった write で、probe はデータ全体の CRC-32 を crc と比べる。合えばオブジェクトを書き終え、
  completed success で答える。合わなければそのオブジェクトを消し、rejected malformed で答える。size 0 のオブジェクトは、offset 0、len 0 の
  write 1 回で書く。
- **書きかけは 1 つ**: probe が持つ書きかけのオブジェクトは高々 1 つ。別の書き込みを始める write（offset 0）と、そのオブジェクトの delete、
  ロックを持つセッションの終わり（end、期限切れ、force。core §6、§9）は、書きかけのオブジェクトを消す。
- **断り**（何も変えない）:
  - size が max_object より大きい: rejected unsupported（固定部分の値、tag 0x00）。
  - 1 回の write の data が size を越える: rejected malformed。
  - 新しい名前で始める write で、すでに max_objects 個ある: rejected unavailable（cause 2、limit）。
  - 媒体に書けない: completed failed。そのオブジェクトは消えていてよい。
- 1 回の write は、ほかの op と同じに max_op_ms（core §7.5）の中で終える。host は 1 回に送る data を経路の max_frame に合わせて分ける。

### 2.4 delete

- name のオブジェクトを消す。無ければ rejected no_resource。書きかけのオブジェクトの delete は、書きかけを消して completed success。

## 3. 保存と電源断

- メモ欄は再起動（`oep.probe.restart` を含む）と電源断を越えて残る。OEP にメモ欄を消す op は delete のほかに無い。
  firmware の書き直しなど、OEP の外の手段で消えることはある。
- **電源断**: write か delete のどの時点で電源が落ちても、ほかのオブジェクトはそのまま残る。その操作のオブジェクトは、前の完全なもの、
  新しい完全なもの、無いもの、crc がデータと合わないもののどれかになる。probe は書き込みを不可分にしなくてよい（不可分にしてもよい）。
- **crc の合わないオブジェクト**: probe はそれを隠さず、直さず、そのまま list と read に出す。host はデータの CRC-32 が crc と合わないことで
  壊れたことを知り、自分の持つ写しから書き直すか、delete する。
- 消したオブジェクトの場所を使い直せることのほかに、probe は量の管理（使い古しの平準化など）を host に見せない。

## 4. host の使い方（規範ではない）

- 名前は、ほかの道具と重ならないように、道具の名前を前に付ける（`oep-bench/port/x035` など）。
- 同じ内容を書き直さない。list の size と crc が手元の写しと同じなら書かない（媒体の書き換えの回数を減らす）。
- 正しい内容は host の側にも置く。メモ欄は、probe について行く写しである。
