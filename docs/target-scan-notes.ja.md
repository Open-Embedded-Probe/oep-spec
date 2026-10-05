# target ごとの scan と attach の記録（ピンの探し方、つなぎ方、つまずき）

状態: **記録**（規範ではない。追記は自由）。2026-10-02 作成。チップ名、ボード名、治具、日付つきの経験をそのまま書く。
規範は [線とデバッグ](oep-if-debug.ja.md)（scan、attach、reset TLV、target_id）と [probe の設定](oep-if-probe-config.ja.md)
§1.1（スロット）。ピンの探し方の一般的な手順は [host 開発ガイド](host-development-guide.ja.md)（§21 リセットの線、§19 ピンの探し方（参考））。

core（ArduinoCore-CH32RV の bench）は自動の scan で何度もつまずいた（特に CH32X035）。原因の多くは target 側の性質と治具の
配線で、規範の外にある。ここに target ごとに集め、次に同じ target をつなぐ人が同じ所で迷わないようにする。

出典の記号: **E1xx** = wch-protocols `experiments/` の実験（`LEDGER.ja.md`）。**bench** = ArduinoCore-CH32RV
`tests/benches/*.toml`（治具の設計）。**LM §3** = [リンクの計測](link-measurements.ja.md) §3（規範から移した逸話）。
**材料** = 2026-10-02 に bench（core）から受けた経験のまとめと、同日の dev-oep の実験。

## 1. 使い方と一般的な順番

target の節（§3）を先に読み、その target の落とし穴を除いてから次の順で進める。各段で「何を見たら次へ進むか」を決めておく。

1. **電源を入れ、入っていることを確かめる。** 線が 1 本も答えないときは、まず電源を疑う（L103 は LinkE が抜けていて無給電
   だった、§3.3）。probe の信号線からの逆給電で、電源を切ったつもりでも target が動き続けることがある（WeAct X035、§3.2）。
2. **ピンを分類し、除く。** target が駆動しているピン（UART の TX、LED の点滅、I2C）と、触ってはいけないピン（USB、USB PD の
   CC、治具の都合で low にしてはいけない線）を候補から外す。電源の入り切りで pull-up / pull-down の読みを比べると候補は出るが、
   **候補を出すだけ**（idle-high の UART の線は SWIO / NRST と同じに見える。§3.1 の 22/23）。
3. **線を scan する。** その target の max_speed と idle_clock（§2）を scan にも付ける（付けないと probe の最も遅い速さと既定の
   休ませ方で試す。L103 は SWCLK high で休むと debug の線が reset されるという記録がある、§3.3）。count = 0 は「今動かしてよい組だけ」を並べる
   （debug §1）ので、plan で持たれたピンは外れる。
4. **target を確かめる。** attach の応答の target_id（scheme 1 = DMI 0x7F）で系統を見る。**同じ系統の板が 2 枚以上あるときは
   ESIG の UID で照合する**（L103 も X035 も 2 枚ずつあり、2 つの probe が「同じ target に届いている」と取り違えた。材料）。
5. **NRST を探す。** 候補を 1 本ずつオープンドレインで low に保ち、target の活動（LED、UART）が止まるピンを探してから、
   attach の reset TLV（method 1）で **dpc = 0** を確かめる（host ガイド §4.6、`Wire.find_reset_line`）。NRST が option で無効
   なら見つからないのが正しい（V003 の RST_MODE、§3.1）。
6. **読み出し保護と option bytes を確かめる。** scan と attach は保護があっても通る。flash を読んで初めて分かる（WeAct X035 の
   出荷デモ、§3.2）。option は読むだけにし、書くのは目的があるときだけ。
7. **スロットに記録する。** wire、pins、max_speed、idle_clock、錠（target_id）を `oep config slot` に、リセットの線（あれば）を label の `<スロットの name>.nrst` に書き、
   治具の設計（bench の toml）にも同じ値を残す。

**走っているかは DM ではなく UART で判断する**（全 target 共通、材料、E158 / E159）。DMSTATUS の allrunning、dpc が flash の中に
あること、halt が通ることは、どれも「アプリが健全に走っている」証拠にならない（§3.2）。治具の fixture UART で banner を見る。

## 2. 要約の表

| target | wire | 治具のピン（channel） | max_speed | idle_clock | NRST | reset の挙動 | 電源 | 触らないピン |
|---|---|---|---|---|---|---|---|---|
| CH32V00x（V003。V006 は LinkE だけ） | swio（1 線） | classic ESP32 + UIAPduino: SWIO 16、NRST 23（bench v003-esp32）。P4 30eda0ea068b + V003: SWIO 19、NRST 4（材料 10-02） | toml に指定なし | —（swio） | 配線済み。有効かは option の RST_MODE（出荷時は無効、PD7 = GPIO） | reset TLV（NRST 4）で dpc 0、6/6。通電から 15.0〜15.2 ms で dpc 0（8/8）。DM は havereset を ack するまで halt / running を凍らせる | P4 GPIO5 から直結の板は host の gpio で入れ直せる。V006 の板は probe 給電でなく `probe power cycle` が cold boot にならない | PD3 / PD4（ソフト USB、治具に未配線、variant が PD4 を low に保持）。PC1 / PC2 は 2.2 kΩ の pull-up |
| CH32X035 | rvswd | P4 治具 F8U6: SWDIO 2 / SWCLK 54（PC18 / PC19）。WeAct F8U6: 22 / 23 | 0（probe の最速。attach で SWCLK 6.3〜6.4 MHz、E158） | high（low で休むと接続できない、E171） | どちらの治具も未配線。reset は ndmreset だけ | ndmreset 後に hart が PC 0 に駐留しうる（6/200、E158）。resethaltreq は無い（E159）。reset は最遅（half 500 ns）で行い、止まってから速さを取り直す | P4 治具は入れ直し不要だった。WeAct は信号線から逆給電され、3V3 と信号線を両方外さないと落ちない | PC14 / PC15（USB PD の CC）、PC16 / PC17（USB。P4 治具では I2C に配線）、PC18 / PC19 を DUT の I2C に使わない。PB3 / PB11 / PB12 は high の後の解放が遅く、pull の判定に使わない（原因未確定、§4） |
| CH32L103 | rvswd | RP2350 Pro Micro: SWDIO GP0 / SWCLK GP1（420 組中これだけ） | 1 MHz（reset 直後の遅い clock では 680 kHz で parity エラー。下限 500 ns） | low（high で休むと debug の線が reset される、LM §3。bench では照合していない） | 未配線 | 走ったまま ndmreset → 線を離して wake で確認は 9/20、reset-halt + resume で 20/20。haltreq が効かず走り続けた件は未解決 | 当初は無給電（LinkE が抜けていた）で、どの線も答えなかった | GP0 / GP1 は Serial1 の既定ピン（fixture.uart は別の組に） |
| CH32V103 / V203 / V307 | rvswd（OEP の治具は無い） | WCH-Link だけ（V103 は WCH-Link(CH549)、V203 / V307 は LinkE）。WCH-Link の fw は 09-16 に V006 の LinkE（2.22）以外すべて 2.12（V103 の WCH-Link(CH549) も 2.12）、E162 / 09-25 の収録では LinkE 2.22（後で更新した可能性）。未確定、頼る前に `ch32rv probe info` で読む。UART は PA9 / PA10 | 記録なし | LinkE は SWCLK 0 / SWDIO 1 で休ませる（V203、E171） | 未配線 | LinkE の attach で RCC / ACTLR が書き換わる（V203 / V307、E162） | V203 は LinkE の 3V3 / 5V を切っても動き続けた（E162） | 記録なし |
| RP2350（ARM SWD、Cortex-M33） | swd（v1 `oep.wire.swd` + `oep.target.arm-adi`） | RP2040-Zero の probe（Rp2040ZeroProbe）→ Pro Micro RP2350: SWCLK GP0、SWDIO GP1 | half 500 ns（SIO の bit-bang） | —（swd） | 記録なし | DPIDR 0x4c013477（ADIv6、DPv3）。multidrop の TARGETSEL は要らず、どの wake でも起きる。flash の後は必ず Rom.reboot()（AIRCR だけでは C_MASKINTS が残り USB が列挙されない） | 記録なし | 記録なし。scan では erratum E9（離した入力が high にラッチ）に注意 |

## 3. target ごと

### 3.1 CH32V00x（V003、V006）

**線と設定**: swio。slot は `wire = "swio"`、`pins = [16]`、at boot、retry 1 s、mechanism dmseq（bench v003-esp32、classic ESP32 +
UIAPduino Pro Micro V1.4、E132 の配線）。NRST は GPIO23 に配線済みで、host が名指ししたときだけ使う（通常は駆動しない）。
新しい P4（30eda0ea068b、FS USB-Serial/JTAG）では SWIO 19、NRST 4（材料 10-02）。

**scan の落とし穴**:

- **idle-high の UART を SWIO / NRST と取り違える**（10-02、P4）。電源を入り切りして読みを比べると、22 / 23 が「通電時だけ high」で
  候補に見えたが、実は target の UART だった。対処: レベルの比較は候補を出すだけにし、scan で DMSTATUS が読めた組だけを信じる。
- **target が push-pull で駆動しているピンを scan / 保持の対象にしない**（10-02、21 番が kHz で点滅）。対処: 活動の見えるピンは
  先に除く。除いた後の全 channel の scan で 19 が即座に見つかった（走っている時も、電源の入れ直し直後も）。
- **P4 の通常の GPIO の書き方では SWIO が出せない**: P4 の GPIO レジスタのアクセスは約 260 ns（94 cycles）で、SWIO の短パルスと
  同じ長さ。dedicated GPIO の PHY（oep-probe-arduino 272dd38、短 250〜280 ns / 長 840〜890 ns）で通った（§4）。
- **UART 経路の probe（classic ESP32 + CH340）は迷いバイトに弱い**: 他のプログラムが口を開くと崩れる（200 ms で resync、client は
  3 回失敗で ESP32 を hard reset）。

**NRST の探し方**（10-02、P4）: `find_reset_line` は外れた（[] が返った。host ガイド §4.6 の 09-24 の実測では V003 で本物だけが
当たっている）。候補を 1 本ずつオープンドレインで low に保ち、アプリの点滅（21）が止まるピンを探すと 4。attach の reset TLV（4）で
6/6 dpc 0。セッションの最初の 1 回だけ failed が返った。外れた原因は client の側だった: `find_reset_line` が attach に pins を
付けず、最初の候補の後で接続が閉じると、以後の attach が unavailable で断られ、それを「リセットに使えない channel」と読んで
飛ばしていた（oep-client-python 6a302e7 で修正。修正後は 48 候補、tries=3 で [4]、4.2 s）。今は `oep pins` が両方の方法で探す。

**NRST が有効か**: option bytes 0x1FFFF800 の word0 = RDPR、nRDPR、USER、nUSER。USER の RST_MODE（bits[4:3]）が 11 なら PD7 は
GPIO で NRST は無い（出荷時）。10-02 の板は USER = 0xF7 → 10（有効、12 ms の窓）。**読むだけで書かない。**

**reset と halt**:

- V00x の DM は havereset を ack するまで DMSTATUS の halt / running を reset 値のまま凍らせる（V006 で、走っているのに halted = 1）。
  ackhavereset してから読む（LM §3、debug §4.6 の規則の由来）。
- 電源の入れ直し + attach(halt): host の gpio だけで、通電から 15.0〜15.2 ms で dpc 0 に止まる（8/8）。アプリは通電の約 138 ms 後に
  動き出す（10-02、P4 GPIO5 から給電）。
- RAM loader の最後の ebreak は、dcsr.ebreakm を立てないと mtvec 0 に飛んでアプリが再起動する。dpc で判断する。RAM の payload は
  mstatus = 0 で走らせる（E161）。
- UIAPduino の bootloader は RCC_RSTSCKR.PINRSTF が立っているときだけ残る。HID に入るには NRST パルス → payload（E161）。

**読み出し保護 / 回復**: 記録なし（RDPR は上の word0 で読める）。

**触らないピン**（v003-esp32）: PD3 / PD4（ソフト USB）は治具に未配線、variant が PD4 を low に保持。PC1 / PC2 は板の 2.2 kΩ の I2C
pull-up（R4 / R5）付きで、pull の判定に使えない。

**走っているかの確かめ方**: fixture UART（USART1 route 0、PD5 TX → 22、PD6 RX ← 21、RX は pull-up で休ませる。bench v003-esp32）。

**速さ**（10-02）: SWIO read_block 64 語 8.1 ms（P4）、classic ESP32 の治具は 35 ms。1 DMI 約 43〜44 µs（うち frame gap 8 µs）。

**SWIO のビットの時間の限界**（予定）: debug §3.2 の low の範囲（1 = 240〜310 ns、0 = 840〜1060 ns）は 1 つの target の系列で動くと測ったもので、target そのものの限界はわかっていない。ベンチで low / high の時間を掃引して測り、ここに記録する（まだ測っていない）。

### 3.2 CH32X035

**線と設定**: rvswd、idle_clock high、max_speed 0（probe の最速）、at boot、retry 1 s、mechanism dmseq（bench x035-p4 / x035-weact）。

| 治具 | probe | SWDIO / SWCLK | UART（USART4 route 0） | 出典 |
|---|---|---|---|---|
| P4 治具（CH32X035F8U6） | P4 30eda0e31108 | 2 / 54（PC18 / PC19） | PB0 TX → 12、PB1 RX ← 6 | bench x035-p4、E143 |
| WeAct（CH32X035F8U6、10-02 追加） | P4 30eda0e34a0e | 22 / 23 | PB0 TX → 4、PB1 RX ← 3 | bench x035-weact |
| LinkE（CH32X035C8T6） | WCH-LinkE FC928F068181 | — | USART1 PB10 / PB11 | bench x035-linke |

- PHY: dedicated GPIO + SWDIO push-pull（明示の turnaround）で half 0 ns まで全数一致、1 DMI read 10.1 µs（E151〜E153）。
  open-drain + 内部 pull-up は half 300 ns 以下で崩れる（上限約 1 MHz、E153）。§4。
- idle_clock を high にする理由: X035 は SWCLK low で休むと接続できない（oep-probe-arduino の記録、LinkE も X035 では SWCLK 1 /
  SWDIO 1 で休ませる、E171）。
- RVSWD の wake burst（100 clock）や SWDIO を high / low にしたままの長い列で、正常な X035 は reset されない（E170、09-26）。
  「wake burst は target を reset する」は L103 の記録。

**scan の落とし穴**:

- **reset の後に速さを取り直さない**（09-24、E158 / E159）。attach で決めた half はスケッチが上げた clock 用で、ndmreset の後の遅い
  既定 clock では DMI の書き込みが化け、hart が 1 命令も実行せずに PC 0 に駐留した（DMSTATUS-only の reset で 6/200、E158。駐留の
  98 % は half 100〜200 ns が要った attach と重なる、E159）。対処: reset は最遅（half 500 ns）で行い、止まってから速さを取り直す
  → 0/100（材料）。half は attach ごとに選び直す（E159）。
- **DUT が PC18 / PC19 で I2C を駆動すると probe が落ちる**。PC18 / PC19 は SWD の線で、I2C の route 3 と兼用。対処: スケッチで
  route 3 を使わない。
- **USB_PHY_V33（AFIO_CTLR bit6、reset 値で立っている）が立っていると、PC16 / PC17 は open-drain でも離さず high を出す**。pull の
  判定や scan の候補に使うと誤る。
- **読み出し保護は scan では分からない**（§3.2 の保護の項）。
- **PB3 / PB11 / PB12 を pull の判定に使わない**: probe が high を駆動した後の解放が遅い（§4。原因は未確定）。

**reset と halt**:

- ndmreset の後の駐留は DMSTATUS では分からない: allrunning = 1 のまま、dpc = 0。halt も dpc の読み出しも通るので「止まっていない」
  証拠にならない。haltreq → resumereq で 15/15 解放（E158）。確認は PC sample（dpc ≠ 0）で 200/200 + 300/300（E158）。
- haltreq を reset 越しに保持する列でも 0 にならず（1.3 %）、probe に入れると「走っているが SysTick の割り込みが止まり millis が
  凍る」が 124/300 出た（E159。次の halt → resume で正常化。修正後は再現せず、材料）。**dpc ≠ 0 だけでは証拠不足、UART が上位。**
- resethaltreq は X035 に実装されていない（E159）。
- reset TLV（reset の線）をかけながらの attach は最初の命令の前で止まる保証が無い。dpc 0x4ac で止まった（10-01、LM §3）。
- X035 は U mode で走る（mstatus に触る命令は trap）。「黙って止まった」ときは、まず CSR の trap を疑う。
- probe が abstract command で DATA0 / DATA1 を使うと、target の dmseq のフレームが消えた（09-30、LM §3）。

**読み出し保護 / 回復**:

- WeAct の出荷デモは RDP が有効で、書き込みが通らなかった。OEP 経由で `ch32rv target protect off` で解除（ch32rv dev 7da2e60 /
  f65ea53）。option は a55a1fe0 に。scan と attach は通り、flash を読もうとして初めて分かる。
- アプリが RCC_CFGR0.HPRE に 1xxx（bit7 = 1）を書くと、LinkE の attach で止まる（E164。/2 の 0001 と /6 の 0101 は止まらない、option
  byte は変わらない、L103 では起きない）。回復は LinkE の特殊消去を 2 回目の 0x0f まで繰り返す（E164、E169）。引き金は特殊消去そのもので、
  AttachChip / RedetectChip / 待つだけでは変わらない（E169）。

**電源**: P4 治具では入れ直しは要らなかった。要ったのは LinkE 側の特殊消去の回復だけ。WeAct は P4 の 3V3 から給電（bench
x035-weact）で、USB-C の PD 電源を外しても P4 の信号線から逆給電されて落ちない（入れ直しは 3V3 と信号線を両方外さないと効かない）。
LinkE の `probe power 3v3 off` の間も X035 は動き続けた（E166）。

**触らないピン**:

| 治具 | ピン | 理由 |
|---|---|---|
| WeAct | PC14 / PC15 | USB PD の CC（約 5 kΩ で引き下げ）。長いリードを付けると PD のメッセージが decode できない。probe に未配線 |
| WeAct | PC16 / PC17 | USB-C（PD の充電器へ）。probe に未配線 |
| P4 治具 | PC14 / PC15（10 / 15） | 配線はあるが part が low に保つ（pulled_low）。PC15 は P4 の GPIO15 / 45 の二重接続（E143） |
| P4 治具 | PC16 / PC17（52 / 50） | I2C（route 2）に使う。P4 側に外付けの pull-up は無い |
| 両方 | PC18 / PC19 | SWD の線。DUT に I2C route 3 で駆動させない |

**走っているかの確かめ方**: fixture UART（USART4 route 0、RX を pull-up で休ませる）の banner。DM の状態では判断しない。

### 3.3 CH32L103

**線と設定**: rvswd、SWDIO GP0 / SWCLK GP1、max_speed 1 MHz、idle_clock low、at boot、retry 1 s、mechanism dmseq（bench
l103-rp2350、SparkFun Pro Micro RP2350、firmware 0.0.19。09-30 に count = 0 の scan で発見、420 組のうち答えたのはこの 1 組）。
この L103 の UID は 3a6fabcda284bc48 で、LinkE 0E028F0692F1 の後ろの L103 とは別の板（bench）。

- idle_clock low の理由: L103 は SWCLK が high で休むと debug の線を reset する（09-23〜25、LM §3。**bench では照合していない**）。
  LinkE も L103 では SWCLK 0 / SWDIO 1 で休ませる（E171。E171 は休ませ方の観測で、reset されることは確かめていない）。
- max_speed 1 MHz の理由: reset 直後の遅い clock では 1 MHz を超えると書き込みの確かめが落ちる（LM §3）。

**scan の落とし穴**:

- **電源が入っていない**: 当初は LinkE が抜けていて L103 が無給電で、どの線も答えなかった。
- **冷えた CH32 は最初の wake を無視する**: 最大 8 回まで再送して、half 500 ns の 5 回目に初めて読めた。対処: wake を再送する。
- **候補の half ごとに bus を初期化し直す**: 追従できない half の後は DM がずれる。
- **reset 直後の速さの探索**: 680 kHz で parity エラー。対処: half 500 ns の下限を置いて 42/42。
- **RP2350 の erratum E9**: 離した入力が high にラッチされ、全ピンが pull-up ありに見える（§4）。対処: 読むときは pad 自身の pull を
  当てる。外付けの pull がある組（GP24 up、GP23 / GP29 down）は、逆に SWDIO / SWCLK でない特徴として使えた。
- **配線のせいにしない**（09-25、ユーザーの訂正）: 上の失敗はどれも probe の速さと手順の問題だった。

**reset と halt**:

- 旧 riscv-dm の reset（走ったまま ndmreset → 線を離して wake で確認）は 9/20、reset-halt + resume にして 20/20。
- wake burst（100 clock）は L103 では target を reset する（09-23、oep-probe-arduino `RvswdPhy::configureBus()` の記録、E170 に引用）。
- hart の状態が変わると DMI の link が落ち、halt 直後の読みが前の値になる。haltreq を立てたまま保つ（LM §3）。
- haltreq が効かず走り続けた件は未解決（低電力か DBGMCU か）。
- NRST: この治具では未配線。host ガイド §4.6 の 09-24 の実測（RP2350、8 候補）では本物の NRST を見つけている（別の配線の時期）。

**読み出し保護 / 回復**: 記録なし。

**触らないピン**: GP0 / GP1 は Serial1 の既定ピンなので、fixture.uart は別の組にする。GP19 は PSRAM に予約（sketch_profile）。

**走っているかの確かめ方**: この治具には UART が配線されていない（bench: 配線はデバッグの 2 本だけ）。今は DM（dmseq）しかなく、
UART で確かめられない。LinkE の bench（l103-linke）は USART1 PA9 / PA10 が Link の UART bridge に来ている。

### 3.4 CH32V103 / V203 / V307

OEP の治具はまだ無い。どれも WCH-Link の bench（V103 は WCH-Link(CH549)、V203 / V307 は LinkE）で、UART は
USART1 PA9 / PA10（bench v103 / v203 / v307-linke）。firmware: 09-16 は V006 の LinkE（2.22）以外すべて 2.12（V103 の CH549 も 2.12）、
E162 / 09-25 の収録と今の bench の toml では 2.22（V103 は 2.12）。その間に更新した可能性があるが未確定で、頼る前に `ch32rv probe info` で読む。LinkE の attach で clock が書き換わる（§5）。V103 は long 形式に応答する（E165）。

### 3.5 RP2350（ARM SWD）

出典: bench、2026-09-23〜24。

**線と設定**: RP2040-Zero の OEP probe（Rp2040ZeroProbe、v1 の `oep.wire.swd` + `oep.target.arm-adi`）から Pro Micro RP2350 へ SWD。
SWCLK = GP0、SWDIO = GP1。SIO の bit-bang で half 500 ns。DPIDR 0x4c013477（ADIv6、DPv3）。multidrop の TARGETSEL は要らず、
どの wake でも起きる。

**AP**: 0x2000 / 0x4000（M33 の AHB-AP）、0xA000（APB-AP）、0x80000（RP-AP）。MEM-AP の読みは約 47 KiB/s。

**落とし穴**:

- **AHB-AP は non-secure で上がる**（CSW bit 30）。対処: bit 30 を下ろす。下ろさないと SRAM の読みが FAULT になる。
- **scan で全ピンが pull-up ありに見える**: RP2350 の erratum E9（離した入力が high にラッチされる）。対処: pad 自身の pull を当てて読む（§4）。

**flash と reset**: ROM 経由の書き込みが通る（98 KiB / 5.5 s）。**最後は必ず Rom.reboot()**。AIRCR だけの reset では C_MASKINTS が
立ったまま残り、USB が列挙されない。

**NRST、保護、触らないピン**: 記録なし。

## 4. probe 側の注意

| 項目 | 内容 | 出典 |
|---|---|---|
| classic ESP32 の SWIO のエッジの漏れ込み | 既定の出力の強さ（20 mA）の SWIO の線のエッジが隣の fixture の線に乗り、V003 治具で、SWIO でコンソールを読んでいる間、1 MHz の spi-target が bit を落とす・ずらす（64 B の 36 frame 中 23。失敗は中身違いの満数、または 10 bit 前後で CS の解除を見る）。スロットのコンソールを外すと 24/24、SWIO のピンを最弱（約 5 mA）にすると 72/72 で、線の速さは変わらない（read_block 64 語 36 ms）。配線は全ベンチでほぼ同じで、同じ配線の P4 治具は平気（classic の入力にはノイズのフィルタが無い）。UART bridge の損失（921600 で 0.4〜1.7 %）はこれと無関係で CH340 のもとからの分 | bench の実験 1〜4、dev-oep の実験 5〜6（10-02）、oep-probe-arduino d4f6293 |
| P4 の GPIO の速さと SWIO | P4 の GPIO レジスタのアクセスは約 260 ns（94 cycles、`gpio_ll` では約 300 ns/access）で、SWIO の短パルス（250〜280 ns）と同じ長さ。classic ESP32 の書き方は使えず、dedicated GPIO（1 bit 94.5 ns）が要る | E151、E152、材料 10-02、oep-probe-arduino 272dd38 |
| RVSWD の PHY: open-drain と push-pull | open-drain + 内部 pull-up は X035 で half 300 ns 以下で崩れる（上限約 1 MHz、`gpio_ll` では half 0 ns だけ崩れる）。push-pull + 明示の turnaround は half 0 ns まで全数一致（1 DMI read 10.1 µs） | E152、E153 |
| half 0 ns の parity | half 0 ns の DMI read が run によって 6〜8 割 parity 不一致になることがある。reset 直後の attach では 31 % が half 0 で clean にならない | LEDGER `x035-dmi-parity-intermittent`、E159 |
| RP2350 erratum E9 | 離した入力が high にラッチされ、全ピンが pull-up ありに見える。pull の判定は pad 自身の pull を当てて読む（probe 側でも target 側でも同じ: L103 の治具の RP2350 probe、SWD の target の RP2350） | 材料（L103）、bench 2026-09-23〜24（SWD） |
| X035 の PB3 / PB11 / PB12 の遅い解放 | PB3 / PB11 / PB12 は、probe が high を駆動した後の解放が遅い（数百 ms）。2 つの P4 治具の別の channel（x035-p4 は 13 / 9 / 14、WeAct は 2 / 54 / 53）で同じ。原因は未確定（X035 側が有力。DUT を外して同じ channel を測ったことはなく、2 台とも F8U6）。仮説の 1 つは P4 の SD の pad だった。idle のレベルは DUT の事実として使わない | bench x035-p4 / x035-weact、bench の確認 2026-10-02 |
| 長い op と線の速さ | 線の op の時間はリンクではなく線の速さで決まる | LM §1.3 |


## 5. WCH-Link の注意（参考、比べるとき用）

| 項目 | 内容 | 出典 |
|---|---|---|
| attach で clock を書き換える | LinkE（fw 2.22 でも）は attach のたびに target の RCC / ACTLR を固定の PLL 設定に書き換える。L103 CFGR0 0 → 0x001c040a・ACTLR 0x1（ループ約 6 倍）、V203 / V307 は約 1.3 倍、アプリの UART が文字化け。V003 と既定 clock の X035 は変化なし。V006 でも書き換わる（材料）。core は SysTick で直す（5e0e646） | E162、材料 |
| HPRE 1xxx の X035 で止まる | §3.2。回復は特殊消去を 0x0f まで繰り返す | E164、E169 |
| X035C8T6 の RST_MODE（E162） | HPRE /2 で動く X035C8T6 に LinkE で接続 → 応答しなくなった → USER が 0x07（RST_MODE 00、PA21 が外部 reset）だった → 特殊消去の窓で USER を 0x1f（RST_MODE 11）に書き戻して回復。接続が RST_MODE を変えたかは未確定（事故の前に option byte を読んでいない） | E162 |
| HPRE 1xxx の停止（E164、別の件） | HPRE 1xxx の X035 は attach で止まる。option byte は変わらない。特殊消去を 2 回目の 0x0f まで繰り返して回復 | E164 |
| 休ませ方 | L103 / V203 は SWCLK 0・SWDIO 1、X035 は SWCLK 1・SWDIO 1 で休ませる（OEP の治具の観測と同じ向き） | E171 |
| 速さの段 | SetSpeed の high / medium / low の線上の Hz | E163 |
| 識別が固まる | probe-rs / minichlink のセッションの後、chip の識別が古い値のまま固まる。`81 0d 01 03` の redetect で回復（V003） | 材料 |
| 電源 | `probe power 3v3 off` でも target は動き続ける（X035、E166）。L103 / V203 / V003 は LinkE の 3.3 V / 5 V を切っても動き続けた（E162）。特殊消去の窓は LinkE の中だけ（E166） | E162、E166、E167 |

## 6. 出典

| 記号 | 内容 | 日付 |
|---|---|---|
| E132 | UIAPduino（V003）の pin map（classic ESP32 治具の配線） | 2026-09-22（bench v003-esp32 の配線の計測日） |
| E143 | P4 治具の X035 の pin map（20 本、PC15 は GPIO15 / 45 の二重） | 2026-09-20 |
| E151〜E153 | P4 の GPIO のコスト、`gpio_ll` と dedicated GPIO の RVSWD の上限、od / pp | 2026-09-20〜22 |
| E158 | X035 の reset 後の「走っている」証拠（駐留 6/200、PC sample、attach 6.3〜6.4 MHz） | 2026-09-22 |
| E159 | X035 の ndmreset の書き順、resethaltreq なし、SysTick の停止、half 500 ns の教訓 | 2026-09-22〜24 |
| E161 | UIAPduino の bootloader が残る条件（PINRSTF、mstatus = 0） | 2026-09-22 |
| E162 | LinkE の attach で target の clock が変わる | 2026-09-25 |
| E164、E169 | HPRE 1xxx の X035 が LinkE で止まる、特殊消去で回復 | 2026-09-25 |
| E165〜E168 | LinkE の特殊消去、電源の窓、3V3 の出力、RAM の目印 | 2026-09-25 |
| E170 | wake burst は X035 を reset しない | 2026-09-26 |
| E171 | LinkE の RVSWD の休ませ方 | 2026-09-30 |
| bench | ArduinoCore-CH32RV `tests/benches/*.toml`（x035-p4、x035-weact、l103-rp2350、v003-esp32、*-linke） | 2026-10-02 に読んだ版 |
| LM §3 | [リンクの計測](link-measurements.ja.md) §3 | 2026-10-02 |
| 材料 | bench の経験のまとめ（wch-protocols の E 番号つき）と dev-oep の実験（P4 30eda0ea068b + V003） | 2026-10-02 |
| bench（SWD） | RP2040-Zero の probe → Pro Micro RP2350 の SWD（DPIDR、AP、CSW bit 30、Rom.reboot） | 2026-09-23〜24 |
| bench の確認 | 遅い解放の pad、E162 の RST_MODE の順、LinkE の fw、ARM の記録 | 2026-10-02 |
| commit | ch32rv dev 7da2e60 / f65ea53（`target protect off`）、core 5e0e646（SysTick で clock を直す）、oep-probe-arduino 272dd38（P4 の SWIO PHY） | — |

E 番号の日付は各 README に最初に出る日付（wch-protocols `experiments/<e番号>/README.ja.md`）。本文の日付（09-24 など）は 2026 年。
