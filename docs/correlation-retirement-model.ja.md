# Open Embedded Probe — Request correlationのretire条件

状態: **検討中の論理protocol案**。この文書は、解決済みまたは結果不明のrequest correlationを、古いresultを新しいrequestへ誤適用せず再利用可能にする条件を整理する。

具体的な保持時間、duplicate window、connection APIおよび回復messageは決定しない。

## Retireが必要な理由

requesterがresultを処理し終えたことと、そのcorrelationを持つ別のresultが到着不能になったことは同じではない。

- HID response cacheが同じresultを再取得可能な場合がある
- binding ACK喪失により同じtransport dataが再送される場合がある
- responderまたは中継がlogical resultを再送する場合がある
- timeout後に元のresultが遅れて到着する場合がある

古いresultが到着するだけなら、対応するpending requestがなければunknownとして分離できる。同じcorrelationを新しいrequestへ再利用した後に古いresultが到着すると、新しいrequestへの正常resultに見えるため危険になる。

## Requester側の状態

correlation値を少なくとも次に分ける。

| 状態 | 意味 | 再利用 |
|---|---|---|
| available | 現在のcontextで安全に割当可能 | 可能 |
| pending | requestを送信し、resolutionを待っている | 不可 |
| indeterminate | timeout、取消しまたは通信異常によりresolution不明 | 不可 |
| resolved-retained | resultは処理済みだが、古いresultの到着可能性を閉じていない | 不可 |

`accepted` resultを受信した場合もcorrelationは一度resolved-retainedになる。activity referenceへの移行はrequest contextの引継ぎであり、古いaccepted resultが到着不能になった証拠ではない。

実装は各値へこのenumをそのまま保存する必要はない。pending table、recent set、generation、bitmap、単調増加値またはconnection更新で同じ不変条件を満たせる。

## 基本遷移

```text
available -- request送信 --> pending
pending   -- result受信 --> resolved-retained
pending   -- timeout等 --> indeterminate

resolved-retained -- 古いresultが到着不能と確認 --> available
indeterminate      -- result受信とwindow終了を確認 --> available
indeterminate      -- context終了/安全な再同期 --> available（新context）
```

`indeterminate`をlocal timeoutだけで`available`へ戻さない。requestが実行されたか、resultがcacheまたは通信中に残っているかをtimeoutから判断できない。

## Retireの根拠にできるもの

### Bindingが上位への一回deliveryを保証する

bindingが一つのlogical messageを上位へ一度だけdeliveryし、delivery後に同じmessageを再度上位へ渡さないことを保証する場合、受信済みresultについてbinding由来のduplicate windowは終了できる。

これはresponderが別のlogical messageとして同じresultを再送しないという上位規則と組み合わせる必要がある。

### Response cacheの無効化または置換を確認する

HID等でresponseがcacheされる場合、次の有効requestによって以前のcacheが置換された、明示的に消費確認された、またはbinding resetで無効化されたことを確認できれば、そのcacheを根拠とする保持を終了できる。

単にGET_REPORTを一度開始したことは、transfer中断時にもcacheを残す実装では無効化の証拠にならない。

### Bounded duplicate windowを経過する

bindingまたはprofileが古いlogical resultの最大遅延を規定し、その測定起点も明確な場合、window終了後にretireできる。根拠のない固定待機時間や平均latencyを使用しない。

時間ではなく、確認済みsequence、acknowledgementまたは一定数のgenerationでwindowを表せる場合もある。

### Epochまたはconnection contextを更新する

同期済みの新しいepochまたは新connectionへ以前のmessageがdeliveryされないことをbindingが保証する場合、新しいcontextでは以前のcorrelation namespaceを引き継がなくてよい。

物理linkが一時的に切れたように見えることだけを、新context確立の証拠にしない。双方が同じepoch/context境界を認識する必要がある。

### 明示的な状態照会または回復

将来、requestのresolutionとresponse保持状態を照会し、古いresultを破棄または再取得する共通操作を定義した場合、その完了をretire根拠にできる。現在はその操作を定義しない。

## Retireの根拠にしないもの

- requesterのlocal timeoutだけ
- 新しいrequestを送りたい、またはslotが不足したという都合
- activityがterminalになったこと
- targetやoperationが前回と異なること
- correlation値を一巡したこと
- transportが通常は速いという期待
- responderが再起動したように見えるがcontext更新を確認していないこと

activity terminalとcorrelation retireは別である。古い`accepted` resultが再送される可能性はactivity終了だけでは消えない。

## Binding候補への適用

| Binding候補 | 解決済みresultの主なretire根拠 | 結果不明時 |
|---|---|---|
| HID feature report | cacheの置換・無効化、lifecycle reset | 古いcacheを識別して取得するか、reset後に新contextを確立 |
| UART stop-and-wait | sequenceによるduplicate抑止とresult DATAの一回delivery | epoch再同期だけでOEP実行結果は確定しない。必要なら結果不明のままcontext更新 |
| TCP等 | 完全なlogical resultの一回deliveryと、上位が重複resultを生成しない規則 | 同じconnectionを使い続けるなら遅延resultを待つ。破棄する場合は新connection contextへ移行 |

UART transport ACKはframe受領を示すだけで、機能requestのresolutionを示さない。request DATAがACK済みでもOEP resultを失った場合、そのrequestは結果不明になり得る。

## 枯渇時の動作

availableな値がなくなった場合、新しいrequestを開始しない。実装は次のいずれかを選べる。

- pending resultまたは定義済みduplicate windowの終了を待つ
- cache消費、同期または状態照会を行う
- connection contextを安全に終了し、新しいcontextを確立する
- 利用者へlocal resource/correlation exhaustionを通知する

枯渇は相手へ送信済みrequestの`rejected`ではない。新しいrequestをまだ送っていないlocal状態である。

## 現時点の方向

- result処理完了とcorrelation retireを分ける
- timeoutしたrequestは`indeterminate`として値を保持する
- 古いresultが到着不能になった根拠がある場合だけ再利用する
- 根拠はbinding保証、cache無効化、bounded window、同期済みepochまたは新connectionから得る
- 根拠を得られない場合は同じcontext内で再利用しない
- 枯渇時に使用中値を上書きしない
- bindingごとに、duplicate windowをどの事実で閉じるか定義する

## この文書で決めないこと

- bindingごとの具体的retire API
- HID response消費確認のwire方式
- duplicate windowの長さ
- result recordを保持する最大数
- indeterminate requestの照会・取消し・再実行
- connection contextを更新する共通操作
- crashまたは電源断を越えるcorrelation保持

次段階では、HID、UARTおよび順序付きstreamについて、bindingが上位へ提供するduplicate-free境界を個別文書へ反映する。

