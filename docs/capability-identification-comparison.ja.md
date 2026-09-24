# Open Embedded Probe — 能力（interface）の識別方式の比較

状態: **非規定の比較案**（2026-09-24）。probe が提供する機能を host がどう見分けるかについて、数値、UUID、
UUID と短縮番号の併用、文字列（パッケージ名型）の 4 案を比較し、推奨案と wire の具体案を示す。
採用・数値・文字集合はまだ決定しない。

## 背景

v0 の registry は機能を `owner(16):id(16):revision(8)` で識別し、標準を owner 0x0000、oep-probe-arduino の
独自 tool を 0x0100 としている。この方式には次の問題がある。

- owner の払い出しを誰かが管理しないと、独自拡張どうしが衝突する。現在の 0x0100 も場当たりに決めた値である。
- 番号から「何の仲間か」が読めず、階層もない。ログや診断で意味を引くには registry が要る。
- 層の違い（どのピンでもビットバンで動く BASIC、専用ペリフェラルで速い拡張、probe 固有の独自拡張）を
  表す場所が、番号の割り当て方しかない。

目標は、**独自拡張を誰でも登録なしに作れ、しかも衝突しない**こと。

## 前提: 識別子の長さはふだんの通信に効かない

v0 はすでに、`list` で見つけた機能にセッション内の 16 bit 参照（`fn`）を振り、以後の request はその `fn` で送る。
識別子が wire に出るのは **発見（list）のときだけ**である。したがって識別子を長くしても、通常の request/result は
重くならない。短さより、衝突しないことと読めることを優先して選べる。

## 候補

| 候補 | 内容 | 先例 |
|---|---|---|
| A. 数値 | 今の `owner:id`。owner を中央で払い出す | USB の VID:PID、クラスコード |
| B. UUID | 128 bit UUID で全機能を識別 | — |
| C. UUID + 短縮 | 標準は 16 bit の短縮番号（基底 UUID に埋め込む）、独自は 128 bit | BLE の GATT |
| D. 文字列 | ドメイン名を逆にした階層名（`oep.fixture.uart`、`io.github.<org>.p4.i2c-target`） | Wayland のインターフェース名、D-Bus、Android のパッケージ名、Vulkan の拡張名 |

## 観点ごとの比較

| 観点 | A. 数値 | B. UUID | C. UUID + 短縮 | D. 文字列 |
|---|---|---|---|---|
| 独自拡張どうしの衝突 | owner の管理次第 | 実質起きない | 実質起きない | ドメインの持ち主が決めるので起きない |
| 中央の登録 | 要る（owner） | 要らない | 標準分だけ | 標準の `oep.` だけ |
| 人が読めるか | 読めない | 読めない | 標準だけ読める | 読める |
| 階層 | ない | ない | ない | 名前そのものが階層 |
| 版 | revision と別 id | 別 UUID | 別 UUID | revision と名前の変更 |
| list の 1 件の大きさ | 5 byte + 付随 | 16 byte + 付随 | 2 または 16 byte + 付随 | 名前の長さ（目安 20〜40 byte）+ 付随 |
| 低スペック probe | 最も軽い | flash に 16 byte/件 | 同左 | flash に名前を置くだけ |
| 仕組みの数 | 1 | 1 | 2（短縮と完全形） | 1 |
| 接頭辞での絞り込み | owner 単位のみ | できない | できない | 名前空間の任意の深さでできる |

## 推奨: D. 文字列（パッケージ名型）

- 衝突しない条件が「ドメイン名を持っていること」だけで、登録の窓口が要らない。
- 名前が階層になるので、層の対応（後述）と、接頭辞での絞り込みが自然に書ける。
- 最も近い先例の Wayland は、サーバーが「番号・インターフェース名・版」を通知し、クライアントが名前で選んで
  セッション内の番号で使う。OEP の list と `fn` の構造と同じである。
- UUID は衝突の点で同等だが、読めず、階層を作れない。C は仕組みが 2 つになる。低スペック probe で list が
  重すぎると分かったときは、標準分だけ短縮番号を後から足せる（D を捨てずに C の利点を取れる）。

### 名前の規則（案）

- 区切りは `.`、各区切りは小文字 ASCII の英数字と `-`。長さは 48 byte 以下（64 byte frame の低スペック probe で
  list の 1 件が 1 frame に収まる長さ: 名前 48 + 項目の固定部分 7 + 応答の見出し約 8 = 63 byte）。**probe が宣言できる
  frame の最小は 64 byte とし、名前の上限とこの最小は一緒にしか変えない**（CH32V003 を probe にする場合の点検、
  2026-09-24）。
- 先頭の区切りで名前空間の種類を見分ける。

| 先頭 | 用途 | 衝突しない根拠 |
|---|---|---|
| `oep.` | OEP 標準（予約） | `oep` は実在のトップレベルドメインではないので、逆ドメイン名と重ならない |
| `com.` `io.` `jp.` など | 自分が持つ実在のドメインを逆にした名前 | ドメインの持ち主 |
| `io.github.<name>.`、`io.gitlab.<name>.`、`page.codeberg.<name>.` | 自分のドメインを持たない作者（ホスティングが与えるドメインを使う） | ホスティングがその `<name>` を一人にしか与えない |
| `uuid.<32 桁の小文字 16 進>.` | ドメインがなく、それでも確実に一意にしたい作者 | UUID |
| `local.` | 手元の実験用。公開しない | 相互運用を保証しない（MIME の `x-` に当たる逃げ道） |

- ホスティングのドメインは、実在するドメインをそのまま逆にする。GitHub なら `io.github.<name>`（GitHub が
  `<name>.github.io` を与えている）とし、`github.<name>` や `com.github.<name>` は使わない。前者は実在しない
  トップレベルで、後者は GitHub が `github.com` のサブドメインを利用者に与えていないので持ち主の根拠にならない
  （Maven Central も `com.github` から `io.github` に切り替えている）。
- oep-probe-arduino と ch32rv は `io.github.ch32-riscv-ug.` の下に置く（例:
  `io.github.ch32-riscv-ug.p4.i2c-target`、37 byte）。

## 層との対応

| 層 | 名前の置き場所 | 分け方 |
|---|---|---|
| BASIC（よくある機能） | `oep.*` | 最小の約束。どのピンでもビットバンで実現できることを前提にし、低スペック probe でも実装できる |
| 高速・拡張 | 同じ `oep.*`、または `oep.*` の拡張インターフェース | 約束（操作と意味）が同じで速いだけなら、インターフェースは分けず、describe の上限・role ごとのピン候補・ピンの組の制約で表す。操作や意味が増える場合（ストリーミング、DMA の一括転送など）は `oep.target.flash.bulk` のような標準の拡張インターフェースにする |
| 独自拡張 | 自分のドメイン名の下 | 何を定義しても衝突しない |

書き込みの経路（DMI のビットバン、SPI、PIO）は、約束が同じ「target に書き込む」なので同じ `oep.target.flash`
とし、経路は describe の参考情報として宣言する。約束そのものが違う経路（debug module ではなくブートローダの
UART ISP や USB HID を使う書き込み）は `oep.target.isp.*` のように別のインターフェースにする。

## 規則

1. **1 つのインスタンスが複数のインターフェースを持てる。** 例: P4 の I2C target が標準の
   `oep.fixture.i2c-target` と独自の `io.github.ch32-riscv-ug.p4.i2c-target`（`read_hw`、意図的な clock stretching）
   を同時に提供する。操作番号はインターフェースごとの空間なので、**インターフェースごとに別の `fn` を振り**、
   同じインスタンスの仲間であることは describe の TLV（instance group）で示す。操作番号も TLV のタグも衝突しない。
2. **標準インターフェースの TLV タグは標準だけ。** 独自の情報は独自インターフェースの describe に置く。
   標準の中に独自タグを混ぜる余地を作ると、そこで衝突する。
3. **版**: 後方互換の追加（request の任意 TLV、result の末尾 field）は revision を上げる。互換を壊す変更は
   名前を変える（例: `oep.fixture.uart2`）。
4. **任意の操作・モードの有無**は、標準インターフェースなら仕様で定めたビットマスクの TLV、独自なら独自
   インターフェースで表す。呼んでみて reject されるまで分からない状態をなくす。

## list の取り方

1 つの操作で「全部」「名前空間の下」「完全一致」を選べるようにする。

```text
list request : flags(u8), first(u8), prefix_len(u8), prefix(bytes)
               flags bit0 = exact（prefix を完全な名前として一致させる）
list result  : total(u8), entries: array of
               { fn(u16), revision(u8), flags(u8), name_len(u8), name(bytes) }
```

- prefix が空なら全部。今の list と同じくページ送り（`first`）で取る。
- 一致は `.` の区切りの単位で見る。`oep.fixture.uart` は `oep.fixture.uart.stream`（子）に一致し、
  `oep.fixture.uart2`（別物）には一致しない。子を含めないときは exact を立てる。
- exact で同じインターフェースのインスタンスが複数あれば、すべて返す。
- probe 側は flash 上の名前との先頭比較だけなので、低スペック probe でも軽い。64 byte frame では 1 ページに
  2 件程度しか載らないので、絞り込みで往復を減らせる（BLE にも同じ目的の「UUID で絞って探す」操作がある）。

## 現行 registry からの対応（案）

**BASIC の能力として何を標準にするかは、まだ決めない。** 下の表は命名の例であり、`oep.` の下にこれらを
標準として置くことを決めるものではない。決めるのは宣言の仕組み（名前、list、describe）である。

| 現行（owner:id） | 名前（案） | 備考 |
|---|---|---|
| 0:0x0000 core | `oep.core` | `fn` 0 に固定 |
| 0:0x0001 probe_identity | `oep.probe.identity` | u64 のピンマスクは `oep.probe.capabilities` の TLV へ |
| 0:0x0010 target_control | `oep.target.control` | reset の mode 1/2（UIAPduino 専用の RAM ペイロード）は独自インターフェースへ |
| （target_control の read_dmi / read_register） | `oep.target.riscv-dm` | アーキテクチャ別に分ける |
| 0:0x0011 target_memory | `oep.target.memory` | |
| 0:0x0012 target_flash | `oep.target.flash` | 経路は describe |
| 0:0x0013 target_console | `oep.target.console` | 対応 framing は describe |
| 0:0x0020 fixture_gpio | `oep.fixture.gpio` | |
| 0:0x0021 fixture_uart | `oep.fixture.uart` | |
| 0:0x0022 fixture_capture | `oep.fixture.capture` | |
| 0x0100:0x0001 p4_i2c_target | `oep.fixture.i2c-target` + `io.github.ch32-riscv-ug.p4.i2c-target` | 標準部分と P4 固有部分に分ける |
| 0x0100:0x0002 p4_spi_target | `oep.fixture.spi-target` + `io.github.ch32-riscv-ug.p4.spi-target` | 同上 |

## 未決

- 名前の最大長（48 byte 案）と文字集合の確定。
- instance group の表し方（describe の TLV か、list の entry の field か）。
- registry と codegen での名前の扱い（生成物の定数名、codec の選び方）。
- 低スペック probe の list の重さの実測（64 byte frame、名前 5〜8 件）。
- 標準の短縮番号を足すかどうか（D のまま始め、必要になってから判断する）。
