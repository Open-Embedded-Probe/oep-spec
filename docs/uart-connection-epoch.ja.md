# Open Embedded Probe — UART connection epoch同期候補

状態: **UART bindingの振る舞い候補**。この文書は、明確な接続開始を持たないUART byte streamで、hostとprobeが同じtransport sequence状態を開始するためのconnection epoch同期を整理する。

frame type、field配置、epoch token幅、timeoutおよびretry回数はまだ決定しない。

## 解決する問題

UARTではportをopenしても、次が一致しているとは限らない。

- hostとprobeが期待する次のtransport sequence
- 直前のDATAが上位へdelivery済みか
- UART bridge、OSまたはring bufferに以前のbyteが残っているか
- probeがresetしたか、以前のconnection stateを保持しているか
- hostだけが再起動または再接続したか

alternating-bit方式では、片側だけがstateを失うと、新しいDATAを以前のframeの重複と誤認したり、以前のframeを新しいDATAとしてdeliveryしたりし得る。

delimiterによるframe再同期はbyte境界を回復するが、hostとprobeの論理的な接続状態までは一致させない。

## 目的

connection epoch同期は、次を成立させるためのbinding-level手順とする。

1. 両端が以前のpartial frameとtransport sequence状態を終了する
2. 両方向の初期sequenceを一致させる
3. hostが、現在開始しようとしている同期への応答を識別できる
4. 同期が成立するまでDATAをOEP coreへ渡さない
5. 同期後にOEP endpoint確認を新しく実行できる状態にする

これは以前のOEP操作が実行されたかを確定する手順ではない。また、以前開始した操作を取消したり、probeの機能状態を初期化したりしない。

## 暫定方向

最小UART bindingでは、**host主導のSYNC / SYNC-ACK exchange**を第一候補とする。

```text
host binding                         probe binding
     |                                    |
     | --- SYNC(epoch token) -----------> |
     | <--- SYNC-ACK(same token) -------- |
     |                                    |
     | ===== connection epoch active ==== |
     |                                    |
     | --- OEP endpoint confirmation ---> |
```

hostがepoch tokenを選び、probeは同じ値を変更せず返す。tokenは認証情報ではなく、古いSYNC-ACKや別の同期試行を現在の試行と取り違えないためのopaqueな値である。

probeへ乱数生成または不揮発counterを要求せず、host側だけがtoken生成を担当できる形を優先する。

## Binding state候補

概念上、少なくとも次の状態を区別する。

| state | 意味 | DATAの扱い |
|---|---|---|
| unsynchronized | 有効なepochがない | 上位へdeliveryしない |
| synchronizing | hostがSYNC-ACKを待っている | 上位へdeliveryせず、現在のSYNCに関係しないframeを無視する |
| active | 同じepochと初期sequenceを共有している | stop-and-wait規則に従ってdeliveryする |
| failed | retry上限等により継続不能 | transport failureを上位へ示し、再同期までdeliveryしない |

`synchronizing`は主にhost側の状態である。probeは有効なSYNCを受けるまで`unsynchronized`に留まり、受けた後はSYNC-ACKを返して新しいepochを開始する。

## Hostの動作候補

新しい同期を開始するとき、host bindingは次を行う。

1. 以前の未確認送信frame、decoder途中状態およびsequence状態を破棄する
2. 新しいepoch tokenを選ぶ
3. DATAを送信せず、`SYNC(token)`を送る
4. 完全性検査を通過した`SYNC-ACK`のうち、現在のtokenと一致するものだけを受理する
5. timeout時は同じtokenのSYNCを再送する
6. 一致するSYNC-ACKを受けたら両方向のsequenceを初期値へ設定し、epochをactiveにする
7. OEP endpoint confirmationを新しいOEP requestとして送る

SYNC retryごとにtokenを変えない。同じ同期試行の応答がどのretryに対するものかを区別する必要はない。

host APIやOSが入力bufferの破棄を提供する場合は利用できるが、それだけを同期成立の根拠にしない。破棄操作と並行して到着するbyteや、USB-UART bridge内部に残るbyteが存在し得るためである。

## Probeの動作候補

probe bindingはreset後、DATAを受理できるactive stateから開始しない。

完全性検査を通過した`SYNC(token)`を受けた場合は次を行う。

1. partial frame、未確認送信frameおよび以前のsequence状態を終了する
2. tokenを現在のepoch識別値として保持する
3. 両方向のsequenceを定められた初期値へ設定する
4. `SYNC-ACK(token)`を返す
5. 新しいepochをactiveにする

以前の未確認responseを破棄しても、そのresponseに対応する機能操作を未実行へ戻したことにはならない。以前のhostから見た操作結果は不明のままであり、OEP側のrecovery規則で扱う。

### 同じtokenのSYNC再受信

SYNC-ACKが失われると、probeは同じtokenのSYNCを再受信する。

現在のepoch tokenと同じSYNCは、同じ同期試行の再送として扱い、同じSYNC-ACKを返す。既にactiveであっても、上位へDATAを再deliveryしたり、機能状態を初期化したりしない。

同じtokenを受けるたびにepochを作り直すと、遅延したSYNC retryによって正常なDATA exchangeを途中でresetする可能性があるため避ける。

### 異なるtokenのSYNC受信

異なるtokenの有効なSYNCは、新しいhost connection epochの開始要求として扱う。以前のtransport stateを終了し、新しいtokenと初期sequenceへ切り替える。

これは同じUART connectionを同時に複数hostが共有することを許可する規則ではない。最小UART bindingは、一つの物理streamに一つのactive hostを前提とする。

## Tokenに必要な性質

tokenは暗号学的な認証を提供しない。ただしhostは、古いbuffer内に残り得るtokenと偶然一致しにくい値を新しい同期試行へ使用する必要がある。

候補となる生成方法には次がある。

- hostの十分な乱数源から生成する
- 再利用間隔を保証できるcounterを使用する
- process固有値とcounterを組み合わせる

token幅は、wire overheadと偶然の再利用確率を実測・評価して決める。probeはtokenをopaqueなbyte列としてechoできればよく、数値演算や乱数生成を必要としない。

tokenをすべてのDATA frameへ付加するかは別の選択である。順序を保存する一対一のUART streamでは、SYNC境界以後のDATAだけを新しいepochとして扱えるため、最小案ではDATAごとのtokenを必須にしない。

frameの並べ替え、複数送信元の混在または接続を越えたdatagram遅延が起こり得るbindingでは、この前提を使用せず、各messageへのconnection識別または別のbinding規則が必要になる。

## SYNC frameの性質

SYNCとSYNC-ACKは通常のOEP logical messageではなく、UART bindingのcontrol frameとする候補である。

少なくとも次を満たす必要がある。

- 通常frameと同じ境界復元と完全性検査を使用できる
- 以前のtransport sequenceを知らなくても解釈できる
- 固定された小さい上限内で処理できる
- tokenを欠落なく対応付けられる
- 未知または非対応のbinding revisionをactive epochとして受理しない

SYNCへOEP機能一覧、製品情報または通常のcapability negotiationを入れない。同期後のOEP endpoint confirmationと情報取得がそれらを担当する。

binding revisionをSYNCへ含める場合も、そのrevision fieldを読み取るための最小framing自体は事前に共有されていなければならない。

## 順序に関する前提

最小案は、各方向のUART byte streamが送信順序を維持することを前提とする。

この前提では、hostからprobeへ残っていた古いbyteはSYNCより前に処理または破棄され、probeからhostへの古いresponseはSYNC-ACKより前に現れる。hostは同期中に現在のtokenと一致しないframeを受理しないため、以前のresponseでactiveにならない。

SYNCの前にprobeへ到達してOEP coreへdelivery済みとなった以前のrequestを、同期によって取り消すことはできない。そのrequestの結果がhostへ返らなければ、OEP操作状態は不明である。

下位実装が送信順序を維持しない場合、または別connectionのbyteを同じstreamへ混在させる場合は、この最小UART bindingの前提を満たさない。

## 同期を開始する条件

hostは少なくとも次の場合に新しいepoch同期を行う。

- portを新しくopenした
- host processまたはbinding stateを再初期化した
- probe resetを検出または推定した
- transport retry上限へ達した
- 連続したframe error等によりsequence状態を信頼できない
- baud rateまたはline settingの切替に失敗した

probeは少なくとも次の場合に`unsynchronized`へ戻る。

- probe自身がresetした
- decoderまたはtransport stateを継続不能として破棄した
- bindingが定めるconnection failureを検出した

単一frameのCRC failureだけで直ちにepochを破棄するか、通常のretryに任せるかはfailure thresholdと共に決める。

## OEP coreとの境界

bindingはepochがactiveになるまで、受信したDATAをOEP coreへ渡さない。

epoch成立後も、最初のOEP exchangeとしてendpoint confirmationを行う。SYNC-ACKだけを根拠に、相手がOEP endpointであること、core revisionが互換であること、または以前と同じprobe個体であることを仮定しない。

```text
UART framing synchronized
          |
          v
connection epoch active
          |
          v
OEP endpoint confirmation
          |
          v
capability / constraint discovery
          |
          v
function request
```

binding同期失敗はtransport failureである。正常なSYNC後のOEP非互換は、transport failureではなくOEP endpoint confirmationの結果である。

## Resetと操作結果

| 状況 | bindingの扱い | OEP操作の扱い |
|---|---|---|
| DATAを送る前にhost reset | 新しいepochを開始 | 未送信requestは存在しない |
| DATA送信後、ACK前にhost reset | 新しいepochを開始 | probeへのdelivery有無は不明 |
| ACK後、response前にhost reset | 新しいepochを開始 | 操作開始・完了状態は不明 |
| probe reset | `unsynchronized`から再開 | volatileなactivityや状態は失われ得る |
| SYNC-ACK喪失 | 同じtokenでSYNC retry | OEP requestはまだ送らない |
| retry上限超過 | epochをactiveにしない | transport failure |

新しいepochで同じOEP requestを再送するかはbindingが自動決定しない。再実行が安全か、activity照会を行うか、結果不明として利用者へ示すかはOEP request semanticsに従う。

## 暫定合意候補

- UART bindingはreset直後またはport open直後にactiveと仮定しない
- host主導のSYNC / SYNC-ACKを第一候補とする
- 現在の同期試行を識別するopaqueなepoch tokenを使用する
- SYNC retryでは同じtokenを使用し、probeは同じtokenへの応答をidempotentにする
- 異なるtokenのSYNCは以前のtransport stateを終了させる
- epoch成立までDATAをOEP coreへdeliveryしない
- sequence初期化はbinding同期の責任とする
- OEP endpoint confirmationはSYNC後に別途行う
- epoch変更によって以前の機能操作を取消したことにはしない
- epochを越えたexactly-onceを保証しない

## 比較実装による中間結果

非規定の[UART binding比較実装](../experiments/uart-binding/README.ja.md)へhost/probe roleとepoch stateを追加した。比較用tokenは4 byteとしたが、仕様値ではない。

host-arduino-core上で次を確認した。

- 初回SYNC後だけDATAをdeliveryする
- SYNC-ACK喪失と同じtokenのretry
- hostだけのresetと異なるtokenによる再同期
- probeだけのreset後に未同期DATAを拒否する
- 古いSYNC-ACKおよび以前のresponseをhostが無視する
- 新しいepochで両方向のsequenceが初期値へ戻る

ATmega328P向け測定用ELFでは、epoch同期を含むstop-and-wait構成はFlash 2,764 byte / static RAM 156 byteだった。epoch同期追加前の測定との差はFlash 686 byte / static RAM 10 byteである。測定harnessを含むため、最終実装量ではない。

## 次の検証

実UARTでは、port open時のDTR reset、OS input purge、USB-UART bridge bufferおよびACK turnaroundを別途検証する。

## この文書で決めないこと

- SYNC、SYNC-ACKおよびtokenのfield layout
- token幅と生成algorithm
- binding revisionの表現
- sequenceの幅と初期値
- timeout、retry回数およびfailure threshold
- baud rateとline settingの切替手順
- half-duplex UARTでの方向切替
- 認証、暗号化または不正hostへの防御
