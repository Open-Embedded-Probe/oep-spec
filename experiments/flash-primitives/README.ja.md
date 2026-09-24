# flash の書き込みを host の知識で行う実験（F1〜F4）

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
| **OEP F4**（1 回 1024 byte = 16 ページ） | **3.60 秒** | **1.78 秒** | **8.1〜8.2 秒**（Python の起動込み） |
| OEP F4（1 回 1 ページ、先頭 8 ページで測定） | 31 ms / ページ | — | — |

- ローダーの実行は 1 ページ 6.2 ms（16 ページで 98.5 ms）。全面で 1.58 秒で、これだけで LinkE の書き込み全体と同じ。
  消去 + 書き込み + 確認を 1 ページずつ行うローダーのため。
- 残りは UART の転送。115200 bps の上限は約 11.5 KB/s で、16 KB は片道だけで 1.4 秒以上かかる。読み戻しも同じ。
- F4 で実際のスケッチ（DmSeqTest）を書き、リセットで flags 0x03、PC 0x1d4。
- **一度、読み戻しが化けたのにエラーにならなかった**（1024 byte ずつの 1 回目。全ページ ebreak で終わり、読み直すと
  全ページ一致）。v0 のフレームには CRC がなく、USB-UART の変換チップは長い連続送信でバイトを落とすことが分かって
  いる（2026-09-22）。書き込みの方式ではなく経路の問題で、UART の binding に CRC が要る根拠になる。

## 分かったこと

1. **host の知識と汎用の部品 2 つ（ブロック書き込み、実行して停止を待つ）で、X035 は LinkE と同等の速さで書ける**
   （消去 + 書き込みはほぼ同じ、読み戻しの確認は OEP の方が速い）。1 語ごとの繰り返しを target の CPU に回させるのが
   効く。probe-rs / CMSIS の flash algorithm や WCH の方式と同じ結論。
2. **V003 は同じ部品で正しく書けるが、LinkE の 4 倍遅い。** 主な原因は 115200 bps の UART と、1 ページずつ消去する
   ローダー。部品の形の問題ではない。
3. **「手順のリスト」だけでは遅い。** page buffer のように 1 語ごとに状態を待つ手順は、DM 経由の汎用アクセスでは
   DMI の回数が多すぎる。
4. `runUntilHalt` では dcsr の ebreakm と **prv = M** を立て、host が mstatus = 0 を渡す。ArduinoCore-CH32 の
   スケッチは V3B/V4 で U モードで動くので、止めた hart が U モードのままだと割り込みを止められない。
5. ローダーの呼び方（レジスタの割り当て、止まる位置）は host が知っていればよく、probe は何も知らない。V003 は
   v0 の probe の中にあったローダーのバイト列を host に移しただけで同じ形になった。

## 未確認

- V003 で、チップの一括消去 + 書き込みだけのローダーにしたときの速さ（LinkE と同じ条件）。
- V003 を速い transport（USB の probe）で書いたときの速さ。
- L103 など他の系統、ばら配線の Pico（DMI が化けやすい）での F4 の頑健さ。
- 低スペック（64 byte フレーム）での F4 のバッファ転送の往復数。

## 実行

```sh
cd <oep-client-python>
uv run python <この dir>/f1_builtin.py PORT IMAGE                      # 組み込み、リセットなし
uv run python <この dir>/f2_host_driven.py PORT a|b PAGES IMAGE
uv run python <この dir>/f3_steps.py PORT PAGES IMAGE [PAGES_PER_BATCH]
uv run python <この dir>/f4_loader.py PORT PAGES IMAGE x035_loader.bin [PAGES_PER_BATCH]
uv run python <この dir>/f4_v003.py PORT IMAGE v003_loader.bin [BYTES_PER_RUN]
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
