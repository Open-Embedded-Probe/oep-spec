# 調査・移行メモ

[English](memo.md)

状態: **informativeな作業メモ**。このファイルはOEP仕様projectを開始するために使った背景を記録する。normativeではなく、判断内容が仕様とissue管理へ移った後に再編または削除できる。

## 出発点

OEPは、より広い調査repositoryである[wch-protocols](https://github.com/ch32-riscv-ug/wch-protocols)から分離した。元repositoryは、MCU protocol調査、USBとOSの実験、ESP32-P4 captureの実測、初期product設計議論の根拠資料として残す。

新organizationでは、platform非依存の契約と実装を分離する。

- `oep-spec`: protocol、registry、適合規則、PID方針
- `oep-probe-arduino`: Arduino firmware実装とplatform backend
- `oep-client-python`: Python library、CLI、bridge、初期conformance runner

既存調査は丸ごと複製せず、仕様へ要点を抽出する。実験logとhardware固有の性能資料は`wch-protocols`に残し、normativeな判断が実測に依存するときはOEP仕様から参照する。

## 引き継ぐ調査結果

### 異なるMCUでprobeを実装できる

既存調査により、RP2040とESP32-S3でUART、GPIO/reset、SWD、JTAGを実装できる見込みがある。時間制約の厳しいbackendはMCU固有になる。再利用する境界は、bitごとのhost往復や`digitalWrite()`だけのAPIではなく、batch化されたsequenceまたはtransfer engineである。

したがってprotocolはserviceの意味を共通化し、PIO、GPIO、SPI、RMT、DMA等のplatform固有実装を許容する。

### Capability discoveryがproductの中心になる

probeは選択したserviceだけを組み込んでよい。性能値と構成上限はMCU、firmware build、USB経路、resource割当によって変わる。clientはboard名の対応表ではなく、申告されたcapabilityからserviceを選択する必要がある。

ESP32-P4のlogic capture実験からは、一つの最大sample rateだけでは能力を表せないことも分かった。channel幅、channelごとの縮約、encoding cost、USB budget、trigger mode、resource共有によって受理できる構成が変わる。このためprotocolには、静的な限界記述と、構成を問い合わせてaccept/rejectを返す仕組みの両方が必要になる。

### 一つのengineを標準serviceと特殊serviceの両方で表現できる

logic analyzerは、範囲を絞ったportableなcapture serviceと、ESP32-P4固有の高機能なmixed-rate serviceを同時に宣言できる。拡張を理解するclientは後者を選び、一般的なclientは標準serviceを利用する。二つを独立engineとして同時openしないよう、代替関係または共有resource関係も宣言する必要がある。

### USB identity、USB layout、protocol capabilityは別の問題である

同じprotocolを、USB、既存USB-serial bridge、network経由で運べる。OEP USB descriptor profileとPID方針が必要なのは、firmwareがnative USB deviceのdescriptorを制御する場合だけである。

E062のWindows 11観測により、初期の仮説は訂正された。正常にinstall済みのdevice instanceは基本的に現在のdescriptorへ追随し、単機能とcompositeの切替やinterface functionの変更でもdriverを再bindできる。`bcdDevice`はdevice instance identityに含まれず、一般的なprofile selectorにはならない。一方でinterface pathや永続propertyには規律あるprofile・interface番号管理が必要であり、MS OS descriptorのregistry property変更には適切なvendor revision機構が必要になる。

この結果は、任意layoutの互換性costが消えたことを意味しない。protocol capabilityは自由に変えられるが、外部に見えるUSB layoutには登録済みprofileまたは合成規則を設ける。

### PID利用には割当元の了承と独立したgovernanceが必要である

Openmokoとpid.codesを、MCU非依存なOSS向けPID割当候補として調査した。想定する利用範囲は一つのfirmware imageより広く、複数MCUへのportと、場合によっては独立した準拠実装が一つのproject identityを共有する。この範囲を約束する前に、割当元から明示的な了承を得る必要がある。

MIT Licenseはproject VID:PIDの利用を許可するものではない。将来の`PID-USE.md`で、利用資格、identity規則、source公開要件、適合性、USB profile、非準拠利用の扱いを別途定義する。serial、vendor ID、独自に割り当てられたIDを使う実装は、project PID規則へ同意しなくてもOEPを実装できるようにする。

### 既存ecosystemはcoreの制約ではなくadapterにする

CMSIS-DAP、OpenOCD、SUMP、BeagleLogic、sigrok/PulseView、標準USB classには相互運用上の価値がある。host側adapterでOEP serviceと変換すれば、すべてのprobe firmwareやcore wire modelを既存protocol一つの制約へ合わせずに済む。

USB Audio、Video、CDC、DFU等のclass functionは、内部serviceをOS標準class interfaceへ投影できる。そのdescriptorで定義されるformatとtopologyはUSB profile側で管理し、OEP capability discoveryでは対応する内部serviceとresource関係を報告する。

## 引き継がない結論・避けること

- VID:PIDを完全な機能識別に使わない。OEPかどうかはhandshakeで確認する
- `bcdDevice`をdescriptor profileの区別に使わない
- 実現性確認に有用だったという理由だけで、すべてのreference probeへUART、SWD、JTAGを必須化しない
- 将来の全serviceが共有する単一global command ID空間を作らない
- 特定firmware libraryの利用を、protocol互換や将来のPID利用資格の必須条件にしない
- 共通PIDを認証、certification、security boundaryとして説明しない
- 実験で得た性能値をnormativeなcapability上限として写さない

## 未決の設計事項

次は意図的に未決のまま残す。

1. core messageのframingと表現形式
2. protocolおよびserviceのversion negotiation規則
3. 安定したdevice identity、implementation identity、USB serial形式
4. 標準service identifierの大きさとprivate namespaceのencoding
5. 最小capability directoryとserviceごとの詳細記述model
6. 共有resource、排他、動的availabilityの表現
7. 検証に使う最初のcontrol serviceとstream/batch service
8. 最初のUSB bootstrap profileとOSごとの発見方法
9. optionalな標準class functionのUSB profile合成規則
10. conformance levelとtestの管理主体
11. PID割当元と、了承された複数実装での利用範囲
12. PID利用許可、review、version/profile互換性の方針
13. captureのデータの持ち方の宣言。channelごとに並べる（planar）か、複数channelを同時に取った形のまま
    sampleごとに並べる（interleaved）か。probeは取得したときの形のまま送って詰め替えず、hostが詰め替える方が
    probeは楽になる見込み（2026-09-25のメモ。[captureの提案](docs/logic-capture.ja.md) §3.0, §3.2）
14. probeから送る通知ができると、割り込み系の出来事も送りたくなる。fixtureのGPIOの割り込み（エッジ）、probeの
    ハートビート（生きていること、再起動したこと）など（2026-09-25のメモ。[v1 wire](docs/v1-core-wire-delta.ja.md) §4.5）
15. **シリアルをCDCで転送する口**（2026-09-25のメモ）。LinkEからの置き換えを考えると、targetのUART（またはtargetの
    コンソール）をOSのシリアルポート（CDC）として見せる機能が無いと、今の導線（ArduinoのSerial Monitor、書き込み後の
    動作確認）に乗らない。OEPのシリアルパケットだけだと、Arduinoとのつなぎ込みや動作確認が面倒。
    - 既にある考え方: [セッションと排他](docs/session-and-exclusivity.ja.md)の「コンソール専用の口」（OEPの制御の外の
      CDCで、Monitorが占有する）。中身は固定ピンのUARTの素通し、OEPで割り当てたピン、targetのコンソール（dmseq）の
      どれでもよい、とだけ書いてあり、**何を流すかを決める操作と、実装が無い**。
    - 決めること: 口に流すものを選ぶ操作（`oep.fixture.uart`の線、`oep.target.console`のストリーム、のどれを結ぶか。
      baudの扱い。CDCのline codingをUARTに写すか）、USBの構成（P4 HSならvendor bulkとCDCの複合デバイス）、
      下の16の永続化との関係（電源を入れたらすぐ前回の結び付けで流れること）。
    - **ch32rvセッションの意見**（2026-09-25）: coreではなく独立したインターフェース（例 `oep.probe.cdc`、revision 1）に
      して、持たないprobeはlistに出さない。操作は`bind(port, source, …)`の1つ（source: 0 なし / 1 fixture.uart / 2
      target.console（connection、mechanism）/ 3 固定ピンの素通し、ロック要）。consoleもuartの受信も読んでも消えないので、
      CDCは読み手が1人増えるだけでOEPのhostの読みとぶつからない（この性質は崩さない）。line codingはfixture.uartを
      結んだときだけUARTに写し、bindのflagで「line codingに従う / configureのまま」を選ぶ（開いただけで別のhostの
      baudを変えないため）。**DTR / RTSは転送を止めない・targetをresetしない（既定）**、resetに使うならbindのflagで明示。
      1200 baudのtouchも特別扱いしない（LinkEはDTRでSDIの転送を止める実例あり）。PC → targetはCDCとOEPのwriteが
      混ざったときの順序を未定義とする。describeにCDCのUSB interface番号と今のbindを出し、複合デバイスのinterfaceの
      並びは固定（hostがOSのポートとprobeを結び付けるため）。ch32rvのmonitor / runはOEPのconsole / uartのreadを使う
      予定で、CDCはArduinoのSerial Monitorと人が端末で見る用途。
    - **ユーザーの前提（2026-09-25、ch32rvセッション経由）**: CDCは複数作れて、物理UARTのほかにSDIやDMSEQなど、いろいろな
      ものを繋げられる想定。これを受けたch32rvの意見: 口の数はUSBのenumerationで決まるので、describeに口の数と口ごとの
      USB interface番号を出し、bindは口に何を流すかを変えるだけ。sourceは 0 なし / 1 fixture.uart（番号）/ 2 targetの
      console（connection + mechanism。mechanismはconsoleの番号をそのまま使うので、SDI、DMDATA、DMSEQ、RTTが新しい番号
      なしで入る）。**同じconnectionでDMのmailbox（DATA0 / DATA1）を使うmechanismは1つだけ**（dmdata / dmseq / sdiは
      同時に成り立たない）なので、開いているconsoleと違うmechanismを求めるbindはrejected。同じstreamを複数の口とOEPの
      readで読むのは「消えない読み」でそのまま成り立つ。SDIのようにprobeがDMをpollingするmechanismはhostのDMI操作と
      線を取り合うので、hostのdmi / runの間はpollingを止めるか間に挟むかを規範にする。起動直後や、connectionを失った
      後は、consoleを結んだ口は閉じずに保留（connectionができてconsoleが開けば流れる。Serial Monitorを開いたままtargetを
      resetしても流れ続ける）。bit-bangのlow-speed USBのprobe（V003）はbulkが規格外でCDCを持てないので、口の数0と出す。
16. **設定の永続化**（2026-09-25のメモ）。LinkEのようにピンが固定なら要らないが、自由な配線だと、探してピンを見つける
    ところまではできても、probeをリセットすると設定が消える。
    - 候補: CDCの設定（15の結び付け）、前回つないだアダプタ（target）の種類とピン（線の組、NRST）、ピンの目印（ラベル）を
      probeに保存し、起動時に自動で設定する。
    - 決めること: 何を保存するか（planそのものか、ラベルと「前回の線」だけか）、いつ書くか（hostの明示的な保存の
      操作か、成功したattachのたびか）、起動時に自動で何をするか（planの再適用、attachまではしない、など）、
      保存した内容を読む・消す操作、保存先（NVS / flash）の書き換え回数。describeで宣言するラベル（core tag 0x46）と
      の関係（保存したラベルを宣言に出す）。
    - v1 のwireには足すだけで入る見込み（coreの0x01〜0x0Fかセッションの範囲に操作を足す、またはインターフェースを
      足す）。固める前に番号の置き場だけは確かめる。
    - **ch32rvセッションの意見**（2026-09-25）: 書くのは**hostの明示的な保存だけ**（attachのたびに書くと書き換えが増え、
      試しの誤ったピンが残る。同じ内容なら書かない）。**起動時の自動の動作はplanの再適用とCDCのbindまで。attachはせず、
      targetの線に能動的な信号を出さない**（NRSTも駆動しない。E164のようにattachだけで止まるtargetがある。配線を
      変えた後の古いplanで出力を駆動するとぶつかる）。保存はplan + ラベル + CDCのbindを1つの塊にし、形式の版とhashを
      付ける。firmwareの更新で読めなくなったら適用せず、describeで「保存はあるが読めない」と出す。操作はsave / read /
      eraseの3つとdescribeの「保存あり・適用済み・hash」。hostはhashを比べて同じなら何もしない（1コマンド1プロセスの
      hostが毎回planを送らずに済む）。保存したラベルはdescribeのラベル（core 0x46）に出し、hostは`label:<name>`で
      probeを選べるようにできる。独立したインターフェース（例 `oep.probe.config`）にして、保存先の無いprobeは持たない。
    - **ユーザーの前提（2026-09-25、ch32rvセッション経由）**: 永続化しにくいV003などもあるので、そこも考慮する。これを受けた
      ch32rvの意見: 保存は「ある / なし / 小さい」を認め、describeに保存できる最大byte数を出す（0 = 保存なし。V003は
      flash 16 KiBでEEPROM / NVSが無く、書けるのはflashのpage（64 B）かoption byteのData0 / Data1の2 byteくらい）。
      **小さいprobeは「planの識別子」（hostが選ぶu32のplan_id、またはhashの先頭）だけを保存**し、planの中身はhostが持つ
      （describeのplan_idが違えばhostがplanを送り直す。大きいprobeは中身ごと保存して、hostが無くても起動時に再適用できる）。
      自分のflashを書く間はprobeの仕事（USBを含む。bit-bang USBのV003では特に）が止まるので、saveは明示的な操作のとき
      だけ、実行中はほかの要求を受けない（completedまで待たせる）と書く。同じ内容なら書かないことに加え、saveの回数を
      describeか応答で数えられると、hostが書きすぎを警告できる（任意）。

関係するnamespaceとlifecycle規則を合意するまで、数値registry値を割り当てない。

## 推奨する作業順序

1. 用語、role、scope、normative languageを合意する
2. discoveryとcapability matchingのuse case・failure caseを書く
3. wire encodingを選ぶ前にcore state modelを定義する
4. service/private extensionのidentityとversioningを定義する
5. 意図的に異なる二つのprobe buildと、一つのclient選択algorithmをmodel化する
6. portable版とESP32-P4固有版のlogic captureをextensionの試験例としてmodel化する
7. 最小USB bootstrap profileを選び、Windows、Linux、macOSで検証する
8. 最初のframing draftと同時に機械可読test vectorを公開する
9. 同じdraftを`oep-probe-arduino`と`oep-client-python`で実装する
10. 単なる別board wrapperではなく独立した根拠になる段階で、二つ目の実装ecosystemを追加する
11. conformance claimを定義し、`PID-USE.md`のdraftを作る
12. 共通PIDを申請または利用可能と約束する前に、選択した割当元へ想定範囲を確認する

## 元資料の候補

`wch-protocols`の次のファイルを出発点とする。これら自体は仕様ではない。

- [probe product concept](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/probe-product-concept.ja.md)
- [Arduino probe protocol実現性](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/arduino-probe-protocol-feasibility.ja.md)
- [probe実現性gate](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/probe-feasibility-gates.ja.md)
- [PID取得roadmap](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/pid-acquisition-roadmap.ja.md)
- [OSS USB PID申請調査](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/oss-usb-pid-application-report.ja.md)
- [USB host descriptor persistence](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/usb-host-descriptor-persistence.ja.md)
- [E062: 同一identityでのUSB layout変更](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/experiments/e062_usb_same_identity_layout_change/README.ja.md)
- [ESP32-P4 logic analyzer調査](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/p4-logic-analyzer-investigation.ja.md)
- [ESP32-P4 probe roadmap](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/p4-probe-roadmap.ja.md)
- [PulseView連携](https://github.com/ch32-riscv-ug/wch-protocols/blob/main/references/pulseview-integration.ja.md)

結論をOEPへ移すときは、調査経緯全体を複製せず、仕様には結果となる規則を簡潔に記載し、根拠資料へリンクする。
