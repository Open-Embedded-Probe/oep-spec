# Open Embedded Probe — 共通message model候補

状態: **比較検討中のprotocol設計案**。この文書は、[最小interaction pattern](interaction-patterns.ja.md)をwire protocolへ対応付けるための共通message model候補を比較する。現時点では候補を採用せず、messageのencoding、field配置、数値、framingおよびconnection bindingを規定しない。

ここでいうmessageの役割は論理的な分類である。将来、一つのwire形式に統合すること、複数の形式に分けること、またはconnection binding上で一部を最適化することを妨げない。

## Message modelで解決する範囲

message modelは、少なくとも次の問いに共通の答えを与える必要がある。

- hostがprobeへ何を求めたか
- probeが要求を受理したか、拒否したか
- 受理と処理完了が同じ時点か異なる時点か
- 結果、失敗、変更およびdataが何に対応するか
- 同時進行する処理を区別する必要があるか
- 未知の機能または追加情報をどのscopeで扱えないと判断するか

一方、この段階では次を決めない。

- binary、textその他のencoding
- fieldの幅、並びおよび数値割当
- USB packet、serial frame、network transportとの対応
- 個別機能の操作名、入力、結果およびdata形式
- 暗号化、認証および認可の具体的方式

## 比較の前提

### 小さな実装を成立させる

最小のprobeは、一度に一つの要求を処理し、結果を同じやり取りで返してよい。使用しない非同期処理、通知、複数activityまたはdata flowのために、実行時状態を常に保持することは要求しない。

### 必要な実装は拡張できる

長時間操作、継続的なdata flow、状態変化の通知および複数の同時処理を実装する場合は、結果やdataを正しい対象へ対応付けられなければならない。

### 機能固有の意味を共通層へ集めない

共通message modelは、scope、相関、結果および失敗を運ぶための共通性を担当する。個別機能の操作、parameter、dataおよび結果の意味は、標準機能または独自機能の定義が担当する。

独自機能は、共通message modelへ従う限り、共通実装が解釈できないpayloadを使用できる。

### Connection interfaceから独立させる

同じ論理的interactionをUSB、UART、networkその他のconnection bindingで表現できる必要がある。特定のinterfaceが持つ転送境界、順序性または信頼性を、すべてのconnectionへ暗黙に仮定しない。

## 評価軸

各候補を次の観点で比較する。

| 評価軸 | 確認すること |
|---|---|
| 最小実装 | 単純な同期処理だけを持つprobeへ不要な状態管理を要求しないか |
| 完了の明確さ | 受理、進行中、完了、partial resultおよび失敗を誤認しないか |
| Data flow | 継続的または大量のdataを無理なく扱えるか |
| 同時進行 | 必要な実装が複数処理を区別できるか |
| 拡張性 | 標準機能と独自機能を同じ枠組みで扱えるか |
| 未知情報 | 理解できない要素の影響scopeを限定できるか |
| Transport独立性 | USB、UART、network等へ意味を変えずに対応できるか |
| 実装一貫性 | 機能ごとの独自な共通処理を増やさずに済むか |

## 候補A: Request/response中心

すべての基本操作をhostからのrequestとprobeからのresponseとして扱う。通常は一往復で完了し、長時間操作、通知およびdata flowだけに追加の仕組みを設ける。

```text
host                         probe
  | -------- request --------> |
  | <------- response -------- |
```

### 長所

- 同期的なcontrol操作を小さく実装しやすい
- hostが開始する操作について流れが明確である
- endpoint確認、提供情報取得および単純なconfigurationに適する
- requestとresponseを同じやり取りとして対応付けやすいconnectionでは、明示的な状態を減らせる可能性がある

### 課題

- 受理後に長時間継続する操作へ別のmodelが必要になる
- probeからの変更通知をresponseとして表現できない
- 双方向または継続的なdata flowが例外的な仕組みになりやすい
- 後から非同期拡張を加えると、response、完了通知およびdataの関係が機能ごとに異なる可能性がある

### 適合しやすい範囲

OEP-INT-001、OEP-INT-002、OEP-INT-003および即時に完了するOEP-INT-004には適合しやすい。OEP-INT-005、通知を使うOEP-INT-007および長時間activityには追加規則が必要になる。

## 候補B: Activity中心

すべての要求をactivityの作成として扱い、受理、進行、data、完了、停止および失敗をactivity lifecycleへ統一する。

```text
host                         probe
  | ----- start activity ----> |
  | <------ accepted ---------- |
  | <---- data / progress ----- |
  | <--- outcome / failure ---- |
```

### 長所

- 短時間操作と長時間操作へ同じlifecycleを適用できる
- 複数処理、停止、進捗、partial resultおよびdataを対応付けやすい
- 非同期操作やdata flowを基本modelとして扱える

### 課題

- 単純な情報取得にもactivity identityと状態管理を要求しやすい
- activityの作成、保持、完了および回収に共通規則が必要になる
- 小さなprobeにとって、即時応答だけの操作まで過剰に複雑になる可能性がある
- 接続喪失後のactivity lifetimeや再取得を早い段階で決める必要が生じる

### 適合しやすい範囲

OEP-INT-004、OEP-INT-005およびOEP-INT-008を統一しやすい。一方、endpoint確認や単純な情報取得にも同じmodelを必須にする妥当性が課題になる。

## 候補C: 役割を分けた共通model

即時に評価できるrequest/resultを基本とし、必要な場合だけactivity、notificationおよびdata transferを使用する。それぞれは共通のscopeと相関規則を共有する。

```text
host                         probe
  | -------- request --------> |
  | <---- result または受理 --- |
  |                             |
  | <---- notification -------- |  必要な場合
  | <====== data flow ========> |  必要な場合
  | <--- activity outcome ----- |  activityを作る場合
```

論理上、少なくとも次の役割を区別する。

- **request** — 相手に評価または操作を求める
- **result** — requestの受理、拒否、即時の結果または失敗を示す
- **activity update/outcome** — request後も継続する処理の状態または最終結果を示す
- **notification** — 直前のrequestへの応答ではない変化を示す
- **data transfer** — 機能が定義するdata単位を運ぶ

これらをそのままwire上の五つのmessage typeにすることは、この候補の必須条件ではない。重要なのは役割を誤認しないことである。

### 長所

- 単純な実装はrequest/resultだけで成立できる
- 必要な機能だけがactivity、notificationまたはdata flowを追加できる
- 受理と完了が同じ場合と異なる場合を表現できる
- 共通のscopeと相関を保ちながら、機能固有payloadを運べる

### 課題

- 役割間の境界を定義する必要がある
- resultで完了する操作とactivityを作る操作の区別が必要になる
- dataを通常のresultへ含める範囲とdata flowへ移す範囲を決める必要がある
- 実装が対応しない任意の役割を、提供情報または機能定義から判断できる必要がある

### 適合しやすい範囲

すべてのinteraction patternへ段階的に対応できる。小さな実装と高機能な実装の両方を一つの共通modelに収めやすいが、共通部分を増やしすぎない規律が必要になる。

## 候補D: 最小dispatchのみ共通化

共通protocolはendpoint確認、機能識別およびpayloadの配送だけを担当し、request、response、notification、activityおよびdataのmodelを各機能定義へ委ねる。

### 長所

- 共通protocolを非常に小さくできる
- 個別機能が用途に最適化したinteractionを定義できる
- 独自機能へ最大限の自由を与えられる

### 課題

- 受理、完了、失敗、停止および相関の意味が機能ごとに分かれる
- 汎用host libraryが提供できる共通処理が少なくなる
- 各機能が似た仕組みを別々に定義し、相互運用上の差異が増えやすい
- 未知の独自機能を共通層が安全に中継または診断しにくい
- connection bindingごとの実装へ機能固有の知識が漏れやすい

### 適合しやすい範囲

独自機能は実装しやすいが、OEP全体として共通の相互接続性を得る目的には共通部分が不足する可能性が高い。

## 候補の比較

| 観点 | A: Request/response | B: Activity中心 | C: 役割分離 | D: 最小dispatch |
|---|---|---|---|---|
| 単純な同期操作 | 強い | 過剰になり得る | 強い | 機能定義次第 |
| 長時間操作 | 追加方式が必要 | 強い | 必要時に対応 | 機能定義次第 |
| Notification | 追加方式が必要 | lifecycleへ統合可能 | 明示的に対応 | 機能定義次第 |
| Data flow | 追加方式が必要 | activityへ統合可能 | 明示的に対応 | 機能定義次第 |
| 小さなprobe | 強い | 負担が大きい可能性 | 使用部分を限定できる | 共通層は小さい |
| 汎用host library | 一部を共通化 | 多くを共通化 | 必要部分を共通化 | 共通化しにくい |
| 機能間の一貫性 | 拡張部分が分かれやすい | 高い | 高くできる | 低くなりやすい |
| 設計上の主なrisk | 非同期機能が後付けになる | 全操作が重くなる | 共通役割を増やしすぎる | 相互運用性が機能ごとに分断される |

## 現時点で有力な方向

要求との対応では、**候補Cを基礎とし、単純な実装が候補A相当のrequest/resultだけで成立できる構成**が最も適合しやすい。

この方向は、次を意味する。

- すべてのrequestがactivityを作ることを要求しない
- 即時に完了する操作は一つのresultで完了できる
- 受理後も処理が継続する場合だけactivityを区別する
- notificationを実装しないprobeは、許容される範囲でhostからの再取得を利用できる
- 継続的dataを提供しない機能へdata flow対応を要求しない
- 独自機能のpayloadを共通層が理解することを要求しない
- 共通層は、未知payloadでもscope、役割およびcriticalityを誤認しないために必要な情報を扱う

これは採用決定ではない。特に、どの役割を共通protocolの必須要素とするかは、次の未決事項を検討した後に決める。

## 次に決める事項

1. requestに対する最初のresultが、受理結果と最終outcomeの両方を表せるか
2. activityを作成したことをhostがどの時点で確定できるか
3. activity identityを誰が割り当て、どのscopeとlifetimeで有効にするか
4. notificationを共通の役割として定義するか、情報再取得だけでも適合できる範囲をどうするか
5. data transferを共通messageの一種にするか、別の論理channelとして扱えるようにするか
6. requestとresultの相関を、直列実装では省略可能にするか
7. probeからhostへの自発的なrequestを共通modelで許可するか
8. 一つのmessageに複数の要求または結果を含めるbatchを初期仕様へ入れるか
9. result、activity outcomeおよびnotificationに共通するfailure表現をどこまで設けるか
10. unknownなmessage role、機能、操作または追加情報を受信した場合の処理

次段階では、候補Cを仮の比較基準として、最初の四項目であるrequestの完了意味、activityの作成、identityおよびnotificationの必須範囲を順に検討する。
