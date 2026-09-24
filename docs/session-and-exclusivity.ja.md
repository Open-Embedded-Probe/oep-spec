# Open Embedded Probe — セッションと排他

状態: **仮置き**（2026-09-24 の議論の合意）。実験してから調整する。wire format（フィールドの幅、置き場所、番号）は
決めない。以前の文書と食い違う点は、この文書を優先する（食い違いは末尾の表）。

## 前提

- **probe は transport を開閉してもリセットしない。host はリセットせずに開く。** 開き方の詳細（DTR / RTS の順序など）は
  [host 開発ガイド](host-development-guide.ja.md) に書き、protocol には「リセットしない・させない」までを置く。
- **probe の状態は transport を閉じても残る。** attach、ピンの割り当て、線の状態（RVSWD のアイドル時のクロックの
  レベルなど）は、host のセッションや transport の寿命と結び付けない。one-shot CLI（1 コマンドごとに開閉する）は
  これを前提にする。
- **開くとどうしてもリセットされる probe** は、それを probe 全体の describe で宣言する。host はそれを読んだら閉じずに
  1 つのセッションで使い続ける。one-shot CLI はその probe では使えない。

### 前提の根拠（実測、2026-09-24）

| probe | 開閉でのリセット |
|---|---|
| ESP32（USB-Serial/JTAG の P4 ×2、CH340 の classic ESP32 と P4、CH343 の S3） | DTR を立てたまま開けばリセットしない。閉じてもリセットしない |
| RP2350（arduino-pico、Pico SDK の USB スタック） | DTR / RTS のどの組み合わせでもリセットしない。DTR=0 の間は出力が止まる |

probe がリセットすると RVSWD の同期が落ち、立て直すと debug module がリセットされ（止めていた hart が走り出す）、
起こしの系列で target のアプリケーションも再起動する。状態を保つことは one-shot CLI の都合だけではない。

## 制御の口は 1 つ、使えるのは 1 つの host

- probe が持つ OEP の制御の口は 1 つとする。コンソール専用の口（下記）は数えない。
- 同時に OEP を使えるのは 1 つの host（1 プロセス）だけとする。
- **排他は session_id で行う。** OS やライブラリの排他（Windows の COM ポート、libusb の claim、pyserial の
  `exclusive=True`）は効けば 2 つ目の open を早く失敗させられるが、Linux の tty のように開けてしまう経路が残る。
  protocol はそれに頼らない。
- 同時に複数の制御の口を開けて、probe が送り主ごとに返し、キューで順に処理する形は v1 では扱わない。
  送り主を区別できない形（HID を複数プロセスで共有するなど）が出てくるのを防ぐためでもある。

### コンソール専用の口

LinkE の USB シリアルと同じく、コンソール専用の CDC を持つ probe がある。これは OEP の制御の外に置き、Monitor が
占有する。中身は固定ピンの UART の素通しでも、OEP で割り当てたピンや target のコンソール（dmseq）を流したものでも
よい。口が 1 本しかない probe は、コンソールを OEP の中のストリームとして運ぶ（[コンソールのストリーム](console-stream.ja.md)）。

## session_id によるロック

```text
open(session_id, 希望するリース時間, force)  → 結果, 実際のリース時間, boot_id
状態を変える要求はすべて session_id を伴う
end(session_id)                             → ロックを下ろす
keepalive(session_id)                       → 何もしない（期限を伸ばすだけ）
```

- **session_id は host が乱数で選ぶ**（u32 を想定）。probe に乱数も不揮発のカウンタも要求しない。
- **ロックは watchdog 型。** session_id を伴う要求が来るたびに期限を伸ばす。期限は要求の**完了**から数える
  （長い verify の最中に自分のセッションを捨てた失敗があった）。リース時間は host が希望し、probe が上限で切る。
- **期限切れと end ではロックだけを下ろし、最後の session_id は覚えておく。**
- **probe の状態はセッションと結び付けない。** end や期限切れで attach やピンは戻さない。

### 要求を受けたときの判定

| ロック | 要求の session_id | 結果 |
|---|---|---|
| 空き | 最後の session_id と同じ | そのままロックを立て直して処理する（再開） |
| 空き | 違う（open 以外） | 「セッションなし」。host は open からやり直す |
| 空き | open（任意の ID） | ロックを立てる。最後の session_id を更新する |
| 自分が保持 | 同じ | 処理する |
| 他が保持 | 違う | BUSY と残り時間。今の session_id は返さない |
| 他が保持 | open(force) | 奪う。最後の session_id を更新する |

- **session_id が変わっていないことは、間に他の host が操作していないことを意味する。** one-shot CLI は
  session_id を保存しておき（probe の個体ごと）、次のコマンドで同じ ID を使う。通れば「前のコマンドのあと誰も触って
  いない」、通らなければ「間に誰かが入った」と分かる。
- **force は誰でも使える。** 乗っ取りを防ぐことは目的にしない。防ぐのは取り違え（古いプロセスが自分のセッションが
  続いていると思い込むこと）だけで、それには乱数の ID が偶然一致しなければよい。
- この保証が成り立つために、**状態を変える操作はすべて session_id を要する。** ロックなしで使えるのは読むだけの
  操作（confirm、list、describe、ロックの状態）に限る。
- session_id が変わらなくても、target 自身の変化（リセット、電源断）は起こりうる。それは接続の喪失やコンソールの
  マークで伝える。

### boot_id

open の応答に boot_id を入れる。probe の起動ごとに変わる値で、host は前回の値と比べて「probe が再起動した
（attach や割り当ては消えた）」ことを知る。

- 再起動すると最後の session_id も消えるので、古い ID は「セッションなし」になる。boot_id はその理由の区別に使う。
- 値の作り方は probe に任せる（ハードウェアの乱数、不揮発の起動回数など）。作れない probe は 0（不明）を返し、
  host は「セッションなし」を常に再起動の可能性ありとして扱う。

## 長くかかる操作

以前の [request の受理と完了](request-completion-semantics.ja.md) の 3 つの結果（rejected / completed / accepted）を
そのまま使う。accepted（以下 PENDING）は activity を作る。

```text
要求            → PENDING（すぐ終われば普通の結果）
status()        → PENDING と進捗 (done, total) ／ 完了と結果
cancel()        → 止められる操作なら止める
```

- **どの操作も PENDING を返しうる。** 同じ操作でも速い probe はすぐ結果を返す。host のライブラリは両方を同じように扱う。
- 進捗は (done, total)。単位は操作が決める。total が分からない操作（止まるまで走らせる）は 0。
- **実行中の長い操作は probe 全体で 1 つ。** 実行中にぶつかる要求が来たら、即時に BUSY を返す。ぶつからない要求
  （status、cancel、confirm / list / describe、コンソールの読み出し）は受け付ける。
- status の問い合わせはロックの期限を伸ばす。
- 止めてはいけない操作（消去の途中など）は cancel を断ってよい。
- **host がいなくなっても、長い操作は最後まで進める。** 最後の結果は、同じ session_id で戻ったときに取り出せる。
  **新しい session_id でロックが立ったら、最後の結果は消す。**
- 裏で処理を進められない低スペックの probe は、PENDING を使わず終わるまで応答しない（ブロックする）形でよい。
  どちらの動きをするかは describe で宣言する。

長くかかりうる操作の例: 止まるまで走らせる（gdb の continue、無期限）、flash の一括消去、広い範囲の CRC、全組み合わせの
スキャン（Pico で 400 組が 0.5 秒前後、P4 の 40 本なら数秒。眠っている target を拾うなら 10〜20 秒）、attach の起こしの
再試行、fixture による電源の入れ直し、fixture の「待つ」操作。

## 重複

- フレーム（binding）にシーケンスがあれば、binding が再送の重複を判定する。
- シーケンスが無ければ（v0 の USB CDC の長さ付きフレームなど）、host が要求を再送したときの二重実行を許す。
- epoch をまたいだ exactly-once は保証しない（[UART connection epoch](uart-connection-epoch.ja.md) と同じ）。

## probe の実装への要求

- 開閉でリセットしない。DTR / RTS の変化でリセットする回路を持つボードは、その扱いを host 開発ガイドに書く。
- **DTR に頼らない。** arduino-pico の USB シリアルは DTR が下りていると出力しない。`Serial.ignoreFlowControl()` など
  で、host の開き方が違っても通信が止まらないようにする。
- セッションを失っても状態を戻さない。以前の「host を見失ったら target をリセットする」「切断で pin を入力に戻す」は
  やめる。

## 以前の文書との食い違い（この文書を優先）

| 以前の文書 | 以前の方向 | この文書 |
|---|---|---|
| [activity reference の lifecycle](activity-reference-lifecycle.ja.md) | activity の参照は接続の中だけで有効。再接続後は無効 | セッションの中で有効。同じ session_id で戻れば最後の結果を取り出せる |
| [開発ガイドライン](development-guidelines.ja.md) §3.2 | disable / host 切断 / watchdog で pin を input に戻す | 明示的な disable / release でだけ戻す。切断とロックの期限切れでは戻さない |
| [target の発見と接続](target-connection-use-cases.ja.md)（旧版） | host を見失ったら probe が安全な状態に戻す | 戻さない |

以前の方向の方がシンプル・合理的だと分かったものは、別途見直す。session_id を host が選ぶのは、以前の
「probe に乱数の生成を要求しない」方針（UART connection epoch）に合わせたものである。

## 未決（実験で決める）

1. session_id を載せる場所（フレームのヘッダか、各要求の payload か）と長さ。64 byte フレームの probe での負担。
2. リース時間の範囲と既定値。
3. コンソールの読み出しをロックなしで許すか（読んでも消えないので、他の host の邪魔にならない）。
4. boot_id が本当に要るか。session_id の再開の判定だけで足りる場面が多い。
5. 開くとリセットされる probe の宣言の形。
