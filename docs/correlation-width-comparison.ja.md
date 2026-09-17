# Open Embedded Probe — Request correlation幅と再利用の比較

状態: **非規定の比較案**。この文書は、初期共通logical protocolで明示するrequest correlationについて、8、16および32 bitの候補と安全な再利用条件を比較する。

field位置、byte order、初期値、予約値および採用幅はまだ決定しない。

## 幅と正しさを分ける

correlationの役割は、同じconnection contextとrequest方向で、resultを対応するrequestへ適用することである。必要な値空間は総request回数ではなく、同時に再利用できない値の数で決まる。

次の値は再利用できない。

- resultをまだ受信していないrequestの値
- timeout等によりresolutionが不明なrequestの値
- duplicateまたは遅延resultがまだ到着し得る、解決済みrequestの値
- response cacheが保持しているresultの値

したがって32 bitでも、wrapした値を古いresultが届き得る状態で再利用すれば誤対応し得る。8 bitでも、再利用不能な値が256未満であり、古いresultの到着可能性を終了できれば正しく運用できる。

## 候補比較

| 観点 | 8 bit | 16 bit | 32 bit |
|---|---:|---:|---:|
| 値の総数 | 256 | 65,536 | 4,294,967,296 |
| request/result各messageのfield | 1 byte | 2 byte | 4 byte |
| 一往復のwire費用 | 2 byte | 4 byte | 8 byte |
| 10 request/sで全値を一巡する時間 | 25.6秒 | 約109分 | 約13.6年 |
| 1,000 request/sで全値を一巡する時間 | 0.256秒 | 約65.5秒 | 約49.7日 |

一巡時間は単純な連番を休みなく使う場合の参考値であり、その時間後に必ず再利用可能または不可能になることを意味しない。安全性はbindingの遅延上限、cache、未解決requestおよびconnection epochに依存する。

### 8 bit

小さいheaderに有利だが、高rateまたは長いretention windowではすぐに同じ値へ戻る。最大同時request数が小さくても、timeout後の結果不明値を多数保持すると枯渇し得る。

交換境界が強く制約されたcompact profile、短命なconnection、または最大rateとretentionを共に制限する用途には候補となる。初期の汎用幅として採用するには、profile制約への依存が大きい。

### 16 bit

現在のbootstrap候補Bと通常routing実験で使用している幅であり、16 byte HID report内でもrequest/resultと小さいpayloadを共存させられる。同時requestと短期retentionに十分な余裕を持ちながら、32 bitよりmessageを2 byte短くできる。

一方、高rateで値を単純に回すだけなら一巡は速い。16 bitを選んでも、結果不明値を放置したまま無条件にwrapする実装は認められない。

### 32 bit

wrap頻度を大幅に下げ、host実装のallocatorを単純化しやすい。しかしwrapを実質的に遠ざけるだけで、connectionを越えたidentityや暗号学的nonceにはならない。

小さいHID/UART control messageでは16 bit候補よりrequestとresultを各2 byte大きくする。現在想定する最小probeの同時request数だけを理由に32 bitを必須化する根拠はまだない。

## 16 byte HID reportでの差

[Message header構成比較](message-header-layout-comparison.ja.md)のrole別仮layoutで、offered function requestを`role + operation + correlation + target reference`、resultを`role + resolution + correlation`とする。

| correlation幅 | request header | request payload残量 | result header | result payload残量 |
|---|---:|---:|---:|---:|
| 8 bit | 5 byte | 11 byte | 3 byte | 13 byte |
| 16 bit | 6 byte | 10 byte | 4 byte | 12 byte |
| 32 bit | 8 byte | 8 byte | 6 byte | 10 byte |

いずれも16 byte reportへ収まるが、32 bitでは16 bitより機能固有payloadが2 byte減る。transport fragmentationで補える場合もあるが、最小操作が追加往復を必要とする境界を変え得る。

Bootstrap候補Bの仮layoutでは16 bit時にrequest 10 byte、response 14 byteである。correlationだけを8 bitにすれば9/13 byte、32 bitにすれば12/16 byteとなる。32 bit responseは16 byte reportを使い切り、現在の仮fieldを増やす余地をなくす。

## 再利用条件

requesterは、候補値が少なくとも次のどれにも一致しないことを確認してから割り当てる。

1. 現在pendingなrequest
2. resolution不明として保持しているrequest
3. bindingまたはprotocolのduplicate window内にある解決済みrequest
4. 相手が再送またはcacheし得るresult

値を安全に再利用できないまま空間を使い切った場合、新しいrequestを開始せず、次のいずれかを行う。

- resultまたはduplicate windowの終了を待つ
- 明示的な同期により古いresultが到着しない状態を確立する
- connection contextを終了し、新しいcontextを確立する
- 将来定義する広いcorrelation profileへ切り替える

使用中の値を上書きしたり、最も古いpending requestを暗黙に破棄したりしない。

## Bindingとの関係

- HID response cacheは、次の有効requestがcacheを置き換えたことまたはresetで無効化されたことが明確になるまで、そのcorrelationを再利用不能にし得る
- UART stop-and-waitはframe duplicateを抑止するが、OEP requestの結果不明状態を解決しない。新しいepochでは以前のframeが届かない保証を再利用境界に利用できる
- TCP等では、同じconnection上で遅延resultが到着し得る間は値を保持する。connectionを閉じ、新しいcontextへ古いbyteが入らない場合はnamespaceを新しくできる

binding sequence、HID report ID、USB transfer番号またはTCP byte位置をcorrelation値として暗黙に流用しない。

## 現時点の方向

**16 bitを初期共通protocolの有力候補として、実験とlayout比較を継続する。**

これはwire幅の採用決定ではない。現時点では次の釣り合いがよい。

- 8 bitほど短い再利用周期へ依存しない
- 32 bitより小さいHID reportのpayloadを確保できる
- 現在のbootstrap、routingおよびmatcher実験を同じ幅で比較できる
- 値空間が不足した場合に上書きせず停止またはconnection更新できる

採用前に、最大同時request数、結果不明値の保持、duplicate windowおよびconnection更新との関係を確認する。8 bit compact profileや32 bit拡張を同じ初期仕様へ同時に入れることは、必要性が確認されるまで避ける。

## Allocator実験

[Message routing比較実装](../experiments/message-routing/README.ja.md)へ、固定pending slotから未使用値を探索するallocatorを追加した。4値の縮小namespaceを完全に保持した場合は使用中値を上書きせず枯渇し、1値をresolveしてretireした後だけその値を再利用した。8 bit全256値と16 bit全65,536値もallocate、resolve、retireしてwrap境界を確認した。

同じgeneric 16 bit内部実装へ8 bitまたは16 bitの上限を与えたbare ELFでは、code/RAM差はなかった。これは実装が同じ型と探索処理を使うためであり、wire上の1 byte差を否定しない。generic allocatorはATmega328PでFlash 1,120 byte、CH32V003でtext 812 byteだったが、protocolはこのalgorithmを要求しない。固定一件、bitmap、mapその他の実装でも、使用中値を再利用せず枯渇を明示的に扱えばよい。

## この文書で決めないこと

- 16 bitの正式採用
- zeroその他の予約値
- sequential、randomまたはgeneration付きallocator
- duplicate windowの時間またはrequest数
- correlation exhaustionを示すwire failure
- request deduplication keyとの共有
- connection再開時に以前のcorrelationを引き継ぐ方法

[Request correlationのretire条件](correlation-retirement-model.ja.md)で、pending、indeterminateおよびresolved-retainedを分け、binding保証から再利用可能性を判断する。
