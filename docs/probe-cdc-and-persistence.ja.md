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
