# Open Embedded Probe — シリアルの口（CDC）と設定の永続化

状態: **検討中**（2026-09-25〜）。論点と選択肢を並べ、実験で決めてから [v1 wire](v1-core-wire-delta.ja.md) に足す。
発端は [memo](../memo.ja.md) の 15 / 16（ユーザーの発案と ch32rv セッションの意見）。

## 0. 何のためか

- **LinkE の置き換えの導線**: Arduino IDE で書き込み → Serial Monitor で見る、を OEP の probe でもそのまま行う。
  Serial Monitor は OS のシリアルポート（CDC）しか開けないので、target の出力を CDC に流す口が要る。
- **自由な配線**: LinkE はピンが固定なので設定が要らない。OEP の probe はどのピンにもつなげるので、探して見つけた
  ピンと、口に何を流すかを覚えておかないと、probe の電源を入れ直すたびに設定し直すことになる。

## 1. 前提（ユーザーの前提と、これまでの決定）

- CDC の口は複数あってよく、物理 UART のほか、target のコンソール（SDI、DMDATA、DMSEQ、RTT）など、いろいろなものを
  つなげられる。
- 永続化しにくい probe（V003 など: EEPROM / NVS が無く、flash は 16 KiB）もある。
- OEP の制御の口は 1 つ（[セッションと排他](session-and-exclusivity.ja.md)）。CDC の口は OEP の制御の外で、Monitor が
  占有する。
- コンソールと fixture.uart の受信は、読んでも消えない（位置付きのストリーム）。読み手が増えても互いに取り合わない。
- 同じ connection で DM の mailbox（DATA0 / DATA1）を使う方式は 1 つだけ（DMDATA、DMSEQ、SDI は同時に成り立たない）。
- 接続（attach）だけで止まる target がある（wch-protocols E164: HPRE の bit 3 を立てて走る X035 は、WCH-LinkE の attach
  だけで止まった）。

## 2. 論点

### 2.1 いつ attach するか（いちばん大きい）

| 案 | 内容 | 良い点 | 悪い点 |
|---|---|---|---|
| A. しない | probe は自分から attach しない。host（ch32rv、IDE の書き込み）が attach したときだけ | target を勝手に触らない。E164 のような事故が無い | 書き込みの後に IDE を閉じて Monitor だけ開くと、コンソール（SDI / DMSEQ）は流れない |
| B. 起動時 | 電源を入れたら前回の線に attach する | 何もしなくても流れる | 配線を変えた後や、別の target をつないだときに、知らない target を触る |
| C. CDC を開いたとき | Monitor が口を開いた（DTR が立った、または最初の読み）ときに attach | 見たいときだけ触る | 開いた瞬間に attach するので、最初の出力を取り逃がすことがある（§3 の実験）。DTR を target の reset に使う慣習とぶつかる |
| D. 条件付きで自動 | 前回の線に target があることを、線を駆動せずに確かめられたときだけ attach | B / C の便利さを保ちつつ、知らない target を触りにくい | 「線を駆動せずに確かめる」が本当にできるか（§3 の実験） |

attach の中身も分ける: **止めない attach（method 0）** は、動いている hart に触れずに DM を使える状態にするだけ
（v1 wire §5.5）。UART の素通しには attach は要らない。

### 2.2 前回のピンにアダプタがあるかを確かめるか

- 確かめ方の候補（線を駆動しない順）:
  1. 弱いプル（probe の内蔵プルアップ / プルダウン）だけを掛けて、線の電位を読む。CH32 の SWDIO は target 側で引き上げ、
     SWCLK は引き下げられている（L103 で観測）。target の電源が落ちていれば、どちらも probe のプルに従う。
  2. 読むだけの DMI（DMSTATUS）。線の上には clock を出すので「駆動しない」ではないが、target の状態は変えない。
  3. chip ID（ESIG）を読み、保存した target と同じかを比べる。
- 確かめた結果を describe や出来事で host に知らせるか。

### 2.3 CDC の口

- 口の数は USB の列挙のときに決まる。describe に口の数と口ごとの USB interface 番号を出す。bind は口に流すものを変える。
- 流すもの: なし / fixture.uart / target.console（connection + mechanism）/ 固定ピンの素通し。
- line coding（baud）を fixture.uart に写すか（bind の flag）。DTR / RTS / 1200 baud touch は、既定では何もしない。
- connection がないときの口: 閉じずに保留（connection ができれば流れる）。
- SDI のように probe が DM を読み続ける方式と、host の DMI の操作との取り合い。

### 2.4 永続化

- 何を保存するか: plan、ラベル、CDC の bind、前回の target（線、chip ID）。小さい probe は plan の識別子だけ。
- いつ書くか: host の明示的な保存だけ。同じ内容なら書かない。書く間はほかの要求を待たせる。
- 起動時に何をするか: plan の再適用と CDC の bind まで。attach するかは §2.1。
- 保存の形: 版と hash を付けた 1 つの塊。読めなければ適用せず、describe で知らせる。

## 3. 実験（決める前に測ること）

| 番号 | 問い | 方法 | 決めること |
|---|---|---|---|
| X1 | P4 で vendor bulk と CDC を複数持つ複合デバイスが作れるか。interface の番号が固定か、OS からどう見えるか | EspUsbDevice で vendor + CDC 3 口を作り、usbipd / WSL の by-id、Windows の COM を見る。line coding と DTR の通知 | 口の数、名前の付け方、interface の並び |
| X2 | 線を駆動せずに、前回のピンに target がいるか分かるか | 内蔵プルアップ / プルダウンを掛けて読む。target のいる線（LinkE の分岐の線、治具の線）と、何もつながっていないピンで比べる | §2.2 の 1 が使えるか |
| X3 | 止めない attach は、動いているアプリを乱さないか。何 ms かかるか | UART に時刻付きで出し続けるスケッチを動かし、attach / detach を繰り返して、UART の出力の途切れと時間を測る | §2.1 の B / C / D を許せるか |
| X4 | SDI / DMSEQ の target は、probe がいない間と attach の直後にどう振る舞うか | probe を attach しない状態で出力させ、途中から attach する。取り逃がす量、アプリの遅れ | 「CDC を開いたとき attach」で最初の出力を取り逃がすか |
| X5 | 小さい probe（V003）に何が保存できるか | flash の page、option byte の Data0 / Data1 | plan の識別子だけにするか |

### 3.1 結果 X1: P4 の vendor bulk + CDC の複合デバイス（2026-09-25、`30eda0e343c6`、EspUsbDevice 2.5.1）

- vendor（OEP、interface 0）+ CDC 3 口（interface 1 / 3 / 5、名前 "OEP port 0/1/2"）で列挙できた。P4 HS の制御以外の
  IN endpoint は 7 本で、vendor 1 + CDC 2 本ずつ（通知 + データ）なので、OEP と一緒なら CDC は 3 口まで。
- Linux の `/dev/serial/by-id/` はシリアル番号と interface 番号で名前が付く（`…-30eda0e343c6-hs-if01` など）。並びが同じなら
  名前も変わらない。usbipd の共有も、シリアル番号が同じならそのまま効いた（構成が変わっても bind し直し不要）。
- 口ごとに baud と DTR / RTS を持ち、開いたまま baud を変えると通知が来る。**Linux の cdc-acm は開くときに DTR / RTS を
  必ず一度立てる**（pyserial で DTR を下げて開いても、dtr=1 → dtr=0 と 2 回通知が来た）。閉じると 3 口とも dtr=0 rts=0。
  → DTR を reset などに使うと、開くたびに一瞬反応してしまう。DTR は「開かれている」の目安にしかならない。
- **CDC を持つと OEP の速さが落ちる**: bulk IN が 3 本以上になると vendor の送信 FIFO を 2 packet にできない
  （EspUsbDevice の自動判定）。

| CDC の口 | link_source（16 KiB × 16） | 2 本 150 MHz のストリーミング | 160 MHz |
|---:|---|---|---|
| 0 | 35.3 MB/s | 欠けなし | 欠けなし |
| 1 | 33.6 MB/s | 欠けなし | 欠けなし |
| 2 | 25.6 MB/s | 欠け（29.9 MB/s） | 欠け |
| 3 | 26.0 MB/s | 欠け（29.9 MB/s） | —（未測） |

### 3.2 結果 X2: 線を駆動せずに target の有無が分かるか（2026-09-25）

内蔵プルアップ / プルダウンを掛けて 16 回読み、何もつながっていないピンと比べた（`scratchpad/PinProbe`）。

| 治具 | 線 | プルアップ | プルダウン |
|---|---|---|---|
| X035（P4 `30eda0e31108`） | SWDIO（PC18）、SWCLK（PC19）、DUT の PA0 / PA5、何もつながっていない 20〜23 | すべて high | すべて low |
| V003（classic ESP32） | SWIO（PD1）、DUT の PA1 / PC0、何もつながっていない 2 / 15 | すべて high | すべて low |
| V003 | NRST | high | **high**（基板のプルアップが勝つ） |

- **CH32 の debug の線は probe の内蔵プルに勝たないので、プルだけでは target の有無は分からない**（何もつながっていない
  ピンと同じに見える）。NRST は基板のプルアップが強ければ分かるが、基板しだい。RP2350 は E9 の errata でプルの読みが
  当てにならない（pico-bench の記録）。
- したがって「前回のピンに target がいるか」を確かめるには、線を駆動する操作（DMSTATUS を読むなど）が要る。
  target のアプリがその線を GPIO として使っている場合は、駆動すると出力とぶつかる。

## 4. 決めたこと

（実験の後に書く）
