# OEP v1 外部公開仕様レビュー（2026-10-07 再確認）

Status: **record**（非規範）。OEP v1 freeze 前の仕様を、第三者による相互運用実装、曖昧さ、独自拡張、単純性の観点からレビューした記録。

この版は、core の範囲をさらに縮小した変更後の `3bca24c` を対象とする。以前のレビュー内容を現状に合わせて更新し、特に core と TCP transport を重点的に確認した。

## 1. レビュー範囲

主に次を確認した。

- 公開された規範文書だけから、第三者が互換 host / probe を実装できるか。
- 同じ入力や状態に対して、wire encoding、応答、拒否理由が十分に一意か。
- core が、すべての probe に本当に必要な機能だけに絞られているか。
- 未知の TLV、enum、op、event、interface を安全に扱えるか。
- 第三者が既存実装を変更せず、独自機能を追加できるか。
- transport ごとの差をまたいでも、同じ interface declaration が成立するか。
- registry、生成物、test vector が一致しているか。

対象は主に次の規範文書とデータである。

- [OEP core](oep-core.ja.md)
- [OEP transports](oep-transports.ja.md)
- [standard interface common parts](../interfaces/oep-if-common.ja.md)
- [plan](../interfaces/oep-if-plan.ja.md)
- [restart](../interfaces/oep-if-restart.ja.md)
- [link](../interfaces/oep-if-link.ja.md)
- [wire and debug](../interfaces/oep-if-debug.ja.md)
- [console](../interfaces/oep-if-console.ja.md) と [dmseq](../interfaces/target-console-dmseq.ja.md)
- [fixture](../interfaces/oep-if-fixture.ja.md)
- [capture](../interfaces/oep-if-capture.ja.md)
- [probe settings](../interfaces/oep-if-probe-config.ja.md)
- [v1 registry](../registry/oep-v1.toml)
- [versioning](versioning.ja.md) と [conformance](conformance.ja.md)

freeze 前は日本語版が作業上の規範であり、英語版は古い可能性があるため、このレビューも日本語版を基準にした。

## 2. 結論

core の縮小は成功している。`plan`、`restart`、`link` は名前付きの任意 interface に移され、fn 0 は名前を持たない protocol core として、次の8操作だけになった。

- `confirm`
- `list`
- `describe`
- `clock`
- `open`
- `end`
- `keepalive`
- `lock_state`

通知も interface ごとの任意機能になり、heartbeat は削除された。data の batching と event の即時送出が分かれ、`ops` の境界と encoding も明確になった。以前の主要な指摘は解消されている。

現在の日本語仕様から通常の互換実装を作れる水準には達している。ただし、異なる transport や broker を含む実装で解釈が分かれる可能性がある規範上の問題が残る。

freeze 前の優先順位は次のとおりである。

1. transport の「frame は複数 transfer / report にまたがってよい」と「host は一回の write で送る」の矛盾を解消する。
2. interface の `max_length` と transport ごとの `max_frame` の関係を一意にする。
3. broker 経由で `oep.probe.restart` を公開する場合の保証を定義するか、broker はこの interface を公開しないことにする。
4. fn 0 を固定形式の `(name, revision)` 規則から明示的に除外する。
5. channel 数と channel ID の有効範囲を明記する。
6. 実際の TCP probe、特に ESP32 の Wi-Fi 実装で仕様を検証する。

## 3. 現在残る規範上の指摘

### 3.1 High: transport の分割許可と「一回の write」が矛盾する

[OEP transports](oep-transports.ja.md) は、vendor bulk では一つの OEP frame が複数の USB transfer に、HID では複数の report にまたがってよいと定めている。一方、共通規則では host が一つの frame を一回の write で送らなければならないとしている。

この規則は次の理由で相互運用要件として成立しにくい。

- HID API の一回の write は通常一つの report であり、それより大きい frame は一回では送れない。
- stream / serial / TCP の write は、API が全 byte を一度に受理することを一般には保証しない。
- OS API の write 呼び出し境界は wire 上には残らず、probe は検証できない。

規範は API 呼び出し回数ではなく、wire 上で観測できる条件にすべきである。次のように統一することを推奨する。

- 一つの frame は複数の write、USB transfer、HID report に分割してよい。
- TCP 以外では、frame の途中に `probe_frame_gap_ms` 以上の空白を置いてはならない。
- TCP は byte stream として length 分を受信するまで待ち、write / packet / `recv` の境界に意味を持たせない。

### 3.2 High: interface の `max_length` と transport の `max_frame` の関係が曖昧

core は `max_frame` を transport ごとの値としている。一方、interface declaration の `max_length` は一つだけで、debug interface は host が `max_length` から操作量を決め、`max_frame` から再計算しないとしている。

例えば同じ probe が `max_frame = 1024` の USB bulk と `max_frame = 64` の UART を持つ場合、同じ `max_length` が両方で送信可能なのかが決まらない。第三者実装は次の二通りに分かれ得る。

- `max_length` は最小の transport でも送れる値だと解釈する。
- host が現在の transport の `max_frame` と header overhead からさらに小さくする。

最も単純な規則は次である。

> interface declaration の `max_length` と、その値で生成される最大 message は、その probe が同時に広告するすべての transport の最小 `max_frame` に収まらなければならない。

transport ごとに性能を最大化したい場合は、declaration を transport ごとに変えるか、host が両方の値から上限を計算する規範式が必要になる。しかし cache と実装を単純に保つなら、全 transport の最小値に合わせる方がよい。

### 3.3 Medium: broker と `oep.probe.restart` の end-to-end 保証が一致しない

restart interface は、応答後に probe が再起動し、`restart_max_ms` 以内に同じ transport で `confirm` に応答できることを要求する。

一方、TCP broker は upstream transport が失われたときに client connection を閉じる。broker が upstream probe の restart interface をそのまま relay すると、client から見た「同じ transport」は broker への TCP connection だが、その connection は維持されない。`restart_max_ms` も、broker の再接続や再公開までを含む保証かどうか不明である。

core を小さく保つ方針に合う最小の解決は、broker が `oep.probe.restart` を client に広告しないことである。relay するなら、次を restart または transports の規範として定義する必要がある。

- TCP connection が閉じられるか維持されるか。
- client が同じ address へ再接続する時点。
- `restart_max_ms` が upstream の復帰だけか、broker 経由の `confirm` 成功までか。
- restart response が client へ届いた後に upstream response が失われた場合の結果。

### 3.4 Medium: fn 0 と固定形式の識別規則が一致しない

core は fn 0 が名前を持たず、`list` にも現れないことを明記している。一方、固定形式は `(interface name, interface revision)` によって決まるという一般規則が fn 0 を除外していない。

次のように識別規則を二つに分ければ曖昧さがなくなる。

- 名前付き interface の固定形式は `(interface name, interface revision)` で決まる。
- fn 0 の固定形式は protocol revision で決まる。

これは wire format の変更を伴わない小さな修正である。

### 3.5 Medium: channel の存在と有効範囲が完結していない

core は channel ごとの empty-state や電気的な共通規則を定めているが、declaration の `channels` tag は必須ではない。次が明示されていない。

- `channels` が無い場合、channel 数は0なのか、未知なのか。
- 有効な channel ID が `0 .. channels - 1` なのか。
- role declaration や各 request に含まれる channel ID も同じ範囲に制限されるか。
- channel を使用する probe / interface が `channels` を必ず返すか。

次の規則を推奨する。

- `channels` が無い場合、その probe の共通 channel は0個である。
- channel を使用する probe は `channels` を必ず返す。
- 有効な channel ID は `0 <= channel < channels` である。
- declaration、request、response、event に含まれるすべての channel ID にこの範囲を適用する。

## 4. core の範囲と単純性

### 4.1 縮小により改善した点

- fn 0 は名前を持たず、名前付き interface の発見機構と二重に広告されない。
- `plan` は `oep.probe.plan` へ移り、resource の事前確保を必要としない probe は実装しなくてよい。
- `restart` は `oep.probe.restart` へ移り、再起動制御を持たない probe から特別な状態遷移を除ける。
- `link` は `oep.probe.link` にあり、transport 設定が core operation に混ざらない。
- notification は interface ごとの `ops` で宣言され、通知を使わない probe は subscription state と timer を実装しなくてよい。
- data だけが batching 対象で、event は即時送出になった。
- `ops` の長さ、範囲、canonical encoding、不正時の扱いが定義された。

以前のレビューで提案した主要な core 縮小は反映されている。

### 4.2 `clock` を必須 core に残すかは再検討の余地がある

現在もすべての probe が `clock` と、非 wrap の u64 nanosecond timebase を提供する。GPIO の単純操作など、時刻を使用しない最小 probe にもこの実装が必要になる。

小さな core を最優先するなら、`clock` を `oep.probe.clock` のような任意 interface に移し、timestamp を返す interface がその存在を要求する構成も可能である。core には次だけを残せる。

- `boot_id` による再起動の検出。
- 同じ `boot_id` 内で timestamp を比較する場合の一般規則。

ただし、多くの interface が共通 timebase を使い、同期や cache の前提として常に必要なら、core に残す合理性もある。freeze 前に「時刻を一切使わない適合 probe を許したいか」を判断すべきである。

### 4.3 channel の電気規則は条件付き core と明記するとよい

core の channel / role / empty-state / 電気的安全性は、複数の hardware interface で共有されるため core に置く価値がある。一方、channel を持たない probe にまで実装義務があるように読めると core の範囲が広く見える。

別 interface に分離すると依存関係が増えるため、まずは「channel を広告する probe にだけ適用する条件付き core 規則」と明記するのが小さい変更である。

## 5. 仕様書だけからの互換実装可能性

現在の日本語の規範文書から、次は実装可能である。

- serial / vendor bulk / HID / TCP の framing と frame validation。
- request、response、event、data の header と TLV。
- confirm、list、describe による discovery。
- session、lock、lease、resend、deduplication と resource lifetime。
- 名前付き interface の optional op と通知能力の発見。
- 標準 interface の request / response と主な状態遷移。
- reverse-DNS 名を使った独自 interface の追加。

通常の正しい message について、独立した host と probe が同じ byte layout を実装できる。残る問題は基本 encoding よりも、複数 transport、broker、channel 境界などの組合せに集中している。

実際に USB、SWD、ADI、RISC-V DM、I2C などを動かすには、各 interface 文書が列挙する外部仕様も必要である。これは OEP protocol の欠落ではなく hardware backend の依存関係である。

freeze 前は日本語版だけが最新の規範である。正式な v1 release では英語版を同期し、規範文書、registry、生成物、vector を同じ immutable release tag に含める必要がある。

## 6. 拡張性

拡張モデルは単純で、第三者による追加にも適している。

1. 既存の文脈へ独立した追加情報を入れる場合は TLV を使う。
2. 任意操作は `ops` で宣言する。
3. 安全に無視できる event、enum、bit は、文書で定めた互換条件の範囲で追加する。
4. 意味が異なる機能は新しい interface name にする。
5. 固定形式を変える場合は interface revision を上げる。

`oep.` は project が管理し、第三者は reverse-DNS name を登録なしで使える。標準 interface と独自 interface が同じ discovery mechanism を使うため、vendor extension 専用の分岐も必要ない。

critical TLV、未知 op の拒否、未知 event の無視、declaration cache の範囲も定義されている。固定形式の暗黙の末尾拡張を禁止したことで、互換 reader の規則は少ない。

設計原則は次の一文にまとめられる。

> 固定形式は revision で守り、互換追加は TLV、操作の有無は ops、意味が違うものは別 interface。

## 7. TCP/IP と ESP32 Wi-Fi 実装による仕様検証

TCP transport は規範化されているため、IP network 上の probe は実装できる。ただし文書と byte vector だけでは、TCP 固有の分割・結合、複数 client、切断復帰の不足を見つけにくい。freeze 前に、独立した host と実際の TCP probe を作って相互接続することを強く推奨する。

特に ESP32 の Wi-Fi は、安価で再現しやすく、組込み側の制約も確認できるため検証対象に適している。これは新しい「IP transport」を追加する提案ではなく、現在の TCP transport を IPv4 または IPv6 上で実装して検証する提案である。

### 7.1 最小の ESP32 検証実装

最小実装は次を含めればよい。

- Wi-Fi 上の TCP listener。
- `length(u16), message` の framing。
- fn 0 の必須8操作。
- session、lock、resend、deduplication。
- 少なくとも一つの小さな名前付き interface、または core だけの適合構成。
- `boot_id` を更新する実際の reboot。

ESP-IDF、Arduino など使用 framework は仕様要件にしない。別コードベースの host から操作し、既存実装同士の自己整合だけで合格にしないことが重要である。

### 7.2 TCP で必ず試す項目

- 2 byte の length 自体を複数の `recv` に分ける。
- payload を1 byte単位を含む任意位置で分割する。
- 複数 frame を一回の write / TCP segment / `recv` に結合する。
- write と TCP packet の境界に依存しないことを確認する。
- TCP には `probe_frame_gap_ms` による途中破棄を適用しないことを確認する。
- 同時に複数 client を接続し、global session / lock と connection ごとの状態を確認する。
- 正常 close、突然の切断、half-open、Wi-Fi loss、再 association を試す。
- probe reboot 後に再接続し、`boot_id`、session、resource、resend state の失効を確認する。
- 通知を実装する場合、購読した connection だけへ event / data が届くことを確認する。
- `oep.probe.restart` を公開する場合、response、切断、復帰、再 `confirm` の順序と時間保証を確認する。

TCP の framing test は、ESP32 実機だけでなく、write を意図的に分割・結合する deterministic な fake client / server として CI にも入れるとよい。実機試験は release checklist に置く。

### 7.3 複数 client で確認すべき状態の所有範囲

実装により、少なくとも次の区別が仕様どおりか確認する。

- probe 全体で共有する session、resource、lock。
- connection ごとの negotiated revision、受信途中の frame、送信 queue。
- transport ごとの `max_frame`、window、`max_inflight`。
- connection 消失時に維持するものと解放するもの。

ここを実装すると、単一 serial connection の試験では見えない state ownership の曖昧さを発見しやすい。

### 7.4 discovery、port、security の扱い

現在の TCP 規範は port 番号と network discovery を範囲外にしている。ESP32 検証では固定または手動設定した address / port を使ってよい。そのうえで、外部利用者が実際に困らないかを確認し、必要なら mDNS 等を別仕様として標準化する。参考実装だけの暗黙の discovery 手順を事実上の仕様にしてはならない。

また、OEP 自体には network authentication や encryption がない。TCP probe は trusted LAN または認証された tunnel 内で使う前提を明記し、一般の Internet へ直接公開して安全だと解釈されないようにする必要がある。

## 8. 以前の指摘への反映確認

| 指摘 | 現在の状態 |
|---|---|
| request header が複数形式 | 解決。`session_id` を常に持つ10 byteの一形式 |
| TLV header が複数形式 | 解決。固定 u16 length の一形式 |
| sequence element の外側 length が不統一 | 解決。`count, count × element` に統一 |
| fixed part の暗黙の末尾拡張 | 解決。固定形式は revision で固定 |
| optional op の宣言が interface ごと | 解決。共通 `ops` tag |
| `ops` の範囲と canonical encoding | 解決。境界 vector も追加 |
| 通知が任意か必須か矛盾 | 解決。interface ごとの任意機能 |
| data と event の batching が曖昧 | 解決。data は batching、event は即時 |
| heartbeat が最小 probe に必須 | 解決。heartbeat を削除 |
| end 後の resource 継承と implicit resume | 解決。終了時に解放し、open だけが開始 |
| `plan` が core にある | 解決。`oep.probe.plan` へ移動 |
| `restart` が core にある | 解決。`oep.probe.restart` へ移動 |
| transport 設定が core に混在 | 解決。`oep.probe.link` と transports に分離 |
| fn 0 が名前付き interface と二重に見える | 大部分を解決。名前と list entry を削除。固定形式の識別文だけ要修正 |
| HID stream の再構成規則が不足 | 解決。fragment、複数 frame、padding、report ID、途切れを定義 |
| 外部仕様の参照が不足 | 解決。文書名、版、利用部分を列挙 |

## 9. 検証結果と不足

次の check は成功した。

```text
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest registry_v1 vectors
```

pytest は27件すべて成功した。生成物、registry、現在の vector に不一致は見つからなかった。

vector は CRC、COBS、header、confirm、discovery、refusal、session、`ops` と `ops` encoding の境界を含む。以前不足していた `ops` の機械検証は改善された。

一方、共有の自動適合試験では次が十分に扱われていない。

- TCP stream の任意分割と複数 frame の結合。
- 複数 TCP client と global session / lock の競合。
- transport ごとに異なる `max_frame` と一つの interface declaration の組合せ。
- broker 経由の restart と upstream の切断・復帰。
- describe と各 interface の paging の連続シナリオ。
- standard interface の多くの op と状態遷移。
- timing、lease、`max_op_ms`、frame gap、port speed の復旧。
- 電気的な規則と実機の振る舞い。
- probe 全体を相手にする自動 conformance test。

ESP32 TCP probe と独立 host の相互接続を加えることで、上の最初の4項目と、組込み実装での resource 上限を具体的に検証できる。

## 10. Freeze 前の推奨変更

### 必須

1. transport の一回の write 要件を削除し、wire 上の分割許可と frame gap で規定する。
2. `max_length` と複数 transport の `max_frame` の関係を定義する。
3. broker が restart interface を隠すか、end-to-end の復帰規則を定義する。
4. fn 0 の固定形式は protocol revision で決まることを明記する。
5. `channels` の欠落時の意味と channel ID の範囲を定義する。

### core をさらに小さくする場合

1. 時刻を使わない probe を許すなら、`clock` を任意の名前付き interface に移す。
2. channel の共通規則は、channel を広告する probe にだけ適用すると明記する。

### 実装による Freeze 判定

1. ESP32 Wi-Fi 上に最小 TCP probe を実装する。
2. 別コードベースの host から、serial と TCP の両方を同じ操作モデルで動かす。
3. TCP の分割・結合を強制する test を CI に追加する。
4. 2 client の session / lock 競合を試験する。
5. Wi-Fi 切断、再接続、probe reboot、`boot_id` 変更を試験する。
6. restart を公開するなら broker 経由でも試し、規範上の保証と一致しなければ仕様を直す。

### Release 前

1. 日本語の規範文書から英語版を同期する。
2. 節番号の欠番を整理する。
3. `features` tag の説明に残る notification の例を、実際に表す mode に明確化するか削除する。
4. 複数の誤りを同時に含む request で refusal reason が一意でない設計を、意図した単純化として conformance 文書に明記する。
5. 規範文書、registry、生成物、vector を同じ immutable release tag に含める。

## 11. 最終評価

現在の仕様は、以前より明確に小さく、規則が少なく、拡張可能になった。通常の protocol path は日本語の規範文書だけから互換実装でき、独自 interface の追加にも十分な namespace と前方互換規則がある。

特に、`plan`、`restart`、`link`、通知を core の必須機能から外した判断はよい。残る問題は core の基本構造ではなく、transport 間の上限、TCP / broker の接続境界、名前を持たない fn 0、channel の条件付き規則に集中している。

文書レビューだけで freeze するより、ESP32 Wi-Fi の TCP probe と独立 host を一度実装した方がよい。TCP の任意分割、複数 client、切断・再接続、reboot を通すことで、仕様だけを読んだ段階では見えない状態所有と時間保証の不備を発見できる。上記の規範修正と実装検証を終えれば、外部公開 v1 として第三者に互換実装を求められる水準に達する。
