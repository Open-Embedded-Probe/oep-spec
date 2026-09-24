# flash の書き込みを host の知識で行う実験（F1〜F4）

状態: **非規定の実験**（2026-09-24）。[target の発見と接続](../../docs/target-connection-use-cases.ja.md) の
「flash の書き込み（実験してから決める）」の入力。どの部品を標準にするかは決めていない。

## 問い

v0 は CH32 の flash コントローラの扱いを probe の中に持っていた（`target.flash`）。これは「target の知識は host が
持つ」と食い違う。汎用の部品だけで、host が CH32X035 を書き込めるか。どれくらいの速さか。

## 方式

| 段 | 方式 | probe の変更 |
|---|---|---|
| F1 | 基準: v0 の組み込み `target.flash`（probe が autoexec で page buffer に流す） | なし |
| F2a | host が v0 の `target.memory` read / write だけで、1 アクセス 1 要求で手順を組む | なし |
| F2b | F2a の 1 ページ分の要求をパイプラインで送る（状態の読み出しはあとで確かめる） | なし |
| F3 | 手順のリスト（write32 / read32 / poll、1 要求に数十手順）を probe が順に実行する | 実験用サービス |
| F4 | host が持つ RAM ローダー（`x035_loader.S`、196 byte）を target の RAM に置き、ページごとに「バッファへのブロック書き込み」と「実行して停止を待つ」 | 実験用サービス |

実験用サービスは oep-probe-arduino の `ExpTargetPrimitives`（owner 0x0100、id 0x00F0。payload は bytes のまま、
v0 registry の外）と、`Ch32Dm::writeWordsFast`（autoexec のブロック書き込み）/ `Ch32Dm::runUntilHalt`（PC と
レジスタを設定して走らせ、ebreak で止まるのを待つ）。

## 結果（CH32X035F8U6、ESP32-P4 の RVSWD、USB-Serial/JTAG、62 KB = 248 ページの乱数イメージ）

| 段 | 1 ページ | 全面 | 要求の数 | 読み戻し |
|---|---|---|---|---|
| F1 組み込み | 13.5 ms | 3.34 秒（2 回とも） | 248 | 一致 |
| F2a 1 要求ずつ | 180 ms | 約 45 秒（4 ページから外挿） | 約 214 / ページ | 一致（4 ページ） |
| F2b パイプライン | 91 ms | 22.7 秒 | 52,698 | 一致 |
| F3 手順のリスト | 61 ms | 15.2 秒 | 744（3 / ページ） | 一致 |
| **F4 RAM ローダー** | **8.6〜8.8 ms** | **2.12 / 2.19 秒** | 496（2 / ページ） | 一致（2 回とも） |

- F4 のローダーの実行時間（消去 + 書き込み、target の CPU が回す）は 1 ページ 4.75 ms で一定。残りはバッファの転送と
  レジスタの設定。
- F4 で実際のスケッチ（DmSeqTest、11 ページ）を書き、v0 のリセット（PC のサンプルで実行を確認）で flags 0x03、
  PC 0x210 = 走っている。
- F3 は要求をまとめても 1 ページ 61 ms のまま。上限は probe の DM アクセス（1 語ごとに「書く・BUFLOAD・状態を読む」の
  汎用アクセス 3 回、それぞれ DMI 8〜11 回）で、往復ではない。
- F2 / F3 / F4 とも、全面の読み戻しで不一致は 0。

## 分かったこと

1. **host の知識と汎用の部品だけで、組み込みより速く書ける**（F4 は F1 の 1.6 倍）。1 語ごとの繰り返しを target の
   CPU に回させるのが効く。probe-rs / CMSIS の flash algorithm や WCH の方式と同じ結論。
2. **「手順のリスト」だけでは遅い**（F3 は F1 の 4.5 倍遅い）。page buffer のように 1 語ごとに状態を待つ手順は、
   DM 経由の汎用アクセスでは DMI の回数が多すぎる。
3. F4 に要った部品は **ブロック書き込み（autoexec）** と **実行して停止を待つ** の 2 つ。ロックの解除は v0 の
   memory.write で済んだ（手順のリストでも書ける）。
4. `runUntilHalt` では dcsr の ebreakm と **prv = M** を立て、host が mstatus = 0 を渡す。ArduinoCore-CH32 の
   スケッチは V3B/V4 で U モードで動くので、止めた hart が U モードのままだと割り込みを止められない。

## 未確認

- CH32V003（QingKe V2、RAM 2 KB、64 byte ページ）で同じ汎用部品を使うこと。v0 は V003 だけ probe の中の RAM
  ローダー（wlink 由来）で書いており、そのバイナリを host に移せば F4 と同じ形になるはず。
- L103 など他の系統、ばら配線の Pico（DMI が化けやすい）での F4 の頑健さ。
- 低スペック（64 byte フレーム）での F4 のバッファ転送の往復数。

## 実行

```sh
cd <oep-client-python>
uv run python <この dir>/f1_builtin.py PORT IMAGE                      # 組み込み、リセットなし
uv run python <この dir>/f2_host_driven.py PORT a|b PAGES IMAGE
uv run python <この dir>/f3_steps.py PORT PAGES IMAGE [PAGES_PER_BATCH]
uv run python <この dir>/f4_loader.py PORT PAGES IMAGE x035_loader.bin [PAGES_PER_BATCH]
```

ローダーのビルド（ESP32 コアの RISC-V binutils を流用）:

```sh
B=~/.arduino15/packages/esp32/tools/esp-rv32/2601/bin
$B/riscv32-esp-elf-as -march=rv32imac_zicsr -mabi=ilp32 -o x035_loader.o x035_loader.S
$B/riscv32-esp-elf-ld -Ttext=0x20000000 -o x035_loader.elf x035_loader.o
$B/riscv32-esp-elf-objcopy -O binary x035_loader.elf x035_loader.bin
```

`f4_loader.py` の `DONE_OK` / `DONE_FAIL` は、このビルドでの ebreak の位置（0x200000b0 / 0x200000c0）。
乱数イメージは `random.Random(1 or 2).randbytes(63488)`。乱数のコードは走らないので、F1 はリセットせずに測る。
