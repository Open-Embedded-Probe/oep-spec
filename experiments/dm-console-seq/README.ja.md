# DM console: 番号とCRC付きフレーミングの比較実験

状態: **非規定の実験実装**。`target.console` の新しいフレーミング(番号付き、番号+CRC)を決めるための
実験であり、wire formatを仕様として割り当てるものではない。仮のフレーム形式と規則は
[SPEC-draft.md](SPEC-draft.md)、実測結果も同じファイルの末尾にある。

## なぜ

今の `target.console` framing 1(ArduinoCore-CH32 の `SerialDMDATA`、minichlink互換)には通し番号がない。
probe の答えの DMI 書込みが黙って落ちると target の word がもう一度読まれて**重複**し(RP2350 の probe 越しの CH32L103、
2026-09-23)、それを読み戻しで救おうとすると同じ文字が続く箇所を**取り違えて落とす**(CH32V003、同日)。
番号があればどちらも区別できる。CRCは化けた word を捨てるためのもの。

## 中身

| path | 内容 |
|---|---|
| `SPEC-draft.md` | 仮のフレーム形式、規則、実測結果 |
| `DmSeqTest/` | target 側。`DmSeq.h` が試作クラス、`.ino` がテスト(RUN で既知の文字列、`E <text>` で echo)。`-DDMSEQ_BASELINE` で同じテストを `SerialDMDATA` で回す |
| `dmseq_host.py` | host 側。OEP probe で書込み、`target.console` を指定 framing で開き、1 byte 単位で照合 |
| `tools/run_matrix.sh` | 3 target × 変種をビルドして並行実行。変種 1 = framing 1、2 = 番号のみ、3 = 番号+CRC(bit計算)、4 = 番号+CRC(表引き) |
| `tools/flash_probes.sh` | 3 台の OEP probe を書き直す。引数 = 故障注入率(‰、0 = なし) |
| `tools/picoflash.sh` | WSL から RP2350 を BOOTSEL 経由で書き直す |

probe 側の実装は oep-probe-arduino の `TargetConsole::pollSeq()`(framing 2/3、**未コミットの実験コード**)。
故障注入は `-DOEP_CONSOLE_FAULT_PERMILLE=<n>` で、答えの書込みを落とす・答えを化かす・読んだフレームを化かす。

## 実行

```sh
tools/flash_probes.sh 0                       # 故障注入なし
FRAMINGS="1 2 3" tools/run_matrix.sh clean    # 結果は $DMSEQ_WORK(既定 /tmp/dmseq-work)にも残る
tools/flash_probes.sh 20                      # 2 % ずつ故障注入
FRAMINGS="2 3" tools/run_matrix.sh fault20
```

治具は ArduinoCore-CH32 の `tests/manual/oep_smoke/targets.py` の x035 / v003 / l103。
