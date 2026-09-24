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

## NRST を使った attach under reset（SWIO を止めたファームからの復旧、2026-09-24）

SWIO（PD1）を setup の先頭で GPIO にするスケッチ（下）を OEP で書き、普通の attach が届かなくなったところから、
`oep.wire.swio` の attach_under_reset（リセット線は probe の既定値 = GPIO23 → V003 の NRST）で戻した。
classic ESP32 の V003 jig、probe は oep-probe-arduino 25be7ce。

```cpp
void setup() {
  *(volatile uint32_t *)0x40021018 |= 1u;                      // RCC_APB2PCENR.AFIOEN
  volatile uint32_t *pcfr1 = (volatile uint32_t *)0x40010004;  // AFIO_PCFR1.SWCFG = 0b100: SDI off
  *pcfr1 = (*pcfr1 & ~(7u << 24)) | (4u << 24);
  Serial.begin(115200);
}
void loop() { Serial.println("swio off"); delay(200); }
```

| hold_ms | 普通の attach（書いた後） | attach_under_reset | 止まった dpc | core_api の書き戻し | 普通の attach（戻した後） |
|---|---|---|---|---|---|
| 20 / 1 / 5 / 50 / 200 / 500（各 1 巡） | 6 巡とも失敗 | 6 巡とも 1 回目で成功 | 0x0 | 検証まで通る | DMSTATUS 0x400c82 |

- hold_ms によらず 1 回目で止まった。probe は NRST を保持したまま attach して haltreq を立て、それを保持したまま
  NRST を放すので、hart は最初の命令の前で止まる。「リセット直後の窓に SWIO を差し込む」競争になっていない。
- V003 の DM は NRST を保持している間も SWIO で答える。答えない target では窓の競争になるので、host は hold_ms や
  解放後の待ちを変えながら再試行する（利用者の指摘）。V003 では必要なかったため、その再試行はまだ実装していない。
- SWIO を止めるスケッチを書いた直後の riscv-dm reset（run）は `failed` を返す。走り出したスケッチが SWIO を止め、
  確認の読み出しが届かないため。
- 実行: `uv run swio_recover.py <上のスケッチを swio_off/swio_off.ino に置いたディレクトリ> [--hold=N] [--recover-only]`
  （ArduinoCore-CH32 の tests/manual/oep_smoke を import する。破壊的: SWIO を止めたファームを書く）。
