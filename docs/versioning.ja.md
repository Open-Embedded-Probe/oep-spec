# OEP の版と安定性

[English](versioning.md)

状態: **ガイド**（規範ではない）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。何が変わらないかの約束を、core §2.7 と、2026-10-02 に合意した凍結の
範囲から集めた。規則そのものは [OEP core](oep-core.ja.md)（§2.3、§2.5、§2.7、§7.1、§13）と、core と `registry/oep-v1.toml`
の冒頭にあり、このページと食い違えばそちらが正しい。§6 のリリースのタグは決まっている。


## 1. 版を持つもの

| もの | 運ぶ所 | 変わるとき |
|---|---|---|
| **プロトコルの revision** | confirm の revision（u8。v1 = 1）。経路ごとに取り決める（core §7.1） | core の形が変わるとき（core §2.7）。confirm そのもの、その magic、64 byte の決まりは変わらない |
| **インターフェースの revision** | list の fn ごとの revision（u8）と、registry のインターフェースごとの `revision` | インターフェースの固定部分の意味か長さが変わるとき（core §2.7） |
| **インターフェースの名前** | list | インターフェースの意味が変わるとき（名前が違えば別のインターフェース） |
| **registry の schema** | `[registry] schema`（1） | registry のファイルの形が変わるとき（線の上ではない） |
| **REGISTRY_HASH** | 生成したファイル | registry のどこかの byte が変わるとき。生成したコードが registry と合うかを示すだけで、線の上の互換については何も言わない（core の冒頭） |
| **仕様のリリース** | このリポジトリの git のタグ（§6） | 規範の文か registry が変わるとき |

## 2. 凍結の前（今）

OEP v1 は凍結の候補。凍結までは、壊す変更も **どの revision も上げずに** 入れる: 互換を保つ利用者がまだおらず、参照の実装は変更に
すぐ追う。これらの変更に互換や移行の注は書かない。

## 3. 凍結が止めるもの

凍結の後、次のものは revision を上げることでしか変わらない:

- フレームの形: COBS + CRC-16、`length(u16)`、HID の report、見出しの順と長さ、confirm の前の 64 byte（core §3）;
- メッセージの形: 要求 / 応答 / 出来事 / データの固定部分、TLV の形と critical の規則、断りの理由、outcome、断り方の順（core §2、§4）;
- 名前が `oep.` で始まるインターフェースの payload: op の表、固定部分、TLV の tag、出来事、status、資源の寿命（`interfaces/oep-if-*.ja.md`）;
- **`registry/oep-v1.toml` のすべての数**: op、tag、reason、status、enum、`timing`、`limits`、`usb`、インターフェースの名前と revision。
  `[reference]` の表（参照の firmware の値）は凍結の外;
- core、`oep-if-*` の文書、dmseq の規範の文。

固定部分か意味を変えるインターフェースは revision を上げ、core の形の変更はプロトコルの revision を上げる（core §2.7）。

凍結の後も自由なもの: ガイドとその中の参考の数字、記録（追記は自由）、リリースの前の試験、仕様が probe に選び方を任せる所での fake の
動き、各実装の方針と宣言する値。

### 3.1 意図して固定するものと、その理由

次のものは意図して固定し、伸ばさない。理由を崩す使い方があれば、それは凍結の前に直す候補になる。

| 固定するもの | 理由 | もし要るなら |
|---|---|---|
| フレームの見出し（要求 10 byte、応答 5 byte、通知 5 / 6 byte） | 替えるのは本体の revision。confirm で revision を交渉するので将来の道は閉じない | プロトコルの revision |
| COBS + CRC-16 / `length(u16)` / HID report の詰め方 | 経路の種類ごとに決まる | 新しい transport kind が自分の方式を定める |
| op（u8）、TLV の tag（u8、bit 7 critical）、reject reason（u8）、出来事の kind（u8） | 足りなくなったらインターフェースを分ける。空間を広げるより名前で分ける方が host に優しい | 別の名前のインターフェース（別の fn） |
| 並びの要素に len を置かず、固定の形を末尾で延ばさない | どの読み手にも規則は一つ: 要素の形は revision で決まる。足すものは TLV で、要素についての情報は、その要素の番号を持つ応答の TLV に入れる | TLV、revision |
| 応答の固定部 | 固定部を変えるのは revision と新しい fn。足すものは TLV（伸ばし方は 1 つ） | TLV、revision |
| 線の試験（`oep.probe.link` の source / sink）の意味 | 線の試験のためにある。意味を足す理由が無い | — |
| confirm の前の 64 byte | 交渉の前の約束。小さいほど安全 | — |
| probe.config の項目のキー（slot u8、port u8、fn u16、channel u16） | 1 台の probe の中の数。u8 / u16 で足りる | — |
| confirm に host の受けの上限を入れない | 応答の量は host が同時に出す要求の数で、通知の量は min_bytes で決める。probe が host の上限を知っても使い道が無い（通知に ack が無い） | confirm の非 critical の要求 TLV を後から |
| max_frame は両方向の上限 | シリアルの口の受けの問題は 1 フレームではなく burst の量（transports §4 の host の規則） | — |
| DFU / firmware の更新は OEP の外（core §0） | USB の記述子にすべてある。OEP が写しを持つと版ごとに食い違う。unit_id = USB の serial は変わらないので、焼く側は個体を見失わない | `oep.probe.firmware` のような名前つきのインターフェース |
| read_block に `max_count` の宣言や専用の理由を足さない | max_length（byte）で表せる。断りは unsupported | address_hi は予約（RV64） |
| port_speed で probe は速さの候補を宣言しない | 通る速さは host 側の変換チップで決まり、probe からは見えない。候補は host の表 | 「試した結果」を運ぶ要求 TLV を後から |
| ブリッジの実際の baud（整数分周のずれ）は出さない | host 側の性質で probe は知れない。応答の baud（probe の UART の実際の値）で足りる | — |
| block の転送をまとめる op（system bus のまとめ読みなど）は足さない | read_block の意味は「target のバスを通して読む」で、手段は probe が選ぶ | riscv-dm の features ビットと op 0x09〜 |
| 予約の番号: 長い操作、role 0x03 / 0x04、u32 の番地の dmi の step、reset の method 2、swd の 0x04 attach_under_reset、capture の 0x40 以降の値 | 使う実例が無いまま形を決めない | 予約の番号に後から定める |

## 4. revision を変えずに足せるもの

凍結の後の OEP の伸び方はこれだけである（core §2.3）。これらを足しても、どの revision も変わらない。それを知らない host や probe は動き続ける（core §2.7）:

| 道 | 決まり |
|---|---|
| 任意の要求 / 応答 / 出来事の TLV | op の文脈の新しい tag。host は知らない非 critical の tag を読み飛ばし、probe は知らない critical の tag を unsupported で断る（core §2.2、§2.3） |
| 任意の op と出来事 | インターフェースの op 0x01〜0xEF、出来事の kind 0x01〜0x7F。あるかどうかは describe で宣言する（core §2.5、§2.7） |
| 新しい enum の値と予約の bit | 要求では: 定義が使っていなかった値は、それを知らない probe が unsupported で断る（core §2.5、§4.3 の順 6）。応答、出来事、データでは: どのフィールドのあるなし、長さ、位置もその値に依らず、core §2.4 の知らない値の扱いが安全で、意味がその値に依るフィールドはどれも、その値を知らない読み手が無視するか生のまま見せるときだけ足せる（core §2.5）。そうでなければ新しい TLV、revision、インターフェース |
| インターフェースの断りの理由と status の値 | 0x40〜0x7F（core §2.5、common §3） |
| describe の tag | 共通 0x01〜0x3E、インターフェース 0x40〜0x7F。どの固定の形とも同じく、describe の値は延ばさない（core §2.3、§7.4） |
| probe.config の項目と線の名前 | 新しい項目の tag（項目の形は固定）。標準の線の名前は registry に（probe の設定 §1、§1.3） |
| 新しいインターフェース | `oep.` の名前はこのリポジトリを通して。逆 DNS の名前は誰でも登録なしに（core §13） |
| 新しい経路 | フレームの方式と一緒に新しい transport の kind を（transports §1） |

インターフェースの revision を上げる probe は、できれば古い revision も別の fn で出し続ける（core §2.7）。古い host が動き続けるように。

## 5. registry の約束

- 凍結の後、**キーは名前を変えず、消さない**。新しいキーを足す（core の冒頭、registry の冒頭）。生成した識別子はキーから作るので、
  それを使うコードはそのまま通る。
- キーの値は変わらない（凍結した数、§3）。実験用の値（u8 の enum の 0xF0〜0xFE、op の 0xF0〜0xFF）は登録しない（core §2.5）。
- 新しい表の種類や、インターフェースや op の新しいキーは、pull request による registry の変更（CONTRIBUTING）。

## 6. 仕様のリリース

- このリポジトリに **git のタグ `vMAJOR.MINOR.PATCH`** を付け、指す commit と一緒に push する。
  - MAJOR は、正式リリースからはプロトコルの revision（プロトコルの revision 1 は `v1.y.z`）。その前は 0。
  - MINOR は §4 の追加、新しいインターフェースか新しいインターフェースの revision、registry への追加で増える。
  - PATCH は振る舞いを変えない errata で増える: 文言、訳、ガイド、記録、道具。
- **正式リリースの前のタグは `v0.MINOR.PATCH`**（レビューのためでも凍結でも同じ）。凍結は、CHANGELOG が凍結と書く `v0` のタグで、`v1` では
  ない。**`v1.0.0` は正式リリース**で、そこから MAJOR はプロトコルの revision に従う。
- **凍結の前は、revision 1 だけでは形が一つに決まらない**: 壊す変更は revision を上げずに入る（§2）ので、違う commit から作った 2 つの実装が
  どちらも revision 1 と言いながら、つながらないことがある。だから実装は、自分が実装する仕様のタグを示す。
- タグは、`python3 tools/oepgen1.py --check` と `python3 tools/oepvectors1.py --check` が通り、`cd tests && uv run pytest registry_v1 vectors`
  が通る commit にだけ付ける。
- 根の **CHANGELOG.md** にリリースごとの変更（日付、タグ、commit）を並べ、次のタグまでの変更は「Unreleased」の節に集める。規範の文か
  registry の変更はすべて項を持つ。文言だけの変更はまとめてよい。
- 実装は、実装したタグを（README に）、扱うプロトコルとインターフェースの revision と一緒に書く。probe は、
  fn 0 の describe の `firmware`（0x40）の自由な文にもタグを入れてよい。host が食い違いを調べるときに見せられるように。
- **線の上にも registry にも edition のフィールドは無い。** 凍結の後は revision だけが形を決めるので、そうしたフィールドは
  プロトコルの寿命の間ずっと意味を持たない。凍結の前は、`firmware` の自由な文が調べるためのタグをもう運んでいる。

## 7. 凍結の後の errata

文言だけを直す errata は PATCH。振る舞いを変えるものは規則の変更で、上の revision の決まりと [CONTRIBUTING](../CONTRIBUTING.ja.md) に従う。
