# OEP v1 外部公開仕様レビュー（2026-10-06、再レビュー）

Status: **record**（非規範）。OEP v1 freeze 前の仕様を、第三者による相互運用実装、曖昧さ、独自拡張、単純性の観点から再レビューした記録。

この版は、同日に行った最初のレビュー後の変更（request / TLV / sequence の単一形式化、session の単純化、共通 `ops`、transport の分離、試験 vector の追加など）を反映した再レビューである。

## 1. レビュー範囲

主に次を確認した。

- 規範文書だけから、第三者が互換 host / probe を実装できるか。
- 同じ入力や状態に対して、wire encoding、応答、拒否理由が一意に決まるか。
- 未知の TLV、enum、op、event、interface を安全に扱えるか。
- 第三者が既存実装を変更せず、独自機能を追加できるか。
- core が十分小さく、拡張方法と状態遷移が理解しやすいか。
- registry、生成物、test vector が一致しているか。

対象は主に次の規範文書とデータである。

- [OEP core](oep-core.ja.md)
- [OEP transports](oep-transports.ja.md)
- [standard interface common parts](../interfaces/oep-if-common.ja.md)
- [wire and debug](../interfaces/oep-if-debug.ja.md)
- [console](../interfaces/oep-if-console.ja.md) と [dmseq](../interfaces/target-console-dmseq.ja.md)
- [fixture](../interfaces/oep-if-fixture.ja.md)
- [capture](../interfaces/oep-if-capture.ja.md)
- [probe settings](../interfaces/oep-if-probe-config.ja.md)
- [link](../interfaces/oep-if-link.ja.md)
- [v1 registry](../registry/oep-v1.toml)
- [versioning](versioning.ja.md) と [conformance](conformance.ja.md)

freeze 前は日本語版が作業上の規範であり、英語版は古い可能性があるため、このレビューも日本語版を基準にした。

## 2. 結論

仕様は最初のレビュー時点から大幅に改善された。通常の OEP frame、message、discovery、session、標準 interface は、現在の日本語の規範文書から独立実装できる水準にかなり近い。特に、wire 上の基本形式と拡張方法が少数の規則に整理され、以前より相互運用実装を作りやすい。

次の大きな問題は解決済みである。

- request header は `session_id` を常に持つ 10 byte の一形式になった。
- TLV は `tag(u8), len(u16), value` の一形式になった。
- sequence は一律 `count, count × element` になり、element の外側の length は無くなった。
- 固定形式を末尾拡張せず、形を変える場合は revision を上げる規則になった。
- optional op は全 fn 共通の `ops` tag で宣言するようになった。
- session resume と終了後の resource 継承が無くなり、end、expiry、force で同じように解放するようになった。
- transport が別文書になり、HID の byte stream、report ID、padding、途切れが定義された。
- 外部仕様の文書名、版、利用範囲が列挙された。
- SDI / DMDATA が規範として定義された。
- session と一部の op の byte vector が追加された。

一方、freeze 前に直すべき規範上の矛盾が1件、相互運用上の曖昧さが2件ある。また、「小さく単純な core」という設計目標に対して、任意の `restart` を core に置いたことは再検討した方がよい。

推奨する優先順位は次のとおりである。

1. 通知対応が任意か必須かの矛盾を解消する。
2. `ops` bitmap の正しい範囲と canonical encoding を定義する。
3. 通知の `min_bytes` / `max_delay_ms` が data と event にどう適用されるかを定義する。
4. `restart` を core ではなく任意の名前付き interface に移す。

## 3. 現在残る指摘

### 3.1 High: 通知対応が「任意」と「必須」の両方になっている

core §1.2 は、すべての probe に fn 0 の `subscribe` と `unsubscribe` の実装を要求している。core §11.3 はさらに、fn 0 を購読すると heartbeat が届くと定めている。

一方、core §11 冒頭は「probe の対応は任意」と書いている。この文だけを根拠に、通知をまったく実装しない probe も適合すると解釈できる。

互換実装を一意にするには、次のどちらかへ統一する必要がある。

1. 通知機構と fn 0 heartbeat は必須で、各 interface の通知だけが任意である。
2. `subscribe`、`unsubscribe`、heartbeat を一組の任意機能とし、fn 0 の `ops` で宣言する。

小さな probe と単純な core を優先するなら2を推奨する。通知を使わない probe から、heartbeat の timer、subscription state、notification buffer を除ける。共通 `ops` がすでにあるため、host の判定に新しい仕組みは要らない。

1を選ぶ場合は、少なくとも §11 冒頭を「通知機構と fn 0 heartbeat は必須、各 interface の通知は任意」に直す。

### 3.2 Medium: `ops` bitmap の正しい符号化範囲が定義されていない

core §7.4 の `ops` は次の形である。

```text
base(u8), bitmap
```

しかし、次が未定義である。

- bitmap は空でよいか。
- bitmap は最大何 byte か。
- `base + i > 0xFF` となる bit をどう扱うか。
- 先頭または末尾の zero byte を許すか。
- 同じ op の集合に複数の wire encoding を許すか。
- 不正な `ops` を受けた host が、その fn、probe、transport のどれを使用不能とするか。

例えば `base = 0xF8` の2 byte bitmapは、実装によって「0x100 以降を無視する」「u8 で一周する」「宣言全体を不正とする」に分かれ得る。

単純で canonical な形として、次を推奨する。

- value の長さは2〜33 byte、bitmap は1〜32 byte。
- `base + 8 × bitmap_bytes <= 256`。
- bit 0 は立っており、最後の bitmap byte は0でない。
- `base` は宣言する最小の op。
- experimental op と、その interface が定義しない op の bit は立てない。
- 条件を満たさない `ops` を受けた host は、その fn を使用しない。

これにより、一つの op 集合に一つの encoding だけが対応し、生成、比較、適合試験が単純になる。

### 3.3 Medium: 通知のまとめ条件が data と event を区別していない

core §11.3 は、`min_bytes` byte がたまるか、最初の byte から `max_delay_ms` が経ったら送ると定めている。しかし role 0x05 の event について、次が明確でない。

- `min_bytes` に event payload の byte も数えるか。
- 複数の event をまとめるのか。
- capture の `segment`、`stopped`、`triggered` を発生後すぐ送るのか。
- `min_bytes > 0`、`max_delay_ms = 0` の購読で、event だけの fn が永久に何も送らないことがあるか。

次のように役割を分けると単純である。

- `min_bytes` と `max_delay_ms` のまとめ条件は role 0x06 の data にだけ適用する。
- role 0x05 の event は、発生後、先行する response を送り終えた時点で送る。
- fn 0 では `max_delay_ms` を heartbeat の周期として使い、`min_bytes` は無視する。

event をまとめたい場合は、複数 frame の送信開始を遅らせるのか、一つの frame に複数 event を入れるのかも明記する必要がある。現在の message 形式を変えないなら、event はすぐ送る規則が最も小さい。

### 3.4 Design: `restart` は core の線引きと合わない

core §0 は、core に入れるのは interface 名を知る前に必要なもの、または一つの名前付き interface では定義できないものだけとし、core の仕組みだけで名前付き interface にできるものは core に入れないと定めている。

`restart` は discovery 後に使う任意の操作であり、第三者も独自の interface として同じ機能を定義できる。そのため、この線引きに従えば core よりも名前付き interface に置く方が自然である。

さらに `restart` を core に入れたことで、次の特別規則が core と transports に増えた。

- response 後の全 transport の停止。
- USB の再列挙と TCP の再待受。
- `restart_max_ms`。
- response が失われた場合の特別な待ち方。
- broker での中継と、待っている間の `result_lost`。
- UART bridge の port speed の復旧。

これは、transport の分離と `oep.link` への機能移動で得た単純さを一部失わせている。

`restart` は `oep.probe.control` などの任意の標準 interface に移すことを推奨する。core には次だけを残せばよい。

- `boot_id` による再起動の検出。
- probe が再起動すると session、resource、subscription、resend table が失われるという一般規則。
- transport が失われた場合の一般的な回復規則。

restart interface の文書は、response を先に送ること、再起動までの上限、復帰を待つ手順を定義できる。既存 core の安全性を失わず、restart を持たない最小 probe の core 実装を小さくできる。

## 4. 仕様書だけからの互換実装可能性

### 4.1 実装できる範囲

現在の日本語の規範文書から、次は実装可能である。

- serial / vendor bulk / HID / TCP の OEP framing。
- request、response、event、data の header と TLV。
- confirm、list、describe による discovery。
- session、lock、lease、resend、deduplication と resource lifetime。
- plan と共通の refusal order。
- 標準 interface の request / response と主な状態遷移。
- 独自 interface の名前、revision、op、TLV の割り当て。

通常の正しい message については、独立した host と probe が同じ byte layout を実装できる。

### 4.2 外部仕様が必要な範囲

OEP の protocol 自体はこの repository の規範文書で定まる。実際に USB、SWD、ADI、RISC-V DM、I2C などを動かすには、各文書の「参照する仕様」に列挙された外部仕様も必要である。

これは protocol の欠落ではなく、hardware backend の依存関係である。外部仕様の文書名、版、使用部分が明記されたため、最初のレビュー時点の問題は解消された。

### 4.3 現在の制限

通知については §3.1 と §3.3 を直すまで、二つの適合実装が異なる動作をする可能性がある。`ops` も通常の宣言は実装できるが、境界値と不正な宣言の扱いは一致しない。

また、freeze 前は日本語版だけが最新の規範で、英語版は古い可能性がある。作業中の仕様としては明示されているため問題ないが、外部公開する正式な v1 release では英語版を同期し、同じ release tag に含める必要がある。

## 5. 拡張性と単純性

### 5.1 良い点

- interface を name と revision で発見する。
- `oep.` は project が管理し、第三者は reverse-DNS name を登録なしで使える。
- standard interface と独自 interface を同じ core mechanism で扱う。
- request TLV の critical bit により、無視されると意味が変わる追加情報を安全に送れる。
- 固定形式は revision 中で変えず、追加情報は TLV に置く。
- optional op の有無を、全 interface 共通の `ops` で宣言する。
- 未知の TLV、event、enum、status の基本的な扱いが定義されている。
- response enum を revision なしで追加できる条件が明文化された。
- chip 固有の手順を generic interface に混ぜず、別名の interface にする原則がある。
- declaration と可変 state が分離され、同じ boot_id の間の cache 規則がある。
- interface 作成の checklist に op、TLV、outcome、status、reason、resource lifetime、event、外部仕様が含まれる。

第三者は reverse-DNS interface を別の fn として追加できる。既存の標準 interface に vendor-specific field を混ぜる必要がなく、namespace collision も避けられる。

### 5.2 現在の拡張モデル

freeze 後の基本的な拡張方法は、次の4つに整理された。

1. 既存の文脈へ独立した追加情報を入れる新しい TLV。
2. `ops` で宣言する新しい optional op、または安全に無視できる optional event。
3. 条件を満たす予約済み enum 値または bit の定義。
4. 新しい意味には新しい interface name、固定形式の変更には新しい revision。

固定部分、TLV value、sequence element を暗黙に末尾拡張しないため、reader が持つ前方互換規則は以前より少ない。「固定形式は revision で守り、互換追加は TLV、意味が違うものは別 interface」と説明できる状態に近づいている。

### 5.3 さらに小さくする余地

最も効果が大きいのは次の2点である。

- 通知を使わない probe では、subscribe / unsubscribe / heartbeat を一組の任意機能として省けるようにする。
- probe 自身の restart を任意の名前付き interface に移し、core と broker の特別規則を減らす。

それ以外の大きな単純化案はすでに反映されている。corr を u32 にする案は採用されず u16 のままだが、再送表、再利用、wrap の規則は明文化されているため、現時点では相互運用を妨げる曖昧さではない。

## 6. 最初のレビュー指摘への反映確認

| 最初の指摘 | 現在の状態 |
|---|---|
| answer sequence の element length が不統一 | 解決。一律 `count × element`、外側の element length なし |
| SDI / DMDATA の規範性が不明 | 解決。規範として定義 |
| freeze 前の revision 1 同士が非互換になり得る | 運用を明記。freeze 前は実装した spec tag を示し、release tag の規則を定義 |
| HID stream の再構成が不足 | 解決。fragment、複数 frame、count 0、padding、report ID、途切れを定義 |
| 外部仕様の参照が不足 | 解決。文書名、版、利用部分を列挙 |
| response enum の追加条件が広い | 解決。安全に追加できる3条件を定義 |
| probe.config paging の文が不完全 | 解決 |
| scan の空候補が不明 | 解決。`tried = 0` の success を定義 |
| fixed part の末尾拡張が多い | 解決。固定形式を revision で固定し、追加は TLV |
| end 後の resource 継承と implicit resume | 解決。終了時に解放し、open だけが session を開始 |
| request header が複数形式 | 解決。10 byte の一形式 |
| TLV header が複数形式 | 解決。固定 u16 length の一形式 |
| optional op の宣言が interface ごと | 解決。共通 `ops` tag |
| core と transport binding が混在 | 大部分を解決。transports と `oep.link` に分離。ただし restart の broker / transport 特則が再び増えた |

## 7. 検証結果と不足

次の check は成功した。

```text
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest registry_v1 vectors
```

pytest は24件すべて成功した。生成物、registry、現在の vector に不一致は見つからなかった。

vector は以前より増え、次を含む。

- CRC、COBS、header、TLV、confirm。
- list、describe と一部の拒否。
- probe.config の canonical hash。
- session decision table、resend、end、force、session_id 0。
- restart、`oep.link`、GPIO、RVSWD、RISC-V DM、console、probe.config、logic の一部の op。

ただし、conformance 文書自身が記すとおり、次は共有の自動適合試験で十分に扱われていない。

- describe と各 interface の paging の連続シナリオ。
- plan と resource contention。
- standard interface の多くの op と状態遷移。
- timing、lease、max_op_ms、frame gap、port_speed の復旧。
- 電気的な規則と実機の振る舞い。
- probe 全体を相手にする自動 conformance test。

freeze 前に少なくとも次の vector を追加するとよい。

- `ops` の最小値、最大値、不正長、0xFF 境界、非 canonical encoding。
- subscribe / unsubscribe、heartbeat、data、event、seq の欠落。
- describe の複数 page と終端。
- plan の成功、競合、release、session 終了時の解放。
- restart の response 喪失と broker の待機状態。

## 8. Freeze 前の推奨変更

### 必須

1. core §11 の「通知対応は任意」と、必須 subscribe / heartbeat の矛盾を解消する。
2. `ops` の長さ、範囲、overflow、canonical encoding、不正時の host 動作を定義する。
3. notification batching が data と event にどう適用されるかを定義する。

### 小さく単純な core を重視する場合

1. subscribe / unsubscribe / heartbeat を一組の optional core capability にする。
2. restart を `oep.probe.control` などの optional interface に移す。

### Release 前

1. 日本語の規範文書から英語版を同期する。
2. 規範文書、registry、生成物、vector を同じ immutable release tag に含める。
3. conformance 文書に残る未試験範囲を release test で確認する。

## 9. 最終評価

現在の仕様は、最初のレビュー時点より明確に小さく、規則が少なく、拡張可能になった。通常の protocol path は仕様書だけから互換実装でき、独自 interface の追加にも十分な namespace と前方互換規則がある。

freeze を妨げる主な問題は protocol 全体の構造ではなく、通知の矛盾、`ops` の境界、event の送出条件という局所的な規範不足である。これらを直せば、外部公開 v1 として独立実装を求められる水準に達する。

設計目標を最も簡潔に表す原則は、引き続き次である。

> 固定形式は revision で守り、互換追加は TLV、操作の有無は ops、意味が違うものは別 interface。
