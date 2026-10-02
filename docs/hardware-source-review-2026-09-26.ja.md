# OEP 実機・ソース・テスト項目レビュー（2026-09-26）

状態: **記録**（規範ではない。実測とコードレビュー）。対象のソースは `oep-probe-arduino` `3160dee`、
`oep-client-python` `75ee13e`、[OEP core](oep-core.ja.md) と各標準インターフェース。
probe と target の接続・配線は ArduinoCore-CH32 の `tests/manual/oep_smoke/targets.py` を使用した。

## 1. 今回実際に動かした範囲

| probe / target | probe firmware | 発見・宣言 | probe 自身のチェック | target sketch 回帰 |
|---|---|---|---|---|
| ESP32-P4 `30eda0e31108` / CH32X035F8U6 | 現行ソースを clean build し、USB-Serial/JTAG から転送・hash 検証済み | revision 1、10 fn、max_frame 1024 | 転送後 14/14 | 転送後 14/14、fail 0 |
| classic ESP32 `0070070d9394` / CH32V003 | 現行ソースを clean build し、CH340 経由で転送・hash 検証済み | revision 1、9 fn、max_frame 512 | 転送後 16/16 | 転送後 14/14、fail 0 |
| RP2350 `9489dd2ae0953650` / CH32L103 | 現行ソースを clean build し、Windows の BOOTSEL ドライブに UF2 をコピーして転送 | 転送後 revision 1、6 fn、max_frame 1024 | 転送後 16/16 | 転送後 14/14 を2回、fail 0。ただし追加書き直しは1回目4ページ、2回目5ページ |

host の `uv run pytest -q`: **134 passed**。oep-spec の registry 試験: **5 passed**。
前者は host の fake / model を使う試験で、独立した probe の適合を証明するものではない。
target sketch 回帰は `oep_smoke.py --sketch all`。各 sketch を target に書き込み、読み戻して照合し、reset 後の dmseq console と
必要な UART / GPIO / I2C / SPI の期待値を確かめる。14 sketch 回帰の直後に target に残るのは `wire_selftest`。
その後の共有順序テストで X035 だけ `periph_probe`、次に `i2c_probe_write` に書き換えたため、現在の X035 は後者。
出力の `rewrote N pages` は初回の書き込みページ数ではなく、初回の書き込み応答の失敗または読み戻し不一致による
**追加書き直し数**を意味する（`oep_client.v1.ch32_flash.program`）。個々の原因はこの集計値だけでは区別できない。
P4 / classic ESP32 は全 sketch で 0。RP2350 → L103 は1回目に `heap_string` で1、`hooks_selftest` で2、
`serial_echo` で1ページ、2回目に `core_api` で1、`route_selftest` で2、`stdio_printf` で1、`tone_selftest` で1ページを
再書き込みし、最終照合は全て成功した。
したがって L103 の結果は「修復なしで14本成功」ではない。

probe のチェックは scan→attach、connection 番号、再送の重複排除、corr_reused / result_lost、end と lease の寿命、
reset-halt、step、DMI delay、NRST がある治具では attach_under_reset と reset 線探索を含む。
X035 治具には NRST の線がないので、attach_under_reset の項目は skip が正しい。

## 2. 実機で確認した共有と仕様違反

**訂正: GPIO と capture の同一ピン割り当て自体は仕様違反と断定しない。** [core §8.1](oep-core.ja.md) は、
安全な共有を probe が許すことを認めている。現行ファームウェアでは、P4 の channel 46 を
`oep.fixture.gpio` role 1 と `oep.fixture.capture` role 0 に同じ `plan_apply` で割り当てる要求が success。
classic ESP32 の channel 25 でも success だった。前回はこれを単独で P1 の競合違反と判定したが、
入力専用の observer と駆動側の共有を意図した設計・既存の実績を考えると、その判定を撤回する。

追加の実測では、P4 の LED channel 51 に同時 plan を入れ、capture→GPIO 出力 high と
GPIO 出力 high→capture の両順で 8192/8192 サンプルが high。P4 の I2C target と PARLIO capture を同じ
SCL/SDA に置いた 100 kHz テストでは、target の受信・ACK と wire trace が一致した。P4 の SPI target と
capture を同じ4線に置いたテストでも、10の速度・mode 条件で送受信が通り、デコード対象の低速条件は
wire trace も一致した。よって「共有を一律に拒否する」修正は適切ではない。

**この正常系の順序は重要。** P4 の登録は capture が fn 7、I2C target が fn 8、SPI target が fn 9。
[Endpoint::replaceFns](../../oep-probe-arduino/src/OepV1Endpoint.cpp) は TLV の並びではなく fn 昇順で `planApply()` するため、
同時 plan では capture の `pinMode(INPUT)` が先、I2C / SPI のピン予約が後になる。
[I2C](../../oep-probe-arduino/src/OepP4I2cTarget.cpp)・[SPI](../../oep-probe-arduino/src/OepP4SpiTarget.cpp) の
実際の driver 起動は、その後の各 `configure` で行われる。実機テストが I2C / SPI を設定した後に
`capture.configure` を呼び直していても、最初の **capture `planApply` は peripheral 起動前**に済んでいる。
したがって「動作中の peripheral に後から capture の plan を足しても安全」の証拠にはならない。

**P1: 後から capture を追加すると、動作中の P4 peripheral が壊れる。**
[LogicCapture::planApply](../../oep-probe-arduino/src/OepV1Capture.cpp) と
[SamplerCapture::planApply](../../oep-probe-arduino/src/OepV1Sampler.cpp) は共有ピンに `pinMode(INPUT)` を呼ぶ。
ESP32 Arduino core の `pinMode()` は `gpio_config()` を呼び、[Espressif の P4 GPIO 文書](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32p4/api-reference/peripherals/gpio.html)
は後者が既存の IO 設定を上書きすると明記する。

この逆順を実機で確認した。P4 I2C target だけを plan して configure・arm した状態では、X035 の 100 kHz
`WRITE 0x42 01020304` は `rc=0`、target 受信も一致。**I2C は触らず**、同じ SCL=52 / SDA=50 へ capture の
plan だけを追加すると、その `plan_apply` は success なのに次の `WRITE 0x42 05060708` は `rc=2`（アドレス NACK）となり、
target の受信データは前回のまま。`capture.configure` はまだ呼んでいないので、壊した遷移は後付けの plan である。
その後 I2C target を再 configure・arm すると、次の書き込みは再び `rc=0` となり受信データも一致した。
同様に、SPI target を先に configure した後、SCK=4 / MOSI=5 / MISO=11 / CS=53 に capture plan を追加すると、
DUT の MISO 読み値が期待 `3c96c30f` から `FFFFFFFF` に変わった。SPI target の MOSI 受信は続いた。
この SPI 測定では plan 追加後に `capture.configure` も呼んでから転送したため、単独の破壊操作の切り分けは
I2C の測定ほど厳密ではない。

LED channel 51 の試験は同時 plan 後に *configure* の順序を入れ替えたもので、動作中の peripheral への
後付け plan の安全性を示す試験ではなかった。P4 の順序依存は確認したが、全 peripheral・全 MCU に一般化はしない。

仕様案は **二段階の交渉**。host はまず普通の `plan_apply` を送る。probe が既存 fn の再設定なしには
適用できないときは、副作用なしの `rejected unavailable` に「再設定すれば可能」と影響を受ける fn の一覧を載せる。
host がその中断を許せば、**新しい corr** で同じ plan と「この fn の一時中断を許す」critical TLV を送る。
同じ corr で payload を変えると `corr_reused` になる。probe は2回目も資源と現在の状態を再検証し、
許可した fn の範囲で capture の入力設定後に I2C / SPI を再構成するなど、必要な順序を自分で実行する。
hint は成功の予約ではなく、その時点での可能性の通知である。影響する fn が許可一覧から増えれば再度拒否する。
成功応答時には、残した plan の機能が再び使える状態に戻っていなければならない。
「一時中断可」は「成功後も壊れたままでよい」という意味ではない。中断中の通信・取得データが失われる可能性と、
どの既存 fn の中断を host が許すかを wire 上で明示する。全 fn を無条件に止めてよい1 bit より、
許可する fn の一覧の方が reset・debug・保存 bind を不用意に巻き込まず安全である。
「再設定」は peripheral / interface の再起動を指し、MCU 全体の reboot を暗黙には含めない。
この案はレビュー上の提案であり、core の規範と wire の番号はまだ変更していない。
P4 での「capture の入力設定 → I2C / SPI driver 起動」は実装の手順として記録するが、
この順序を OEP 全体の MCU 非依存な必須手順にはしない。
describe に共有の全組み合わせを必須列挙させるより、まず `plan_apply` の成功をその組み合わせへの明示的な許可とし、
必要なら任意の共有情報を追加する方が単純で拡張しやすい。

**P1: 拒否された plan 更新が、動作中の UART を止める。** P4 の `oep.fixture.uart`（fn 5）に
RX=12、TX=6 を割り当て、115200 bps で configure（実測 115211 bps）。空データの write は変更前に成功する。
同じ fn を RX=12、TX=12 に置き換える `plan_apply` は `rejected unavailable` となるが、その後の同じ write は
`rejected unavailable`。最後に当該 fn の plan を解放した。
ソースでは `replaceFns()` が候補の `planCheck()` 前に元の UART の `planRelease()` を呼び、失敗後に元のピン割り当てだけ
`planApply()` し直す。`configured_`、baud、UART の受信状態は戻らない。実機でも [core §8](oep-core.ja.md) の
「拒否なら何も変えない」を満たしていない。

## 3. ソースレビューで見つけた箇所

### P1: plan の適用失敗が拒否応答に化ける

[Endpoint::planApply](../../oep-probe-arduino/src/OepV1Endpoint.cpp) は、`replaceFns()` が `uint16_t` で返す
「検証は通ったが、実際の planApply に失敗した」印 `kRejectUnavailable + 0x100` を `uint8_t reason` で受け取る。
続く `reason > 0xff` は真にならず、結果は `rejected unavailable` になる。
この経路は通常の正常系では通らないが、初期化失敗、割り込みによる資源競合、外部デバイスの異常時に
[core §4.2](oep-core.ja.md) の「受理後の失敗は completed failed」と食い違う。
戻り値の幅を保ち、適用失敗を模擬する interface のテストで応答と旧 plan の状態を確かめたい。

また `replaceFns()` は、候補の検証前に既存 fn の `planRelease()` を呼び、失敗すると再度 `planApply()` する。
戻り値上は旧 plan を復元しても、UART の受信中断・capture の区画消去・ピンの短い Hi-Z 化は巻き戻せない。
UART の中断は上記のとおり実機で再現した。
`planCheck` を既存割り当てを仮に除いた状態で先に行うか、資源予約と commit の段階を分ける必要がある。

### P2: probe.config の拡張と保存上限の境界が試験されていない

[ProbeConfig::apply](../../oep-probe-arduino/src/OepV1Config.cpp) は、知らない item tag を critical bit に関係なく
`rejected unsupported` にする。[core §2.3](oep-core.ja.md) の「知らない非 critical TLV は無視して ignored を返す」を
`set` にも適用する設計なら不一致である。この文脈の item に例外を設けるつもりなら規範に書く必要がある。

同ファイルの `canonical()` は 512 byte の保存バッファに収まらないと長さ 0 を返し、`hash()` / `save()` はその 0 を
空設定と同じように扱う。設定の項目数の上限を組み合わせで越えたとき、`save` が空を保存してしまう可能性がある。
現行 prototype の 16 plan role、最大 64 idle、最大 4 bind、最大 2 target の wire 長だけでも 512 byte を超え得る。
保存前に上限を検証して失敗として返す試験が必要。今回この経路を実機で発火させたわけではない。

### P3: host の表示文が古い

実機の `dump` は core の summary に `status, cancel` を表示するが、現行 v1 の長い操作は予約で、この op は存在しない。
[interfaces.py](../../oep-client-python/src/oep_client/v1/interfaces.py) の文字列によるもの。
wire の動作確認とは別に表示文を更新したい。

## 4. 動かすときの暗黙知

1. **probe firmware を先に書き込む。** 既存の USB デバイスが revision 1 と答えても、現行 checkout のファームウェアとは
   限らない。今回は古い状態での発見・probe チェックと、転送後の結果を区別した。ESP32 の2台は
   `oep-probe-arduino/examples/{Esp32P4X035Probe,Esp32V003Probe}` の `sketch.yaml` の profile で `--clean` build し、
   下記の固有ポートに upload した。target sketch の転送はその後。
2. **ポートは USB の個体 ID で選ぶ。** P4 は `/run/board-identify/by-id/esp32-series-30eda0e31108`、classic ESP32 は
   `/run/board-identify/by-id/esp32-d0wd-v3-0070070d9394`、RP2350 は
   `/dev/serial/by-id/usb-SparkFun_ProMicro_RP2350_9489DD2AE0953650-if00`。`ttyACM*` の番号は再列挙で変わる。
3. **USB-Serial/JTAG と USB-UART はフレームの形が違う。** P4 / RP2350 は length、CH340 経由の classic ESP32 は
   COBS + CRC。client の `open_host()` は USB VID:PID を見て選ぶ。別経路から開くときはこの判定を確かめる。
4. **USB の共有が BOOTSEL で切り替わる。** RP2350 はアプリ状態 `1b4f:0026`（今回 Windows busid `11-1`）から
   `2e8a:000f` へ変わる。`arduino-cli upload` は WSL で BOOTSEL drive を見つけられず `No drive to deploy`。
   `picoflash.sh` も `no BOOTSEL device` で停止した。Windows の `usbipd list` は `11-1 2e8a:000f Not shared` と表示し、
   WSL からの USB 接続には Windows 管理者による bind が必要だった。ただし、**この治具では Windows の BOOTSEL ドライブへ
   UF2 を直接コピーできる**。今回 `Get-Volume` でラベル `RP2350` の `E:` を確認し、`INFO_UF2.TXT` の
   `Model: Raspberry Pi RP2350` を照合してから、UF2 を `E:` にコピーした。自動再起動後、同じ個体 ID の CDC が再列挙された。
5. **probe と target は別の firmware。** `oep_smoke.py` は probe を転送しない。CH32 target の sketch を順に書き込み、
   最後は `wire_selftest` が残る。target flash の内容を保持したい場合は、このテストを実行しない。
6. **OEP と同じ CDC を serial monitor で同時に開かない。** フレームが混ざり、応答がなくなる。通常の表示は
   `oep_client.v1 dump`、probe 自身の確認は `oep_probe_checks.py` を使う。
7. **NRST と UART の配線は profile に閉じている。** X035 には NRST の配線がなく、NRST テストの skip は欠陥ではない。
   V003 の UART は probe 22/21、X035 は 12/6。L103 は RP2350 13/12 で、debug 線 GP0/GP1 と別。
8. **失敗時の観測を分ける。** `confirm` / `list` / `describe` が返らない場合は経路・framing・firmware、
   `attach` の `status line` は target 給電・配線・線のタイミング、flash verify 失敗は RAM loader / debug 線の書き込み、
   console が空なら DATA0 の同期・target sketch 起動状態を先に見る。これらを一つの「通信失敗」にまとめない。
9. **serial の制御線と速度にも意味がある。** [host 開発ガイド](host-development-guide.ja.md) の実測どおり、
   RP2350 を 1200 bps で開閉すると BOOTSEL に移る。通常の OEP 通信で 1200 bps を使わない。
   DTR を下ろしたままでは RP2350 の出力が止まる。ESP32 では DTR/RTS の変更順で自動 reset が起き得る。
   classic ESP32 の CH340 経由は 115200 bps で開く。通常は `open_host()` に制御線・速度の扱いを任せる。
10. **現行 P4 の observer 共有は plan の順序に依存する。** I2C / SPI target と capture を同じピンで使う場合、
    先に両 fn を同じ plan に入れ、capture の `planApply` が終わってから I2C / SPI を configure する。
    fn 昇順のため同時 plan ではこの順序になる。driver 稼働中に capture の plan を後付けすると、
    I2C は NACK、SPI は MISO が `FF` に変わった。これは**現行 firmware の回避手順**であって
    OEP の共通仕様として host に要求する順序ではない。修正後はどの順序でも状態維持、または副作用のない拒否が必要。

### 再実行するための最短手順

ESP32 系は各 example ディレクトリで build・転送する。`--port` に USB 個体 ID の固定パスを使う。

```sh
cd /home/mt/dev_oep/oep-probe-arduino/examples/Esp32P4X035Probe
arduino-cli compile --clean --profile esp32p4 --jobs 2 .
arduino-cli upload --profile esp32p4 --port /run/board-identify/by-id/esp32-series-30eda0e31108 .

cd /home/mt/dev_oep/oep-probe-arduino/examples/Esp32V003Probe
arduino-cli compile --clean --profile esp32 --jobs 2 .
arduino-cli upload --profile esp32 --port /run/board-identify/by-id/esp32-d0wd-v3-0070070d9394 .
```

転送後、ArduinoCore-CH32 側の作業ツリーで各 target を調べる。`--sketch all` は target flash を変更する。

```sh
cd /home/mt/dev_wch/ArduinoCore-CH32
uv run tests/manual/oep_smoke/oep_probe_checks.py --target x035
uv run tests/manual/oep_smoke/oep_smoke.py --target x035 --sketch all
uv run tests/manual/oep_smoke/oep_probe_checks.py --target v003
uv run tests/manual/oep_smoke/oep_smoke.py --target v003 --sketch all
```

RP2350 は BOOTSEL に入ると別の USB 装置として列挙される。今回の Windows/WSL 環境では、Windows 側で見える
`RP2350` のドライブに、`arduino-cli compile --clean --profile rp2350` が生成した `.uf2` をコピーした。
ドライブ文字は固定しない。`Get-Volume` と `INFO_UF2.TXT` で機種を確かめてからコピーする。
WSL から Windows のドライブへアクセスする場合の例は次のとおり。`$uf2` と `$drive` はその回の build と列挙に合わせる。

```powershell
$drive = (Get-Volume | Where-Object FileSystemLabel -eq 'RP2350').DriveLetter
Get-Content "${drive}:\INFO_UF2.TXT"
$uf2 = '\\wsl.localhost\Ubuntu-24.04\home\mt\.cache\arduino\sketches\1527AE5585367956AA6160ED17CDBDFD\Rp2350L103Probe.ino.uf2'
Copy-Item -LiteralPath $uf2 -Destination "${drive}:\Rp2350L103Probe.ino.uf2"
```

この `sketches` 以下の hash は build ごとに変わり得る。アプリ CDC が再列挙され、転送後の `dump` が成功してから
次の `--target l103` の2種類のテストを行う。WSL の `usbipd` / `picotool` 経路を使う場合だけ BOOTSEL identity の bind が要る。

```sh
cd /home/mt/dev_wch/ArduinoCore-CH32
uv run tests/manual/oep_smoke/oep_probe_checks.py --target l103
uv run tests/manual/oep_smoke/oep_smoke.py --target l103 --sketch all
```

## 5. 次に必要なテスト項目

| 優先 | テスト | 現状 |
|---|---|
| P1 | GPIO / UART / capture / wire / 永続 bind の共有可否と、先後どちらの plan / configure / release でも既存機能が維持されるか | 同時 plan の正常系と P4 I2C / SPI への後付け capture plan による破壊を確認。中断を許可しないときの副作用のない拒否、許可したときの probe による復元を修正後に検証。他 MCU は未試験 |
| P1 | 拒否された plan 更新でも旧 UART / capture が維持されること。planCheck 成功後に planApply が失敗する模擬も行う | UART の状態喪失を実機で再現。適用失敗の模擬試験なし |
| P1 | 保存した fn 一覧を変更した firmware で、旧設定が安全に適用されないこと | 現行の対応表でも未検証 |
| P1 | RP2350 → L103 の初回 flash 失敗の切り分け、追加書き直しが必要な条件の特定 | 14/14 を2回合格したが、1回目4ページ、2回目5ページの再書き込みあり。失敗が初回応答か読み戻しかは現行の集計出力だけでは不明 |
| P2 | `probe.config` の非 critical unknown item と、保存上限超過時の安全な失敗 | prototype の境界未試験 |
| P2 | SWD multidrop の targetsel 切替拒否、アナログのチャネル別 scale / skew | 対応する実機・実装で未試験 |
| P2 | V003 の DMI delay の反復測定、L103 の新規 attach(halt) の失敗率と波形 | 今回の単発では通過。既報の間欠不良は否定できない |

今回の14 sketch と probe チェックは、3台それぞれの代表的な正常系を確かめた。
独立実装との相互運用、アナログ、IP 経路、SWD multidrop、保存設定の firmware 更新時の挙動は、この結果からは判断しない。
