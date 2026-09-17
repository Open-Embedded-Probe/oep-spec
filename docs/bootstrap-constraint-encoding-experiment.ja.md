# Open Embedded Probe — Bootstrap constraint encoding実験

状態: **非規定の比較案**。この文書は、bootstrap responseを小さく保ちながら、16 bitをOEP logical message長のprotocol上限にしない表現を比較する。field幅、予約値、byte orderおよびdetail operationはまだ割り当てない。

## 比較する表現

| 候補 | Bootstrapで使う幅 | exact値 | 大きい値の扱い |
|---|---:|---|---|
| 固定16 bit | 2 byte | 0〜65,535 | 65,535を超えられない |
| 固定32 bit | 4 byte | 0〜4,294,967,295 | 32 bitをprotocol上限にする |
| 32 bit可変長整数 | 1〜5 byte | 0〜4,294,967,295 | response長とparser pathが増える |
| 16 bit summary + detail | 2 byte | 0〜65,534は直接exact | 予約値でdetail取得を要求する |

固定幅を広げる方式は一往復でexact値を返せるが、最小HID reportと小さいprobeにも常に追加幅を要求する。可変長方式は小さい値を短くできるが、bootstrap response自体を可変長にするか最大幅のbufferを持つ必要がある。

## 16 bit summary + detail候補

実験では次の意味を仮定する。

- `0..65534`: probeが受信できるexactな最大logical message長
- `65535`: 少なくとも65,535 byteを受信できるが、それを超えるexact値にはconstraint detail取得が必要

予約値は「無制限」や「不明」を意味しない。detail取得前にhostが安全に送れる長さは65,535 byteまでである。より大きいmessageを送りたいhostは、同じconnection contextでexact constraintを取得してから使用する。

この方式では小さいprobeのresponse形状を変えず、16 bitをprotocol全体の上限にしない。大きなmessageを実装するprobeと、それを必要とするhostだけが追加round tripとdetail用整数表現を実装する。

## Byte数への影響

候補Bの仮responseは現在14 byteで、うち2 byteをmessage上限に使用している。

| 表現 | Core response最大 | HID外側に必要なdata | rv003usb現revisionで安全な固定report | UART derived-length wire概算 |
|---|---:|---:|---:|---:|
| 固定16 bit | 14 byte | 16 byte | 16 byte | 19 byte |
| 固定32 bit | 16 byte | 18 byte | 20 byteへpadding | 21 byte |
| 32 bit可変長整数 | 13〜17 byte | 15〜19 byte | 最大20 byteへpadding | 18〜22 byte |
| 16 bit summary + detail | 14 byte | 16 byte | 16 byte | 19 byte |

HID外側はreport ID 1 byteとeffective length 1 byteを含む。rv003usb `5cddcd5e1d46`は全長を8で割った余りが1〜3となるOUT reportの末尾をuser callbackへ渡さないため、18または19 byteを固定reportにする場合は20 byteへのpaddingを仮定した。これはHID一般の制約ではない。

## Logic検証

`bootstrap_limit_summary`の純粋ロジックをhost-arduino-coreで試験した。

- 0〜65,534の全値がsummaryからexactに復元できる
- 65,535、65,536、1 MiBおよび32 bit最大値はすべてdetail必須になる
- detail取得前も65,535 byteまでは安全な下限として利用できる
- detail取得前に65,536 byte以上を許可しない

この試験は32 bitを最終detail表現として採用するものではない。detail側は将来の共通整数encodingまたはconstraint表現を利用できる。

## 比較上の方向

最小bootstrapでは16 bit summary + detailが有力である。小さい実装ではexact値を一往復で返し、高能力実装の上限だけを別取得にできるためである。

ただし、次は未決定である。

- 予約値と境界値
- detail operationをbootstrap namespaceに置くか、通常の提供情報取得に含めるか
- hostとprobeで送受信上限を別々に示すか
- logical message上限以外のconstraintにも同じsummary方式を使うか
- detail整数の最大幅とencoding
- bootstrap直後に保証する共通最小message長
