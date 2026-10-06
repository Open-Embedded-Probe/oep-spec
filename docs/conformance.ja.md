# OEP v1 への適合

[English](conformance.md)

状態: **ガイド**（規範ではない）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。規則を足さない。各行は規則を持つ規範の文書を指し、この文書と規範の文書が食い違えば規範の文書が
正しい。答える問いは一つ: probe と host が OEP v1 に適合するには何をするか、実装者はそれをどう確かめるか。
適合の条項そのものは [core](oep-core.ja.md) §1.2 である。

## 1. probe のチェックリスト

probe は、自分が出す transport とインターフェースについてこの一覧のすべてを行うとき適合する。

**transport とフレーム**

- transports §1 の transport を少なくとも一つ、そのフレームとともに（§1.2）。
- シリアルの口: 両側を 0x00 で囲んだ COBS + CRC-16 のフレーム（transports §1）、受け方と生バイトの規則（transports §4）、UART ブリッジの
  回線と起動時の速さ（transports §4）、DTR / RTS で何も決めない（transports §4）、セッションが口を持つ間の生転送の停止（transports §4）。
- vendor bulk と TCP: `length(u16) message`（transports §1）、vendor bulk の長さ 0 の転送の規則（transports §1）、TCP では途切れで読み直さない（transports §2）。
- HID: `count(u16)` の report が運ぶ長さつきの流れ、report をまたぐフレーム、count 0 は飛ばす、詰め物は 0 で送り無視する、report ID は 1 つか無し、流れの上のフレームの途切れ、長すぎる count（transports §1）。出力 report を interrupt OUT と SET_REPORT の両方で受ける（transports §3）。
- max_frame を超える長さ: 捨てて待つ。TCP では閉じる（transports §1）。`probe_frame_gap_ms` の途切れで読み直す。TCP を除く（transports §2）。
- confirm の前でも 64 バイトまでのメッセージを受ける（transports §3）。max_frame を超えて送らない（transports §3）。
- USB: probe が選べる口では シリアル番号 = unit_id（transports §3）。vendor bulk と HID は transports §3 の形で、それぞれ一つまで。
- 自分で OEP の要求に答える端点は、後ろに何があっても probe である。中継する broker は transports §1 と core §5.2 に従う（probe への transport が無くなったら終わることを含む）。

**メッセージ、断り方、TLV**

- 要求と答えのヘッダ（§4.1、§4.2）。要求一つに答え一つ、来た transport へ、来た順に（§4.2、§4.4）。
- rejected は受け付けなかったものだけ。受け付けて失敗したものは completed failed / partial（§4.2）。
- 断りの順序。最初に当てはまる理由で断る（§4.3）。payload は §4.3 のとおり（unavailable の TLV、unsupported の tag）。payload の中で
  指す fn は順 5 の終わりで確かめる（§4.3）。
- role が要求の role でないメッセージと、10 バイトのヘッダより短い要求は、答えずに捨てる（§2.4）。ロックが要る op で session_id 0: session_required（§4.1）。
- fn 0 とすべての fn の describe は ops（0x09）を載せる: 必須の op はすべて立て、任意の op は持つときに限り立て、実験用の op は立てない（§1.2、§7.4）。ops に立っていない op は unknown_operation、probe が持つ op の任意の機能は unsupported（§1.2）。インターフェースの表の op は、文書が任意と書かない限り必須。
- 要求の TLV: critical の印、知らない critical TLV は unsupported、知らない非 critical TLV は ignored、知っているより長い TLV、短い TLV、
  繰り返さない TLV の繰り返し、tag 0x7F / 0xFF（§2.2、§2.3）。
- ignored（tag 0x7F）を、それが要る completed の答えすべてに、要求の順で、最大 16 項目、16 番目は 0x00、置き場を必ず残して（§2.3）。
- TLV の形は `tag len(u16) value` の一つ（§2.2）。並びは要素の長さを持たない `count × element`、固定の形はどれも定義のとおりで、末尾を延ばさない（§2.3）。要求の真偽値と文字を確かめる（§2.1）。出荷するものは実験用の値を使わない（§2.5）。
- window / max_inflight は transport ごと（§4.4）。
- 一周する値: 1 つの空間で同時に持つ値の広がりは幅の 4 分の 1 未満（§2.6）。

**セッションとロック**

- ロックは一つ、§6.2 の判定表、lease の再開始と実行中は数えないこと（§6.1）。
- open / end / keepalive / lock_state / force / owner（§6.4）。lease は 1000〜60000 ms に丸める（§6.4）。session_id 0 は断る（§6.1）。
- 再送の表: 少なくとも max_inflight 件、rejected の答えも覚える、成功した open のたびに捨てる、probe に一つ（§5.2）。
- ロック不要の op は状態を変えない（§6.3）。boot_id は起動のたびに変わり、§6.5 の素をその順に使う（§6.5）。
- 時計: 起動からの ns で、同じ boot_id の間、減らず一周しない（§2.6a）。
- セッションが作ったものはすべて、そのロックが終わるとき end、期限切れ、force のどれでも同じに解放し、再送された open では残す（§9）。再開は無い（§6.4）。資源の番号（§9）。閉じたコンソールのストリームは、同じ場所で同じ mechanism が次に open されるまで読める（[コンソール](../interfaces/oep-if-console.ja.md) §2）。

**fn 0（本体。名前を持たず、list に載らない）**

- 必須の op: core §12 で「yes」の行（confirm、list、describe、open、end、keepalive、lock_state、subscribe、unsubscribe）。
- confirm: revision の選び方、transport TLV、扱える範囲つきの断り。max_frame は 64 以上、window は max_frame 以上、
  max_inflight は 1 以上（§7.1）。
- list: fn 0 を載せない、ラベル境界での一致、instance の番号、boot_id が同じ間は答えが変わらない、first が一致の数以上なら total と count 0
  （§7.2）。
- describe: ページ送り、宣言だけで boot_id が同じ間は変わらない、要求に TLV を置かない（§7.3）。
- fn 0 の describe の必須の tag: unit_id、transport（transport ごとに一つ、interface の欄は §7.5 のとおり）、max_op_ms（1〜
  `max_op_ms_max`）（§1.2、§7.5）。
  discoverable は、probe がプロジェクトの USB の VID:PID で列挙するときだけ 1、ほかは 0（§7.5）。unit_id の一意性と不変性、transport の index の不変性（§7.5）。
- channel: 解放したピンは空きの状態へ、起動したら最初の答えの前に reserved でないすべての channel を空きの状態へ、ピンを取ってもピンは変わらない、資源の取り合いは何も変えずに断る（§8、§8.1）。
- 通知: subscribe / unsubscribe、seq、fn 0 の heartbeat、答えを先に送ることと溜める量の上限（§11.2〜§11.4）。
**時間の上限**（値は `registry/oep-v1.toml`）

- `probe_frame_gap_ms`（transports §2）。宣言した max_op_ms より長い要求はなく、超えうる op は断る（§7.5）。lease の範囲
  （§6.4）。heartbeat の周期（§11.3）。port_speed の verify_ms / idle_ms と戻る条件（[リンク](../interfaces/oep-if-link.ja.md) §3）。各 wire の attach と scan の予算
  （[線とデバッグ](../interfaces/oep-if-debug.ja.md) §1）。restart の答えから再起動を始めるまでの `restart_after_answer_ms` と、同じ transport で confirm にまた答えるまでの、宣言した restart_max_ms（[再起動](../interfaces/oep-if-restart.ja.md) §1、§2）。

## 2. host のチェックリスト

- **フレーム**: 1 フレームを 1 回の write で送り、途中で 100 ms 以上止まらない（transports §2）。COBS の受け方（transports §1）。confirm の答えの前は
  64 バイトを超えて送らず、後は max_frame を超えて送らず、65535 バイトまで受けられる（transports §3）。vendor bulk の長さ 0 の転送（transports §1）。
- **見つけ方**: USB の自動識別は project の VID:PID `1209:4F45` だけ、名指しの probe は unit_id で、それ以外は
  利用者が選ぶ（transports §3）。試し方の規則: confirm だけを送り、正しい答えがなければ閉じる（transports §3）。OEP の probe と分かった機器の中の口の選び方（transports §3）。
  transport を試す順（transports §3）。排他で開く（transports §3）。DTR / RTS を立てる（transports §4）。
- **confirm と revision**: 扱える範囲を送り、その後は使っている revision を `min_rev = max_rev` で送る（§7.1）。revision を知らない
  インターフェースは使わない（§2.7）。§7.1 の範囲（max_frame、window、max_inflight）を外れた confirm の答え: その transport には
  もう何も送らず、値を知らせる（§7.1）。
- **待ち**: すべての要求に §4.4 の下限、自分のリンクの要求も含む。UART ブリッジでの転送時間、その transport での最初の confirm の
  答えまでは `min_max_frame` で（§4.4）。max_op_ms が 0 か `max_op_ms_max` を超える: その probe を使わない（§4.4）。シリアルの口での
  受け取れる量（transports §4）。
- **再送と回復**: 同じ corr で一度まで（§5.2）。corr は要求ごとに 1 進め、0 を飛ばす（§4.1）。長さつきフレームの再同期と
  `host_resync_wait_ms`（transports §5）。再送にも答えが無ければその transport は失敗した: そこで何かを送る前に、どの種類のフレームでも transports §5 の
  confirm で立て直すか開き直し、状態を変える要求を繰り返す前に状態を読む（§5.2）。
- **セッション**: 0 でない乱数の session_id（§6.1）。答えの lease_ms が正で、keepalive が延ばす（§6.4）。no_session /
  locked への対応（§4.3、§6.2）。no_session の後は新しいセッションを開いて設定し直す。boot_id が（confirm でも open でも）変われば自分の状態は無効で、
  list し直す（§6.5）。一つのセッションの要求は一つの transport で（transports §3）。セッションの要らないロック不要の要求は session_id 0 で（§4.1）。
- **答えの読み方**: role が要求の role のメッセージは捨てる。5 バイトより短い答えと、ヘッダより短い出来事やデータのフレームは
  壊れたフレーム（§2.4）。知らない TLV と tag を飛ばす、繰り返された tag は最初を使う、0 でない真偽値は真と読む（§2.1、§2.3）。知らない
  値は §2.4 のとおり。ignored とその 0x00 の項目を読む（§2.3）。role と corr で振り分ける（§11.1）。TLV が効かなければ意味のない要求では
  critical の印を付ける（§2.3）。
- **文字列**: 答えの文字を見せる前に制御文字と不正な UTF-8 を置き換える（§2.1）。unit_id とシリアル番号、unit_id どうしは ASCII の
  大文字小文字を区別せず比べる（transports §3）。`x-` の unit_id でまとめたり、名指したり、何かを覚えるキーにしたりしない（§7.5）。iProduct と
  インターフェースの文字列は表示だけ（transports §3）。`name#instance` と `oep://` のアドレス（§7.2、§7.6）。
- **restart**（`oep.probe.restart`）: 使うときは、答え（または答えが来なかったとき）の後にその probe に何も送らずに閉じ、`restart_after_answer_ms` 以上待ってから新しく開くのと同じに開き直し（最初は confirm、UART bridge では起動時の速さ、USB では列挙し直すのを待つ）、答えを受けてから（答えが来なかったときはその待ちが過ぎてから）describe の restart_max_ms まで開き直しと confirm を繰り返し、正しい答えが無ければその probe を無くなったものとして扱う。confirm の boot_id が変わったことを確かめて覚えた状態を捨てる（[再起動](../interfaces/oep-if-restart.ja.md) §3、[リンク](../interfaces/oep-if-link.ja.md) §3 の host の義務 6）。
- **port_speed**: host が使うときは [リンク](../interfaces/oep-if-link.ja.md) §3 の host の義務 1〜7。UART bridge のどの口でも、上げた速さの後に confirm を繰り返す（transports §4）。
- **アナログのキャプチャ**: host が電圧を示すときは、値 0 と 2^b − 1 を電圧ではなく振り切れ（低い端以下、高い端以上）として示す
  （[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.2 規則 6）。

## 3. 標準インターフェース

`oep.` の名前を list に出す probe は、そのインターフェースの文書全体に従う。必須のものの短い一覧:

| インターフェース | 必須 | 任意（宣言するもの） |
|---|---|---|
| 位置つきのストリーム（[共通部品](../interfaces/oep-if-common.ja.md) §1） | それを使う各インターフェースで §1 の read、marks、clear、mark、write。§3 の status の値 | — |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §0〜§3、§5） | scan（ピンのない wire では count = 0 がその 1 つの組を試す。skip の後に何も残らない count = 0 の並びは tried 0 の success で答える）、attach（max_speed は必須。既存の connection に加わる attach は、運ばない設定（idle_clock など）をその connection の今のまま保つ）、detach、connections。§1 の attach の規範と予算。§2 の寿命と線の状態 | attach の reset TLV（role_channels の role 3）。持つなら、線を離した後に DM を待つ（§3、`reset_settle_ms`） |
| `oep.target.riscv-dm`（§4） | dmi、halt、resume | reset、read_block / write_block、run、step: ops。reset があれば、ndmreset を解いた後に DM を待つ（§4.3、`reset_settle_ms`）。read_block / write_block があれば max_length |
| `oep.target.arm-adi`（§6） | transfer、read_block、write_block。max_length は必ず出す | — |
| `oep.target.console`（[コンソール](../interfaces/oep-if-console.ja.md)） | §1 の op。describe の mechanisms は必ず出す。mechanism 1 か 2 を持てば describe の send_queue（64 以上）を出し、write をその送りの列で受ける（§2）。方式 2 の枠は [dmseq](../interfaces/target-console-dmseq.ja.md) のとおり | どの方式か（describe の mechanisms） |
| `oep.fixture.gpio`（[fixture](../interfaces/oep-if-fixture.ja.md) §1） | set、read。describe の modes に mode 0 | 出力の強さ（§1.1） |
| `oep.fixture.uart`（§2） | §2 の op。describe の formats に 8N1 | ほかの format |
| `oep.fixture.i2c-target`（§3） | stretch を除く §3 の op。mode 1 と 2 | stretch（ops、max_stretch_us とともに）。mode 3（features bit0）。プルアップ（features bit2、pullup_ohms とともに） |
| `oep.fixture.spi-target`（§4） | §4 の op。MISO をソフトウェアで駆動するなら cs_setup_ns | LSB first（features bit0） |
| `oep.fixture.logic`、`oep.fixture.analog`（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1〜§3） | query と force を除く §3.2 の op。§3.5 の describe。calibration はアナログだけ | query、force（ops）。通知（features bit2） |
| `oep.fixture.capture-group`（§4） | force を除く §4.1 の op。§4.3 の describe | force（ops）。通知（features bit2） |
| `oep.probe.plan`（[plan](../interfaces/oep-if-plan.ja.md)） | plan の役割を持つインターフェースがあれば list に出す。plan_apply（fn ごとに不可分）、plan_release、§2.5 の断り方、設定の plan。上限があれば describe の plan_roles | — |
| `oep.probe.restart`（[再起動](../interfaces/oep-if-restart.ja.md)） | restart。describe の restart_max_ms（`restart_after_answer_ms` 以上）。ロックの要る op として断る。答えは completed success で、それを先に送る。答えの後はどの transport の要求も処理せず、connection を閉じて reserved でない channel を空きの状態にし、答えが transport を出てから `restart_after_answer_ms` のうちに再起動する。再起動の後は電源を入れたときと同じ（新しい boot_id、保存した設定だけが残る）。答えが transport を出てから restart_max_ms のうちに、同じ transport で confirm にまた答える | — |
| `oep.probe.link`（[リンク](../interfaces/oep-if-link.ja.md)） | source、sink | port_speed（ops）: その状態と戻る条件（§3） |
| `oep.probe.config`（[probe の設定](../interfaces/oep-if-probe-config.ja.md)） | 設定を扱う probe だけが list に出す。get、set、unset、state。hash。§2 の断り方。§4 の describe | save / erase（ops、storage の tag とともに。無ければ unknown_operation）。slot。bind（あれば bind_modes の bit 0 と 1） |

## 4. 確かめ方

**試験のベクタ**（[`tests/vectors/`](../tests/vectors/)）。`tools/oepvectors1.py` が規範の文書から計算する。ベクタと文書が
食い違えば文書が正しい（core §0 規則 4）。扱う範囲:

| ファイル | 扱うもの |
|---|---|
| `checks.json` | CRC-16（transports §1）、CRC-32（§5.2）、dmseq の CRC-8 |
| `cobs.json` | COBS の符号とシリアルの口のフレーム全体。復号が受け入れるもう一つの形も含む（transports §1） |
| `headers.json` | 要求と答えのヘッダ、TLV の符号（§2.2、§4.1、§4.2） |
| `confirm.json` | confirm のやりとり（§7.1） |
| `discovery.json` | list（§7.2。fn 0 を載せないので、インターフェースの無い例の probe では空）、fn 0 の describe（§7.3、§7.5）、終わりを越えた describe、ヘッダの断り unknown_function / unknown_operation（§4.3 の順 1） |
| `probe_config_hash.json` | probe.config の正規形と hash（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §2） |
| `refusals.json` | §4.3 の断り方と §2.3 の ignored の一覧について、要求とそのとおりの答え |
| `sessions.json` | セッションの場面: 判定の表（§6.2）、送り直しの表（§5.2。送り直した end）、end での解放と no_session（§9）、force、session_id 0（§4.1）。決めた初めの状態から順に送る要求と答え |
| `ops.json` | op ごとのバイト列: 要求、それが前提とする probe の状態、答え（`oep.probe.restart`、`oep.probe.plan`、`oep.probe.link`、gpio、rvswd、riscv-dm、console、probe.config、logic の一部）。並びの答えは要素の長さ無しの `count × 要素`（§2.3） |

実装は JSON を読み、自分の符号器、復号器、答えをバイト単位で比べる。ベクタが文書と registry に合っているかを確かめるには:

```sh
python3 tools/oepvectors1.py --check      # 規則が与えるものとファイルが違えば exit 1
cd tests && uv run pytest vectors          # 別のコード（binascii、zlib）でのベクタの確認と、tool の --check
```

**host のための偽の probe。** [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python) は、この仕様のとおりに答える
probe を pty（シリアルの口）か TCP（どちらのフレームでも）で出す。再送と回復を試すための故障（答えを落とす、CRC を壊す、雑音）も入れられる:

```sh
python -m oep_client.fake_serve --pty     # 最初の行が開く先。profile と故障は --help
```

**probe を見る。** 同じパッケージの `oep dump --port <port>` が、すべてのインターフェースの list と describe を見せる。そのクライアントの
試験も、ベクタを自分のコードと偽の probe に対して確かめる。

**まだ扱っていないもの。** probe のための自動の適合試験は無い。ベクタが扱うのは符号、一部の断り方、いちばん小さな probe の発見、セッションの場面、一部の op
で、ページ送りの続き、plan の取り合い、インターフェースの多くの op と状態の移り変わりはまだ扱わない。時間（待ち、lease、max_op_ms、フレームの途切れ、port_speed の戻る条件、
attach と scan の予算）は共有の道具では確かめていない。電気的な規則（idle の状態、wire が答えない間の線、cs_setup_ns）と実機での
振る舞いは、実装者が自分で実機の試験をする必要がある。

## 5. 適合で名乗れること

認定は無い。適合の主張は実装者自身の言明で、この一覧と規範の文書に照らして確かめたものである。

- 1 節を満たし、list に出すすべての `oep.` のインターフェースについて 3 節を満たす probe は、**OEP v1 の probe** と名乗ってよく、
  実装するインターフェース（と revision）を挙げる。2 節を満たす host は **OEP v1 の host** と名乗ってよい。主張はプロトコルの
  revision 1（core §2.7）についてで、任意の機能を含むことは意味しない。
- 線の上の形を変える実装、仕様が許さない答え方をする実装、自分のインターフェースや tag を `oep.` の名前の下に置く実装は
  適合しない（core §13 規則 1 と 7）。自分のインターフェースは逆ドメインの名前を使う。
- 適合は project の USB VID:PID を使う許可を与えない。それは [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino)
  の PID-USE の条件（そのライブラリから作る、ソースを公開する、仕様どおりに OEP を話す、正直に名乗る、など）のもとで別に与えられる。
  ほかの実装は自分の USB ID を使う。host は利用者がそれを名指すか口を選んだときに開く（transports §3）。
- 適合しても probe が自動で識別されるようにはならず、扱える target のチップ、速さ、規範の文書が求める以上の電気的な振る舞いについては何も言わない。
