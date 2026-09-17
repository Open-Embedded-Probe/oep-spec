# Open Embedded Probe — UART frame layout比較

状態: **非規定layoutの比較結果**。この文書は、COBS系delimiter framingでpayload lengthを明示する方式と、frame境界から導出する方式を比較し、最小UART bindingの実験候補を選ぶ。

frame type割当、bit配置、CRC polynomial、最大payloadおよび正式なwire encodingはまだ決定しない。

## 比較する二方式

どちらも次を共通条件とする。

- 最大payloadは比較用に32 byte
- 1 byteにframe typeと1 bit transport sequenceを仮配置
- CRC-16をframe headerとpayloadへ適用
- COBS系encodingと`0x00` delimiterを使用
- 一つのDATA frameへ一つのlogical messageを格納

### A: 16 bit explicit length

初期のstop-and-wait比較実装で使用した。

```text
type/sequence: 1 byte
payload length: 2 byte
payload:        N byte
CRC:            2 byte
```

decode後overheadは5 byteである。

### B: Delimiter-derived length

比較用alternativeではlength fieldを持たない。

```text
type/sequence: 1 byte
payload:        N byte
CRC:            2 byte
```

decode後frame全体の長さから3 byteを除いた値をpayload lengthとする。decode後overheadは3 byteである。

## Length fieldを省略できる理由

COBS系framingではdelimiterがframe終端を与える。receiverは次を別に検査する。

- encoded frameが実装上限を超えていない
- COBS decodeが正常に完了した
- decode後frameが最小長以上である
- 導出payload長がprofile上限以下である
- CRCがheaderとpayloadに一致する

この条件では、16 bit lengthはframe境界の発見に使われず、decode後の実長と一致するかを確認する冗長fieldになる。

length fieldが破損、欠落または挿入を検出する唯一の根拠でもない。それらはframe decode、上限およびCRCで検出する。

## 比較結果

32 byte上限ではdecode前のraw frameが254 byte未満なので、COBS系encoding overheadを1 byte、delimiterを1 byteとして比較できる。

| 項目 | explicit length | derived length | 差 |
|---|---:|---:|---:|
| decode後overhead | 5 byte | 3 byte | -2 byte |
| payloadなしACK | 7 byte | 5 byte | -2 byte |
| 4 byte token SYNC | 11 byte | 9 byte | -2 byte |
| 10 byte bootstrap request | 17 byte | 15 byte | -2 byte |
| 14 byte bootstrap response | 21 byte | 19 byte | -2 byte |
| 最大32 byte DATA | 39 byte | 37 byte | -2 byte |
| bootstrap request/responseと各ACK | 52 byte | 44 byte | -8 byte |
| incremental decoder state | 40 byte | 38 byte | -2 byte |
| 最大wire保持buffer | 39 byte | 37 byte | -2 byte |

stop-and-wait state全体をderived方式へ移植した実測では、stateが97 byteから93 byteへ4 byte減った。

最大payloadを仕様として決める前の資源量比較として、同じstop-and-wait構造をcompile-timeに変更して測定した。

| 最大payload | 最大COBS系wire | stop-and-wait state | 測定用ELF static RAM |
|---:|---:|---:|---:|
| 8 byte | 13 byte | 45 byte | 50 byte |
| 16 byte | 21 byte | 61 byte | 66 byte |
| 32 byte | 37 byte | 93 byte | 98 byte |
| 64 byte | 69 byte | 157 byte | 162 byte |
| 128 byte | 133 byte | 285 byte | 290 byte |

この比較用stateは受信decoderと未確認送信frameを別々に保持するため、最大payloadを1 byte増やすとstateが2 byte増える。ELFのRAM値は共通の小さいharnessを含むが、Arduino core、UART ring buffer、OEP coreおよびstackを含まない。buffer共有等で傾きが変わる可能性があるため、この表だけで最大payloadを決定しない。

## ATmega328P code size比較

同じ14 byte messageをencodeし、decoderへ戻す測定用ELFを、avr-gcc 7.3.0、`-Os`、section garbage collectionありで比較した。

| codec | Flash | static RAM |
|---|---:|---:|
| explicit length | 1,294 byte | 94 byte |
| derived length | 1,178 byte | 90 byte |
| 差 | -116 byte | -4 byte |

ELFには小さい`main`、14 byte test message、最大wire bufferおよびdecoder stateを含む。Arduino core、UART driverおよびstop-and-waitは含まない。

derived版decoder単体のcode symbolはexplicit版よりわずかに大きかったが、encoderと補助処理を含むELF全体では小さくなった。この差を別toolchainでも同じと仮定しない。

stop-and-wait、epoch同期およびpartial frame abortを含む構成も同じtoolchainでderived方式へ移した。explicit方式のFlash 2,816 byte / static RAM 156 byteに対し、derived方式はFlash 2,696 byte / static RAM 150 byteだった。差はFlash -120 byte / static RAM -6 byteである。測定harnessを含む中間比較であり、最終実装量ではない。

## 破損・再同期試験

host-arduino-core上でderived方式について次を確認した。

- 0から32 byteまでの全payload長をround tripできる
- explicit方式より各frameが常に2 byte短い
- 最大長frameの全byte位置について、一byte破損後に正常frameへ再同期する
- 最大長frameの全byte位置について、一byte欠落後に正常frameへ再同期する
- 最大長frameの全byte位置について、一byte挿入後に正常frameへ再同期する
- delimiter欠落で直後のframeが巻き込まれても、その次のframeで回復する

この試験はCRC方式の数学的な完全性証明ではない。現在のbounded codec実装が不完全frameを正常deliveryせず、delimiterから再同期できることを確認する。

## Explicit lengthが有利になり得る場合

次の場合はlength fieldを持つ別layoutが有利になり得る。

- delimiter framingを使わず、lengthだけでframe境界を決める
- transport fragmentationの総長をframe headerで表す
- payload以外の可変領域を複数持ち、個別長が必要になる
- hardware DMA等が事前lengthを必要とする
- delimiter到着前に受信完了予定を判断する必要がある

これらは現在の最小COBS系UART control frameには必須ではない。将来の大容量profileが異なるlayoutを持つことを妨げない。

## CRC幅の比較

UARTはUSBやTCPと異なり、OEP frameの下に必ずしも完全性検査を持たないため、frame全体を覆うCRCを第一候補として維持する。

- CRC-8はCRC fieldを1 byte短縮できる
- CRC-16はCRC-8より偶発的な未検出誤りを大きく減らせる
- CRC-32はさらに強いが、小さいcontrol frameでは2 byte増える

理想化した一様誤りに対する偶然一致は、CRC-8で約1/256、CRC-16で約1/65536である。実際のburst error検出特性はpolynomialとframe長に依存する。

1 byteの差よりUART上の完全性を優先し、最小候補ではCRC-16を第一候補とする。ただしpolynomial、初期値、反転、byte orderおよびtest vectorはまだ決定しない。CRCは認証や改ざん防止を提供しない。

## COBS系encodingとSLIP型escapeの比較

現在の32 byte上限では、COBS系encodingはpayload内容によらず最大wire長を小さく固定でき、`0x00` delimiterから再同期できる。

同じderived length raw frameを、`0xc0` delimiterと`0xdb` escapeを使うSLIP型alternativeにも載せて比較した。

| 項目 | COBS系 | SLIP型 |
|---|---:|---:|
| 最大32 byte DATAのworst-case wire長 | 37 byte | 71 byte |
| incremental decoder state | 38 byte | 38 byte |
| 最大wire保持buffer | 37 byte | 71 byte |
| 測定用ELF Flash | 1,178 byte | 1,018 byte |
| 測定用ELF static RAM | 90 byte | 124 byte |

SLIP型は同じ測定用ELFでFlashが160 byte小さかった。escape対象を含まないframeはCOBS系より短くなり得る一方、data内容によってwire長が変わる。worst caseでは再送用wire bufferとline timeがほぼ二倍になる。測定RAMの34 byte差は最大wire bufferの差と一致する。

host-arduino-core上では、SLIP型についても0から32 byteのpayload、全byteがescape対象となるpayload、および最大試験frameの各byte位置での一byte破損・欠落・挿入後の再同期を確認した。これは任意の複数誤りに対する保証ではない。

両方式について、encoderへ必要量ちょうどのbufferと一byte不足するbufferを与え、境界外を書き換えないことも確認した。また固定seedで256通りのnoise列を生成し、上限超過や不完全escapeを含み得るnoiseをdelimiterで区切った後、続く正常frameを受信できることを確認した。

最小RAM、固定上限およびtimeout計算の単純さを重視し、現在の主要候補ではCOBS系を維持する。ただしFlashと平均wire長を優先するprofileでSLIP型が有利になり得るため、正式encodingの決定とはしない。

254 byte以上を扱う将来profileでは、現在の小さい比較実装をそのまま使用せず、連続非zero blockを含む完全なCOBS処理と上限を再検証する。

## 暫定判断

最小UART control channelの次の実験候補を次とする。

- payload lengthはdelimiterから導出し、明示length fieldを置かない
- frame全体を覆うCRC-16を維持する
- COBS系encodingとdelimiterによるbounded frameを維持する
- 最大payloadは引き続き未決とし、32 byteは比較値としてだけ使用する
- 大容量または異なるtransport profileが別layoutを持つことを許容する

これは正式なwire format採用ではない。stop-and-wait、epoch同期およびpartial timeoutをderived layoutへ載せた実験では、既存の再送、重複抑止、同期および双方向通信試験を維持したまま、wire長と実装量を削減できた。

## この文書で決めないこと

- frame typeとflagのbit割当
- transport sequenceの幅
- 最大payload
- CRC-16の具体parameter
- 正式なCOBS variant
- COBS系とSLIP型の最終選択
- byte order
- UART以外のbindingで同じlayoutを使用すること
