# Open Embedded Probe — コンソールのストリーム

状態: 方針と考え方の文書。**番号と書式は [v1 wire](v1-core-wire-delta.ja.md) §5.7（console）と §5.8（uart）で決めた**（2026-09-25）。

制御の口が 1 本しかない probe（CH340 の classic ESP32、P4 の USB-Serial/JTAG）で、target のコンソールや fixture の
UART を OEP の中で運ぶ形を決める。コンソール専用の口を持つ probe は、その口を OEP の外に置いて Monitor に占有させる
（[セッションと排他](session-and-exclusivity.ja.md)）。

## 方針

- **host からは同じインターフェース、経路は probe の設定で選ぶ。** ストリームは debug の connection（dmseq など）か
  UART のピンの割り当ての上に開き、読み出しはストリームの番号で行う。出し先は OEP の中のストリームか、コンソール専用の
  CDC（OEP の外）。`oep.fixture.uart` の受信も同じ形にそろえる（[能力の名前の階層](capability-name-hierarchy.ja.md)）。
- **host が読みに行く（ポーリング）。** 要求と応答だけで済み、今のフレームのままで動く。応答に「まだ残っている」
  フラグを付け、残っていれば host はすぐ次を読む。probe から勝手に送る通知は将来の拡張にする。
- **probe はセッションと関係なく吸い出してためる。** dmseq は probe が DM を読み続けないと target が送信で詰まる。
  Monitor が書き込みのために一度閉じても、その間の出力は probe に残る。
- **ストリームごとに別の fn。** target のコンソール（dmseq）、fixture の UART（複数あってよい）は、それぞれ別の
  インターフェースとして list に出る。

## 位置付きのストリーム

- probe はストリームの各 byte に、起動からの通し番号（u64、一周しない）を振る（2026-09-26。以前は u32 で一周した）。
- **読み出しはバッファを消費しない。** 押し出されたときだけ消える。
- 応答が失われても、同じ位置でもう一度読めば同じデータが返る（読むと消える方式では、失われた応答の分が消える）。
- 要求した位置がすでに押し出されていれば、応答の先頭の位置との差が失われた量になる。

### 捨てるタイミング（これだけ）

1. **あふれ。** 古いものから押し出す。target を待たせる方式は持たない（UART の素通しでは待たせられず、方針が
   2 つになると複雑になる）。
2. **host の明示的な消去。**
3. **probe の再起動。** 位置も 0 から数え直す（boot_id が変わる）。

target のリセットでは捨てない。リセット直前のログ（クラッシュやウォッチドッグの原因）が最も見たいものであることが
多いため。代わりにマークを付け、host がどこから読むかを選ぶ。

## マーク

```text
mark : position(u64), kind(u8), time_ms(u32, probe の起動からの時刻), detail(u8)
```

| kind | 名前 | 付ける契機 | detail |
|---|---|---|---|
| 0x01 | reset | probe の指示で target をリセットした | 方法（ndmreset / NRST / fixture 経由の電源の入れ直し） |
| 0x02 | restart | target の再起動を検出した | 検出元（DM の havereset / コンソールの再同期） |
| 0x03 | attach | attach した | — |
| 0x04 | detach | detach した | — |
| 0x05 | lost | あふれで押し出した、または受信エラー | 理由 |
| 0x06 | clear | host が消去した | — |
| 0x07 | host | host が付けた印（テストの開始など） | host が決める値 |
| 0x08 | link-lost | 線が落ちた（RVSWD の切断など） | — |

- 番号空間は describe の TLV と同じ分け方: 0x01〜0x3F が標準、0x40〜0x7F がインターフェース固有。
- マークは本文とは別の小さなリングにためる。上限を超えたら古いものから捨てる。
- **byte ごとの時刻は持たない。** 時刻はマークにだけ付ける。表示用の時刻は host が受け取った時刻で足りる。
- attach 中の RISC-V target なら、DM の havereset でリセットボタンによる再起動も見える。UART の素通しでは、
  target 側から起きたリセットは分からない。

## 操作

```text
read(from, max)   from = 位置 | 最古 | 今 | 最後のマーク（kind を指定できる）
                  → start_pos, flags(more, gap), data
marks(from_pos)   → from_pos 以降のマーク
clear()
mark(value)       → host の印を付ける
write(data)       → 受け付けた byte 数（target への入力。バッファしない）
```

**read と marks はロックなしで使える。** 読んでもバッファは消えず、probe は読み手ごとの状態を持たないので、
他の host のロック中に読んでも混ざらない。clear、mark、write、設定は状態を変えるので session_id を要する
（[セッションと排他](session-and-exclusivity.ja.md)）。

| 読み始め | 使う場面 |
|---|---|
| 最後のマークから | Arduino の書き込み → Monitor。今回の起動の分だけを表示する |
| 今から | 過去のログは要らない |
| 最古から | 何が起きたか全部見る |
| 位置 X から | Monitor が一度閉じて戻ったとき、続きから読む |

入力方向はバッファせず、受け付けた分だけを返す。dmseq では host からの payload が 1 回に 2 byte までなので、
残りは host が送り直す。

## describe で宣言するもの

| 宣言 | 値 | 目的 |
|---|---|---|
| buffer_bytes | u32 | 何秒ぶんのログが残るかの見積もり |
| mark_capacity | u8 | マークを何個まで覚えるか |
| detects | ビット | 付けられるマークの kind（restart を検出できるか、など） |
| max_read | u16 | 1 回の read で返せる最大長 |

## Monitor と書き込みの交代

口が 1 本の probe では、Monitor 自身が OEP の host になる。書き込みの間は Monitor が一度閉じる（Arduino IDE の
pluggable monitor と同じ）。戻った Monitor は、session_id が変わったことで誰かが操作したと分かり、
「最後の reset マークから」読めば書き込み後の起動の分だけを表示できる。

## 未決（実験で決める）

1. マークの kind の番号と detail の中身。
2. （2026-09-26 決定）位置は u64（一周しない）。max_read は u16 のまま。
3. （決定: read と marks はロックなし。上記）
4. 通知（probe から送る）を入れる時期。
