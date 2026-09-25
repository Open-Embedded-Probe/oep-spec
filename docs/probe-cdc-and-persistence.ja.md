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

### 2.5 起動モード（プロファイル）（2026-09-25、ユーザーのメモ）

- probe に「起動モード」を持たせる案。例: ロジアナ特化、LinkE のような RVSWD 用 / SWD 用のデバッガ。ピンが固定の製品でも
  構成を切り替えられるものがある（Sipeed SLogic Combo 8: ロジアナ / DAPLink / USB シリアルを切り替える）。
- X1 の結果と噛み合う: CDC を 2 口以上持つと vendor の送信 FIFO が 2 packet にならず、2 本 150 MHz のストリーミングが
  出ない。**ロジアナのモードは vendor だけ（CDC なし）で帯域を優先し、デバッガのモードは vendor + CDC** にできる。
- USB の構成（interface の数と並び）は列挙のときに決まるので、モードを変えるには USB の付け直し（probe の再起動）が要る。
  モードは永続化の対象（§2.4）で、起動時にそのモードで列挙する。
- 決めること: モードの一覧を宣言する形（describe）、切り替える操作（保存して再起動）、モードごとに list に出る
  インターフェースと CDC の口の数、モードが違うときの host の振る舞い（今のモードでは使えないと分かる）、USB の
  product 名やシリアル番号にモードを出すか（OS から見分けるため。ただし usbipd の bind はシリアル番号ごと）。

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

### 3.3 結果 X3: 止めない attach は動いているアプリを乱すか、何 ms かかるか（2026-09-25、X035 治具）

DUT（CH32X035）は PA0 を 50 µs ごとに反転し（micros() で刻む）、probe のキャプチャが PA0 を 2 MHz で取り続ける間に、
host が止めない attach（method 0）と detach を 200 ms ごとに 10 回繰り返した（`scratchpad/x3/x3.py`）。

| 条件 | 半周期の中央値 | 100 サンプルから外れた半周期 |
|---|---|---|
| attach なし（基準、3.5 s） | 99 サンプル（49.5 µs） | 0 |
| attach / detach を 10 回 | 99 サンプル | 長いものが 1〜4 回。**すべてキャプチャの区画の途切れ（host が attach で読み出しを止めた間に格納先があふれた所）と同じ位置** |

- **止めない attach は、0.5 µs の分解能では DUT のアプリを乱さなかった**（外れはキャプチャ側の欠け）。
- **attach には約 168 ms かかる**（10 回とも 167.6〜169.3 ms。この probe は速さを選ぶまで遅い速さで書き、読むだけで速い
  速さを探す。v1 wire §5.4 の規範）。CDC を開いたときに attach する案では、開いてから約 170 ms は debug 経由の出力
  （SDI / DMSEQ）が流れない。
- attach の途中で、以前このセッションの中で残った接続を取り戻すと、probe の中の「止まっている」の状態が古いまま
  だった不具合が見つかった（直した: 既存の接続では halt で状態を合わせる）。

### 3.4 結果 X4: probe がいない間と、attach しても読まない間の SDI / DMSEQ（2026-09-25、X035 治具）

DUT は 1 行ごとに PA0 を反転し、SerialSDI 版と SerialDMSeq 版で、反転の間隔（= 1 行にかかる時間）を測った
（`scratchpad/x3/x4.py`）。

| DUT | (a) attach なし | (b) attach だけ（コンソールを開かない） | (c) コンソールを開いて probe が読む |
|---|---|---|---|
| SerialSDI | 1 行 40 µs（出力は捨てられる） | **1 行に最大 300 ms 待つ** | 1 行 102 µs、行の抜けなし |
| SerialDMSeq | 38 µs（捨てられる） | 38 µs（待たない） | 165 µs、行の抜けなし |

- **SDI は、DM が有効（attach 済み）なのに誰も DATA0 を読まないと、1 行ごとに最大 300 ms 止まる**。自動で attach する
  なら、同時にコンソールも読み始めなければならない。attach したまま読むのをやめてもいけない（CDC を閉じたときも読み続ける）。
- どちらも、probe がいない間の出力は target 側で捨てられる。attach より前の出力は取れない（X3 の約 170 ms も含めて）。
- UART の素通しは attach が要らず、probe が受信を始めた時点から全部取れる。

### 3.5 X5: 小さい probe に何を保存できるか（机上）

- CH32V003 を probe にする場合（rv003usb など）: flash 16 KiB、EEPROM / NVS なし。書けるのは flash の page（64 B、消去は
  page 単位）か option byte の Data0 / Data1（各 8 bit）。書く間は bit-bang の USB も止まる。
- classic ESP32 / ESP32-P4 / RP2350: NVS（ESP32）や flash の末尾（RP2350）に数 KiB は置ける。
- したがって「plan の中身ごと」と「plan の識別子だけ」の 2 段を認めるのが現実的（ch32rv の意見どおり）。

## 4. 案（2026-09-25。§5 のユーザーの方針で見直す）

X1〜X5 から導いた案。

### 4.1 attach は、既定では probe が自分からしない

- 理由: (1) 線を駆動せずに target の有無を確かめる方法が無い（X2）。確かめるだけでも線を駆動する。(2) attach だけで
  止まる target がある（E164）。(3) attach して読まないと SDI のアプリが止まる（X4）。(4) 配線を変えた後に、前回の
  ピンで知らない target や GPIO として使われている線を駆動しうる。
- 利用者が選べる**自動の attach**（bind ごとの設定、永続化する）:

| 設定 | 動き | 向く使い方 |
|---|---|---|
| 0 しない（既定） | host（書き込みツール、ch32rv）が attach したら、その connection でコンソールを開いて口に流す。CDC は開いていても、それまで流れない | 書き込み → Monitor の導線（書き込みツールが attach するので流れる）。安全 |
| 1 CDC を開いたとき | 口の DTR が最初に立ったら、止めない attach（method 0）をしてコンソールを開き、以後は読み続ける | 書き込みツールを使わずに Monitor だけ開く。最初の約 170 ms は取れない |
| 2 起動時 | probe の起動時に同じことをする | 据え付けの監視。配線が変わらない前提 |

- 自動の attach（1 / 2）では、attach の直後に chip ID（ESIG）を読み、保存した target と違えば、コンソールを開かずに
  detach し、出来事と describe で知らせる。
- 自動でも**止めない attach だけ**（hart を止めない、reset しない、NRST を駆動しない）。
- 一度開いたコンソールは、CDC を閉じても読み続ける（SDI を止めないため。取った分はストリームに残る）。止めるのは
  unbind、detach、connection を失ったとき。

### 4.2 UART の口は attach が要らない

- 保存した bind が fixture.uart なら、起動時から RX（入力）で受信を始めて貯める。**TX は口が開かれるまで入力のまま**
  （プルアップ）にし、開かれたら UART の休止（high）で出力にする（配線を変えた後に出力でぶつからないため）。

### 4.3 CDC の口と起動モード

- 口の数と並びは起動モードで決まる（§2.5）。ロジアナのモードは vendor だけ（CDC なし）で帯域を優先、デバッガのモードは
  vendor + CDC 1〜3 口。2 口以上では OEP のストリーミングの上限が下がる（X1）ことを describe に出す。
- DTR / RTS / 1200 baud touch は何もしない（Linux は開くたびに DTR を立てるので、reset などには使えない。X1）。
  DTR は「開かれた」の合図（自動の attach の設定 1）にだけ使う。

### 4.4 永続化

- 書くのは host の明示的な保存だけ。保存するのは起動モード、plan、ラベル、bind（自動の attach の設定を含む）、前回の
  target の chip ID。版と hash を付けた 1 つの塊。小さい probe は plan の識別子だけでもよい。
- 起動時は、起動モードで列挙し、plan を適用し、UART の受信を始める。attach は自動の attach の設定が 2 のときだけ。

### 4.5 ch32rv セッションのレビューを受けた修正（2026-09-25）

- **自動の attach の合図（設定 1）と TX を出力にする合図**: Linux の ModemManager は新しい ttyACM を開いて AT コマンドを
  送る。DTR だけを合図にすると、利用者以外が開いただけで attach が走り、target の RX に "AT\r" が入る。CDC は
  bInterfaceProtocol 0（AT コマンドなし）で宣言し、udev の `ID_MM_DEVICE_IGNORE` を案内する。TX を出力にする合図は
  「line coding の設定か最初の書き込み」にする（DTR だけでは出力にしない）。
- **自動の attach の後の確かめ**: chip ID は WCH の DM レジスタ 0x7f（LinkE が AttachChip の中で使う。hart を止めずに読める。
  wch-protocols 6623b14）で読む（ESIG のメモリの読み出しは、系統によっては hart を止めないとできない）。X3 の attach が
  触ったのは DMSTATUS の読みだけ。比べるのは系統 / SKU まで（UID まで比べると、同じ種類の基板に差し替えただけで止まる。
  UID は任意）。
- **読み続けている間**: バッファが一杯になったら古い方から捨てて position を飛ばす（コンソールの今の規則のまま）。その間
  debug は attach したまま。CH32 は debug がつながっていると低消費電力の状態が変わりうる（推定、WCH の資料で未確認）ので、
  sleep の電流を測るときは注意、と文書と describe に書く。
- **host の DMI とコンソールの読みの取り合い**: 抽象コマンドは DATA0 / DATA1 を引数と戻り値に使うので、host が flash や
  read をしている間に probe がコンソールのために DATA0 を読み書きすると両方が壊れる（dmdata / SDI は失う・重複する。
  dmseq は通番で立て直せる）。**規範: ロックの持ち主が riscv-dm の操作（dmi / run / block）をその connection に出し始めたら、
  probe はその connection のコンソールの読みを止め、ロックが外れたら再開する**（コンソールの read / marks の操作だけの
  host、例えば monitor では止めない）。止めている間、SDI のアプリは遅くなる（X4）が、書き込みの間だけなので許す。
- **書き込み → Monitor の導線（設定 0）**: 1 コマンド 1 プロセスの host（ch32rv）は、書き込みの最後に reset して detach
  する。そこで connection が消えると、新しい firmware の最初の出力を取り逃す。**(a) 口に結んだコンソールが使っている
  connection は、host の detach では閉じない**（host の分の参照を外すだけ。閉じるのは unbind、または detach の force）。
  **(b) host が OEP の reset で target を reset したら、probe は havereset を確認応答して connection を保つ**（「target の
  reset で失われる」のは、線が本当に切れたときだけ）。これで「書き込みツールの reset の後の出力」から確実に取れる。
  v1 wire §5.5 の detach と reset の意味を、この形に直す必要がある（今は detach で connection が消える）。
- CDC の口の数で OEP のストリーミングの上限が下がることは、describe に数で出す（host が capture の設定を事前に断れる）。

## 5. ユーザーの方針（2026-09-25）

- **既定の値という考え方は持たない。設定の項目はすべて host が設定する**。probe は設定されたとおりに動き、設定されて
  いない項目については何もしない（「既定は attach しない」のような既定の振る舞いを仕様に書かない。§4.1 の表の「既定」は
  取り消し）。
- **USB の機能は vendor bulk のほか、HID や Mass Storage も候補にする**。vendor bulk は権限の問題で使えない環境がある
  （Linux は udev の規則、Windows は WinUSB の割り当て）。どの機能を開くかは probe の選択（起動モード）。
- **最初の約 170 ms を取れないのは仕方ない**。自動の attach でもよい。開発用の probe なので、probe の再起動で target が
  再起動することがあっても、最悪問題ない。
- **今は破壊的な変更を入れてよい**。仕様をシンプルに、拡張しやすい形で固める（v1 wire の connection の寿命、reset の
  扱いを含む）。

### 5.1 権限の整理（机上）

| 経路 | Linux | Windows | macOS | ブラウザ |
|---|---|---|---|---|
| vendor bulk | udev の規則が要る | WinUSB（MS OS 2.0 の記述子で自動） | そのまま | WebUSB |
| HID（vendor 定義） | hidraw は既定で root だけ。udev の規則（または uaccess）が要る | ドライバ不要 | そのまま | WebHID |
| CDC | dialout のグループ（多くの環境で済んでいる） | 自動（usbser） | そのまま | WebSerial |

→ OEP の制御の口を、vendor bulk / CDC / HID のどれでも運べるようにする（probe がどれを開くかを選ぶ）。Linux では CDC が
いちばん壁が低く、Windows では HID がドライバなしで使える。Mass Storage は OEP の制御ではなく、ドラッグ＆ドロップの
書き込み（DAPLink のような）や設定のファイルに使う候補（別の論点として残す）。

### 5.2 次の実験

| 番号 | 問い |
|---|---|
| X6 | OEP を CDC と HID で運んだときの速さ（link_source / link_sink）と遅れ。vendor bulk と比べる |

### 5.3 結果 X6: OEP を CDC と HID で運ぶ（2026-09-25、`30eda0e343c6`、1 つの USB デバイスに vendor / CDC / HID の 3 つの口）

HID は vendor 定義（report 511 byte）。scratch の束ね方: output report = 長さ(u16) + 長さの見出し付きのフレームのバイト列、
input report は先頭に report ID（6）が付く（EspUsbDevice の HID vendor の形）。

| 経路 | probe → host（16 KiB × 16） | host → probe | 往復（lock_state） |
|---|---|---|---|
| vendor bulk（direct build） | 37.4 MB/s | 5.5 MB/s | 0.37 ms |
| CDC | 8.2 MB/s | 0.23 MB/s | 0.60 ms |
| HID（511 byte） | 0.84 MB/s | 0.96 MB/s | 0.66 ms |

- どの経路でも制御（往復 1 ms 未満）には足りる。大きなデータ（キャプチャのストリーミング）は vendor bulk だけ。
- HID はホストが 1 report ずつ同期で読んだ値。EspUsbDevice の CR-8 では非同期の読みで 4.03 MB/s。CDC の host → probe は
  scratch の Stream の中継が 1 byte ずつ読むため（改善の余地）。
- WSL（Linux）では hidraw が root だけ（`crw------- root`）で、libusb でカーネルのドライバを外して使った（権限の表のとおり）。
- HID の probe の送信は、前の report が送り終わっていないと sendInput が失敗する。捨てると区切りが崩れる（待って送り直す）。
- 3 つの経路にそれぞれ Endpoint を置いたが、OEP の制御の口は probe に 1 つという前提（セッションと排他）と合わない。
  複数の経路を開くなら、1 つのセッションとロックを共有する（どの経路から来た要求も同じ Endpoint で扱う）形にする。

## 6. probe 自身の firmware の更新（OTA）（2026-09-25、ユーザーの問い）

P4 は HS ポートだけでつなぐのが主になるので、USB-Serial/JTAG の esptool に頼らない更新の経路が要る。

| 経路 | endpoint | host に要るもの | 備考 |
|---|---|---|---|
| USB DFU（runtime + DFU mode） | 0（EP0 だけ） | `dfu-util`（標準） | EspUsbDevice の FirmwareDFU。endpoint 予算を使い切った構成にも足せる |
| Mass Storage（.bin を放り込む） | bulk 1 組 | なし（ファイルマネージャ） | FirmwareMSC。いちばん敷居が低いが endpoint を使う（CDC / vendor の FIFO 予算とぶつかる） |
| vendor の独自コマンド | bulk 1 組 | 自作のツール | FirmwareVendor。最速 |
| CDC のスクリプト | CDC 1 口 | 自作 | FirmwareCDC |
| ROM の download loader | — | esptool | FirmwareBootMode。DFU runtime から入れる。壊れた firmware からの復旧用 |
| HTTP（CDC-NCM） | 数本 | ブラウザ | FirmwareHTTP |

案:
- **OTA は OEP の wire の外**（OEP は target を扱うプロトコルで、probe 自身の更新は USB の標準に任せる）。
- **どう更新するかは probe の選択**で、仕様には基本の経路を書かない（2026-09-25 のユーザーの方針）。**試作の probe は複数の
  経路を用意する**（DFU runtime、Mass Storage、vendor の独自コマンドなど）。参考: DFU runtime は endpoint を使わないので
  vendor + CDC 3 口の構成にも足せ、DFU runtime から ROM の download loader に入れば壊れた firmware からも esptool で戻せる。
  Mass Storage は endpoint を使うので、起動モードの 1 つに置くのが合う。
- OEP 側で知らせるのは、describe の firmware の版（core tag 0x40、既存）だけで足りる。更新の経路は USB の記述子で分かる。
- 要確認: DFU の Windows での扱い（MS OS 2.0 の記述子で WinUSB を割り当てられるか）、usbipd 越しの DFU detach と再列挙。

- **P4 のブートモード（ROM の download loader）**: 動いているスケッチから入れる（CDC の 1200 bps touch、DFU_DETACH、独自の
  コマンド。EspUsbDevice の `rebootToBootloader()`）。その loader が HS の口でも使えるかは**未確定**。
  - Espressif の FAQ（esp-faq, peripherals/usb「Is the High-Speed USB of ESP32-P4 available for programming?」）は
    「download mode に入れば High-Speed USB で書き込める」としている。EspUsbDevice の ota-over-usb 2.3 節の「P4 の loader は
    USB-Serial/JTAG でだけ応答する」はこれと食い違う。
  - P4 の ROM は DWC-OTG の CDC-ACM と DFU を持つ（esp32p4.rom.ld の `cdc_acm_*`、`usb_dfu_*`、`chip_usb_set_persist_flags`）。
    eFuse の DIS_USB_OTG_DOWNLOAD_MODE は 43c6 で 0。
  - Windows の PnP 履歴に `USB\VID_303A&PID_0012\80:F1:B2:D0:B2:61`（製品名 "ESP32-P4"、Composite、rev 0912）が残っている。
    80f1 で 2026-09-15 に 6 秒だけ列挙された。80f1 は CH340 の自動リセット（GPIO35 の strap）で download mode に入る
    ボードなので、strap で入ったときの ROM の OTG デバイスと見られる（入り方の記録は無い）。
  - 43c6（rev v1.3、ROM esp32p4-eco2-20240710）で、USJ 経由の esptool、スケッチからの force download、persist フラグ
    （bit 30 / bit 31 / 両方）を試したが、HS の口は Windows で列挙が完了しなかった（USB Tree View で
    `0x09 Device is enumerating` のまま。ハブ 3 段、USB 機器の接続過多で環境が不安定だった）。**環境が壊れかねないため
    実験は中断**（2026-09-25）。
  - 副産物: スケッチから force download（`LP_SYSTEM_REG_SYS_CTRL_REG` bit 2）で再起動すると、P4 の ROM はこのビットを
    消さない。USJ のチップリセットや esptool の hard reset でも download mode に戻り続ける。
    `esptool write-mem 0x50110008 0 0x4` で消してからリセットすると戻る。
  - 結論が出るまでは、HS の口だけのプローブにはアプリの更新の経路（DFU runtime、Mass Storage、vendor、CDC のスクリプト）
    を用意する。FS の口でデバイスを動かす構成なら、同じケーブルが USJ の loader として戻り esptool が使える。

## 7. 進め方（2026-09-25 のユーザーの方針）

実験と試作を先にし、その結果で仕様を固める。§4 の案と v1 wire §5.10 は、試作で確かめてから直す。

| 番号 | 試作 |
|---|---|
| P1 | vendor bulk と HID の両方で OEP を受け、セッションとロックを 1 つ共有する（応答は来た経路へ） |
| P2 | host の HID の経路（非同期の読み、Windows は HID の API） |
| P3 | CDC の口に fixture.uart を素通しで流す（line coding、TX を出力にする合図、ModemManager） |
| P4 | 設定の保存（NVS）と起動モードの切り替え（USB の構成が変わる、再列挙、usbipd） |
| P5 | probe 自身の更新の経路を複数（DFU runtime、Mass Storage、vendor） |
| P6 | コンソール（dmseq / SDI）を CDC の口に流す、自動の attach、host の detach / reset を越えて続くか |
| P7 | （2026-09-25 の追記）X035 の治具の P4 で P3 を回し直したら、921600 の 64 KiB の折り返しが 3 回中 2 回、gap（stream の 8 KiB があふれた）で失敗した（実効 63 kbaud。2 Mbaud は 3 回とも通過。43c6 では 3 回とも通過）。CDC の IN が 90 ms 以上吸い出されなかったと見られる（usbip の遅れの疑い、未切り分け）。stream を大きくするか、口に流す前の緩衝を持つかを、チューニングで見る |
| P7 | （ユーザーの依頼、2026-09-25）probe の受信のチューニングの後、USB の構成別（vendor だけ、vendor + HID、vendor + HID + CDC 1〜3 口など）に、経路ごとの速さ（link_source / link_sink、往復）と capture のストリーミングの上限を測る |

### 7.1 P1 / P2 の結果（2026-09-25、43c6）

構成: P4 HS の 1 つのデバイスに vendor bulk（direct build）、vendor 定義の HID（511 バイトのレポート、Report ID 6）、
CDC ACM を載せ、Endpoint 1 つに `addTransport` で 3 つの経路をつないだ（oep-probe-arduino c7a4933、scratch の
OepShared）。host は oep-client-python c78430d（`open_usb_host` が vendor、HID の順に試す）。

| 確認したこと | 結果 |
|---|---|
| vendor で開いたセッションのロックが HID / CDC の lock_state に見える | 合格（remaining 2999 ms） |
| HID / CDC から別のセッション ID で open | locked で拒否 |
| HID / CDC から同じセッション ID で open | resumed = 1、ロックの要る要求が通る |
| 購読（heartbeat）の届き先 | 購読した経路だけ（HID で購読 → [vendor 0, HID 7, CDC 0]）。vendor で購読し直すと vendor へ移る |
| CDC から end | 共有していたセッションが終わり、vendor から見てロック無し |

link_speed（16368 バイト × 16、1 秒）: vendor 33.3 / 5.6 MB/s、HID 1.07 / 1.01 MB/s、CDC 8.1 / 0.24 MB/s
（probe → host / host → probe）。host → probe が遅いのは probe の受信側（Stream の 1 バイトずつの read）で、
仕様ではなく実装の調整の課題。

わかったこと:
- **HID の Report ID は両方向に付ける**（HID の規則どおり）。EspUsbDevice は、HID クラスが 1 つだけのときは
  割り込み OUT のレポートを ID ごと渡す（data[0] = 6、長さはレポート + 1）。ID を外すのは HID を複数まとめたときだけ。
  X6 の host は出力に ID を付けておらず、count の下位バイトが 6 のときに 1 バイト失う不具合を持っていた。
  probe は「長さがレポート + 1 で先頭が自分の ID なら飛ばす」で両方に対応する。
- WSL の hidraw は、usbipd で付け直した後、hidapi（OS の HID ドライバー）で開けた。開けない環境では libusb1 に落ちる。
- 応答は来た経路へ、push とイベントは購読した経路へ、の規則で足りた（経路ごとのセッションや、経路を名指す仕組みは要らない）。

### 7.2 P3 の結果（2026-09-25、43c6）

構成: §7.1 の 3 つの経路に、データの CDC の口（"UART bridge"）を 1 つ足し、oep.fixture.uart（UART1、plan で TX 20 / RX 21）に
両方向でつないだ（oep-probe-arduino `FixtureUart::setPort` / `setLineCoding`、実験の機能。scratch の OepBridge）。
線はつながず、GPIO マトリクスで UART1 の RX を自分の TX のパッドから取って折り返した。口をつなぐ・外すのは scratch の
`oep.test.bridge`（host が決める。既定の結び付けは持たない）。

| 確認したこと | 結果 |
|---|---|
| CDC → TX →（折り返し）→ RX → CDC | 一致 |
| 同じバイトが OEP の read（position stream）にも入る | 入る（CDC の転送は stream とは別の読み位置で、OEP の read を乱さない） |
| 口の line coding で UART が掛け直される | 921600 → 922190、2000000 → 2000000（最後に来た設定が勝つ。OEP の configure も同じ UART を掛け直す） |
| 64 KiB の折り返し（host は読みながら書く） | 921600 / 2000000 とも全バイト一致、取りこぼしなし。実効は約 910 kbaud で頭打ち（probe の受信側の調整、P7） |
| 口が閉じている間に来たバイト | 口には流さない。stream にだけ残る（2 回とも口は空、stream は一致） |

わかったこと:
- **port → TX は、UART がすぐ受け取れる分（availableForWrite）だけ書く**。TX に書く間待つ作りでは、その間に UART の受信の
  バッファ（4096）があふれて、64 KiB の折り返しで 5 KB しか戻らなかった。
- **口が閉じている間のバイトを、開いたときにまとめて渡すのはやめた**。
  - EspUsbDevice の CDC の write は DTR を見ないので、閉じている間に書いたバイトは USB スタックの FIFO に入り、開いたときに消えた。
  - stream に残して、DTR が立ってから渡す形にしても、pyserial は open の最後に受信を空にするので消えた。
  - 端末は、アプリが raw モードにするまでは echo のモードなので、渡したバイトが echo で probe の TX、つまり target の RX へ戻りうる。1 回だけ届いたときは 1 バイト化けていた（'d' → 0xe4）。
  - そこで、USB-UART のケーブルと同じく「開いている間に来たバイトだけ流す」とした。履歴は OEP の read で取れる。
- CDC の記述子は bInterfaceProtocol 0（AT コマンドなし）。WSL には ModemManager がいないので、§4.5 の ModemManager の問題は
  ここでは確かめられない（Linux の実機で P6 と一緒に見る）。
- TX を出力にする時期は、今は plan の適用で UART の休止（high）に駆動する（v1 の fixture.uart の今の規則）。§4.2 の
  「口が開かれるまで入力」は、起動時に保存した bind から始める形（P4 の永続化）で要る。

### 7.3 P4 の結果（2026-09-25、43c6）

構成: oep.probe.config の最小の実装（oep-probe-arduino 35f624d `ProbeConfig`、ESP32 は NVS）。項目は boot_mode、plan（Endpoint が持つ plan そのもの）、bind（source は fixture.uart だけ）。label と target は持たず、set すると rejected unsupported になる。起動モードは 2 つ（scratch の OepConfigProto）。

- mode 0 "debug": vendor + HID + CDC（OEP）+ データの口 1 つ
- mode 1 "logic": vendor だけ

保存が無いときは sketch 自身の選択で mode 0 から始める。

| 確認したこと | 結果 |
|---|---|
| set の hash と、host が同じ項目から計算した正規形の CRC-32 | 一致（0x9b2c1a7e）。空の設定は 0 |
| save | 2 ms（NVS）。同じ内容の 2 回目は書かない（0.4 ms） |
| reboot → Windows に再列挙 | 1.4〜1.6 s。usbipd は毎回 Shared に戻るので attach し直す（WSL に来るまで計 6〜8.5 s） |
| 再起動後 | 保存した plan と bind が戻る。口を開くと line coding（bind の flags bit0）で UART が動き、折り返しが通る |
| boot_mode 1 を保存して reboot | インターフェースが vendor の 1 つだけで列挙される。describe の current_mode = (1, 1) |
| mode 1 から boot_mode 0 に戻す | 6 インターフェースに戻り、bind も残っていてブリッジが動く |

わかったこと（仕様 §5.10 に入れる点）:
- **設定は起動モードに依存しない**。
  - 最初の実装は、今のモードに無い口への bind を適用の失敗とし、保存を「読めない」にした。ところが plan はその前に適用されていて（set が原子的でなかった）、mode 1 で save し直すと bind が消えた。
  - 直した形: 今のモードに無い口への bind は保持し、何もしない（そのモードに戻ると結ぶ）。describe の port は今のモードの口だけを出す。
  - set は、bind が結べなければ plan も元に戻して何も変えない。
- **fixture.uart の bind には baud の出どころが要る**。
  - plan と bind だけを保存しても、再起動後に UART を掛けるものがない。
  - 試作は flags bit0（口の line coding を写す）で、口が開かれたときに掛けた。
  - bit0 を立てない bind でも使えるようにするなら、bind の引数に baud と format を持たせる（または fixture.uart の configure を項目にする）。
- **erase は保存だけを消し、今の設定は変えない**（仕様どおり）。host が「まっさらにする」には、erase と、全 tag を長さ 0 で送る set が要る。
- reboot の応答は、送ってから 100 ms 後に再起動して届いた。host の待ち時間（describe storage の再列挙の最長）は、usbipd の attach を含めずに 5000 ms とした。

### 7.4 P5 の結果（2026-09-25、43c6）

構成: §7.3 の試作に、probe 自身の更新の経路を 2 つ足した（OEP の外。EspUsbDevice 2.5.1 の機能）。

- DFU（ダウンロード形、EP0 だけ）を両方のモードに入れた。
- Mass Storage のファームウェアのディスク（.bin をコピーする）を mode 0 に入れた。

どちらも予備の OTA パーティションに書き、確かめてから再起動する。起動して USB が上がったら markValid する（そうしないとブートローダーが元に戻す）。

mode 0 は 8 インターフェースになった: HID、vendor、CDC（OEP）、CDC（UART bridge）、MSC、DFU。

| 経路 | host | 結果 |
|---|---|---|
| DFU | pyusb で書いた DFU 1.1 のダウンロード（WSL に dfu-util が無いため）。wTransferSize 1024 | 451 KB を 5.4 s（83 kB/s）。manifest の後に再起動し、11 s で再列挙。新しいビルドで動く |
| Mass Storage | usbipd から外し、Windows がマウントしたドライブ（E:、FAT 1.3 MB、README.TXT が見える）へ PowerShell でコピー | コピー 6.1 s。再起動して新しいビルドで動く。ボリュームラベルは Get-Volume に出なかった |

わかったこと:
- 更新の経路は、OEP の制御の経路（vendor / HID / CDC）と同じデバイスに並べても干渉しない。DFU は EP0 だけなので、どのモードにも入れられる。
- WSL では、Mass Storage は disk グループの権限が要り、DFU には dfu-util が要る。どちらも標準では使えない。Windows では Mass Storage が道具なしで使える。
  - 開発用の probe では、DFU（Linux / macOS の標準の道具）と Mass Storage（Windows / macOS で道具なし）の両方を持つのがよい。
  - OEP の vendor の経路で更新する独自のコマンドは、今回は作っていない（OEP の外なので、要るときに probe が決める）。
- P4 の ROM のブートモード（USJ の esptool）は、43c6 の USJ の口がつながっている構成ではいつでも使える（§6）。

### 7.5 P6 の結果（2026-09-25、X035 の治具）

構成: 治具の P4（30eda0e31108、OEP は USJ）に HS の CDC の口 "Target console" を 1 つ足した（oep-probe-arduino
`examples/Esp32P4X035ConsolePrototype`、eef626d の WIP を試験した）。

- oep.probe.config の bind（source 2 = target.console、mechanism 2 = dmseq）で、その口にコンソールを流す。
- connection に利用者（host / bind）を持たせた。host の detach は host の分だけを外し、force の TLV か、利用者がいなくなったときに切る。
- X035 には、コアの例 HelloDMSeq（1 秒ごとに uptime、入力を大文字で返す）を、oep_smoke と同じ host 側の書き込みで焼いた。

| 確認したこと | 結果 |
|---|---|
| attach 0（host に任せる）: host が attach するまで | 口には何も来ない |
| host が attach（止めない） | 口にコンソールが流れる。users = host + bind |
| host の普通の detach | 線は残る（users = bind）。コンソールも続く |
| 口に打った文字 | target に届き、大文字で返る（口 → dmseq → target） |
| host が attach し直して riscv-dm の reset | connection とコンソールが続き、reset 後の最初の出力（"hello from the debug module"）から取れる |
| force の detach | connection が切れ、口も止まる |
| attach 1（口を開いたとき）、target の項目が違う chip_id | attach して DM 0x7f を読み（0x035e0601、ESIG と同じ値）、違うので外す（state = 不一致） |
| attach 1、正しい chip_id | DTR で attach し、コンソールが口に流れる。口を閉じても読み続ける |
| attach 2（起動時）を保存して reboot | host なしで自分で attach し、口に流れる。uptime は続いていて、probe の再起動で target は再起動しない |

わかったこと:
- **§4.5 の (a)(b) の形で動く**: 口に結んだコンソールの connection は host の detach では閉じず、host の reset でも保たれる。
  書き込み → Monitor の導線（1 コマンド 1 プロセスの host が reset して detach した後の出力を取る）が成り立つ。
- **違う chip_id で断った直後は、正しい target で開いてもコンソールが戻るまで 1〜6 s かかった**。
  - probe の再 attach の間隔（250 ms）では説明できない。
  - target の SerialDMSeq（ホストの応答が 1 s 途切れると諦め、以後の書き込みを捨てる）のやり直しと、attach が DATA0 に残す値（0xffffffff）との相互作用と見られる（未確定。コアは凍結中なので target 側は触っていない）。
  - 断るときに DM に触る量を減らせるか（0x7f を読むだけで DATA0 は触らない）は、dmseq の文書と合わせて見る。
- 試作の段階で、bind の attach は chip_id の確かめまでを含めて 5 つの状態で足りた: なし / コンソール中 / 不一致 / attach 失敗、それに口の DTR。
- 未実装: lease の失効で host の分の利用を外すこと（§0 の寿命の規則）、host の riscv-dm の要求の間のコンソールの読みの停止（1 本のループなので、要求の途中には挟まらない）。

### 7.6 P7 の結果（2026-09-26、X035 の治具の P4 30eda0e31108。43c6 がつながっていないため）

チューニング（oep-probe-arduino 8abd078）:
- Endpoint は各経路を 2 KiB ずつまとめて読む（`Stream::readBytes`）。DirectBulkStream と試作の CDC / HID の Stream は、まとめて写す readBytes を持つ。
- FixtureUart は UART をまとめて読み、P4 では stream を 32 KiB にした。
- 試作に、USB の構成ごとの起動モードを足した（`host/usb_configs.py` がモードを切り替えて測る）。

link_speed（16368 バイト × 16、1 秒ずつ）と、lock_state の往復（200 回の平均）:

| モード | USB の構成 | vendor（probe→host / host→probe、往復） | HID | CDC（OEP） |
|---:|---|---|---|---|
| 1 | vendor | 36.1 / 10.2 MB/s、0.43 ms | - | - |
| 2 | vendor + HID | 36.2 / 10.0、0.42 | 1.07 / 1.03、0.65 | - |
| 3 | vendor + HID + CDC | 36.0 / 9.7、0.39 | 0.94 / 1.03、0.65 | 8.5 / 6.8、0.49 |
| 0 | vendor + HID + CDC + データの口 1 + MSC | 25.2 / 9.8、0.42 | 1.07 / 1.04、0.62 | 9.0 / 6.7、0.41 |
| 4 / 5 | vendor + HID + CDC + データの口 2 / 3 | USB の構成が組めない（`usbDevice.begin` が ESP_ERR_INVALID_SIZE） | | |

チューニング前（§5.3 X6、§7.1）との比較:

| 経路 | host→probe の前 | host→probe の後 |
|---|---|---|
| vendor | 5.5 MB/s | 約 10 MB/s |
| CDC | 0.23 MB/s | 6.7 MB/s |
| HID | 約 1.0 MB/s | 変わらず（report の往復が上限） |

UART bridge の 64 KiB の折り返し: 921600 / 2 Mbaud とも線の速さまで出て、取りこぼしも無い（2 回とも）。実効は 1003 / 2174 kbaud で、線の速さを上回って見えるのは WSL の時計が遅れるため。前は 2 Mbaud でも約 880 kbaud で頭打ちだった。921600 で stream があふれた件（§7 P7 の追記）は、32 KiB で 3 回とも起きなかった。

わかったこと:
- **probe → host（vendor）は、データの口と MSC を足すと 36 → 25 MB/s に落ちた**。HID と CDC を足しただけでは落ちない。X1 の「CDC を 2 口以上にすると 150 MHz のストリーミングが崩れる」と同じ傾向。
- **vendor + HID + CDC にデータの口を 2 つ以上足した構成は、EspUsbDevice が受け付けない**（エンドポイントか FIFO の予算の不足）。X1 では HID なしで vendor + CDC 3 口まで入っていた。
  - 起動モードの組み合わせは、probe が組めるものだけを describe に出す必要がある。
  - 保存されたモードが組めないときに USB から戻れなくならないよう、試作では保存した起動モードを捨てて、自分の選んだモードで起動し直すようにした（`ProbeConfig::forgetBootMode`）。仕様では describe の storage の状態（読めない）で知らせる形になる。
- 往復はどの経路・構成でも 0.4〜0.65 ms で、制御にはどれでも足りる。
- 再起動から再列挙までは約 4 s だった（再起動後の Windows では usbipd が自動で付け直していた）。
- capture のストリーミングの上限は、構成ごとには測り直していない。以前の試験のスクリプトが再起動で消えたため。必要なら試作に capture を足して測る。

#### 7.5.1 断った直後にコンソールが戻らない件の調べ（2026-09-26）

- ch32rv の指摘で、DmConsole の start() が dmseq でも DATA0 に 0 を書いて 4 回読み捨てていたのをやめた。dmseq では host が DATA0 を書いてよいのは bit 7 が立っているときだけ（oep-probe-arduino ed44d15。oep_smoke x035 は 14/14 のまま）。ただし、遅れは直らなかった（0.5 / 10 秒超 / 4.0 s）。
- 断った後に host として dmi で読むと、DATA0 = 0x00002df0（タイムアウトした空の frame。T=1、TO=1、S=1、N=0）で、仕様どおり待っていた。
- 遅れている最中は、プローブは 1 秒に約 7 万回 DATA0 を読んでいるのに、bit 7 の立った語を一度も読まない。host の dmi で読んでも DATA0 = 0、DMSTATUS = 0x00030c82（ハートは走っている）。
  - target の SerialDMSeq は、0 の語を沈黙として扱い、20 ms ごとに frame を出し直すはずなので、target の DATA0 への書き込みが効いていないと見られる。
- 候補の原因: 断るときの detach が DMCONTROL = 0（dmactive = 0）を書き、デバッグモジュールをリセットする。次の attach は CFGR（WCH の 0x7d / 0x7e、"allow output from slave"）を dmactive を立てる前に書くので、それが効かず、ハートの出力が許されないままになる。
  - コンソールの読みがバスを休ませないので、アイドル後に CFGR を書き直す処理も走らず、何かの拍子に書き直されるまで止まる（遅れがばらつくことと合う）。
  - dmactive を立てた後にも CFGR を書くように直した（LinkE も線上でこの順。wch-protocols link-to-target §5）。
    **直らなかった**: 5 回中 2 回は 8 s 以上戻らず、残りも 7.4 s かかった。遅れている間は DATA0 = 0 のまま。oep_smoke x035 14/14 は保つので、変更は残した。
  - 原因は未確定。わかっていること:
    - target のハートは走っていて、uptime は続いている。
    - DATA0 は 0 のまま（プローブも host も同じ値を読む）。
    - 通常の開始（断ることを挟まない）では、すぐ流れる。
- **原因（2026-09-26 に特定）**: 断るときの detach が DMCONTROL = 0 を書き、デバッグモジュールをリセットしていた。
  - 遅れている最中に dmi で見ると、DATA0 は 60 回続けて読んでも 0、CFGR を書き直しても変わらない。
  - DATA0 に無効な語（0x00000001）を書くと、target はすぐ 0x00000a90（S=0、TO なしの普通の frame）を出し直した。target は答えを待っている最中だった。
  - 流れ: リセットで DATA0 が 0 に戻り、target の frame が消える。SerialDMSeq は 0 を沈黙と読んでタイムアウトまで待つ。その待ちは target が DATA0 を読む回数で数えるので、probe が DMI を 1 秒に約 7 万回読んでいると 1〜10 s に延びる。
  - 直し方: `Ch32Dm::detach` は DMCONTROL = 1（dmactive だけを残す）を書く（oep-probe-arduino 901bbd8）。
    - 直す前はおよそ 3 回に 2 回遅れた。直した後は 8 回 + 5 回とも、すぐ戻った。
    - oep_smoke x035 / v003 は 14/14、oep_probe_checks は 4/4、6/6。L103 は未確認（RP2350 のプローブがつながっていない）。
  - 同じ frame は、host の「書き込み → reset → detach」の後にも消えうる。dmseq の仕様と v1 wire §5.5 に「detach でデバッグモジュールを reset しない」を足した。
  - WCH-LinkE は DetachChip で dmactive を下ろす（AttachChip ではない。wch-protocols の訂正、link-to-target §5）。次の AttachChip が ESIG を読んで DATA0 に 0 でない語を残すので、target はすぐ出し直し、LinkE の host（ch32rv、7 系統）には空白が出ない。OEP の probe の attach は DATA0 に何も書かないので、0 が残って待たされた。DATA0 がリセットで消えるのを確かめたのは X035 だけ。
