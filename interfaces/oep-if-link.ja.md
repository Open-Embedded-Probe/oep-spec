# OEP インターフェース: リンク v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.link` | 1 | 経路を試し（線の試験）、セッションの間だけ UART bridge の口の速さを上げる（port_speed） | どの系統にも使う |

- `oep.probe.link` は任意のインターフェースである。port_speed を持つ probe はこれを list に出す。線の試験だけのために出してもよい。probe が
  list に出す `oep.probe.link` は高々 1 つ。
- その op は、port_speed が変える口の速さのほか、probe の状態を変えない。

## 1. 操作

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x10 | source | length(u32)、[TLV] | len(u16)、data、[TLV] | 不要 | 必須 |
| 0x11 | sink | count(u16)、data、[TLV] | — | 不要 | 必須 |
| 0x12 | port_speed | baud(u32)、step(u8: 0 試す、1 決める、2 戻す)、verify_ms(u16)、[TLV] | baud(u32: 実際に掛かる速さ)、[TLV] | 必要 | 任意 |
| 0x13 | port_state | [TLV] | baud(u32)、state(u8: 0 起動時、1 試し、2 決めた、3 復帰保留)、[TLV] | 不要 | port_speedを持つとき必須 |

port_stateは要求経路の現在のUART速度/phaseを読む。kind 1以外ではunavailable cause 6。
phase3は復帰条件を満たし、frame境界を待つ状態。新しいcorrで問い合わせ、過去のport_speed成功応答を現在のphaseとして扱わない。

## 2. 線の試験（source、sink）

source と sink は経路の速さを測るためのもの。状態を変えない。

- **source**: data は len バイトで、k バイト目（k は 0 から）は k & 0xFF。len は length と、要求の来た経路の max_frame（core §4.4）から 7
  （応答の見出し 5 と len 2）を引いた値の、小さいほう。length 0 なら len 0。
- **sink**: count の後ろに、値が任意の count バイトが続く。count が後ろに続くバイトより大きければ rejected malformed。要求は max_frame に収まるので、count は多くても max_frame − 12（要求の見出し 10 と count 2）。応答は completed success で、
  payload は空。
- host はその応答を、ほかの要求と同じように待つ（core §4.4）。confirm のようには繰り返さない。

## 3. port_speed

port_speed は、UART bridge の口で、セッションの間だけリンクの速さを起動時の速さ（115200 bps、transports §4）より上げる。probe の
fixture UART の速さは別（そのインターフェースの configure と設定）。この節が決めるのは**握手**である。どの速さを試すか、通ったとみなす基準、
使っている間に戻す基準は host が決める。

**probe**

- 対象は、要求の来た経路が transport kind 1（UART bridge）の口のときだけ。ほかの経路からの port_speed は rejected unavailable（cause 6）。
- UART が作れる最も近い速さが要求と `port_speed_tolerance_pct`（2 %）より大きく違えば rejected unsupported。応答の baud は実際に掛けた速さ。
  step 0/1の実際のbaudは起動時より高い値だけ。上げられない要求はunsupported（固定部分の印0）。
  step 0（試す）の verify_ms 0 は rejected malformed。step 1（決める）と step 2（戻す）では verify_ms に意味は無く、どの値も受ける。
- port_stateが返すphaseは口ごとに管理する。stepの受理は次の表に従う。「拒否」はunavailable cause 6で、状態を変えない。
  同時に上げる口は1つだけで、別の口がphase 1/2/3の間はstep 0をcause 6で断る。

| 現在のphase | step 0 試す | step 1 決める | step 2 戻す |
|---|---|---|---|
| 0 起動時 | 今の速さで応答後、応答のbaudへ切替えphase 1。この要求のverify_msを開始 | 拒否 | 拒否 |
| 1 試し | 拒否 | 試したbaudと同じ要求を新しい速さで受け、phase 2 | 今の速さで応答（baudは起動時の値）後、起動時へ戻りphase 0 |
| 2 決めた | 拒否 | 拒否 | phase 1と同じ戻す手順 |
| 3 復帰保留 | 拒否 | 拒否 | 拒否 |

step 1のbaudが試した値と違う場合もcause 6。phase 3は復帰条件が成立し、frame境界を待っている状態である。

- **probe が自分で起動時の速さに戻る条件**（戻ったことは知らせない）:
  1. 試しのまま verify_ms が過ぎた。
  2. 決めた後、その口に正常なフレームが `port_speed_idle_ms`（3000 ms）来ない。正常なフレームを受けた時と応答を送った時から数え直す（要求を実行して
     いる間は、処理する経路によらず進まない）。これはport_speedの復帰timerの規則であり、所有者の要求だけで止めるleaseとは区別する（core §6.1）。
  3. セッションが終わった（end、lease の期限切れ、force で持ち主が替わった）。end と force は応答を送ってから戻る。
- verify/idleのtimerは要求の処理中は進めない。復帰条件を満たしても、送受信中のframeや要求の応答を途中で速さを変えて壊さない。
  復帰が保留になったら新しい通知frameを始めず、現在の送信frameと受信frameの終了（または受信のgap/resync）を待って戻す。
  phase 3は理由によらず取り消さない。phase 3の間のstep 0/1/2はcause 6で断り、拒否によって復帰条件やbaudを変えない。
  phase 3に入った時に受信中のframeは、その要求の応答まで今の速さで終え、その境界で戻す。境界の後に始まる受信は戻した速さで扱い、
  新しい要求を受け続けても復帰を延ばさない。
  いずれもcoreの見出し・再送・sessionの判定を先に行う（例えば終了済みsessionの新しい要求はno_session）。
  試し中のcommit要求がverify期限までに届かなければ、unavailable cause 6で断り、応答後のframe境界で戻す。
- 試しと決めるの間、セッションの資源とロックは変わらない。通知の欠落は通常のseq/positionで扱い、保持量を増やす義務はない。

**host**

試す前に、その経路へ先に送った要求と再送の結果をすべて解決する。port_speedの応答が届くまで同じ経路へ次の要求を送らない。
応答は変更前の速さで最後まで読む。送りかけの通知はprobeがその速さで完了してから応答する。

1. 試すの応答を受けたら、要求した baud（作れなければ応答の baud）に切り替え、`port_speed_switch_wait_ms`（20 ms）以上待ってから、新しい速さで
   次の要求を送る。
2. 戻す、end、異なるsession_idへのforce open、またはprobeを再起動するopの成功応答を受けたら、UART bridgeの口を起動時の速さへ切り替える。
   同じsession_idのopenはforce付きでもセッションを維持し、速さを戻さない（core §6.2）。再送された過去の成功応答では現在の速さを判断しない。

通知だけを待つhostも、決めた速さを保つにはport_speed_idle_msより短い間隔でkeepalive等の正常な要求を送る。
通知の送信だけではidle timerを延ばさない。端点のleaseが長くてもこの条件は独立している。
クラッシュ/応答喪失後の開き直しは、以前の要求の処理時間、frame転送、復帰timerを含めてhostが待ちを決める。
port_speedを扱わないhostへ一定の長い探索待ちを要求しない（transports §4）。
try/commit/revertの応答を失った場合は、起動時/試した速さでconfirmと新しいcorrのport_stateを使って復旧する。
期限で元へ戻った後の再送結果は履歴であり、同じcorrの成功を見ても再び速さが変わるとは限らない（coreの再送規則）。
新しい試行は、現在のphaseを確認してから新しいcorrで始める。ロックを失っていれば通常のセッション復旧を先に行う。
