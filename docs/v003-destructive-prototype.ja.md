# V003開発プローブ破壊的prototype

状態: **非規定・破壊的変更前提の実装計画**。このprototypeはOEP仕様への適合性や後方互換性を
主張しない。実装からprotocol上の不足が見つかった場合、wire形式、service境界、repository内の
APIおよび保存dataをすべて破棄して作り直してよい。

## 目的

無印ESP32とUIAPduino Pro Micro CH32V003 V1.4で成立した既存fixtureを、組合せ固有のASCII
commandではなく仮のOEP共通message、能力公開およびservice requestから操作できるようにする。

成功条件は「現在の実装を残すこと」ではなく、次を実機で判断できることである。

- V003関連機能をOEPの概念modelへ無理なく分離できるか
- Python hostとArduino probeを組合せ固有のcommand parserなしで接続できるか
- 製品HID、SWIO direct flashおよびfixture peerを異なるcommunication path/serviceとして表せるか
- SWIO backendをRVSWD backendへ差し替えてもserviceの意味を保てるか
- 実装で判明した不足を上流の要求、情報modelおよびinteractionへ還流できるか

## Prototypeの立場

- protocol identity、field値、header、function reference、error codeおよびpayloadは仮割当とする。
- 保存済みcapture、client APIまたはfirmwareとの互換性を維持しない。
- production firmware、一般利用可能なPIDまたはOEP準拠表示には使用しない。
- 既存のE129～E132とUIAPduino HILを比較基準として残し、prototypeが失敗しても復旧経路を失わない。
- 一つのhostと一つのprobeだけで通った段階を「相互運用達成」と呼ばない。まずservice境界の検証とする。

## 段階

### P0: 縦断経路

UART binding上で次を通す。

1. endpoint確認
2. prototype revision、実装名、個体情報およびmessage上限の取得
3. offered function一覧とconstraintの取得
4. function request/resultのcorrelation
5. 未知function、未知operation、payload不正、現在利用不能および実行失敗の区別

既存のbootstrap、UART stop-and-waitおよびmessage routing比較実装を出発点とするが、数値割当を
仕様として固定しない。

### P1: V003 control

最初のtarget serviceは次を分けて公開する。

| service候補 | 操作 | 既存比較対象 |
|---|---|---|
| target debug session | attach、halt、resume、状態取得 | E123～E129 |
| target memory | 32 bit read/write、bounded block read | E126、E132 `S/V/v` |
| target boot control | userへ正規化、製品bootloaderへ移行 | E129、E132 `N/B` |
| target flash | 範囲確認、64 byte page書込み・照合、image完了 | E130、E131 `W/V` |

UIAPduino固有のPD4操作と製品boot条件はboard procedureとし、汎用SWIO transportの意味へ混ぜない。
外部RESET線はfallback capabilityであり、通常経路の必須条件にしない。

### P2: UIAPduino release fixture

UART console、GPIO、ADC刺激、I2C targetおよびSPI targetをoffered functionとして公開し、現在の
[`uiapduino_fixture`](https://github.com/ch32-riscv-ug/ArduinoCore-CH32/tree/main/tests/manual/uiapduino_fixture)をOEP clientから
実行する。channel束縛、UART兼用pin、I2C/SPI排他および実際に採用した条件をresultへ残す。

製品applicationの書込みは標準HIDをexternal bindingとして使用できる。OEP側のboot移行成功と、
external consumerによるHID書込み成功を別の結果として扱う。比較用にSWIO direct flash serviceも
残し、同じimageを二経路で投入できることを確認する。

### P3: RVSWD横展開

V003で使用した上位serviceの意味を維持し、target-link backendだけをRVSWDへ差し替える。
別chipでattach、memory、flash、resetおよび最小fixture試験を実行する。

この段階でhostがchip名による分岐を必要とした場合、その知識がfunction definition、probe側
algorithm、board manifestまたはhost toolのどこに属するかを再検討する。V003固有payloadを名前だけ
変えてRVSWDへ流用しない。

## 最初から実装しないもの

- 全OEP機能と全interaction role
- wire互換性またはversion migration
- 複数同時request、notification、continuous data flow
- USB HID/vendor binding、network bindingおよび一般PID
- 全WCH familyのflash algorithm
- security、認証、remote network公開
- production向けの電気的保護やconnector規格

## 実装repository

- `oep-probe-arduino`: ESP32 probe firmware、仮protocol core、V003 SWIO backend
- `oep-client-python`: 仮UART binding、能力取得、V003/fixture orchestration、CLI
- `oep-spec`: 非規定layoutの比較、要求への還流、実機test vectorと判明した反例

prototype固有の数値割当は実装repositoryで管理し、規範仕様の割当と誤認させない。採用判断が出るまで
本文書と実装には`prototype`または`experimental`を明記する。

## 最初の実機完了条件

同じESP32/V003配線で、Python OEP clientから次を順に実行できること。

1. endpointとoffered functionを取得する
2. V003のdebug状態を取得する
3. user modeへ正規化する
4. 製品bootloaderへ移行し、hostが`1209:b803`を別途確認する
5. bounded memory readを行う
6. 64 byte pageまたは小さいfixture imageを直接書込み、read-back verifyする
7. UART/GPIO/I2C/SPIのうち少なくとも一つをoffered function経由で実行する
8. 各操作のrejection、開始後failureおよびcompletedを取り違えない

この完了条件に届くまで、既存fixtureを削除またはOEP版へ一本化しない。

## P1途中結果（2026-09-20）

無印ESP32のGPIO16とV003 PD1のSWDIOだけを使用し、仮TargetControl functionで次を実機確認した。

1. hostがendpoint確認後、実装済みTargetControlだけをoffered functionとして取得する
2. request/resultのcorrelationとoffered function referenceを照合する
3. V003へattach/haltし、FLASH `STATR`からstart modeとboot statusを取得する
4. RAMへ短い処理を注入し、CPU自身のsystem resetによってuser modeへ正規化する
5. 同じ方式で製品bootloaderへ移行し、Windows側で`1209:b803`の再列挙を確認する
6. TargetMemoryでV003 flashの`0x08000000`からbounded readを行う

GPIO23の外部RESET線は使用していない。仮resultではrequestを開始しなかった`rejected`と、開始後の
成功または失敗を持つ`completed`を分けた。数値割当とpayload配置は非規定である。

この試作により、状態取得が単純な観測ではないことも判明した。現在のV003実装はSWDIO attachと
haltを行わなければ対象registerを読めず、status結果の仮flagsでattached/haltedを返している。
状態取得後に自動resumeするか、debug session開始と状態取得を別操作にするか、halt済み状態を
明示的なsession stateとして扱うかは未決定である。少なくとも汎用の「副作用なしGetStatus」として
仕様化してはならない。

最初のmemory操作は4 byte aligned、4～32 byteのreadに限定した。この制約は64 byteの仮message
上限と現在のword readerから導いた実装値であり、TargetMemoryの一般仕様候補ではない。実機では
flash先頭16 byteを取得でき、TargetControlと同じbackendがtarget-link処理を共有できることを
確認した。

TargetFlashでは`address + 64 byte page`を一つの論理requestとして試した。6 byte function headerを
含めると当初の64-byte message上限を超えるため、UART prototypeの論理上限を96 byteへ変更した。
この結果はHID等の一packetへ収める要求ではなく、bindingの分割・再結合後に共通protocolが同じ
messageを見るという層境界の試験入力になる。

実機では`0x08003fc0`のerase、program、backend内verify、および独立したTargetMemoryによる
64-byte read-backが成功した。独立readの初回には、SWDIO/DMIがerrorを返さず古い`DATA0`を
成功値として返す事象を観測した。同じwordの2回連続一致を要求すると正しい内容を取得できた。
このretryと安定化はtarget-link backendの責任であり、OEP requestの再実行や複数resolutionとして
hostへ見せない。

Fixture側ではread-onlyのdigital inputを最初の`FixtureGpio`操作として追加した。board procedureが
許可した14本だけを対象とし、ESP32 boot strap、SWDIOおよびRESETを任意pin番号で操作できない
ようにした。実機request/resultでGPIO14の変化は観測できたが、V003側の既知出力commandと同期した
controlled testはまだ行っていない。汎用GPIO functionと、特定boardのpin allowlistおよび試験手順を
別の層に置けるかを次に確認する。

FixtureUartではinstanceが持つRX/TX pinと、hostが要求するbaudrateを分け、probeがactual baudrateを
返す仮構成を試した。writeとread-availableはapplicationの行形式を解釈せずbyte列を運ぶ。実機で
V003の`PING`/`PONG`が成立し、未知commandに対するpeerの`ERROR command`もそのまま取得できた。
peer applicationの拒否をOEP requestのrejectedやUART転送failureへ変換しない境界を維持できた。

13,780 byte imageの連続page書込みでは、書込み済みpageに対するverify偽陰性と、page内の一部wordが
実際に`FF`のまま残るfailureの両方を観測した。仮completed/failureへ処理段階の診断byteを付け、
独立readで両者を区別した。既に全内容が一致するpageは成功としてeraseを省略できるが、部分一致を
成功にしてはならない。timeoutやfailureを共通protocolが自動retryする根拠にはせず、page操作の
再実行可能性と上限はTargetFlash定義またはhost tool側で明示する必要がある。

製品HIDからfixture imageを復旧した後、FixtureUartでtarget pin 7および9をLOW/HIGH/LOWへ駆動し、
別のFixtureGpio requestでESP32 GPIO27および14として一致することを確認した。これにより最初の
実機完了条件に含めた「少なくとも一つのfixture function」は、UARTとGPIOを跨ぐcontrolled testで
成立した。UART byte転送、peer application command、GPIO観測を一つの機能へ結合せずに実行できた。
