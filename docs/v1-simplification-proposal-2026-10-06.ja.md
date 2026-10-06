# OEP v1 単純化の提案（2026-10-06）

[English](v1-simplification-proposal-2026-10-06.md)

Status: **提案**（規範ではない）。[2026-10-06 の外部レビュー](external-spec-review-2026-10-06.ja.md)に項目ごとに答え、規範文書と registry への変更を提案する。ユーザーが決め、`docs/oep-*.md` と `registry/oep-v1.toml` に変更が入るまで、ここに書いたことは効力を持たない。英語版が正であり、この日本語版はその翻訳である。

## 0. 要約

レビューは参考であって指示の一覧ではない。OEP を小さく単純にしつつ拡張できるままにするものを採り、相互運用上の明らかな利点なしに仕組みを増やすものは採らない。freeze 前は破壊的変更をしてよい（revision は上げない。versioning §2）。

番号: 「レビュー 5.1」はレビューの項目を指す。この文書の節は、レビュー §3 に 2.x で、レビュー §4.2 に 3.1 で、レビュー §5 に 4.x で、レビュー §7 / §8 に 6.x で答える（レビュー 5.1 には 4.1 で、レビュー 5.2 には 4.2 で答える、以下同じ）。

目標を一文で言うと（レビュアーの言葉）: **固定形式は revision で守り、互換追加は TLV、意味が違うものは別 interface。**

| レビューの項目 | 推奨 | wire の変更 | 破壊的 |
|---|---|---|---|
| 3.1 answer の sequence の len と op 表の食い違い | 採る（5.1 を通して）: element の len をどこにも置かない。規則は `count × element` の一つ | あり | あり |
| 3.2 SDI / DMDATA の「(Reference)」 | 採る: そのまま規範とし、由来の注を消す（debug の一つも） | なし | なし |
| 3.3 freeze 前の revision 1 | 一部採る: versioning §6 を決め、tag を明記する。実行時の edition 欄は置かない | なし | なし |
| 3.4 HID の再構成 | 採る: 一本の byte stream、count 0、padding、report ID、途切れの規則 | なし | なし |
| 3.5 外部仕様 | 採る: interface ごとの参照一覧。「文書だけで」の範囲を明記する | なし | なし |
| 3.6 answer の enum の追加 | 一部採る: 3 つの条件。capability による opt-in は置かない | なし | なし |
| 3.7 probe.config の paging の文 | 採る（文言） | なし | なし |
| 3.8 候補の無い scan | 採る: completed success、tried 0、count 0 | なし | なし |
| 4.2 interface のテンプレート | 一部採る: いま core §13 にチェックリスト、テンプレートの手引きは後で | なし | なし |
| 5.1 拡張の道を 4 つに限る | 採る。末尾の省略可能な欄は固定部に入れる | あり | あり |
| 5.2 end 後の resource を残さない、resume を無くす | 採る | あり | あり |
| 5.3 request header を一つに | 一部採る: session_id（0 = なし）を持つ 10 byte の header 一つ。corr は u16 のまま | あり | あり |
| 5.4 TLV header を一つに | 採る: `tag(u8), len(u16), value` | あり | あり |
| 5.5 optional op の宣言を共通に | 採る: describe の共通 tag `ops`（base + bitmap）を全 fn に | あり | あり |
| 5.6 core と transport の分離 | 採る: 3 つのファイル。link test と port_speed を `oep.link` へ移す（ユーザーの判断 D3） | あり（D3） | あり（D3） |
| §7 試験の不足 | 一部採る: op ごとの byte vector と session / resend / paging のシナリオ。timing と電気は release 試験のまま | なし | なし |
| §8 優先順位 | 順序を採る。3 項目を freeze 前へ移し、corr u32 は採らない（6.2） | — | — |

## 1. すべての項目に共通の前提

- **利用者は誰か。** 不特定多数の利用者が必要とするもので判断する: 文書だけから host や probe を書く第三者、CLI のコマンドを一つずつ実行する利用者、操作ごとにツールを起動する IDE、無人で動く試験治具。いまの bench は入力であって、目標ではない。
- **freeze の方針。** v1 freeze 前は、破壊的変更を revision を上げずに入れ、互換や移行の注は書かない（versioning §2）。freeze 後は形式が固定され、4.1 の道だけが残る。
- **仕様に従う実装**: oep-probe-arduino（参照 probe）、oep-client-python とその fake probe、oep-client-js、ch32rv（`crates/oep` の Rust host、CLI、`cli/src/broker.rs` の中継ブローカー、`cli/src/broker_wch.rs` の WCH-Link の endpoint。これは自分で OEP に答えるので core §3.1 により probe である）、WireSkein（Python client を使う）、bench（client を使い、その probe は保存した設定を持つ）。
- **作業の順序**は変えない: 仕様、peer による差分のレビュー、fake、probe、client。
- **UART bridge 上の byte** は §5 で数える。どの単純化も、起動時の速度 115200 bps での帯域と比べて判断するためである。

## 2. 相互運用性の項目（レビュー §3）

### 2.1 レビュー 3.1: answer の sequence、len を置くか置かないか

**前提。** core §2.3 は、answer の sequence の各 element の前に長さを置くと定めている: `count(u8), count × (len(u8), element)`。len は、後の版が element の末尾に欄を足し、古い reader がそれを読み飛ばせるようにするためにある（§2.3 の「末尾に追加する」道）。op 表が len を使うのは構造を持つ element（list の entry、connections の entry、scan の entry、mark、console の streams、capture の segment、probe.config の slot_state と bind_state、bind の項目）だけで、scalar の配列（gpio read の level、dmi と arm-adi transfer の value、read_block の word、run の value）には使わない。core を先に読んだ第三者は scalar の配列にも len を付け、既存のどの実装とも話せなくなる。既存の実装は op 表に従っているので、いま壊れるものは無い。危険はこれから書かれるすべての実装にある。

**推奨: 採る（レビュー 5.1、ここでの 4.1 を通して）。** element の len をすべて取り除き、すべての sequence を一つの規則で表す: `count, count × element`。element の形は revision で固定する。構造を持つ element はどれもすでに自分で終わりがわかる（可変部は自分の長さを持つ）ので、末尾を延ばさないなら len が運ぶ情報は無い。これで食い違いと拡張の道の一つが同時に消える。

レビュー 5.1 を採らない場合の最小の修正は文言だけである: core §2.3 で、len が element の前に置かれるのは op 表が `(len(u8), …)` と書くところだけだと述べる。

**変更。** 新しい配置は 4.1 にある。破壊的: あり（list、connections、scan、marks、streams、segments、probe.config state の answer と、bind の項目）。影響: 4.1 のとおり。

### 2.2 レビュー 3.2: SDI と DMDATA は規範である

**前提。** core §1.1 は (Informative)、例、注を規範でないと定めている。console §3.1 と §3.2 は「(Reference) This is the layout of WCH's SDI printf」と「(Reference) This is the framing the minichlink tool uses」で始まり、この印は core に定義が無い。日本語訳はどちらも （参考） と書き、日本語の core §1.1 は （参考） を規範でないと定めているので、日本語では mechanism 0 と 1 の唯一の定義が規範でないと読める。同じ印が debug の冒頭にもある（「(Reference) RVSWD and SWIO are the 2-wire and 1-wire debug wires of WCH's RISC-V MCUs…」の行）。私たち自身の書き方の決まりも、規範の文にチップ名やツール名を書かない。

**推奨: 採る。** mechanism 0 と 1 の定義は、書いてあるとおり規範である。console の由来の 2 文と debug の 1 文を消す（実装に経緯は要らず、経緯は記録に残っている）。registry のキー `wch_dmi_7f` はそのままにする: これは識別子であり、本文は DMI 0x7F の u32 と定義している。

私たちの読みでは、§3.1 と §3.2 はすでに両側（target が何を書くか、probe が何をいつ読み書きするか）を定めている。peer には、実装の中に本文の外から来たものが無いかを確かめてもらう。

**変更。** 文言だけ: console §3.1、§3.2 と debug の冒頭の行、英語と日本語。破壊的でない。影響: コードは無い。

### 2.3 レビュー 3.3: 「revision 1」の 2 実装が相互に動かないことがある

**前提。** freeze 前は、破壊的変更を revision を上げずに入れる（ユーザーの決定）ので、別の commit から作った 2 つの実装がどちらも revision 1 を名乗り、しかも相互に動かないことがある。versioning §6 は tag を提案している。ユーザーは 2026-10-06 に、仕様の tag は freeze まで `v0.x` のままで、`v1.0.0` を正式リリースとすると決めた。

**推奨: 一部採る。**
- versioning §6 を提案から決定に変える: 正式リリースまでの tag は `v0.MINOR.PATCH`、freeze は CHANGELOG が freeze と名指す `v0` の tag、`v1.0.0` が正式リリース。tag は生成器と vector が通る commit にだけ付ける。規範文書か registry の変更にはすべて CHANGELOG の項目を付ける。
- すべての規範文書の status 行に一文を足す: 「freeze 前は revision 1 だけでは形式が決まらない。実装は自分が実装する仕様の tag を名乗る。」
- 各実装は README に tag を書き、probe は fn 0 の describe の `firmware`（0x40）の自由な text にも書いてよい。
- 実行時の edition 欄（registry か confirm に）は**採らない**: freeze 後は revision だけが形式を決めるので、この欄はプロトコルの寿命のあいだ何も意味しない。freeze 前の診断には、自由な text がすでに tag を運べる。

**変更。** 文言: versioning §6、status 行、各実装の README。破壊的でない。影響: すべてのリポジトリの README の行。probe と broker_wch の firmware の text は任意。

### 2.4 レビュー 3.4: HID の再構成

**前提。** core §3.1 は、length-prefixed frame の byte を `count(u16)`、count byte、0 の padding からなる report に詰めることと、report が運べるより大きい count の report は捨てることを定めている。frame が report をまたいでよいか、1 report に複数の frame を入れてよいか、count 0 の意味、0 でない padding を受けた側がどうするか、どの report ID を使うか、frame が途中で止まったらどうするかは書いていない。Python client（`hid_stream.py`）と ch32rv（`crates/oep/src/hid.rs`）は、すでに report を一本の stream として扱っている。

**推奨: 採る**（文言だけ）。HID の行を置き換え、次を足す:

1. report の OEP の byte は、count の後の count byte である。それを方向ごとに report の順につなげると一本の length-prefixed byte stream になり、vendor bulk の stream と同じである。
2. frame は report をまたいでよく、1 つの report が 1 つの frame の終わりと次の frame の始まりを持ってよい。送る側は frame ごとに新しい report から始めてもよいが、受ける側はそれを当てにしない。
3. count 0 の report は空であり、読み飛ばす。
4. 送る側は padding を 0 にする。受ける側は padding をその値にかかわらず無視する。
5. OEP の HID interface は report ID を宣言しないか、入力 report と出力 report が使う report ID を 1 つ宣言する。宣言したときは、両方向のすべての report がその ID で始まり、count はその後から数える。受ける側は別の ID で始まる report を捨てる。
6. §3.2 の途切れの規則は stream に適用する: frame が途中のまま 200 ms（`probe_frame_gap_ms`）report が来なければ、probe はその途中の frame を捨て、次の byte を長さの始まりとして読む。host は §5.1 で回復する。
7. report が運べるより大きい count の report は捨て、受ける側は stream が壊れたものとして扱う: max_frame より大きい長さのときと同じく、200 ms の途切れまで入力を捨てる。

**変更。** 文言だけ（transport の文書の HID の部分、4.6）。破壊的でない。影響: probe（HID を出すなら）、Python client、ch32rv がこのとおり動くかを確かめる。変更は無い見込み。

### 2.5 レビュー 3.5: 外部仕様

**前提。** OEP の message はこのリポジトリだけから実装できる。target を動かすことはできない: swd と arm-adi は Arm Debug Interface に、riscv-dm と wire は RISC-V の debug 仕様に、i2c-target は I2C-bus 仕様に頼る。本文はそのいくつかを版なしで名指している。fixture の spi-target は「SPI mode 0 to 3」と書くが mode を定義していない（この項目を確かめるうちに見つけた同じ種類の不足）。

**推奨: 採る**（文言だけ）。
- core §0 に書く: 「OEP のプロトコルはこれらの文書だけで定まる。target を動かすには、各 interface の文書が挙げる外部仕様も要る。」
- 各 interface の文書に短い「参照」の節を置き、文書名、版、使う部分を挙げる。案（版は編集者が確かめる）:

| interface | 外部仕様 | 使う部分 |
|---|---|---|
| `oep.wire.swd`、`oep.target.arm-adi` | Arm Debug Interface Architecture Specification ADIv5.2 と ADIv6.0 | SWD の packet、turnaround、line reset、JTAG から SWD への切り替え、dormant からの起こし、TARGETSEL。DP / AP のレジスタ。MEM-AP の TAR / DRW / CSW |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.target.riscv-dm`、`oep.target.console` | RISC-V Debug Specification 0.13.2 と 1.0（DMSTATUS.version 2 と 3） | DMI のレジスタ、abstract command、program buffer、dcsr、havereset。wire の frame そのものは本文で定める |
| `oep.fixture.i2c-target` | I2C-bus 仕様（UM10204） | アドレス、ACK、clock stretching、予約アドレス |
| `oep.fixture.spi-target` | なし（正式な標準が無い） | mode を本文で定める: mode = CPOL × 2 + CPHA |
| core の transport | USB 2.0、USB CDC ACM、HID 1.11、Microsoft OS 2.0 descriptor | 列挙、interface descriptor、report |

**変更。** 文言だけ。破壊的でない。影響: コードは無い。

### 2.6 レビュー 3.6: revision なしで足される answer の enum の値

**前提。** core §2.5 は、使われていない enum の値と予約 bit を後で定義してよいとしている。request ならこれは安全である: 古い probe はその値を unsupported で断る。answer では、古い host が知らない値を受け取る。core §2.4 は、知らない status、reason、outcome を失敗として扱い、ほかの enum を unknown と表示するよう host に求めている。それが安全なのは、知らない値が answer の残りの読み方を変えないときだけである。

**推奨: 一部採る。** answer の enum に revision なしで値を足してよいのは、次の 3 つがすべて成り立つときだけである:
1. どの欄の有無、長さ、位置もその値によらない。
2. core §2.4 の扱い（outcome、status、reason は失敗、ほかは「unknown」）が安全である。
3. 意味がその値による欄はどれも、その値を知らない reader が無視する（または生の値のまま表示する）と定義されている。

それ以外の追加は、新しい TLV、新しい revision、新しい interface にする。capability による opt-in は**採らない**: request はすでに opt-in である（host がその値を送ると選ぶ）。answer では条件 2 で扱いが安全になる。値ごとの宣言は、すべての interface に仕組みを増やす。v1 の answer の enum はすでにどれも 3 つの条件を満たしている（scan の kind が決めるのは id の意味だけ、mark の kind は detail の意味だけ、tid_scheme は tid の意味だけで、tid の長さは tid_len が運ぶ）。

**変更。** 文言: core §2.4 / §2.5（4.1 とともに）、versioning §4。破壊的でない。影響: コードは無い。

### 2.7 レビュー 3.7: probe.config の paging の文

**前提。** probe 設定の §3.3 は「… a host that needs the set of slots and binds to stay the same across its pages pages while it holds the lock …」で終わり、動詞が欠けている。

**推奨: 採る**（文言）: 「page をまたいで slot と bind の集合が変わらないことを要する host は、lock を持ったまま全部の page を読む（slot の状態は変わりうる）。」lock を持てば足りる: set、unset、save、erase ができるのは持ち主だけで、自動の attach が変えるのは状態であって集合ではない。文言だけ。破壊的でない。コードは無い。

### 2.8 レビュー 3.8: 候補の無い scan

**前提。** debug §1 は「少なくとも 1 つの組み合わせを試す」と「tried = 0 は sequence を使い切ったときだけ」と書く。count = 0 の sequence が最初から空のとき（どの候補も保持されている、disable されている、idle の項目がある、または skip がその長さ以上）に何が起きるかは書いていない。

**推奨: 採る。** 次を足す: 「count = 0 の sequence に skip 以降の組み合わせが無いとき（空であるか、skip がその長さ以上）、answer は completed success で tried = 0、count = 0 である。少なくとも 1 つ試すという規則は、組み合わせが残っているときだけに適用する。」これは host の続きの loop がすでに止まる answer であり、新しい拒否は要らない。組み合わせを並べた request は変わらない（保持された channel は rejected unavailable）。

**変更。** 文言だけ。破壊的でない。影響: probe と fake がこのとおり答える（断らない）かを確かめる。host は何も要らない。

## 3. 拡張性（レビュー §4.2）

### 3.1 レビュー 4.2: interface のテンプレート

**前提。** core §13 の規則 2 は interface の定義が決めることを挙げているが、その interface 固有の status の値、completed failed と partial の payload、知らない enum の値と flag の扱い、§4.3 の順の拒否の表は挙げていない。レビュアーはいま拡張の道を 9 つ数えている。5.1 でそれが減る。

**推奨: 一部採る。** core §13 の規則 2 を、すべての interface の文書が埋めるチェックリストに広げる: name と revision。op 表（request、answer、lock、必須か optional か。optional op は `ops` tag で宣言する、5.5）。op ごとの request と answer の TLV。completed success、failed、partial の payload。interface の status の値（0x40〜0x7F）と拒否理由（0x40〜0x7F）。resource とその寿命。event と data の payload。reader が知らない enum の値と flag をどう扱うか（2.6）。§4.3 の順の拒否の表。テンプレートの文書（見出しだけの手引き）は freeze 後でよい。それは規則を足さない。

**変更。** 文言: core §13。破壊的でない。影響: コードは無い。既存の interface の文書をこの一覧で点検する。

## 4. 単純化（レビュー §5）

### 4.1 レビュー 5.1: 拡張の道を 4 つだけにする

**前提。** いま reader は、前方互換の規則をいくつも実装している: answer の TLV の値、event の固定 payload、answer の sequence の element、probe.config の項目の、知らない末尾を読み飛ばすこと、項目の知らない末尾を切らずに保つこと。一方で describe の値、request の TLV の値、link test の answer は閉じた例外である。末尾の道は、小さな版が TLV header の 2〜3 byte なしで欄を足せるように選んだ。freeze がまだ無いので、freeze 後にこの道で足されたものは一つも無い。つまりそれに頼るものは無く、すべての reader がいまその代価を払っている。

**推奨: 採る。** freeze 後に OEP が伸びるのは次だけである:
1. **新しい TLV**（request、answer、event、data、describe の中、または probe.config の新しい項目の tag）。
2. **新しい optional op**（`ops` で宣言する、5.5）または新しい event の kind。
3. **予約された空間の新しい値**（古い probe が unsupported で断る request の値。answer の値は 2.6 の条件のときだけ）。
4. 新しい意味には**新しい interface name**、固定形式を変えるなら**新しい revision**。

すべての固定形式（request、answer、event、data の payload の固定部、TLV の値、sequence の element、probe.config の項目）は (name, revision) で固定する。sequence の element の末尾に足したかった情報は、element の index を付けて繰り返す answer の TLV に入れる（gpio の drive TLV がすでに使っている形）。

**freeze 前に足された末尾の省略可能な欄は、固定部に入れる。** それらは revision 1 の一部で、いま分かっている。probe.config の項目（それ自体が TLV）の中に TLV を入れると入れ子が要る。固定長なら正規形が一つに決まる。いまは、boot_reset 0 を付けて送った slot と付けずに送った同じ slot は同じ設定なのに、probe が送られたままの byte を保つので、hash が 2 通りになる。探索（「optional trailing」、`[…]` の欄、「後で足す欄の場所」）で見つかるのは 3 つである: slot の `boot_reset`、idle の `drive_kind`、`drive_value`、slot_state の `reset_at_ns`（常にあるが、末尾として足された）。

**新しい配置の正確な形。**

```text
core list answer:        total(u16), count(u8), count × entry
  entry:                 fn(u16), instance(u16), revision(u8), flags(u8), name_len(u8), name
wire connections answer: more(u8), count(u8), count × entry, [TLV]
  entry:                 connection(u16), swdio(u16), swclk(u16), speed_hz(u32), users(u8), slot(u8), tid_scheme(u8), tid_len(u8), tid
wire scan answer:        tried(u8), count(u8), count × (kind(u8), swdio(u16), swclk(u16), id(u32)), [TLV]      element 9 byte
marks answer:            more(u8), count(u8), count × mark, [TLV]                                               mark 22 byte、変更なし
console streams answer:  more(u8), count(u8), count × (stream(u16), connection(u16), mechanism(u8), users(u8), state(u8)), [TLV]
capture segments answer: more(u8), count(u8), count × segment, [TLV]                                            segment 37 byte、変更なし
probe.config state answer:
                         more(u8), storage_state(u8), storage_hash(u32), unreadable_reason(u8),
                         n_slots(u8), n_slots × slot_state, n_binds(u8), n_binds × bind_state, [TLV]
  slot_state:            slot(u8), state(u8), connection(u16), last_try_at_ns(u64), reset_at_ns(u64), tid_scheme(u8), tid_len(u8), tid
  bind_state:            port(u8), mode(u8), selected(u8), flow(u8)
probe.config items:
  idle (0x03):           channel(u16), mode(u8), drive_kind(u8), drive_value(u16)                               6 byte
  slot (0x04):           slot(u8), wire_fn(u16), swdio(u16), swclk(u16), attach(u8), boot_reset(u8), retry_ms(u32),
                         max_speed_hz(u32), idle_clock(u8), mechanism(u8), name_len(u8), name,
                         lock_len(u8), [lock_scheme(u8), lock_mask(n), lock_value(n)]    （lock_len > 0 のとき lock の部分がある）
  bind (0x05):           port(u8), mode(u8), selected(u8), n(u8), n × (kind(u8), id(u16))
unset request:           変更なし: n(u8), n × (len(u8), tag(u8), key)   （len は可変長の key の長さで、末尾ではない）
```

- idle: `drive_kind` 0 = level、1 = mA の上限、**2 = 既定**（drive_levels の既定の level。drive_value は 0）。mode 0〜2 は kind 2 と value 0 を運ぶ（それ以外は malformed）。値 2 は共有の `drive_kind` enum に足すので、gpio set の drive TLV でも既定の level を明示できる。drive_levels を持たない probe は、いまと同じくこの欄を保ち、既定を使う。
- slot: `boot_reset` を `attach` の隣へ移す（固定の欄を可変の欄より前に）。0 なし、1 あり。2 以上は malformed、host の slot で 1 も malformed（いまと同じ）。
- slot_state: `reset_at_ns` を可変の `tid` の前へ移す。
- 「probe は項目の byte を送られたまま、知らない末尾の欄も含めて保つ」という規則は取り除く: 項目は tag ごとに一つの形を持ち、それより長い値は、知っているより長い request の TLV である（core §2.3）。
- link test に数を持つ形を与え、§2.3 の例外（「長さの無い可変部で終わる形」）と registry のキー `closed_tail` を無くす: `link_source` の answer は `len(u16), data, [TLV]`（byte k は k & 0xFF、収まるだけ）。`link_sink` の request は `count(u16), data`、answer は空（count が payload と合わなければ malformed）。

**文言と registry。** core §2.3 を 4 つの道を軸に書き直す（「固定形式の延ばし方」の段落と describe の例外は消える）。§2.4 / §2.5 に 2.6 の条件を入れる。§2.7 から「末尾への追加は revision を変えない」を消す。versioning §3.1 / §4 も合わせる。registry: `closed_tail` を schema と fn 0 から取り除く。`drive_kind` に `default = 2` を足す。`idle`、`slot`、`slot_boot_reset` のコメントを合わせる。破壊的: あり。

**影響。**
- oep-probe-arduino: list、connections、scan、marks、streams、segments、state の encoder が len を落とす。idle、slot、bind の parser が固定の形を読む。保存した設定の配置が変わるので、更新後は保存した設定が読めない（reason 1）と出て、入れ直す。
- oep-client-python と fake: 同じ decoder と encoder。probe.config の hash の vector を作り直す。
- oep-client-js: 同じ decoder。
- ch32rv: `crates/oep`（config.rs はいま reset_at_ns を読まずに slot_state を読み、末尾を len で読み飛ばしている。これからは tid の前でその欄を読む。connections、scan、marks には target.rs と stream.rs）。broker_wch の同じ answer の encoder。
- WireSkein: 直接は無い（segment は client を通して読む）。
- bench: 書き込み直し、設定を入れ直して保存する。

### 4.2 レビュー 5.2: end 後の resource を残さない、暗黙の resume を無くす

**前提。** いま（core §6.2、§6.4、§9）、`end` は lock を放すが、session の resource（plan、connection と stream の持ち分）は残す。それは id にかかわらず、次に open した session に移る。end 後に最後の session_id を持つ通常の request が来ると lock を取り直す（resume）。その id の `open` は resumed 1 を返す。lease が切れると resource は取り除かれ、request は `expired` で断られ、その id の open は resumed 2 を返す。そのため probe は、最後の session_id、その lock の終わり方、その owner、resend の表を保ち、判断表は 10 行ある。core と console §2 にある理由: 1 コマンド 1 プロセスの host（ch32rv の CLI）が、前のプロセスが止まったところから次のプロセスで続けられるようにするため。

実装が実際に頼っているもの:
- **id による resume**: Python client の `open(session=…)` は「保存した id で再開する一回きりの CLI」のためにあるが、渡す呼び出し元は無い（その CLI にも、WireSkein にも、ch32rv にも）。ch32rv はコマンドごとに新しい乱数の id で開く。
- **end 後の引き継ぎ**: ch32rv の `flash` は detach せずに end する（「connection は次の open のために残る」）。そのため次のコマンドの attach は、新しく立ち上げる代わりに生きている connection に加わる（flags bit1）。ほかのコマンドは end の前に detach する。
- **expired / resumed 2**: ch32rv のブローカーは、`expired` の後は同じ id で開き直し、`no_session` の後は新しい id で開く。どちらも同じ行動（開き直して作り直す）になる。
- WireSkein は end の前に plan を放し、何にも頼っていない。

**一般の利用者の場合。** 利用者の 2 つのコマンドのあいだで何が残らねばならず、引き継ぎなしでどう残るか:
- target の状態（止まっているか走っているか）: connection を閉じても target は変わらない（debug §2）ので、どのみち残る。
- console の出力: stream の位置と mark は boot のあいだ戻らず、同じ場所の open は同じ stream 番号を返す（console §2）ので、後のコマンドは前のコマンドが止まったところから読める。どのコマンドも動いていないあいだに target を読むのは、probe が持つ、bind 付きの slot の役目である。
- 駆動し続けねばならない pin（電源のスイッチ）: probe が持つ、設定の plan と出力の idle。
- 速い attach: 失われる。slot が connection を保たない限り、コマンドごとに立ち上げ直す（最大 `attach_budget_ms`、1000 ms）。

引き継ぎには一般の利用者にとっての代価もある: 落ちた host や不注意な host が end 後に残したもの（pin を駆動する plan、止まった connection）は、それを作っていない無関係な次の host のものに黙ってなる。end で放せば、残るのは設定が定めるものだけで、どの host も get と state で読める。

**レビュアーの代案は、resume の仕組みなしに 1 コマンド 1 プロセスの host に役立つか。役立つ。** 明示の道はすでにある: 生きている組み合わせへの attach はその connection を返し（flags bit1）、console の open は既存の stream を返す（flags bit0）。slot が使う connection はどの end の後も残るので、コマンドをまたいで速い attach が欲しい利用者は slot を登録する。ch32rv の `flash` が失うのは、省いていた立ち上げだけである。

**推奨: 採る。** probe が持つ resource は設定のもの（plan、idle、slot、bind）である。session が作ったものはすべて、何がその lock を終わらせたかにかかわらず、lock が終わるときに放す。

**変更。**
- `open` の answer: `lease_ms(u32), boot_id(u32), [TLV]`（resumed を取り除く）。
- `end`、lease の期限切れ、force は同じものを放す: session の plan（pin は idle へ）、connection と stream の持ち分（使うものが残らなければ resource は閉じる）、subscription。debug §2 の状態機械は、end の行と lease の期限切れ / force の行を一つにする。common §2 と console §2 は「session が終わるとき」と書く。
- 拒否理由 `expired`（0x0E）は予約にする。lock が空いているときに、持ち主のでない session_id の request は `no_session` で断る。host は開き直す。
- resend の表（§5.2）は最後の session の id をキーにしたまま、次に open が成功したときに捨てる。そのため再送した `end` にも表から答えられる。
- §6.2 の判断（resend の表の後）:

| lock | request | 結果 |
|---|---|---|
| 空き | open（session_id ≠ 0、force の有無を問わない） | lock を確立する |
| 空き | session_id ≠ 0 のほかの request | rejected no_session |
| S が保持 | session_id S の open | lease を始め直す。何も取り除かない。通知はこの transport へ（再送された open） |
| S が保持 | 別の id の open、force なし | rejected locked（残り時間、owner） |
| S が保持 | 別の id の open、force あり | S の resource を放し（§9）、lock を確立する |
| S が保持 | S のほかの request | 処理する |
| S が保持 | 別の id のほかの request | rejected locked |

- owner は lock が保持されているあいだ保つ。
- core §6.5 から「最後の id の open が resumed 0 を返したら再起動」という推論を取り除く。host は open の answer の boot_id に頼る（弱い boot_id の源しか持たない probe は、書いてある確率をそのまま持つ）。
- mark の detail closed 2 は「session が終わった（end、lease の期限切れ、force）」になる。
- registry: core の enum `resumed` を取り除く。`expired` → 予約。`mark_detail_closed` の 2 を `session_ended` と改名する。
- 文言: core §6.2、§6.4、§6.5、§9。common §2。console §2。debug §2。host ガイド §6 と §9。conformance。

破壊的: あり。

**影響。**
- oep-probe-arduino: endpoint が単純になる（swept / expired / resume の道が消え、end は lease 切れと同じ解放を呼ぶ）。
- oep-client-python と fake: `Opened.resumed`、`Expired`、`open(session=…)` が消える。fake も合わせる。
- oep-client-js: 同じ。
- ch32rv: session.rs（resumed / swept）、broker.rs（keepalive の `expired` の道は、新しい id で開く `no_session` の道に合流する。ブローカー自身の open の answer は resumed の byte を落とす）、CLI の `flash`（どのコマンドも attach し直す）。
- WireSkein: 無い（docstring の一つが Expired を名指すだけ）。
- bench: プロセスをまたいで plan や connection が残ることに頼る script があるかを尋ねる。

### 4.3 レビュー 5.3: request header を一つにする

**前提。** いま request は `role 0x01, corr(u16), fn(u16), op(u8)`（6 byte）か、role の bit 7 を立てて同じものの後に session_id(u32) を続けたもの（10 byte）である。`open` だけは session_id を payload に持ち、role 0x01 で送る。2 つの形は lock の要らない request（monitor による console の poll、discovery）で 4 byte を省く。corr は u16 で、表がもう持っていない古い request と再送を見分けるため、通し番号の算術（§2.6）で比べる。

**推奨: 一部採る。** すべての request に一つの header を使い、session_id を常に置く（0 = session なし）。corr は u16 のままにする。

```text
request   role=0x01 | corr(u16) | fn(u16) | op(u8) | session_id(u32) | payload        header 10 byte
answer    role=0x02 | corr(u16) | resolution(u8) | detail(u8) | payload             header 5 byte（変更なし）
event     role=0x05 | fn(u16) | seq(u16) | kind(u8) | fixed part | [TLV]               変更なし
data      role=0x06 | fn(u16) | seq(u16) | position(u64) | len(u16) | data | [TLV]    変更なし
open      request の payload: lease_ms(u32), force(u8), [TLV owner]   （session_id は header のもの。0 は malformed）
          answer: lease_ms(u32), boot_id(u32), [TLV]                  （5.2）
```

- lock の要る op で session_id が 0 なら rejected session_required。lock の要らない op で session_id が 0 なら session の検査なしに処理する。0 でない id なら、いまの role 0x81 と同じく §6.2 を通り、lease を始め直す。
- role 0x81 は無くなる（role の bit 7 は予約。知らない role は捨てる、§2.4）。10 byte より短い request は捨てる。§3.3 と §3.4 の「session の 0x81 の request」は「その session の id を持つ request」になる。
- open は resend の表で引かない（いまと同じ。再送された open は「S が保持、S の open」の行で扱う）。
- **corr u32 は採らない。** 通し番号の算術は消えない: 通知の seq（u16）と mark や segment の通し番号はやはり一周する（§2.6）。すべての request とすべての answer で 2 byte 増える。1 つの session の中で表が持つのは max_inflight 件だけで、§2.6 の 4 分の 1 の範囲の規則に十分収まる。

**byte の代価**（§5）: lock の要らない request だけ +4 byte。lock の要る request とすべての answer は変わらない。

**変更。** core §2.4、§2.5（role）、§3.3、§3.4、§4.1、§5.2、§6、§12。registry の `role_session_flag` を取り除く。vector `headers.json`。破壊的: あり。

**影響。** すべての codec: oep-probe-arduino、oep-client-python と fake、oep-client-js、ch32rv（`codec.rs`、ブローカーの中継、broker_wch の parser）。WireSkein と bench: client の更新だけ。

### 4.4 レビュー 5.4: TLV header を一つにする

**前提。** いま TLV は、値が 0〜254 byte なら `tag, len(u8), value`、255 byte 以上なら `tag, 0xFF, len(u16), value` で、符号化は一意でなければならない。255 byte 以上の値はまれ（大きい probe の role_channels の bitmap、capture の工場校正の raw）なので、長い形は最も通られず、新しい実装で最も間違えやすい道である。

**推奨: 採る。** 常に `tag(u8) | len(u16) | value`。parser は一つで、境界も正規形の規則も無く、どの TLV もすべての道を通る。代価は TLV ごとに 1 byte で、よく流れる通信はほとんど TLV を運ばない（§5）。

**変更。** core §2.2（短い形と長い形、一意性の規則、エスケープが消える）。`ignored` は最大 19 byte（tag、len、16 項目）で、最小は `7F 01 00 00`（4 byte）なので、probe が空けておく余地は 19 byte になる。tag 0xFF は無効のまま。registry の `tlv_len_long` を取り除く。probe.config の正規形と hash が変わる（vector を作り直す）。例、critical で送る max_speed 1 MHz: `81 04 00 40 42 0F 00`。破壊的: あり。

**影響。** すべての codec（probe、Python client と fake、JS client、ch32rv の `codec.rs` と broker_wch）。すべての probe の保存した設定を入れ直す（4.1 とともに）。bench は保存し直す。

### 4.5 レビュー 5.5: optional op の宣言を一つにする

**前提。** core §1.2 は、各 interface が optional op ごとに何で宣言するかを決めてよいとしている。いま:

| interface | optional op | いまの宣言 |
|---|---|---|
| `oep.core` | plan_apply 0x04、plan_release 0x05 | plan の役割を持つ interface があること |
| `oep.core` | port_speed 0x14 | fn 0 の describe の tag 0x4E |
| `oep.target.riscv-dm` | reset 0x04、read_block 0x05、write_block 0x06、run 0x07、step 0x08 | features の bit2、bit0（両方の block op）、bit1、bit3 |
| `oep.fixture.i2c-target` | stretch 0x07 | features の bit1 |
| `oep.fixture.logic`、`oep.fixture.analog` | query 0x09、force 0x04 | features の bit0、bit1 |
| `oep.fixture.capture-group` | force 0x04 | features の bit1 |
| `oep.probe.config` | save 0x03、erase 0x04 | storage の max_bytes > 0 |

host は op があるかを知るだけでも interface ごとのコードが要り、conformance のツールは「提供しないときちょうど unknown_operation」を一般的に確かめられない。

**推奨: 採る。** describe の共通 tag `ops`（0x09）: `base(u8), bitmap`。bit i が立っていれば op base + i を提供する。fn 0 を含めすべての fn の describe がこれを運ぶ。必須の op はすべて立てる。立っていない op には unknown_operation で答える。実験用の op（0xF0〜0xFF）は立てない。`features` は op でない optional な機能（mode、format、通知、内部 pull-up、attach_writes_unbounded）だけを持つ。

例: すべての op を持つ riscv-dm は `09 02 00 01 FF`。dmi、halt、resume だけなら `09 02 00 01 07`。plan の op を持ち link の op を持たない fn 0（5.6）は `09 08 00 01 1F 80 07 00 00 80 02`（op 0x01〜0x05、0x10〜0x13、0x30、0x32）。

**変更。** core §1.2（すべての optional op に一つの宣言）、§7.4（tag 0x09）。registry: `describe_common.ops = 0x09`。riscv-dm の features の block、run、reset、step を取り除く。i2c-target の features の stretch（bit1 は予約）。logic と analog の features の query、force（bit 0 と 1 は予約）。capture-group の features の force。fn 0 の describe の `port_speed` 0x4E。probe.config: storage の tag は save を提供するときちょうど現れ、その max_bytes は 1 以上。破壊的: あり。

**影響。** oep-probe-arduino と fake は fn ごとに `ops` を出す。Python と JS の client は features の bit の代わりに bitmap を調べる。ch32rv の `speed.rs`（port_speed を bitmap で）と broker_wch（いま riscv-dm の features 0x7 を宣言している。代わりに `ops` を出す）。WireSkein は client を通して（capture の query / force）。

### 4.6 レビュー 5.6: core と transport を分ける

**前提。** `oep-core.md` は message の core とともに、USB descriptor、vendor bulk の ZLP、HID の詰め方、serial の生 byte の多重化、UART の port speed、link test を持つ。最小の実装者もそのすべてを読む。core 自身の規則 2 は、core の仕組みだけで名前付き interface にできるものは core に入れないと言っている。link test と port_speed はそういうものである。

**推奨: 採る。** 規範のファイルを 3 つにする:

| ファイル | 内容 |
|---|---|
| `docs/oep-core.md` | 範囲と層、用語、適合、共通の規則と拡張の道（4.1）、message、再送、session、discovery、plan、resource、通知、fn 0 の op 表、interface の規則とチェックリスト（3.1）。host の待ち時間は下限を保ち、転送時間は transport の文書を参照する |
| `docs/oep-transports.md` | frame（serial port の COBS + CRC-16、vendor bulk と TCP の length-prefixed stream、その stream の詰め方としての HID、2.4）、送り方と途切れ、複数の transport、USB の識別と port の選び方、serial port の共有と生 byte、host の受信能力、区切りの回復（§5.1）、UART bridge の回線、起動時の速度、速度を上げた後の confirm の繰り返し、待ち時間の転送時間 |
| `docs/oep-if-link.md` | `oep.link`（D3）: link test と port_speed |

日本語版（`.ja.md`）も合わせる。ほかの `oep-if-*.md` は変わらない。分割は内容の変更の後に別の commit で行い、peer が規則と移動を別々にレビューできるようにする。

**`oep.link`（ユーザーの判断 D3）。** optional な標準 interface、revision 1:

| op | 名前 | request | answer | lock | 必須 |
|---:|---|---|---|---|---|
| 0x01 | source | length(u32) | len(u16), data（byte k = k & 0xFF）, [TLV] | 不要 | yes |
| 0x02 | sink | count(u16), data | — | 不要 | yes |
| 0x03 | port_speed | port(u8), baud(u32), step(u8), verify_ms(u16), idle_ms(u32), [TLV] | baud(u32), [TLV] | 要 | optional（`ops`） |

port_speed を提供する probe は `oep.link` を list に出す。いまの §3.5 の握手、状態、戻る条件はそのまま移す。probe が `oep.link` を持つかどうかにかかわらず適用される host の義務（速度を上げた後の confirm の繰り返し、転送時間）は transport の文書に残す。最小の probe は link test を実装しなくてよくなる。破壊的: あり（fn 0 から op 0x14、0x40、0x41 と describe 0x4E が消える）。

D3 を採らないなら、ファイルだけを分ける: link test と port_speed は fn 0 に残り、4.1 の数を持つ link test の形で transport の文書に置く。

**影響。** 文書とリンク（glossary、conformance、ガイド）。D3 なら: probe は処理を新しい fn へ移す。Python と JS の client の link test と速度の手順は、まず `oep.link` を list で探す。ch32rv の `speed.rs` と `link.rs`。bench の link の測定は client を通して。

## 5. 115200 bps の UART bridge での byte の代価

数え方: 線上の frame は message + 2（CRC）+ 1（254 byte ごとの COBS の code）+ 2（2 つの 0x00）byte である。115200 bps 8N1 では 1 byte に 86.8 µs かかる（11520 byte/s）。「提案」は推奨どおりの 4.3 と 4.4（corr u16）、「レビュアー」は corr u32 の 4.3 である。

| 通信（1 往復） | いま | 提案 | レビュアー（corr u32） |
|---|---:|---:|---:|
| lock の要らない monitor による console の poll（read、空の answer）: request 19 + answer 16 byte | 45 B、3.91 ms | 49 B、4.25 ms（+8.9 %） | 53 B、4.60 ms（+17.8 %） |
| lock の持ち主による console の poll（同じ） | 49 B、4.25 ms | 49 B（±0） | 53 B（+8.2 %） |
| dmi の一続き、abstract command による 1 回の読み（command を書く、busy を待つ、data0 を読む。step 20 byte、値 2 つ） | 62 B、5.38 ms | 62 B（±0） | 66 B（+6.5 %） |
| 1 KiB の read_block | 1064 B、92.4 ms | 1064 B（±0） | 1068 B（+0.4 %） |
| max_speed と pins を付けた attach、target_id と search_retries を付けた answer | 60 B、5.21 ms | 64 B（+4、4 つの TLV） | 68 B |
| fn 0 の describe、TLV 約 11 個の 1 page（connection ごとに 1 回） | — | +11 B | +13 B |
| marks、mark 10 個の 1 page | element 230 B | 220 B（−10、len なし、4.1） | 220 B |

monitor が 50 Hz で console を poll すると、線はいま 2250 B/s（115200 bps の 19.5 %）、提案では 2450 B/s（21.3 %）、corr u32 では 2650 B/s（23.0 %）を運ぶ。大きな転送（read_block、write_block、capture の data）はデータが大半で、変わらない。単純化は lock の要る主要な道に代価を生まない。corr u32 は、取り除ける規則が無いのに、すべての往復で 4 byte を払う。

## 6. 試験の不足（レビュー §7）と優先順位（レビュー §8）

### 6.1 レビュー §7: vector が覆わないもの

**前提。** 共有の vector が覆うのは CRC、COBS、header、TLV、confirm、discovery、probe.config の hash、拒否の一部である。session の状態機械、resend の表、paging、plan と競合、interface の符号化の大部分、状態の遷移、timing、lease、frame の途切れ、port_speed、電気の規則は覆っていない。conformance はすでに probe の conformance ツールを明記した不足として挙げている。

**推奨: 一部採る。**
- すべての標準 interface に **op ごとの byte vector**: 最小の success、境界の値、malformed、unsupported、unavailable、no_connection、op が持つなら completed failed / partial。それぞれ、request の byte、前提とする probe の状態、answer の byte として。本文が元であり続けるよう、ツールの中に書いた場合から `tools/oepvectors1.py` が書き出す。
- session の判断表（5.2）、resend の表、paging（describe、connections、state、segments）、plan の競合に **シナリオの vector**: 決まった初期状態からの（request の byte、answer の byte）の並び。このリポジトリの Python fake と、どの probe に対しても走らせる。
- **timing、lease、途切れ、port_speed、電気の規則**は byte の vector にしない: 実機の probe での release 試験（release-testing）に残し、不足を conformance に明記する。
- **いつ**: 4.1〜4.5 の wire の変更の後。vector を一度で書くためである。5.2 がその表を変えるので、session のシナリオから。

**影響。** このリポジトリのツールと試験。Python fake がそれを走らせる。Arduino probe の host 試験と ch32rv の fake probe は JSON を読み込んでよい。

### 6.2 レビュー §8: 順序

| レビュアーの優先順位 | ここでは |
|---|---|
| freeze 前に: 1 sequence（3.1） | 4.1 で解決 |
| 2 SDI / DMDATA（3.2） | Phase 0 |
| 3 HID（3.4） | Phase 0 |
| 4 文と空の scan（3.7、3.8） | Phase 0 |
| 5 リリースの識別子（3.3） | Phase 0、ユーザーの判断 D4 |
| 単純さのために: 固定部を閉じ、追加は TLV（5.1） | Phase 1、採る |
| end 後の引き継ぎも resume も無し（5.2） | Phase 1、ユーザーの判断 D1 |
| request header を一つに、corr u32（5.3） | Phase 1、header は採る、corr u32 は採らない（D2） |
| TLV の len を u16（5.4） | Phase 1、採る |
| optional op の宣言を共通に（5.5） | Phase 1、採る |
| freeze 後に: テンプレート（4.2） | 前へ移す: チェックリストは Phase 0、テンプレートの手引きは freeze 後 |
| byte vector、状態機械のモデル（§7） | 前へ移す: Phase 2、freeze 前 |
| 外部の参照（3.5） | 前へ移す: Phase 0（文言だけ） |

## 7. 計画

**Phase 0: 文言だけ、wire の変更なし**（互いに独立。文言の修正はそのまま入れてよく、残りは先に peer へ送る）: 3.2（SDI / DMDATA と debug の冒頭の行）、3.4（HID）、3.5（参照、SPI の mode）、3.6（answer の enum の条件）、3.7（文）、3.8（空の scan）、4.2（§13 のチェックリスト）、3.3（versioning §6 と status 行、D4 の後）。

**Phase 1: 破壊的な一式。peer への提案は一つ、各 codec の変更も一度。**
1. 4.1（閉じた形、element の len なし、末尾の欄を固定部へ、数を持つ link test）、4.4（TLV u16）、4.3（header を一つに）を一緒に: 3 つとも codec を変えるので、各実装は codec を一度だけ変え、vector も一度だけ作り直す。
2. 4.5（`ops`）: 1 と独立。同じ提案に入れてよい。
3. 4.2（session）: codec と独立。振る舞いと判断表を変える。同じ提案、別の commit。
4. 4.6（分割と、D3 の後の `oep.link`）: 最後に、規則が決まった後の本文の移動として。

**Phase 2: vector**（6.1）。session のシナリオから、次に op ごとの vector。

**Phase 3: 実装**、いつもの順に: fake、oep-probe-arduino、oep-client-python、oep-client-js、ch32rv、それから WireSkein と bench が新しい client を取り込む。bench は書き込み直して、保存した設定を入れ直す（bench の機材を使う前に b2 に尋ねる）。

**peer への質問**
- ch32rv: (a) 5.2: `flash` が次のコマンドのために connection を残さなくなる（各コマンドが attach し直し、最大 `attach_budget_ms`）ことを受け入れられるか。ほかのコマンドやブローカーが、end の後に resource が残ることに頼っていないか。ブローカーの `expired` の道を、そのまま `no_session` の道に合流させてよいか。(b) 5.3: corr u16 のままの 10 byte の header 一つを、codec.rs、中継、broker_wch で。(c) 4.1: reset_at_ns を tid の前に置いた slot_state と、len の無い element。(d) 5.5: features 0x7 の代わりに broker_wch の riscv-dm の `ops`。(e) D3: port_speed と link test が `oep.link` に移ることの、speed.rs と link.rs への影響。(f) 3.2: SDI / DMDATA の扱いに、本文の外から来たものはあるか。
- WireSkein: `end` の後に plan、capture の track、connection が残ることに頼る流れはあるか。capture の query と force は `ops` で宣言されるが、client の更新で足りるか。
- bench: プロセスをまたいで plan、connection、駆動した pin が残ることに頼る script はあるか。bench の probe をいつ書き込み直し、設定を入れ直せるか。

## 8. ユーザーの判断

**D1. lock が終わるとき、session が作ったものをすべて放す（5.2）。**
前提: いま `end` は session の plan と connection を次に open する session のために残し、host は id を使い回して resume できる。引き継ぎを使うのは ch32rv の `flash` だけで（次のコマンドの立ち上げを省く）、id で resume するものは無い。end で放せば resume の仕組みと `expired` の理由が消え、ある host が別の host の残したものを受け継ぐことも無くなる。利用者がコマンドのあいだ残したいもの（駆動した pin、どのコマンドも動いていないあいだの console の読み、速い attach）は、設定（plan、idle、slot、bind）が残す。代価: slot を使わない CLI のコマンドは attach し直す（最大 1000 ms）。推奨: 採る。

**D2. session_id を常に置く 10 byte の request header を一つにし、corr は u16 のまま（5.3）。**
前提: レビュアーは header を一つにし、corr を u32 にすることを提案している。header を一つにすると、role の bit、6 / 10 byte の分かれ、open の例外が消え、代価は lock の要らない request だけの +4 byte である（monitor の console の poll で +8.9 %）。corr u32 はすべての request と answer で 2 byte を払い、通知と通し番号がなお要る通し番号の算術を取り除かない。推奨: header は一つに、corr は u16。

**D3. link test と port_speed を fn 0 から optional な `oep.link` へ移す（5.6）。**
前提: いまはすべての probe が link_source / link_sink を実装せねばならず、port_speed は core にある。一方 core 自身の規則は、名前付き interface にできるものは core に入れないと言う。移せば最小の probe は小さくなり、fn 0 には discovery、session、plan、通知だけが残る。代価: すべての実装での番号の付け替えと、host が速度の試験の前に `oep.link` を list で探すこと。D3 なしなら文書だけを分ける。推奨: 採る。

**D4. リリースの識別子を決める（3.3）。**
前提: freeze 前は、2 つの実装がどちらも revision 1 を名乗りながら違うことがある。ユーザーは 2026-10-06 に、tag は freeze まで `v0.x` のままで `v1.0.0` を正式リリースとすると決めたが、versioning §6 はまだ「提案」と書いている。決めれば、各実装が実装する tag を名乗れる。推奨: versioning §6 を書いてあるとおり決定とし、status 行の一文を足し、実行時の edition 欄は足さない。
