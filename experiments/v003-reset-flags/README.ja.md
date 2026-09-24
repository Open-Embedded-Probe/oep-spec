# CH32V003 で PINRSTF を立てるもの（UIAPduino のブートローダに入る条件）

状態: **非規定の実験**（2026-09-24）。UIAPduino のブートローダは起動直後に `RCC_RSTSCKR.PINRSTF` を見て、立って
いなければアプリに戻る（wch-protocols E161）。NRST の配線なしに入る道があるかを、v1 の仮置きの probe
（classic ESP32 の V003 治具、`oep.wire.swio`、`oep.target.riscv-dm`）と RAM のペイロードで調べた。

## 結果

| 試したこと | リセットのあとの RCC_RSTSCKR |
|---|---|
| RM の表（device-data） | PINRSTF は読み出し専用、電源投入後 0（PORRSTF は 1）。ソフトウェアからは消すこと（RMVF）しかできない |
| NRST のパルス（probe の GPIO23 → PD7）+ ソフトウェアリセット | SFTRSTF, PINRSTF |
| IWDG のリセット（`iwdg_reset.S`、約 3 ms） | IWDGRSTF だけ |
| WWDG のリセット（`wwdg_reset.S`、T6 = 0 で即） | WWDGRSTF だけ |
| target 自身が PD7 を GPIO 出力 low に（`pd7_low.S`） | リセットが起きない。CFGLR / OUTDR は書いたとおりだが INDR も probe 側も high のまま = リセットの機能が有効な間、GPIO の出力はパッドにつながらない |

- **PINRSTF を立てるのは、外から NRST ピンを引いたときだけ**（電源投入は RM の値から 0 と推定、未測定）。
- 印は RMVF で消すまでリセットをまたいで残る。ソフトウェアリセット（戻しのペイロード）では消えない。
- PD7 を GPIO にするにはオプションバイト（RST_MODE）でリセットの機能を切るしかなく、そうするとピンリセット自体が
  無くなる。UIAPduino のブートローダにも関わるので試していない。

## host 側の手順への反映

oep-client-python `v1/uiapduino.py` の `enter_bootloader` は、先に PINRSTF を読む（`uiap_paths.py` で確かめた）:

| 状態 | 動き | 結果 |
|---|---|---|
| PINRSTF なし、NRST の線なし | 入らず、「ボードのリセットか電源の入れ直し（スケッチが印を消さないこと）」を求める | 断った |
| PINRSTF なし、NRST の線あり | NRST をパルスしてから入る | HID 1209:b803 が出た |
| PINRSTF が残っている、NRST の線なし | **SWIO だけで入る** | HID 1209:b803 が出た |

NRST を配線しない治具でも、前のピンリセットの印が残っていれば入れる。印を消すのは ArduinoCore-CH32 の
`CH32.resetReason()`（初回に RMVF を書く）で、UIAPduino でこれをやめるかは、コアの `docs/todo.ja.md` で利用者の判断
待ちのまま。

## 実行

```sh
B=~/.arduino15/packages/WCH/tools/riscv-none-embed-gcc/8.2.0/bin
for f in iwdg_reset wwdg_reset pd7_low; do
  $B/riscv-none-embed-as -march=rv32ec -mabi=ilp32e -o $f.o $f.S
  $B/riscv-none-embed-ld -m elf32lriscv -Ttext=0x20000000 -o $f.elf $f.o
  $B/riscv-none-embed-objcopy -O binary $f.elf $f.bin
done
cd <oep-client-python>
uv run python <この dir>/reset_flags.py PORT <bin の dir> iwdg wwdg pd7-low
uv run python <この dir>/pd7_level.py PORT <bin の dir>/pd7_low.bin   # PD7 のレベルを probe から見る
uv run python <この dir>/uiap_paths.py PORT                            # ブートローダに入る 3 つの経路
```
