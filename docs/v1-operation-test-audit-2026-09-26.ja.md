# OEP v1 操作・状態遷移・テスト監査（2026-09-26）

状態: 実測とソースレビュー。規範ではない。対象は `oep-spec` 2ff1d62、`oep-probe-arduino` 3160dee、
`oep-client-python` 75ee13e、および ArduinoCore-CH32 の `tests/manual/oep_*`。
個々の機材と firmware 転送、既に見つけた plan の問題、Windows 経由の RP2350 転送手順は
[実機・ソースレビュー](hardware-source-review-2026-09-26.ja.md)に記録した。

## 1. 判定方法と今回の範囲

ここでは「API を呼べた」と「期待した状態がその後も残る」を区別する。各操作について、正常系だけでなく、
拒否、失敗、解放、別の fn の追加、再設定、session の切断・期限切れの前後を観測対象にする。
特に `plan_apply` の success は、単にピンを表に登録したことではなく、既存と新規の機能が応答後に使えることまで
確認する。途中の電気的な中断を許す設計案はあるが、まだ規範ではない。

今回書き込んだ現行 probe firmware で、P4/X035 の probe チェック 14/14、ESP32/V003 と RP2350/L103 の同チェック
各 16/16、target sketch 回帰は3台とも14/14（L103 は2回）を確認した。host の unit test は 134 passed、
v1 registry の test は5 passed、`oepgen1.py --check` は成功。ただし unit test の多くは fake endpoint に対する
host 側の形と例外の試験で、C++ probe の実行結果ではない。
手動 runner は開始時に target sketch を再ビルド・転送する。今回の最後は X035 / V003 に `reset_probe`、
L103 に先の `wire_selftest` が残っている。次の用途では規定どおり使用前に目的の firmware を書き込む。

今回追加した手動実測: P4 の UART2 を 9600 / 115200 bps で双方向・echo・overflow 後回復・64 KiB 連続受信・
target reset 後の受信まで確認（`failures=[]`）。GPIO マトリクスは X035 PA0/PA1 と V003 PA1/PC0 で
出力、入力、pull、open drain、EXTI が全て `OK`。P4 の I2C/SPI と capture の同居の正常系・逆順による
破壊と、UART 片方向 plan の拒否も追加測定した。P4 と V003 の PWM、tone、時間計測、SPI peer、
I2C の read / repeated START / 400 kHz write も走らせた。I2C のデータ照合は両方とも一致した。
reset trace は X035 / V003 とも software・debug 各3回で起動を確認した。X035 の中央値は
software `0.069 ms`、debug `229.523 ms`、V003 はそれぞれ `0.320 ms`、`1.845 ms`。
debug の値は probe による reset 手順を含み、MCU 単体の起動時間ではない。
以下の matrix で「未実測」を消さずに残す。

## 2. v1 の操作群とテストの対応

| 操作群 | 今回の実機証拠 | 単体・静的証拠 | まだ足りない状態遷移 |
|---|---|---|---|
| transport / confirm / list / describe | 3台の転送後 `dump` と各 probe チェック | host の COBS、length、HID、再同期、paging の fake 試験。registry 生成同期 | USB vendor/HID/IP、フレーム途切れ・破損を本物の probe で注入した試験 |
| open / end / keepalive / lock_state / corr | 3台で connection 番号、同 corr の再送、`corr_reused`、`result_lost`、end、lease 失効 | host の session / pipeline の fake 試験 | 2経路の同時 host、強制奪取と継続中の stream、boot_id 更新直後の回復 |
| plan_apply / plan_release / 資源競合 | UART 拒否後の状態喪失、P4 の capture 後付けによる I2C NACK・SPI MISO 喪失、同時 plan の正常系 | C++ の `replaceFns`、各 interface の `planCheck` / `planApply` | 全 fn の取り合い、成功/拒否後の電気的・stream 状態、一時中断を許す二段階交渉 |
| subscribe / unsubscribe / event / data | dmseq console は回帰で使用。capture の手動 runner は主に status/read | host の push と event seq の fake 試験 | 実機で heartbeat、通知欠落、lease 切れ、stream の gap・再購読 |
| RVSWD / SWIO scan・attach・detach | 3 target の scan→attach、reset 下 attach（NRST 配線ありのみ）、不正 pin 拒否 | host の wire / connection fake 試験 | detach(force) の利用者数、複数 connection、別 plan / bind と pin の取り合い |
| RISC-V DM | 3台の reset-halt、step、DMI delay、flash の block read/write・RAM loader・run。X035 / V003 の software・debug reset 後起動を各3回実測 | host の DMI step、partial、status、reset method 等の fake 試験 | 各 op の `wait` / `line` / `fault` / `timeout` / `state`、途中までの転送、繰返し失敗 |
| SWD / ARM ADI | 今回は現行 firmware で target を壊さない実機試験なし | host の ADIv6、MEM-AP、RP2350 flash の fake 試験 | 別個体の probe firmware を先に転送したうえでの transfer、block、multidrop、targetsel |
| target.console | 3台の dmseq console で sketch の判定、flash 後 reset | host の position、mark、partial write の fake 試験 | SDI / DMDATA、読み出し中の detach、mark の巻戻り、複数接続の寿命 |
| fixture.gpio | X035 / V003 の代表2ピンずつで mode、read、EXTI まで実測 | host の set-list 順序と拒否の fake 試験 | 全 pin の予約・電圧条件、共有 observer の追加/解放、拒否後の出力保持 |
| fixture.uart | P4 UART2 の双方向、overflow 後回復、64 KiB 連続受信、target reset 後受信 | host の configure、mark/position、partial write の fake 試験 | 片方向 plan（現行は拒否）、P4 以外の長時間転送、plan 更新拒否後の既存状態 |
| fixture.capture | P4 と classic の capture 宣言、P4 I2C/SPI の trace、P4 LED の 8192 サンプル | host の layout、4 GiB 超 position、gap、read 分割の fake 試験 | query が既存データを壊さないこと、force、repeat/release、streaming と通知、枯渇・停止・再開 |
| fixture.analog | 今回の3台は宣言しない | 規範はあるがアナログ実装・実測なし | scale、skew、frontend、複数 channel、境界 rate |
| probe.config | 今回の3台は宣言しない。P4 HS / console prototype に実装あり | C++ の `ProbeConfig` を静的に確認 | set の原子性、bind、保存上限、save/erase/reboot、firmware 更新後の一覧照合を現行 build で試験 |
| domain I2C / SPI target | P4 / V003 の I2C read・repeated START・400 kHz write はデータ一致。P4 SPI 10条件の peer + capture。逆順の後付けで既存機能が破壊。V003 の SPI peer は3 MHz宣言を超える条件で不一致、範囲内の64 byteでも間欠的不一致 | 専用 host の形の fake 試験 | 宣言範囲内の V003 64 byte 再現条件、再設定と未回収 frame、連続転送中の capture 追加 |

## 3. 監査で確定した問題

### P1: 成功した共有 plan が既存の peripheral を壊す

[実機・ソースレビュー §2](hardware-source-review-2026-09-26.ja.md)の P4 I2C/SPI 逆順テストを参照。
同じピンを読み取り専用 capture と共有すること自体は可能であり、同時 plan では正常に動いた。
一方、I2C target が動作している SCL/SDA に後から capture plan を追加すると、`plan_apply` は success なのに
次の書き込みは `rc=2`（NACK）。`capture.configure` の前に起きる。I2C を再 configure・arm すると `rc=0` に復帰した。
SPI でも後付け後、DUT が読む MISO が `3c96c30f` から `FFFFFFFF` になった。

仕様案: 通常の plan 要求では probe が無変更で `rejected unavailable` と再構成可能な fn 一覧を返し、
host がその中断を許す場合にだけ、新しい corr の要求で該当 fn の再構成を許す。
成功時には probe が全ての維持対象を復帰させる。host に P4 固有の初期化順序を教えない。
wire の形と「中断中の欠損」の扱いは未決。レビュー案であって現行規範ではない。

### P1: UART の片方向 plan が仕様に反して拒否される

[fixture §2](oep-if-fixture.ja.md) は RX だけ、TX だけを plan できると定める。しかし
[FixtureUart::planCheck](../../oep-probe-arduino/src/OepV1Fixture.cpp) は `count != 2` を `unavailable` にする。
P4 の UART fn に RX=12 だけ、TX=6 だけを個別に送った結果は両方 `rejected unavailable`（reason 4）。
probe の `describe` は両 role に利用可能 channel を列挙しており、片方向不可を見分ける宣言もない。
仕様どおり片方向を実装するか、必要なら channel_group で方向ごとの可否を宣言する設計にする。
このほか、拒否された UART plan 更新で既存の UART が止まる件は前の報告に記載。

### P1: 手動 runner の終了コードだけでは合否が分からない

`oep_smoke.py` と `oep_probe_checks.py` は失敗を非ゼロ終了で報告する。一方、
`oep_gpio_matrix.py`、`oep_uart_trace.py`、`oep_adc_trace.py` は `failures` を出力するだけで、
`oep_i2c_trace.py` と `oep_periph_trace.py` も照合結果を列挙するが、期待不一致を終了コードに反映しない。
実測でも X035 の ADC runner は6 pin に `BAD` と `failures=[...]` を出しながら終了コード 0 だった。
そのため CI や自動実行が exit 0 を「合格」に変換すると誤判定する。すべての runner で機械的な
`pass/fail/skip` と非ゼロ終了、対象の firmware hash と target profile、失敗の測定値を残すべき。

### P2: ADC runner の適用範囲・しきい値は整理が必要

X035 はレールの平均値が概ね妥当だが、`max-min <= 8` というばらつき条件で PA0/PA1/PA5/PA6 などが
`BAD` になった。PA3/PA7 はこの lot で ADC channel が無いことを同 runner が後段で確かめており、
最初の `BAD` を通常 pin と同じ失敗として並べるのは紛らわしい。V003 は `--target v003` を受け付けるが、
`adc_probe` の `.bss` と stack が重なって compile できなかった。これは OEP の analog interface の試験ではなく、
CH32 target の ADC と probe GPIO の組の試験。対応 target、期待する例外、しきい値の根拠を runner に反映する。

### P2: V003 の SPI peer 長尺受信が間欠的に不一致

V003 の `periph_trace` は4 byte の mode 0–3 / 1 MHz、250 kHz、4 MHz、5回連続の4 byteでは
DUT の MISO と probe の MOSI 受信が一致した。ただし 12 / 24 MHz では DUT 側 MISO が再現して
不一致になった。この classic ESP32 probe の `describe.max_clock_hz` は3 MHzであり、
`periph_trace` が probe の宣言を超えた条件を無条件で試している。したがって高速側は適合性の失敗とは判定しない。
一方、64 byte・指定1 MHz の3回連続転送では、1回目に #1、再試験では #2 の probe 側 MOSI が不一致
（いずれも bits=512、DUT 側 MISO は一致）。これは宣言の `max_length=64` と `max_clock_hz=3 MHz` の
範囲内なので未解決の実機不具合候補。runner が不一致 byte や SPI status を保存しておらず、転送・IRQ・
FIFO のどこで壊れたかはまだ特定できない。まず期待値と実測バイト列、status、実 SCK を保存して反復する。

### P2: V003 の I2C runner は 400 kHz の周期を誤表示する

X035 と V003 とも、read 2件、repeated START の write-then-read、400 kHz write は DUT と
probe の送受信データが一致し、capture のデコードも期待する START / ACK / STOP を示した。
ただし V003 の表示する SCL period `0.80 us` は測定値ではない。
`oep_i2c_trace.py` は捕捉速度を probe の上限 2 MHz に下げるのに、周期換算だけ固定の5 MHzで割る。
同じ4サンプル間隔なら実際は約 `2.00 us` である。JSON の `scl_us` も同じ誤値なので、速度判定には使えない。
換算に実際に指定した rate を使い、サンプル分解能不足の条件には誤差幅を付ける。

## 4. 次に追加するべき契約テスト

| 優先 | 操作と順序 | 判定すること |
|---|---|
| P1 | 同時 plan → configure → 動作、既存機能 configure → capture plan 追加、capture release、逆順 | success 後に旧/新の両機能が使える。既存を止めない要求なら副作用なく拒否。再構成許可時は probe が復帰 |
| P1 | `plan_apply` を拒否する役割/チャンネル、適用中に backend が失敗する注入 | plan 表だけでなく UART baud・受信位置、capture 区画、GPIO 駆動、bind も元通り。`rejected` と `completed failed` を区別 |
| P1 | UART RX のみ、TX のみ、両方、既存の片方にもう片方を追加 | describe の宣言と plan の受理が一致し、片方向の read/write と解放後 idle が正しい |
| P1 | 各手動 runner に意図的な不一致を注入 | 出力 JSON と終了コードが fail になる。skip と「ビルド不能」を区別する |
| P1 | SPI peer の速度・長さを `describe` に従って列挙し、V003 で64 byte を反復 | 宣言上限超過は明示的な探索試験に分ける。範囲内不一致のバイト位置、status、実 SCK を記録 |
| P1 | L103 flash 14 sketch を反復し、初回応答失敗・読み戻し不一致の内訳を記録 | 再書き直し数だけでは見えない誤書込みの箇所と条件を特定する |
| P2 | capture の query→既存取得の read、one-shot / repeat / streaming / force / release、lease 失効 | query の無副作用、区画と gap、停止理由、通知 seq、解放後の位置を同じ規範で確認 |
| P2 | config set / save / erase / reboot、保存上限、interface 一覧変更後の起動 | 拒否は状態不変、容量不足は `unavailable`、保存の CRC と boot_mode の安全性 |
| P2 | 2経路・2 host の open / force / end / lease、継続中の console/capture | lock と資源の所有者交代、dedup と corr、通知の宛先を確認 |
| P2 | debug / wire の各 status、部分転送、接続消失、reset 方法 | host が target の失敗を probe 応答の失敗と混同せず、done 数と state を返す |
| P2 | SWD/ARM ADI、analog、IP/HID/vendor bulk、probe.config を宣言する別 probe | 現在の3台に無い実装を適合とみなさず、別の現行 build と独立した host で確認 |

この matrix は「現行3台でどこまで言えるか」の境界でもある。全操作を実機で合格と主張するものではない。
