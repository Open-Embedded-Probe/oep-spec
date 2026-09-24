# flash の書き込みを host の知識で行う実験（F1〜F5）

状態: **非規定の実験**（2026-09-24）。[target の発見と接続](../../docs/target-connection-use-cases.ja.md) の
「flash の書き込み（実験してから決める）」の入力。どの部品を標準にするかは決めていない。

## 問い

v0 は CH32 の flash コントローラの扱いを probe の中に持っていた（`target.flash`）。これは「target の知識は host が
持つ」と食い違う。汎用の部品だけで、host が CH32 を書き込めるか。**WCH-LinkE（ch32rv 0.10.0）と比べて**どれくらいの
速さか。

基準は LinkE とする。v0 の組み込みは移植しないので基準にはせず、参考値として残す。

## 方式

| 段 | 方式 | probe の変更 |
|---|---|---|
| F1 | 参考: v0 の組み込み `target.flash`（probe が autoexec で page buffer に流す） | なし |
| F2a | host が v0 の `target.memory` read / write だけで、1 アクセス 1 要求で手順を組む | なし |
| F2b | F2a の 1 ページ分の要求をパイプラインで送る（状態の読み出しはあとで確かめる） | なし |
| F3 | 手順のリスト（write32 / read32 / poll、1 要求に数十手順）を probe が順に実行する | 実験用サービス |
| F4 | host が持つ RAM ローダーを target の RAM に置き、「バッファへのブロック書き込み」と「実行して停止を待つ」を繰り返す | 実験用サービス |

実験用サービスは oep-probe-arduino の `ExpTargetPrimitives`（owner 0x0100、id 0x00F0。payload は bytes のまま、
v0 registry の外）と、`Ch32Dm::writeWordsFast`（autoexec のブロック書き込み）/ `Ch32Dm::runUntilHalt`（PC と
レジスタを設定して走らせ、ebreak で止まるのを待つ）。P4 の X035 用 probe と classic ESP32 の V003 用 probe に載せた。

| ローダー | 中身 |
|---|---|
| `x035_loader.S`（196 byte） | この実験で書いた。a0 = ページ、a1 = RAM のバッファ。1 ページを消去して page buffer に流して書く |
| V003 用（500 byte） | v0 の probe が持っていた wlink 由来のもの（MIT / Apache-2.0）を host に移した。a0 = 0x1d（解除・消去・書き込み・確認）、a1 = アドレス、a2 = byte 数（**64 の倍数なら複数ページを 1 回で書ける**）、sp = 0x20000800 |

## 結果: CH32X035（62 KB = 248 ページ、乱数イメージ）

LinkE: CH32X035C8T6 + WCH-LinkE（USB）。OEP: CH32X035F8U6 + ESP32-P4 の RVSWD（USB-Serial/JTAG）。同じ系統・同じ容量。

| 方式 | 消去 + 書き込み | 読み戻しの確認 | 全体の実時間 |
|---|---|---|---|
| **LinkE + ch32rv**（チップ一括消去） | 約 0.15 + 1.97 秒 | 約 1.1 秒 | **3.28 秒**（確認なし 2.19 秒） |
| **OEP F4**（ページごとに消去） | **1.67〜2.19 秒** | **0.18〜0.39 秒** | **2.97 秒**（Python の起動込み） |
| OEP F3 手順のリスト | 15.2 秒 | 0.40 秒 | — |
| OEP F2b v0 の memory だけ | 22.7 秒 | 0.41 秒 | — |
| OEP F2a 1 要求ずつ | 約 45 秒（外挿） | — | — |
| 参考: v0 の組み込み（F1） | 3.34 秒 | 0.47 秒 | — |

- F4 は 8 ページずつまとめて 1.67 秒、4 ページずつで 2.12 / 2.19 秒。ローダーの実行（1 ページの消去 + 書き込み）は
  4.75 ms で一定。
- F4 で実際のスケッチ（DmSeqTest）を書き、v0 のリセット（PC のサンプルで実行を確認）で flags 0x03、PC 0x210。
- F3 は要求をまとめても 1 ページ 61 ms のまま。上限は probe の DM アクセス（1 語ごとに「書く・BUFLOAD・状態を読む」の
  汎用アクセス 3 回、それぞれ DMI 8〜11 回）で、往復ではない。

## 結果: CH32V003（16 KB = 256 ページ、乱数イメージ）

LinkE: CH32V003F4P6 + WCH-LinkE（USB）。OEP: UIAPduino（CH32V003）+ classic ESP32 の SWIO、**transport は
115200 bps の UART**（USB-UART の変換チップ経由、フレーム 512 byte、同時 1 要求）。

| 方式 | 消去 + 書き込み | 読み戻しの確認 | 全体の実時間 |
|---|---|---|---|
| **LinkE + ch32rv**（チップ一括消去） | 約 0.1 + 1.50 秒（2 回とも） | 約 0.33 秒 | **2.03〜2.05 秒** |
| OEP F4（ページ消去 + 書き込み + 確認、1 回 1024 byte = 16 ページ） | 3.60 秒 | 1.78 秒 | 8.1〜8.2 秒（Python の起動込み） |
| **OEP F4（一括消去 1 回 + 書き込みだけ、LinkE と同じ形）** | **2.88 秒**（一括消去 15 ms） | 1.87 秒 | — |
| OEP F4（同上、ホストとの UART を 921600 bps にした試験） | 1.60 秒 | 64 byte ずつで 1.37 秒（それ以上の長さは落ちた） | — |
| OEP F4（1 回 1 ページ、先頭 8 ページで測定） | 31 ms / ページ | — | — |

- ローダーのフラグ（ローダーのコードを逆アセンブルして読んだ）: bit0 解除、bit1 一括消去、bit2 a2 byte 分の
  ページ消去、bit3 書き込み、bit4 確認。0x1d は「解除 + ページ消去 + 書き込み + 確認」。LinkE と同じ形は、0x03 を 1 回
  （一括消去）のあと 0x09（解除 + 書き込み）。書き込みだけのローダーの実行は 16 ページで 46 ms（1 ページ 2.9 ms）、
  全面で 0.74 秒。
- 921600 bps の試験は、ビルドで速度を変えた一時的なもの（取り消した）。書き込みは LinkE と同じ 1.6 秒になったが、
  probe → host の 256 byte 以上の応答で byte が落ち、v0 の probe が 1.5 秒の無通信で target をリセットして手放した
  （今日の合意で「やめる」と決めた動き）。**速度はビルドで決めず、115200 bps で開いてから取り決める**方針にした
  （[probe 開発ガイド](../../docs/probe-development-guide.ja.md) §3.5）。
- 0x1d（ページ消去 + 書き込み + 確認）のときのローダーの実行は 1 ページ 6.2 ms（16 ページで 98.5 ms）、全面で 1.58 秒で、
  これだけで LinkE の書き込み全体と同じだった。
- 残りは UART の転送。115200 bps の上限は約 11.5 KB/s で、16 KB は片道だけで 1.4 秒以上かかる。読み戻しも同じ。
- F4 で実際のスケッチ（DmSeqTest）を書き、リセットで flags 0x03、PC 0x1d4。
- **一度、読み戻しが化けたのにエラーにならなかった**（1024 byte ずつの 1 回目。全ページ ebreak で終わり、読み直すと
  全ページ一致）。v0 のフレームには CRC がなく、USB-UART の変換チップは長い連続送信でバイトを落とすことが分かって
  いる（2026-09-22）。書き込みの方式ではなく経路の問題で、UART の binding に CRC が要る根拠になる。

## F5: v1 の仮置きだけで書く（CH32X035、2026-09-24）

P4 の X035 用 probe を v1 の仮置き（[core wire model v1](../../docs/v1-core-wire-delta.ja.md)）に置き換え、
`oep.core`（セッション）、`oep.wire.rvswd`（scan / attach）、`oep.target.riscv-dm`（ブロック読み書き、実行して
停止を待つ、ndmreset）だけで、F4 と同じ host のローダーで書いた（`f5_v1.py`）。要求は 1 つずつ（パイプラインなし）。

| | 準備（open、scan、attach） | 消去 + 書き込み | 読み戻しの確認 | スクリプト内の合計 |
|---|---|---|---|---|
| OEP v1（F5）62 KB、要求を 1 つずつ | 0.04 秒 | 2.51 秒 | 0.54 秒 | 3.09 秒 |
| OEP v1（F5）、4 ページずつパイプライン | 0.04 秒 | 1.80 秒 | 0.20 秒 | 2.01 秒 |
| **OEP v1（F5）、8 ページずつパイプライン** | 0.04 秒 | **1.68 秒** | **0.19 秒** | **1.89 秒** |
| 参考: LinkE + ch32rv | — | 約 2.1 秒 | 約 1.1 秒 | 3.28 秒 |

- 読み戻しは全面一致、失敗 0。実際のスケッチ（DmSeqTest）を書いてリセットし、flags 0x3、PC 0x214 で走った。
- scan は固定の 1 組（SWDIO 2 / SWCLK 54）で DMSTATUS 0xc82 を返した。
- `dump --port` で、実機が list 1 回と describe 3 回で `oep.core`（個体の番号 30eda0e31108 = board-identify の名前と
  一致）、`oep.wire.rvswd`、`oep.target.riscv-dm` を宣言した。
- セッションの規則を実機で確かめた（`v1_session_check.py`、同じポートで 2 つの session_id）: 他の host のロック中は
  locked と残り時間、ロック中でも list は通る、session_id なしの状態を変える要求は session required、期限切れの
  あと同じ ID で再開、知らない ID は no session、間に他の host が open したあとは保存した ID が no session。
- パイプラインは host 側だけの変更（`--batch N`、probe が confirm で宣言した同時要求数 8 とウィンドウ 4096 byte を守る）。
  8 ページずつで F4 の最速と並び、LinkE の 6 割弱の時間になった。

## v1 のコンソールのストリーム（CH32X035 + DmSeqTest、2026-09-24）

`oep.target.console` を P4 の probe に足し（v0 の TargetConsole を DM 側の駆動として使い、その上に位置付きのリングと
マークを載せた）、DmSeqTest を相手に確かめた（`v1_console_check.py`）。

- 止めずに attach して dmseq のストリームを開くと、`dmseq READY` を受け取れた（Monitor だけを使う場合の形）。
- `riscv-dm` のリセット（実行の確認つき、flags 0x03）のあと、同じ位置に reset と restart（dmseq の再同期で検出）の
  マークが付き、「最後の reset マークから」読むとリセット後の出力だけが返った。
- セッションを end したあとも吸い出しは続き、セッションなしの別の host がロックなしで読めた。
- probe を再起動しない限りストリームは残る（位置 0 から読むと前の回の出力も全部読めた）。
- エコー（`E hello v1` → `R hello v1`）は 3 回中 2 回返った。返らなかった 1 回は DmSeqTest を書き直した直後の最初の
  書き込み。target の最初の同期の前後に書くと、dmseq の再同期で host の送りかけの分が捨てられる（規則どおり）
  可能性があるが、未確認。

## v1 の fixture（P4、2026-09-24）

v0 の fixture のサービスを v1 の名前（`oep.fixture.gpio` / `uart` ×2 / `capture`）で出し（操作の payload は v0 のまま、
describe は v1 の `role_channels` で作り直し）、core に plan_apply / plan_release（v0 と同じ形）を足した。target を
使わず probe の中で閉じた確かめ方をした（`v1_fixture_check.py`、治具で未使用の GPIO20〜22）。

- uart の TX（GPIO20）と、同じピンを観測する capture の line 0 を 1 つの plan で割り当て、送った 5 byte を 2 MHz の
  サンプル列から host 側で復号して一致した。
- gpio の GPIO22 をプルアップ → プルダウン → プルアップに切り替え、セッションなしの別の host がロックなしの read_bank で
  1, 0, 1 と読めた。

## V003 の probe の v1 化（classic ESP32 + SWIO、UART 115200、フレーム 512 byte、2026-09-24）

V003 の probe も v1 の仮置きに置き換えた（`oep.wire.swio`、`oep.target.riscv-dm`、`oep.target.console`、
`oep.fixture.gpio` / `uart` / `capture`。GPIO23 は NRST のラベル付きの gpio のチャンネル）。

| V003 16 KB | 消去 + 書き込み | 読み戻しの確認 |
|---|---|---|
| **OEP v1**（一括消去 + 書き込みだけ、`f5_v003_v1.py`） | **2.82 秒** | 1.80 秒 |
| 参考: F4（実験用サービス、同じ形） | 2.88 秒 | 1.87 秒 |
| 参考: LinkE + ch32rv | 約 1.6 秒 | 約 0.33 秒 |

- 全面一致。実際のスケッチ（DmSeqTest）を書いてリセットし、flags 0x3 で走った。
- コンソール: 止めずに attach しての受信、エコー、reset / restart のマーク、reset マークからの読み出し、セッション
  終了後のロックなしの読み出しが、すべて P4 と同じに動いた（`v1_console_check.py PORT oep.wire.swio`）。
- fixture: uart の TX（GPIO21 = V003 の PD6、入力のまま）を capture で観測して 5 byte が復号で一致、GPIO25
  （V003 の PA1）のプルアップ / プルダウンをロックなしで 1, 0, 1 と読めた（`v1_fixture_check.py PORT 21 22 25`）。
- 1 回の読み出しの最大は probe のフレームに合わせて宣言する（V003 の probe は 480）。
- UIAPduino のブートローダへの切り替え（v0 ではリセットのモード 1 / 2 として probe の中にあった）を host 側に移した。
  gpio の NRST のパルス → attach → RAM のペイロード → DMI の手順で resume、で HID 1209:b803 が現れ、戻しのペイロード
  で消えて DmSeqTest がまた動いた（`v1_uiapduino_check.py`）。
- 独自の I2C / SPI target（`io.github.ch32-riscv-ug.esp32.*`）は、両方の probe で割り当て・設定・ロックなしの状態の
  読み出しまで確かめた。実際の転送の試験には、マスタ役の target のスケッチが要る。
- UART の経路を COBS + CRC-16 のフレームにしたあとも、同じ確かめ方がすべて通った。16 KB の書き込みは 2.96 秒
  （長さの前置きのときは 2.82 秒）、壊れたフレームの検出 0 回、送り直し 0 回。

## 分かったこと

1. **host の知識と汎用の部品 2 つ（ブロック書き込み、実行して停止を待つ）で、X035 は LinkE と同等の速さで書ける**
   （消去 + 書き込みはほぼ同じ、読み戻しの確認は OEP の方が速い）。1 語ごとの繰り返しを target の CPU に回させるのが
   効く。probe-rs / CMSIS の flash algorithm や WCH の方式と同じ結論。
2. **V003 も同じ部品で正しく書ける。** 115200 bps の UART では LinkE の約 2 倍遅い（一括消去 + 書き込み 2.88 秒 対
   1.6 秒）が、ローダーの時間は 0.74 秒で、差は転送。経路を速くした試験では 1.60 秒で LinkE と並んだ。部品の形の問題
   ではない。
3. **「手順のリスト」だけでは遅い。** page buffer のように 1 語ごとに状態を待つ手順は、DM 経由の汎用アクセスでは
   DMI の回数が多すぎる。
4. `runUntilHalt` では dcsr の ebreakm と **prv = M** を立て、host が mstatus = 0 を渡す。ArduinoCore-CH32 の
   スケッチは V3B/V4 で U モードで動くので、止めた hart が U モードのままだと割り込みを止められない。
5. ローダーの呼び方（レジスタの割り当て、止まる位置）は host が知っていればよく、probe は何も知らない。V003 は
   v0 の probe の中にあったローダーのバイト列を host に移しただけで同じ形になった。

## 未確認

- V003 を USB の probe で書いたときの速さ（今は V003 に USB の probe がつながっていない）。
- UART の速度の取り決めを実装したうえでの、V003 の読み戻しの速さ。
- L103 など他の系統、ばら配線の Pico（DMI が化けやすい）での F4 の頑健さ。
- 低スペック（64 byte フレーム）での F4 のバッファ転送の往復数。

## 実行

```sh
cd <oep-client-python>
uv run python <この dir>/f1_builtin.py PORT IMAGE                      # 組み込み、リセットなし
uv run python <この dir>/f2_host_driven.py PORT a|b PAGES IMAGE
uv run python <この dir>/f3_steps.py PORT PAGES IMAGE [PAGES_PER_BATCH]
uv run python <この dir>/f4_loader.py PORT PAGES IMAGE x035_loader.bin [PAGES_PER_BATCH]
uv run python <この dir>/f4_v003.py PORT IMAGE v003_loader.bin [BYTES_PER_RUN] [FLAGS|mass]
uv run python <この dir>/read_chunks.py PORT IMAGE CHUNK             # 読み出しの長さごとの経路の確認
uv run python <この dir>/f5_v1.py PORT IMAGE x035_loader.bin [--reset] [--batch N]  # v1 の仮置きだけで書く
uv run python <この dir>/v1_session_check.py PORT                     # v1 のセッションの規則を実機で
uv run python <この dir>/v1_console_check.py PORT                     # v1 のコンソール（target は DmSeqTest）
uv run python <この dir>/v1_fixture_check.py PORT [TX RX PULL]        # v1 の fixture（target を使わない）
uv run python <この dir>/f5_v003_v1.py PORT IMAGE v003_loader.bin [BYTES_PER_RUN] [--reset]   # V003 を v1 で
uv run python <この dir>/v1_i2cspi_check.py PORT SDA/SCK SCL/MOSI MISO CS   # 独自の I2C / SPI target の割り当てと状態
uv run python <この dir>/v1_uiapduino_check.py PORT                   # UIAPduino のブートローダへ入って戻る（host 側の手順）
# LinkE の基準（工程ごとの時刻を付ける）
uv run python <この dir>/phase_ts.py ch32rv --probe serial:<SN> --progress ndjson --non-interactive --yes \
    flash --reset none IMAGE
```

X035 のローダーのビルド（ESP32 コアの RISC-V binutils を流用）:

```sh
B=~/.arduino15/packages/esp32/tools/esp-rv32/2601/bin
$B/riscv32-esp-elf-as -march=rv32imac_zicsr -mabi=ilp32 -o x035_loader.o x035_loader.S
$B/riscv32-esp-elf-ld -Ttext=0x20000000 -o x035_loader.elf x035_loader.o
$B/riscv32-esp-elf-objcopy -O binary x035_loader.elf x035_loader.bin
```

`f4_loader.py` の `DONE_OK` / `DONE_FAIL` は、このビルドでの ebreak の位置（0x200000b0 / 0x200000c0）。
V003 のローダーのバイト列は、oep-probe-arduino `src/OepCh32Dm.cpp` の `kV003FlashLoader` を little endian で
並べたもの（ebreak は +0x15c）。乱数イメージは `random.Random(n).randbytes(size)`（X035: n = 1, 2、V003: n = 3, 4）。
乱数のコードは走らないので、リセットせずに測る。
