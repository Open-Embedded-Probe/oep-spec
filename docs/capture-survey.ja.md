# キャプチャの机上調査 — sigrok、市販のロジアナ、ESP32、RP2(OEP 設計向け)

調査日: 2026-09-25。ハードウェアは触っていない(USB 機器へのアクセスなし)。[キャプチャの提案](logic-capture.ja.md)の
根拠資料。実機の測定は提案の §7 にある。

参照ソース:
- libsigrok git HEAD `0bc2487778e660f4d3116729b6f4aee2b1996bb0`(2025-11-20)、比較用にタグ `libsigrok-0.5.2`。https://github.com/sigrokproject/libsigrok を clone し、以下 `src/...` はリポジトリ内パス
- PulseView git HEAD `af02198741b4e57c9f9b796bd5e6c0f2ae9f2f2b`(2025-11-10)。https://github.com/sigrokproject/pulseview
- pico-sdk / pico-examples master(raw.githubusercontent.com から取得)
- Saleae データシート PDF(downloads.saleae.com)
- ESP-IDF master(commit 048ec57f、2026-09-24)の sparse clone、release/v5.5 の soc_caps.h、ESP32-P4 / C6 の TRM とデータシート、espressif/esp-chip-errata(§5)

表記: **[確認]** はソースを読んで確かめた事実。**[未確認]** は推測、または一次資料で裏を取れていないもの。

---

## 1. libsigrok `hameg-hmo` ドライバ

ファイル: `src/hardware/hameg-hmo/{api.c,protocol.c,protocol.h}`

### 1.1 接続方式
- ドライバは SCPI 共通層を使う(`scan()` → `sr_scpi_scan(di->context, options, probe_device)`、`api.c`)。このため SCPI 共通層にあるトランスポートはすべて使える **[確認]**。
  - `src/scpi/scpi_tcp.c`: `tcp-raw/<host>/<port>`、`tcp-rigol/<host>/<port>`
  - `src/scpi/scpi_vxi.c`: `vxi/<host>[/...]`
  - `src/scpi/scpi_usbtmc_libusb.c`: `usbtmc/...`
  - `src/scpi/scpi_serial.c`: prefix なし(シリアルポート名そのまま)
  - `scpi_visa.c`(`visa/`)と `scpi_libgpib.c`(`libgpib/`)はビルド次第
- scanopts は `SR_CONF_CONN, SR_CONF_SERIALCOMM`(`api.c`)**[確認]**
- PulseView の接続ダイアログで TCP/IP を選ぶと、Protocol は "Raw TCP" → `tcp-raw/%1/%2`、"VXI" → `vxi/%1/%2` の 2 択。既定値は host 192.168.1.100、port 5555(`pv/dialogs/connect.cpp` 118–119 行)**[確認]**。`tcp-rigol` は GUI からは選べない。

### 1.2 識別(identify)
- `sr_scpi_get_hw_id()` が `*IDN?` を送り、応答をカンマで分割する。4 フィールドが規定だが、3 フィールドでも「シリアルなし」として受け付ける(`src/scpi/scpi.c` 1150–1195 行付近)**[確認]**
- manufacturer は `"HAMEG"` か `"Rohde&Schwarz"` に完全一致しなければならない(`std_str_idx_s`、`api.c` の `manufacturers[]`)**[確認]**
- model は `scope_models[].name[]` のどれかに `strcmp` で完全一致しなければならない(`hmo_init_device`、`protocol.c`)**[確認]**
- 例: `HAMEG,HMO1202,123456,05.886`

### 1.3 モデル別チャネル数(`protocol.c` の `scope_models[]`)**[確認]**
| モデル名 | アナログ | デジタル | 方言(dialect) |
|---|---|---|---|
| HMO722/1022/1522/2022 | 2 | 8 | hameg (`:POD%d:DATA?`) |
| RTC1002, HMO1002, HMO1202 | 2 | 8 | hameg |
| HMO3032/3042/3052/3522 | 2 | 16 | hameg |
| HMO724/1024/1524/2024 | 4 | 8 | hameg |
| HMO2524/3034/3044/3054/3524 | 4 | 16 | hameg |
| RTB2002 | 2 | 16 | R&S (`:LOG%d:DATA?`) |
| RTB2004, RTM3004, RTA4004 | 4 | 16 | R&S |
| RTM3002 | 2 | 16 | R&S |
| RTH1002 | 2 | 8 | R&S(git のみ。0.5.2 には無い) |
| RTH1004 | 4 | 8 | R&S(git のみ) |

- `DIGITAL_CHANNELS_PER_POD = 8`。1 POD がチャネルグループ 1 つ(`POD1`、`POD2`)。アナログは 1 チャネルが 1 グループ(`CH1`〜)。ロジックのチャネル名は `D0`〜`D15`(`protocol.h`、`protocol.c`)**[確認]**
- 制約: POD1 と CH3、POD2 と CH4 は同時に有効にできない(`hmo_check_channels`、`api.c`)。4ch モデルで効く。2ch モデルでは CH3/CH4 が存在しないので問題にならない **[確認]**

### 1.4 送信する SCPI コマンド(hameg 方言、`protocol.c` の `hameg_scpi_dialect[]`)**[確認]**
open 時(`hmo_scope_state_get`)に送る問い合わせ。応答の要件も付記する。
- アナログ各 ch(n = 1..):
  - `:CHANn:STAT?`: bool。`1/0/ON/OFF/true` 等を `parse_strict_bool` で解釈
  - `:CHANn:SCAL?`: vdiv 表の値に有理数として一致しないと open 失敗(`array_float_get`)。表は 1mV〜10V(RTB2002/2004 は 50V まで)の 1-2-5。例 `1.000E+00`
  - `:CHANn:POS?`: float
  - `:CHANn:COUP?`: `AC/ACL/DC/DCL/GND` のどれか(モデル依存)
  - `:PROBn:SET:ATT:UNIT?`: 先頭文字が `A` なら電流、それ以外は電圧
- デジタル各 ch(i = 0..):
  - `:LOGi:STAT?`: bool
- 各 POD(p = 1..):
  - `:PODp:STAT?`: bool
  - `:PODp:THR?`: `TTL/ECL/CMOS/USER1/USER2`(`USER` も可)。USER 系を返したときは、続けて `:PODp:THR:UDLk?`(float)も来る
- 時間軸・トリガ・取得条件:
  - `:TIM:SCAL?`: timebase 表(1ns〜50s の 1-2-5)に一致する値
  - `:TIM:DIV?`: int。水平目盛り数
  - `:TIM:POS?`: float
  - `:TRIG:A:SOUR?`: トリガソース表のどれか。例 `CH1`
  - `:TRIG:A:EDGE:SLOP?`: `POS/NEG/EITH`
  - `:TRIG:A:PATT:SOUR?`: 文字列。引用符は外して扱う
  - `:ACQ:HRES?`、`:ACQ:PEAK?`: `OFF` かそれ以外か
  - `:ACQ:SRAT?`: float → サンプルレート

設定系(config_set)。どれも送信直後に `*OPC?` を送り、真(`1`)が返ることを期待する:
- `:TIM:SCAL %s`。このあと `:ACQ:SRAT?` を読み直す
- `:CHANn:SCAL`、`:CHANn:COUP`
- `:TRIG:A:SOUR %s`
- `:TRIG:A:TYPE EDGE;:TRIG:A:EDGE:SLOP %s`
- パターントリガ: `:TRIG:A:TYPE LOGIC;:TRIG:A:PATT:FUNC AND;:TRIG:A:PATT:COND "TRUE";:TRIG:A:PATT:MODE OFF;:TRIG:A:PATT:SOUR "%s"`
- `:TIM:POS`、`:ACQ:HRES AUTO|OFF`、`:ACQ:PEAK AUTO|OFF`
- `:PODp:THR`、`:PODp:THR:UDLk`
- チャネル有効化(acquisition start 時、状態が変わった分だけ送る): `:CHANn:STAT 0|1`、`:LOGi:STAT 0|1`、`:PODp:STAT 0|1`。何か変えたら `:ACQ:SRAT?` を読み直す(`hmo_setup_channels`、`api.c`)

データ取得(`hmo_request_data`、`api.c`):
- アナログ: `:FORM:BORD LSBF;:FORM REAL,32;:CHANn:DATA?`(ホストがビッグエンディアンなら MSBF)
- デジタル: `:FORM UINT,8;:PODp:DATA?`。有効な POD ごとに 1 回だけ(POD 内で最初に有効なチャネルを代表にする)
- 応答は IEEE 488.2 definite length block(`#<桁数><長さ><データ>`)でなければならない。`#0`(indefinite length)はエラーになる(`sr_scpi_get_block`、`scpi.c` 978 行〜)**[確認]**

### 1.5 サンプルレートの決まり方
- **読むだけで、設定はできない**。devopts は `SR_CONF_SAMPLERATE | SR_CONF_GET`(LIST なし)。値は `:ACQ:SRAT?` の float をそのまま使う(`hmo_update_sample_rate`)**[確認]**
- ユーザーが操作できるのは `SR_CONF_TIMEBASE`(GET/SET/LIST)。timebase を変えると `:ACQ:SRAT?` を読み直す **[確認]**
- PulseView は SAMPLERATE に LIST が無いと、レート選択 UI を出さない(`sample_rate_.show_none()`、`pv/toolbars/mainbar.cpp`)。取得開始時に `config_get(SAMPLERATE)` を 1 回読む(`pv/session.cpp` 1267 行)**[確認]**

### 1.6 取得モデル: フレーム単位のポーリング(ストリーミングではない)
- ドライバは RUN/SINGLE/STOP のようなアーム系コマンドを一切送らない。スコープが今持っている波形を、チャネル順に `DATA?` で吸い出すだけ **[確認]**(api.c と protocol.c に該当コマンドが無い)
- 1 フレーム = 有効なアナログ ch とデジタル POD を順に 1 回ずつ取得すること。流れは `SR_DF_FRAME_BEGIN` → 各 ch の `SR_DF_ANALOG` / `SR_DF_LOGIC` → `SR_DF_FRAME_END`(`hmo_receive_data`)
- 終了条件: `if (++num_frames >= frame_limit || num_samples >= samples_limit) stop;`(`protocol.c` 末尾)**[確認]**
  - `frame_limit` の既定は 0。0 だと 1 フレームで止まる(`1 >= 0`)。PulseView は LIMIT_FRAMES の 0 を "No Limit" と表示するが、このドライバでは 0 は「1 フレームで停止」の意味になる
  - `num_samples` は直前フレームの 1 ch 分のサンプル数で、累積ではない。PulseView は開始時に sample count を `LIMIT_SAMPLES` に set するので、**フレーム長 < sample count で、かつ frames > 1** のときだけ連続フレームになる
  - 例: `sigrok-cli -d hameg-hmo:conn=tcp-raw/127.0.0.1/5025 --frames 100`
- PulseView は FRAME_END ごとにセグメントを確定する(`Session::feed_in_frame_end`)。**セグメント(フレーム)が次々に積み上がる形**で、連続スクロール表示ではない **[確認]**
- LIMIT_SAMPLES を指定すると、各 ch のデータはその長さで切り詰められる **[確認]**

### 1.7 データ形式 **[確認]**
- アナログ: `REAL,32` のリトルエンディアン float。値は物理量(V または A)そのもの。`num_samples = len/4`
- デジタル: `UINT,8`。1 サンプル 1 バイトで、bit k が POD 内の k 番目のチャネル。
  - POD が 1 つだけなら、受け取ったバイト列をそのまま `unitsize=1` で送る
  - POD2 が絡むと、`pod_count` バイトにインタリーブして `unitsize=pod_count` にする(`hmo_queue_logic_data`)
- ドライバ側に、アナログとデジタルのサンプル数を揃える処理は無い。PulseView は同じ samplerate で描くので、**なりすまし側でアナログ・デジタルの長さを揃える**のが無難 **[確認: 揃える処理が無いこと / 推奨は推論]**

### 1.8 TCP サーバでなりすますときに実装すべきもの
(`tcp-raw` を前提に、上のソースから導いた要件)
1. 受信: コマンドは `\n` 終端(`scpi_send_variadic` が付ける)。1 行に `;` 区切りで複数コマンドが来る。例 `:FORM:BORD LSBF;:FORM REAL,32;:CHAN1:DATA?`。**`;` で分割し、先頭 `:` の有無も吸収するパーサ**が要る
2. 問い合わせへの応答は、テキストなら `...\n` を**1 回の send で**返す。
   - 理由: tcp-raw の read は「読めたバイト数がバッファより少ない = 応答終わり」とみなす(`scpi_tcp_raw_read_data`: `response_length = rcvd < rdlen ? rcvd : rdlen+1`)。応答が 2 つのセグメントに分かれると途中で切れる **[確認]**
   - バイナリブロックは長さヘッダに従って読むので、分割されても構わない **[確認]**
   - ただしブロック後の `\n` が遅れて別セグメントで届くと、次の応答の先頭にゴミとして残る可能性がある。**ブロックと末尾 LF は 1 回の send にまとめる**か、LF を付けない **[推論]**
3. 1.4 の問い合わせにすべて、表に一致する値で答える。1 つでも表外の値を返すと `dev_open` が失敗する(vdiv と timebase は有理数として厳密一致)
4. set 系コマンドは黙って状態を更新し、続けて来る `*OPC?` に `1` を返す
5. `:CHANn:DATA?` には `#<n><len>` + float32LE × N、`:PODp:DATA?` には `#<n><len>` + u8 × N を返す
6. `:ACQ:SRAT?` には、フレームの実サンプルレートを返す。PulseView の時間軸はこの値で決まる
7. 読み出しのタイムアウトは 1 s(`scpi_dev_inst_new`: `read_timeout_us = 1000*1000`)。ただし受信が進んでいる間は延長される。巨大なブロックでも途中で止まらなければよい **[確認]**
8. 「ライブ」に見せるには、ホスト側で波形を 1 フレーム分溜めておき、`DATA?` のたびに最新のフレームを返す。frames を大きく、sample count をフレーム長より大きく設定してもらう必要がある(1.6 参照)。ドライバ任せのフレーム間隔は、SCPI の往復 + ch 数分の転送時間で決まる

### 1.9 いちばんなりすましやすいモデル
- **HMO1202(または HMO1002 / RTC1002): アナログ 2 + デジタル 8(POD1 つ)**。理由:
  - POD が 1 つなのでロジックは `unitsize=1` のパススルー。POD2 のインタリーブ処理を通らない
  - 2ch なので CH3/CH4 と POD の排他制約が効かない
  - 問い合わせの数が最小(アナログ 2 × 5、デジタル 8、POD 1 × 2)
  - hameg 方言は RTB/RTM(R&S 方言の `:DIG%d:TECH?` 等)より素直
- デジタルが 16 本要るなら HMO3032(2 + 16、POD2 つ、インタリーブ経路を通る)
- 注意: 0.5.2 では vdiv 表が 10V までで、RTH 系は存在しない。HMO1202 は 0.5.2 と git の両方にある **[確認]**

---

## 2. TCP で使える他の libsigrok ドライバ

TCP を直接話すドライバ: `beaglelogic`(beaglelogic_tcp.c)と `ipdbg-la`(protocol.c)**[確認]**(`grep socket(|getaddrinfo src/hardware`)。それ以外は SCPI 共通層か、次の serial-over-TCP を経由する。

**重要: git 版には `src/serial_tcpraw.c` がある**(commit c4f0fda、2023-09-24 "serial: introduce support for raw TCP communication")。`conn=tcp-raw/<host>/<port>` を渡せば、**シリアル系ドライバ全般が TCP で動く**。0.5.2(2019)には無い **[確認]**。OLS/SUMP や raspberrypi-pico ドライバを TCP で使えるのは git ビルドだけ。

| ドライバ | 0.5.2 | TCP 方式 | ch | 取得モデル | サンプルレート | 出典 |
|---|---|---|---|---|---|---|
| beaglelogic | ○ | 独自テキスト + 生バイト(`conn=tcp-raw/host/port`。接頭辞は "tcp" で始まればよい) | ロジック 14(`numchannels<=8` なら 8) | **ストリーミング**(`get` 送信後に生サンプルが流れ続ける)。LIMIT_SAMPLES で ONESHOT、未指定で CONTINUOUS。トリガはホスト側のソフトトリガ | steps (10 Hz, 100 MHz, 1)。PulseView は 1-2-5 リスト。SET/GET 可 | `src/hardware/beaglelogic/{api.c,beaglelogic_tcp.c,protocol.c}` |
| ipdbg-la | ○ | 独自バイナリ(1 バイトコマンド、0x55 エスケープ) | ロジック N(`CMD_GET_BUS_WIDTHS` の data_width。任意本数) | ワンショット、メモリ深さ 2^addr_width。トリガ mask/value/edge | **SAMPLERATE キーなし**(時間軸なし) | `src/hardware/ipdbg-la/{api.c,protocol.c}` |
| hameg-hmo | ○ | SCPI | §1 | フレーム | GET のみ | §1 |
| rigol-ds | ○ | SCPI(tcp-raw/vxi/usbtmc)。`tcp-rigol` は Rigol 独自の長さ前置 | アナログ 2/4、MSO モデル(DS1000D、MSO2000A、DS1000Z Plus/MSO1000Z、MSO5000)はデジタル 16 | フレーム。`:SING`/`:TRIG:STAT?` のポーリング等でアームと完了待ちをする状態機械。アナログは `:WAV:FORM BYTE` + YINC/YOR/YREF で換算。デジタルは V4 以降が D ごと 1 バイト(LSB のみ有効)、それ未満は 2 バイト | GET のみ。LIVE なら フレームサイズ /(timebase × 目盛数)、それ以外は 1/`WAV:XINC?` | `src/hardware/rigol-ds/{api.c,protocol.c}` |
| siglent-sds | ○ | SCPI | アナログ 2/4。デジタル 16 は SDS1104X-E / SDS1204X-E のみ | フレーム(`ARM`、`:INR?` ポーリング、`C%d:WF? ALL`、`D%d:WF? DAT2`) | GET のみ(メモリ深さ /(TDIV × 目盛数)) | `src/hardware/siglent-sds/{api.c,protocol.c}` |
| openbench-logic-sniffer | ○(シリアルのみ) | SUMP バイナリ。**git 版は serial_tcpraw 経由で TCP 可** | ロジック最大 32(8ch × 4 グループ) | ワンショット(メモリ)。§4 | steps (10 Hz, 200 MHz または metadata の max, 1) | §4 |
| raspberrypi-pico | ×(2022 年追加) | テキストコマンド + 7bit エンコードのストリーム。**git 版は serial_tcpraw 経由で TCP 可** | アナログ ≤8 + デジタル ≤32(ID 文字列で自己申告) | **ストリーミング**(`F` = 固定長、`C` = 連続 + ソフトトリガ)。RLE あり | 固定リスト 5 kHz〜240 MHz(下記) | `src/hardware/raspberrypi-pico/{api.c,protocol.c}` |
| demo | ○ | (ネットワークなし) | ロジック 8、アナログ 5(既定。scan オプションで変更可) | 連続(LIMIT_FRAMES も可) | steps (1 Hz, 1 GHz, 1) | `src/hardware/demo/api.c` |

補足:
- **汎用の「tcp ロジック」ドライバは存在しない** **[確認]**(ドライバ一覧に無い)。いちばん近いのは beaglelogic(ロジック専用ストリーム)と raspberrypi-pico(アナログ + ロジックのストリーム)
- **raspberrypi-pico プロトコルの要点 [確認]**:
  - scan 時: `*` でリセット → `i\n` → `SRPICO,AxxyDzz,02`(xx = アナログ ch 数、y = アナログ 1 サンプルのバイト数(1 バイト 7bit)、zz = デジタル ch 数、末尾 02 = 版)
  - 開始時: `A<en><idx>\n` / `D<en><idx>\n`(各々 `*` で ACK)→ トリガ `t<type><pin>\n` → `p<pretrig>\n` → `L<limit>\n` → `a<i>\n` に `<scale_uV>x<offset_uV>` で応答 → `R<rate>\n`(`*` で成功)→ `F\n` または `C\n`
  - データ: 各バイト ≥0x80 がデータ。デジタル 7bit ずつ → アナログ(a_size バイト × 有効 ch)の順。0x30–0x7F は RLE。終端は `$<bytecount>+`
  - 停止は `+`。デジタルの有効 ch は連続していなければならない
  - ホストはアナログとデジタルが両方有効なとき、レートを 24 MHz の整数分周に丸める(`api.c` 580 行付近)。ただしこの補正値は PulseView 側の cur_samplerate には反映されない可能性がある **[未確認]**
  - OEP ホストが「TCP で Pico のふりをする」なら、**PulseView(git ビルド)でアナログ + ロジックをストリーミング表示できるいちばん素直な経路**。0.5.2 系の安定版パッケージでは使えない
- 各配布版 PulseView(Windows nightly / AppImage / distro)に hameg-hmo や raspberrypi-pico、serial_tcpraw が入っているかはビルド次第 **[未確認]**

---

## 3. サンプルレートの表現(libsigrok の慣習)

### 3.1 2 つの形 **[確認]**
`config_list(SR_CONF_SAMPLERATE)` は `a{sv}` の辞書を返す(`src/std.c` の `samplerate_helper`):
- `"samplerates"`: `at` の固定列挙(`std_gvar_samplerates`)
- `"samplerate-steps"`: `at` の [min, max, step](`std_gvar_samplerates_steps`)

PulseView の扱い(`pv/toolbars/mainbar.cpp`):
- steps で step == 1 → `show_125_list(min,max)`(min..max の範囲で 1-2-5 系列のドロップダウンを生成)
- steps で step != 1 → スピンボックス(min, max, step)
- samplerates → その列挙をそのまま表示
- LIST が無い → レート UI を出さない

形ごとのドライバ(`grep std_gvar_samplerates(_steps)? src/hardware`):
- steps: agilent-dmm, baylibre-acme, beaglelogic (10 Hz–100 MHz), demo (1 Hz–1 GHz), ftdi-la (3600 Hz–10 MHz), itech-it8500, link-mso19, openbench-logic-sniffer (10 Hz–200 MHz/metadata), pipistrello-ols
- 列挙: fx2lafw, dreamsourcelab-dslogic, saleae-logic16, saleae-logic-pro, kingst-la2016, raspberrypi-pico, asix-sigma, chronovu-la, hantek-*, zeroplus, sysclk-* など

### 3.2 代表的な列挙値 **[確認: libsigrok ソース]**
- **fx2lafw**(Saleae Logic 互換機ほか)`fx2lafw/api.c`: 20k, 25k, 50k, 100k, 200k, 250k, 500k, 1M, 2M, 3M, 4M, 6M, 8M, 12M, 16M, 24M, 48M。48 MHz を整数で割った値の集合で、1-2-5 ではない。16bit 幅だと上限が下がる(`MAX_16BIT_SAMPLE_RATE`、`fx2lafw/protocol.c`)
- **DSLogic**(`dreamsourcelab-dslogic/api.c`): 10k, 20k, 50k, 100k, 200k, 500k, 1M, 2M, 5M, 10M, 20M, 25M, 50M, 100M, 200M, 400M。基本 1-2-5 で 25M が混じる
- **Saleae Logic16**(sigrok 独自ファーム、`saleae-logic16/api.c`): 500k, 1M, 2M, 4M, 5M, 8M, 10M, 12.5M, 16M, 20M, 25M, 32M, 40M, 50M, 80M, 100M
- **Saleae Logic Pro**(`saleae-logic-pro/api.c`): 1M, 2M, 2.5M, 10M, 25M, 50M(sigrok 対応分のみ)
- **Kingst LA2016 系**: 20k〜500M/200M/100M の 1-2-5(`kingst-la2016/api.c`)
- **demo**: steps 1 Hz–1 GHz(PulseView では 1-2-5)
- **raspberrypi-pico**: 5k, 6k, 8k, 10k, 20k, 30k, 40k, 50k, 60k, 80k, 100k, 125k, 150k, 160k, 200k, 250k, 300k, 400k, 500k, 600k, 800k, 1M, 1.2M, 1.5M, 2M, 2.4M, 3M, 4M, 5M, 6M, 8M, 10M, 15M, 20M, 30M, 40M, 60M, 80M, 100M, 120M, 150M, 200M, 240M。ADC 48 MHz と PIO 120 MHz の整数分周を意識した値

### 3.3 Saleae 純正(Logic 2)のレートメニュー
データシート記載の値 **[確認: PDF のテキスト抽出]**:
- **Logic 8**(https://downloads.saleae.com/specs/logic_8_data_sheet.pdf)
  - Digital: 100¹, 50¹, 40¹, 25, 20, 10, 8, 5, 4, 2, 1 MSPS(¹ = 100 MSPS は ≤3ch、50 は ≤6ch、40 は ≤7ch)
  - Analog: 10, 5, 2.5, 1.25 MSPS, 625, 125, 5, 1 kSPS, 100, 10 SPS
- **Logic Pro 16**(https://downloads.saleae.com/specs/logic_pro_16_data_sheet.pdf)
  - Digital: 500¹, 100, 50, 25, 12.5, 10, 6.25, 5, 4, 2.5, 2, 1 MSPS(¹ = 500 MSPS は ≤4ch、USB3)
  - Analog: 50, 12.5, 6.25, 3.125, 1.562 MSPS, 781.25, 125, 5, 1 kSPS, 100, 10 SPS
  - 同じ PDF の例示に「4ch digital only 400 MSPS」があるのに、抽出したリストには 400/250/200 が無い。**抽出漏れの可能性があり、完全なリストは未確認**
- Saleae サポートページ(https://www.saleae.com/support/logic-software/capturing-data/what-sample-rate-settings-are-available)には「組み合わせの全体はソフトで確認せよ」「ch を増やすと上限が下がる」「デジタルとアナログのレートは相互に制約する」とあり、公式の完全な表は無い **[確認]**
- Logic Pro 8 の値は未取得 **[未確認]**

### 3.4 業界の慣習(まとめ)
- 固定列挙が主流。1-2-5 系列(DSLogic、Kingst)と、基準クロックの整数分周の集合(fx2lafw の 48 MHz 系、Saleae のアナログ 50M/4^k 系、pico)が混在する
- Saleae は ch 数と USB 帯域で上限が動く。アナログは 50 MHz ÷ 2^n 系で、低速域は飛び飛び(125k → 5k → 1k → 100 → 10)
- OEP への含意 **[推論]**:
  - デバイスには「実現可能なレートの列挙(または基準クロック + 分周範囲)」を申告させる。ホスト(sigrok 側)はそれを `samplerates` 列挙で見せるのが PulseView 互換の近道
  - steps + step=1 にすると PulseView は 1-2-5 を勝手に生成する。そこに実現できない値が混じると、丸めが必要になる

---

## 4. SUMP / OLS(libsigrok `openbench-logic-sniffer`)の制約

ファイル: `src/hardware/openbench-logic-sniffer/{api.c,protocol.c,protocol.h}` **[確認]**
- **識別**: `0x00` reset(×5)→ `0x02` ID → 4 バイト `1ALS` または `1SLO`。続いて `0x04` metadata。
  - metadata のトークン: 0x01 名前、0x02 FPGA 版、0x20 ch 数、0x21 メモリバイト数、0x23 最大レート、0x24 プロトコル版、0x40/0x41 は short 形
  - metadata が無ければ "Sump Logic Analyzer" として扱う
- **レート**: `CLOCK_RATE = 100 MHz`。`divider = CLOCK/rate − 1`(24bit、`CMD_SET_DIVIDER 0x80`)。実レートは `100 MHz/(div+1)`
  - rate > 100 MHz なら DEMUX モード(`div = 200 MHz/rate − 1`、実レート ×2、ノイズフィルタ off)
  - 要求値と一致しないときはログを出すだけで、実レートに置き換える
  - LIST は steps [10 Hz, max(200 MHz または metadata 0x23), 1]
- **チャネルグループ**: 8ch × 4 グループ。flags の bit2–5 = グループ無効化(1 で無効)。unitsize は有効グループ数で決まる(git 版は "Fix hardcoded unitsize")
- **サンプル数/遅延**: `samplecount = MIN(max_samples/num_changroups, limit_samples)`、`readcount = (samplecount+3)/4`(4 サンプル単位)
  - max_samples ≤ 256K: `CMD_CAPTURE_SIZE 0x81`。readcount−1 と delaycount−1 を各 16bit
  - それ以上: Pepino 拡張の `0x84 READCOUNT` / `0x83 DELAYCOUNT`(各 32bit)
  - `delaycount = readcount × (1 − capture_ratio/100)`
  - LIMIT_SAMPLES の下限は `MIN_NUM_SAMPLES = 4`
  - metadata が無いときの max_samples 既定: Shrimp は 256K、他は metadata 依存
- **トリガ**: basic trigger 4 ステージ(`NUM_BASIC_TRIGGER_STAGES 4`)。ステージ i ごとに `0xC0+4i` mask、`0xC1+4i` value、`0xC2+4i` config を送る。config の arg[2] = stage、最終ステージに `TRIGGER_START(1<<3)`
  - libsigrok が受け付けるマッチは ZERO/ONE だけ(エッジなし)
  - トリガなしのときはステージ 0 を強制発火
  - Demon Core の advanced trigger 用コマンド(0x0F、0x9E、0x9F)は定義があるだけで、使われていない
- **RLE**: flags bit8 `CAPTURE_FLAG_RLE`。サンプルの MSB が立っていればカウント値として扱い、デコードする(`protocol.c` 410–490 行)。RLE モード bit14–15 は常に 0
- **データ順**: OLS はバッファを後ろから送ってくるので、ドライバが逆順に並べ直す
- **その他の flags**: EXTERNAL_CLOCK(bit6)、INVERT_EXT_CLOCK(bit7)、NOISE_FILTER(bit1)、DEMUX(bit0)、SWAP_CHANNELS(bit9)、内部/外部テストパターン(bit10/11)
- 0.5.2 との違い: 0.5.2 でも READCOUNT/DELAYCOUNT と 4 ステージはある。git 版で samplerate range の修正、unitsize の修正、scan 失敗時のポートクローズが入った(`git log`)

---

## 5. ESP32-P4 PARLIO RX / ESP ADC 連続モード

ファイルの置き場所が版で違う: master では ADC の HAL は `components/esp_hal_ana_conv/<chip>/include/hal/adc_ll.h`、
PARLIO は `components/esp_hal_parlio/<chip>/include/hal/parlio_ll.h`。master でいくつかの `SOC_ADC_*` が `ADC_LL_*` に
移ったが、release/v5.5 の `soc_caps.h` では `SOC_*` のままで値は同じ **[確認]**。

### 5.1 PARLIO RX(ESP32-P4)
- **RX ユニットは 1 つ**(`PARLIO_LL_INST_NUM 1`、`PARLIO_LL_RX_UNITS_PER_INST 1`。v5.5 は `SOC_PARLIO_GROUPS 1U`、
  `SOC_PARLIO_RX_UNITS_PER_GROUP 1U`)。C6 / H2 / C5 も 1 つ **[確認]**
- **幅は最大 16**(`SOC_PARLIO_RX_UNIT_MAX_DATA_WIDTH 16`)。`data_width` は 2 のべき乗かつ 16 以下(`parlio_rx.c` 612 行付近)。
  TRM も 1/2/4/8/16 ビット **[確認]**
- **クロック源**: XTAL(40 MHz)、RC_FAST、PLL_F160M(既定)、`PARLIO_CLK_SRC_EXTERNAL = -1`(`clk_tree_defs.h` 744–750 行)。
  分周は整数(〜0x100)+ 分数(`PARLIO_LL_RX_MAX_CLK_INT_DIV 0x100`、`..._FRACT_DIV 0x100`)。C6 / H2 / C5 は整数のみ
  (〜0x10000)**[確認]**
- **外部クロック**: `clk_src = PARLIO_CLK_SRC_EXTERNAL`、`clk_in_gpio_num`(必須)、`ext_clk_freq_hz`(必須、0 不可)。
  `exp_clk_freq_hz` は既定で `ext_clk_freq_hz` と同じで、外部クロックを分周することもできる。`flags.free_clk` は常時動く
  クロック(I2S の BCLK など)か、止まるクロック(SPI の SCLK など)かの区別(`parlio_rx.h`、`parlio_rx.c` 257 / 496–524 行、
  `parlio_rx.rst` 245–280 行)**[確認]**
- **IO クロックの上限は 40 MHz**(P4 データシート v0.7 §4.2.2.18、TRM 61.3。TRM は PRELIMINARY)。soc_caps / LL にこの値は
  なく、ドライバは検査しない **[確認]**。止まるクロックの制約(サンプルのエッジ、開始の順序)は TRM §61.5.2–61.5.3
- **有効信号(valid)と区切り**(`parlio_rx.c` 190–245 / 826–911 行):
  - valid はレベル / パルスの区切りでだけ使う。ドライバの中では `valid_sig_line_id` のデータ線に割り当てられ、
    `valid_sig_line_id < data_width` は拒否される(998–1002 行)。**valid が 16 本のデータ線の 1 本を使うので、
    レベル / パルスの区切りではデータは 8 ビットまで** **[確認]**。TRM §61.5.4.1–2 はパルスのサブモード 5–6 で
    イネーブルのピンをデータと兼用できるとするが、ドライバはそれを出していない
  - レベルの区切り: valid が有効な間だけ取る。`eof_data_len = 0` で valid が無効になったときに終わる。TRM は
    valid による終了をパルスのサブモード 1 / 3 だけに許す(§61.5.5)ので、ドライバとの食い違いがある **[未確認]**
  - パルスの区切り: 開始(と終了)のパルスでフレームを区切る。`eof_data_len` か `has_end_pulse` のどちらかが必須。
    `eof_data_len` は `PARLIO_LL_RX_MAX_BYTES_PER_FRAME` = 0xFFFF バイトまで
  - ソフトウェアの区切り: 外部の信号なし。`parlio_rx_soft_delimiter_start_stop()` で開始と停止。`eof_data_len` は
    1〜0xFFFF。TRM §61.5.4.3 によると、クロックドメインをまたぐので開始と停止の境目はサンプル単位では合わない
  - ビット長での EOF は 1 フレーム 2^19−1 ビットまで(TRM §61.5.12)。valid による EOF には長さの制限がない。
    `timeout_ticks` は源クロックの tick で 16 ビット
  - 割り込みは RX FIFO のあふれだけで、フレームの完了は GDMA の EOF で知る(TRM 表 61.6-1)。ETM に PARLIO の
    イベントはない
- **連続取得**: `parlio_receive_config_t.flags.partial_rx_en = 1` で、DMA の記述子をリングにつなぐ(`GDMA_FINAL_LINK_TO_HEAD`、
  `parlio_rx.c` 183 行付近、最低 2 ノード)。記述子ごとに `on_partial_receive` が呼ばれる。`indirect_mount` は内部の
  DMA バッファから ISR でコピーする形(少し遅くなる)。esp-idf の例 `examples/peripherals/parlio/parlio_rx/logic_analyzer`
  は、ソフトウェアの区切り + 内部クロック + `partial_rx_en` を使う(`parlio_rx.rst` 282–312 行「logic analyzer などに
  向く」)。P4 の持続帯域の公式な数字は見つからなかった **[未確認]**(例の README の数字は C6 のもの)

| チップ | RX ユニット | 幅 | クロック上限 | 分周 |
|---|---|---|---|---|
| C6 | 1 | 16 | 40 MHz(C6 TRM v1.2 §38.3) | 整数のみ |
| H2 | 1 | 8 | 未確認 | 整数 |
| C5 | 1 | 8 | 未確認 | 整数 |

### 5.2 ADC の連続変換(DMA)

| | ESP32 | ESP32-S3 | ESP32-P4 |
|---|---|---|---|
| SAMPLE_FREQ_THRES_HIGH / LOW (Hz) | 2,000,000 / 20,000 | 83,333 / 611 | 83,333 / 611 |
| PATT_LEN_MAX | 16 | 24 | 16 |
| ビット幅 | 9〜12 | 12 | 12 |
| ADC2 の DMA | なし(ADC1 のみ) | 既定では使わない(エラッタ ADC-183) | あり |
| 1 結果のバイト数 | 2 | 4 | 4 |
| 出力の形 | TYPE1 | TYPE2 | TYPE2 |
| IIR フィルタ / モニタ(esp-idf) | なし / なし | あり / あり(各 2) | soc_caps でどちらも無効 |
| データシートのレート | DIG 2 Msps(RTC 200 ksps) | 100 kSPS | 100 kSPS |

出典: master の `soc/<chip>/include/soc/soc_caps.h` と `adc_ll.h`(v5.5 も同値)**[確認]**
- S3 / P4 の `adc_ll.h` のコメント: 「F_sample = F_digi_con / 2 / interval、F_digi_con = 5M、30 ≤ interval ≤ 4095」。
  P4 TRM §65.5.3: 1 回の変換は SARCLK 25 サイクル、SARCLK が 5 MHz を超えると精度が落ちる
- ドライバは ADC1 のみの制限を `adc_continuous.c` 469–483 行、`sample_freq_hz` の範囲を 486 行で検査する
- P4 の ADC2 は GPIO49–54 の 6 チャネル
- **スケジューリング**: パターン表 `adc_digi_pattern_config_t {atten, channel, unit, bit_width}` を 1 変換 1 エントリで
  順に回す。変換モードは `SINGLE_UNIT_1/2`、`BOTH_UNIT`(1 回の契機で ADC1 と ADC2 を同時に)、`ALTER_UNIT`(交互)。
  classic ESP32 は SINGLE_UNIT_1 のみ
- **`sample_freq_hz` は全チャネル合計の変換レート**(HAL が 1 つの間隔を設定する。`adc_hal.c` 118–134 行)。チャネル
  あたりはおおよそ `sample_freq_hz / pattern_num`。ドキュメントは「expected ADC sampling frequency」とだけ書く
  (チャネルあたりの解釈は HAL のコードからの推論)
- classic ESP32 は I2S0 を DMA の FIFO に使う(bclk = 2 × sample_freq、160 MHz 基準)。I2S0 が使用中なら
  `adc_continuous_new_handle` が `ESP_ERR_NOT_FOUND` を返す
- **結果の形**(`adc_types.h` 161–245 行): ESP32 は 16 ビット(`data:12 | channel:4`、unit なし = ADC1)。S3 / P4 は
  32 ビット(`data:12 | reserved:1 | channel:4 | unit:1 | reserved:14`)。チャネルが上限を超える値は無効データ
- **モニタと IIR フィルタ**: 3 つのうち esp-idf で使えるのは S3 だけ。P4 はハードウェアにある(TRM §65.3: フィルタ 2、
  しきい値モニタ 2、上下のしきい値で割り込み)が、soc_caps で無効なので `adc_monitor.c` / `adc_filter.c` がビルドされない。
  P4 の ETM にはモニタのイベント(`ADC_EVT_EQ_ABOVE_THRESH0/1`、`ADC_EVT_EQ_BELOW_THRESH0/1`)と開始のタスクがあるが、
  ADC の ETM ドライバは見つからなかった
  - モニタの API: `adc_monitor_config_t {adc_unit, channel, h_threshold, l_threshold}`。コールバックのイベントデータは
    空で、サンプルの位置も時刻もない。範囲外の間は毎回割り込む。ゼロクロスの検出には直流のバイアスが要る
  - トリガとしては、S3 は CPU の割り込み経由(揺れがあり、サンプル位置は分からない)。P4 は ETM でハードウェアトリガに
    できる可能性があるが、レジスタを直接触る必要がある **[未確認]**
- **既知の問題**:
  - classic ESP32 の実レートが 18〜22% 低い(esp-idf #16768、#10612、#10586)
  - **P4 で 83,333 Hz にすると各サンプルが 2 回ずつ出て実質 40 kHz 前後になる**(#17792、未回答)。実機で再現した
    (提案の §7.4。48 kHz 以上で起きる)
  - S3 の ADC2 DMA はエラッタ ADC-183(偽のサンプリング開始で動かなくなる)
  - classic ESP32 の ADC2 は Wi-Fi と共有。GPIO36/39 は SAR ADC の電源投入で約 80 ns 引き下げられる(GPIO-3.11)
  - 1 つの ADC ユニットは連続変換とワンショットを同時には使えない。連続変換中は RNG の品質が下がる。
    `CONFIG_PM_ENABLE` の APB 周波数の変化で連続変換の挙動が変わる

## 6. RP2040 / RP2350

### 6.1 ADC **[確認: pico-sdk `hardware_adc/include/hardware/adc.h`、`platform_defs.h`]**
- 500 kS/s、独立した 48 MHz クロックで動く。1 変換に 96 サイクルかかる。`adc_set_clkdiv`: 「サンプル周期は平均 (1+div) サイクル。96 未満は 96 にクランプ」。div は 16.8 の小数分周
- 入力: RP2040 と RP2350A(QFN-60)は 0–3 = GPIO26–29、4 = 温度センサ(`NUM_ADC_CHANNELS 5`)。RP2350B(QFN-80)は 0–7 = GPIO40–47、8 = 温度(`NUM_ADC_CHANNELS 9`)
- **ラウンドロビン**: `adc_set_round_robin(mask)`。1 変換ごとに次の有効入力へ移る。ADC は 1 つなので、**合計 500 kS/s を ch 数で割る**(例: 2ch なら各 250 kS/s)。各 ch のサンプル時刻は 1 変換周期ずつずれる(同時サンプリングではない)
- FIFO は 8 段で、満杯だと新しい結果を捨てる。DREQ で DMA できる。`err_in_fifo` で bit15 にエラーフラグ、`byte_shift` で 8bit に縮めて出せる
- sigrok raspberrypi-pico ドライバの上限の目安: 1ch 500k、2ch 250k、3ch 160k(警告を出すだけで強制はしない)
- 精度(ENOB ≈ 8.7bit、RP2040 エラッタ E11 の DNL スパイク)は記憶によるもので **[未確認]**(この調査では一次資料を再確認していない)

### 6.2 PIO によるロジックキャプチャの実践
- pico-examples `pio/logic_analyser/logic_analyser.c` **[確認]**:
  - プログラムは `in pins, N` の 1 命令を wrap するだけ。autopush、RX FIFO join(8 段)
  - 「1〜32 ピン、レートは sysclk 以下」。clkdiv でレートを決める(`sysclk/div`、16.8 小数分周。小数だとジッタ)
  - 32 が N で割り切れないときは早めに push するので、FIFO の各ワードは左詰めで、下位に 0 が入る
  - **ピンは IN_BASE から連続する N 本**(PIO の in ピンマッピングは連続。32 で wrap)
  - DMA は PIO RX DREQ で `capture_buf` へ書き込み、読み出しアドレスは固定。バス優先度を DMA 側に上げている
  - **トリガ**: `pio_sm_exec(pio, sm, pio_encode_wait_gpio(level, pin))` で `wait` 命令を強制実行し、条件が成立するまで SM を停止させる → 以後キャプチャ開始。プレトリガは取れない(トリガ前のデータは捨てる)
- 連続(ギャップなし)DMA **[確認: pico-sdk `rp2350/hardware_regs/include/hardware/regs/dma.h`]**:
  - `CTRL.RING_SIZE`: アドレスの下位 n bit だけが変わる。2〜32768 バイトのリング、RING_SEL で読み側/書き側を選ぶ
  - `CHAIN_TO`: 完了時に別チャネルを起動。2 ch のピンポンでギャップなしにする定石(RP2040 も同じ)
  - **RP2350 のみ** `TRANS_COUNT.MODE`: 0x1 TRIGGER_SELF(カウント 0 で自分を再起動 = 割り込み付きの無限リング)、0xF ENDLESS(減算しない。ABORT まで続く)。TRANS_COUNT は 28bit
  - RP2350 の DMA は 16ch、IRQ 4 本、PIO 3 基。RP2040 は DMA 12ch、PIO 2 基(`platform_defs.h`)
- RP2350 PIO の追加点 **[確認: `regs/pio.h`]**: `GPIOBASE`(0 か 16)で GPIO16–47 を PIO から見える 0–31 に移せる(RP2350B の上位ピン用)。`wait` の JMPPIN ソースなど命令拡張もある **[後者は未確認]**
- 実例: gusmanb/logicanalyzer(https://github.com/gusmanb/logicanalyzer)の README の主張:
  - 24ch、RP2040 で 100 Msps。RP2350 は "blast mode" で 400 Msps
  - トリガは PIO プログラムで実装: edge(キャプチャと同期)、fast pattern(≤5ch、フルレート)、complex pattern(先頭 16ch の連続ビットで ≤16bit)
  - バッファは 8ch で 131071、16ch で 65535、24ch で 32767 サンプル。burst モード(自動再アーム)
  - README の主張をそのまま載せたもの **[未確認: 実測]**
- RP2350 エラッタ E9(GPIO 入力とプルダウンの問題)はピンスキャンやロジック入力に影響しうる。手元メモ由来の既知事項で、本調査では再確認していない **[未確認]**

---

## 付録: OEP 設計への示唆(推論)
- stock PulseView でライブ表示するには、次の 3 経路がある:
  - (a) **hameg-hmo なりすまし**: 0.5.2 と git の両方で動くが、フレーム単位のポーリング、レートは読むだけ、連続フレームにはユーザー設定が要る
  - (b) **raspberrypi-pico なりすまし**: git ビルドの serial_tcpraw が必須。アナログ + ロジックのストリーミングとレート設定ができる
  - (c) **beaglelogic なりすまし**: 0.5.2 から TCP が使える。ロジック専用ストリームで、レートは SET 可。プロトコルが最も単純(テキストコマンド + 生バイト、応答 `ok`)
- アナログ + ロジック + 安定版互換を全部満たすのは (a) だけ。ストリーミングの体験が要るなら (b)(ただし git ビルド)
- どれを使うか、基本の機能をそれに合わせるかは、提案の §2.8 のとおり「どう見せるか」の段で決める
