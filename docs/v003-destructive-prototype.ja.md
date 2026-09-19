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
