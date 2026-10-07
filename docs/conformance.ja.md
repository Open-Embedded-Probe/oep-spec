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
- フレームの区切りを書き込み、転送、report、TCP の segment の区切りに頼らない。TCP 以外では、送るフレームの途中で `probe_frame_gap_ms` 止めない（transports §2）。
- 経路（TCP の接続を含む）が閉じても、セッション、ロック、購読、送り直しの表は残し、閉じた経路への応答と通知は捨てる（transports §3）。
- HID: `count(u16)` の report が運ぶ長さつきの流れ、report をまたぐフレーム、count 0 は飛ばす、詰め物は 0 で送り無視する、report ID は 1 つか無し、流れの上のフレームの途切れ、長すぎる count（transports §1）。出力 report を interrupt OUT と SET_REPORT の両方で受ける（transports §3）。
- max_frame を超える長さ: 捨てて待つ。TCP では閉じる（transports §1）。`probe_frame_gap_ms` の途切れで読み直す。TCP を除く（transports §2）。
- confirm の前でも 64 バイトまでのメッセージを受ける（transports §3）。max_frame を超えて送らない（transports §3）。
- USB: probe が選べる口では シリアル番号 = unit_id（transports §3）。vendor bulk と HID は transports §3 の形で、それぞれ一つまで。
- 自分で OEP の要求に答える端点は、後ろに何があっても probe である。中継する broker は transports §1 と core §5.2 に従う（probe への transport が無くなったら終わることを含む）。

**メッセージ、断り方、TLV**

- 要求と答えのヘッダ（§4.1、§4.2）。要求一つに答え一つ、来た transport へ、来た順に（§4.2、§4.4）。
- rejected は受け付けなかったものだけ。受け付けて失敗したものは completed failed / partial（§4.2）。
- 断りの順序: 見出し、送り直しの表、セッションの順。それ以外は何も変える前にすべて確かめ、当てはまる理由のどれか 1 つで断る（§4.3）。
  payload は §4.3 のとおり（unavailable の TLV、unsupported の tag）。
- role が要求の role でないメッセージと、10 バイトのヘッダより短い要求は、答えずに捨てる（§2.4）。ロックが要る op で session_id 0: session_required（§4.1）。
- fn 0 とすべての fn の describe は ops（0x09）を載せる: 必須の op はすべて立て、任意の op は持つときに限り立てる（§1.2、§7.4）。ops に立っていない op は unknown_operation、probe が持つ op の任意の機能は unsupported（§1.2）。インターフェースの表の op は、文書が任意と書かない限り必須。
- ops の値は base と 1 byte 以上の bitmap で、`base + 8 × bitmap の byte 数 ≤ 256`（§7.4）。
- 要求の TLV: 知らない critical TLV は unsupported、知らない非 critical TLV は無視する。実装する TLV は bit 7 によらず、長さが定義と違えば malformed、
  扱わない値は unsupported（§2.2、§2.3）。
- TLV の形は `tag len(u16) value` の一つ（§2.2）。並びは要素の長さを持たない `count × element`、固定の形はどれも定義のとおりで、末尾を延ばさない（§2.3）。
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

- 必須の op: core §12 の行（confirm、list、describe、clock、open、end、keepalive、lock_state）。
- confirm: revision の選び方、transport TLV、扱える範囲つきの断り。max_frame は 64 以上、window は max_frame 以上、
  max_inflight は 1 以上（§7.1）。
- list: fn 0 を載せない、instance の番号、boot_id が同じ間は答えが変わらない、first が total 以上なら total と count 0（§7.2）。
- describe: ページ送り、宣言だけで boot_id が同じ間は変わらない（§7.3）。経路によらないので、各 TLV と max_length は probe のどの経路の max_frame にも収まる（§7.3、§7.4）。
- clock: boot_id と uptime_ns（要求を受けてから応答を送るまでの間に読んだ時計）。ロック不要で、session_id 0 ならセッションが無くても、ほかのセッションが
  ロックを持っていても答え、セッション、ロック、lease に触れない。中継のブローカーは自分で答えず中継する（§7.7、transports §1）。
- fn 0 の describe の必須の tag: unit_id、transport（transport ごとに一つ、interface の欄は §7.5 のとおり）、channel を持つなら channels（番号は 0〜channels − 1）、max_op_ms（1〜
  `max_op_ms_max`）（§1.2、§7.5）。unit_id の一意性と不変性、transport の index の不変性（§7.5）。
- channel: 解放したピンは空きの状態へ、起動したら最初の答えの前に自分で使う channel を除くすべての channel を空きの状態へ、ピンを取ってもピンは変わらない、資源の取り合いは何も変えずに断る（§8、§8.1）。
- 通知（送り出すインターフェースがあれば）: その fn の subscribe（0x30）/ unsubscribe（0x32）を ops に立てる、送り出さない fn は持たない、seq、データだけをまとめ出来事は先の答えの後すぐ送る、答えを先に送ることと溜める量の上限（§11.2〜§11.4）。
**時間の上限**（値は `registry/oep-v1.toml`）

- `probe_frame_gap_ms`（transports §2）。宣言した max_op_ms より長い要求はなく、超えうる op は断る（§7.5）。lease の範囲
  （§6.4）。port_speed の verify_ms、`port_speed_idle_ms` と戻る条件（[リンク](../interfaces/oep-if-link.ja.md) §3）。attach、scan、riscv-dm の reset は max_op_ms のうちに答える
  （[線とデバッグ](../interfaces/oep-if-debug.ja.md) §1、§3、§4.3）。同じ transport で confirm にまた答えるまでの、宣言した restart_max_ms（[再起動](../interfaces/oep-if-restart.ja.md) §1、§2）。

## 2. host のチェックリスト

- **フレーム**: 1 フレームを 1 回の write で送り、途中で `probe_frame_gap_ms` 止まらない（transports §2）。COBS の受け方（transports §1）。confirm の答えの前は
  64 バイトを超えて送らず、後は max_frame を超えて送らず、65535 バイトまで受けられる（transports §3）。vendor bulk の長さ 0 の転送（transports §1）。
- **見つけ方**: USB の自動識別は project の VID:PID `1209:4F45` だけ、名指しの probe は unit_id で、それ以外は
  利用者が選ぶ（transports §3）。試し方の規則: confirm だけを送り、正しい答えがなければ閉じる（transports §3）。OEP の probe と分かった機器の中の口の選び方（transports §3）。
  transport を試す順（transports §3）。排他で開く（transports §3）。DTR / RTS を立てる（transports §4）。
- **confirm と revision**: 扱える範囲を送り、その後は使っている revision を `min_rev = max_rev` で送る（§7.1）。revision を知らない
  インターフェースは使わない（§2.7）。
- **待ち**: すべての要求に §4.4 の下限、自分のリンクの要求も含む。UART ブリッジでの転送時間、その transport での最初の confirm の
  答えまでは `min_max_frame` で（§4.4）。attach、scan、riscv-dm の reset の引数の時間は max_op_ms（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §1、§4.3）。
- **再送と回復**: 同じ corr で一度まで（§5.2）。corr は要求ごとに 1 進め、0 を飛ばす（§4.1）。長さつきフレームの再同期と、
  最後に書いてから `probe_frame_gap_ms` より長く待つこと（transports §5）。再送にも答えが無ければその transport は失敗した: そこで何かを送る前に、どの種類のフレームでも transports §5 の
  confirm で立て直すか開き直し、状態を変える要求を繰り返す前に状態を読む（§5.2）。
- **セッション**: 0 でない乱数の session_id（§6.1）。答えの lease_ms が正で、keepalive が延ばす（§6.4）。no_session /
  locked への対応（§4.3、§6.2）。no_session の後は新しいセッションを開いて設定し直す。boot_id が（confirm でも open でも）変われば自分の状態は無効で、
  list し直す（§6.5）。一つのセッションの要求は一つの transport で（transports §3）。セッションの要らないロック不要の要求は session_id 0 で（§4.1）。
- **probe の時刻**: probe の時刻を自分の時刻に写すときは clock で読み、送った時と受けた時の中点に当て、不確かさを往復の半分とする（[host 開発ガイド](host-development-guide.ja.md) §12）。
- **答えの読み方**: role が要求の role のメッセージは捨てる。5 バイトより短い答えと、ヘッダより短い出来事やデータのフレームは
  壊れたフレーム（§2.4）。知らない TLV と tag を飛ばす、繰り返された tag は最初を使う、0 でない真偽値は真と読む（§2.1、§2.3）。知らない
  値は §2.4 のとおり。role と corr で振り分ける（§11.1）。効かなければ意味が無いか害のある TLV には
  critical の印を付ける（§2.3）。
- **文字列**: 答えの文字を見せる前に制御文字と不正な UTF-8 を置き換える（§2.1）。unit_id とシリアル番号、unit_id どうしは ASCII の
  大文字小文字を区別せず比べる（transports §3）。`x-` の unit_id でまとめたり、名指したり、何かを覚えるキーにしたりしない（§7.5）。iProduct と
  インターフェースの文字列は表示だけ（transports §3）。
- **restart**（`oep.probe.restart`）: 答えの後は、probe が新しい起動で confirm に答えるまで何も答えないものとして扱い、新しく開くのと同じに開き直して boot_id で確かめる（[再起動](../interfaces/oep-if-restart.ja.md) §2。手順は [host 開発ガイド](host-development-guide.ja.md) §5.2）。UART bridge では起動時の速さに戻す（[リンク](../interfaces/oep-if-link.ja.md) §3 の host 2）。
- **port_speed**: host が使うときは [リンク](../interfaces/oep-if-link.ja.md) §3 の host 1 と 2（試すの答えの後 `port_speed_switch_wait_ms` 以上待ってから新しい速さで送る、戻す・end・再起動する op の答えで起動時の速さに戻る）。UART bridge のどの口でも、上げた速さの後に confirm を繰り返す（transports §4）。
- **アナログのキャプチャ**: host が電圧を示すときは、値 0 と 2^b − 1 を電圧ではなく振り切れ（低い端以下、高い端以上）として示す
  （[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.2 規則 6）。

## 3. 名前が `oep.` で始まるインターフェース

`oep.` の名前を list に出す probe は、そのインターフェースの文書全体に従う。必須のものの短い一覧:

| インターフェース | 必須 | 任意（宣言するもの） |
|---|---|---|
| 位置つきのストリーム（[共通部品](../interfaces/oep-if-common.ja.md) §1） | それを使う各インターフェースで §1 の read、marks、clear、mark、write。§3 の status の値 | — |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §0〜§3、§5） | scan（skip の後に何も残らない count = 0 の並びは tried 0 の success で答える。max_speed が無ければその wire の最も遅い速さ）、attach（max_speed は必須。既存の connection に加わる attach は、運ばない設定（idle_clock など）をその connection の今のまま保つ）、detach、connections。§1 の attach の規範と max_op_ms。§2 の寿命と線の状態（書き込みを繰り返さない再試行、target の状態を変えない再試行） | attach の reset TLV（role_channels の role 3）。持つなら、線を離した後に DM を待つ（§3、max_op_ms のうち） |
| `oep.target.riscv-dm`（§4） | dmi、halt、resume | reset、read_block / write_block、run、step: ops。reset があれば、ndmreset を解いた後に DM を待つ（§4.3、max_op_ms のうち）。read_block / write_block があれば max_length。自分の op で使った DATA0 / DATA1 を戻す（§4） |
| `oep.target.arm-adi`（§6） | transfer、read_block、write_block。max_length は必ず出す | — |
| `oep.target.console`（[コンソール](../interfaces/oep-if-console.ja.md)） | §1 の op。describe の mechanisms は必ず出す。mechanism 1 か 2 を持てば write を送りの列で受ける（§2）。§3 の読みの順（要求の実行中と hart が止まっている間は読まない、要求の後は DMSTATUS を先に読む）。方式 2 の枠は [dmseq](../interfaces/target-console-dmseq.ja.md) のとおり | どの方式か（describe の mechanisms） |
| `oep.fixture.gpio`（[fixture](../interfaces/oep-if-fixture.ja.md) §1） | set、read。describe の modes に mode 0 | 出力の強さ（§1.1） |
| `oep.fixture.uart`（§2） | §2 の op。describe の formats に 8N1 | ほかの format |
| `oep.fixture.i2c-target`（§3） | stretch を除く §3 の op（書き込み 1 回が 1 フレーム、読み出しは preload_tx の置き場から） | stretch（ops、max_stretch_us とともに）。プルアップ（features bit2） |
| `oep.fixture.spi-target`（§4） | §4 の op。MISO をソフトウェアで駆動するなら cs_setup_ns | LSB first（features bit0） |
| `oep.fixture.logic`、`oep.fixture.analog`（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1〜§3） | query と force を除く §3.2 の op。§3.5 の describe。calibration はアナログだけ | query、force（ops）。通知: subscribe / unsubscribe（ops） |
| `oep.fixture.capture-group`（§4） | force を除く §4.1 の op。§4.3 の describe | force（ops）。通知: subscribe / unsubscribe（ops） |
| `oep.probe.plan`（[plan](../interfaces/oep-if-plan.ja.md)） | plan の役割を持つインターフェースがあれば list に出す。plan_apply（fn ごとに不可分）、plan_release、§2.5 の断り方、設定の plan。上限があれば describe の plan_roles | — |
| `oep.probe.restart`（[再起動](../interfaces/oep-if-restart.ja.md)） | restart。describe の restart_max_ms。ロックの要る op として断る。答えは completed success で、それを先に送る。答えの後は再起動するまでどの transport の要求にも答えず、target を reset しない。再起動の後は電源を入れたときと同じ（新しい boot_id、保存した設定だけが残る）。答えが transport を出てから restart_max_ms のうちに、同じ transport で confirm にまた答える | — |
| `oep.probe.link`（[リンク](../interfaces/oep-if-link.ja.md)） | source、sink | port_speed（ops）: その状態と戻る条件（§3） |
| `oep.probe.config`（[probe の設定](../interfaces/oep-if-probe-config.ja.md)） | 設定を扱う probe だけが list に出す。get、set、unset、state。設定が変われば変わる hash。起動時に disable と idle を先に掛ける。§4 の describe | save / erase（ops、storage の tag とともに。無ければ unknown_operation）。slot。bind |

## 4. 確かめ方

**試験のベクタ**（[`tests/vectors/`](../tests/vectors/)）。`tools/oepvectors1.py` が規範の文書から計算する。ベクタと文書が
食い違えば文書が正しく、ベクタを直す。扱う範囲:

| ファイル | 扱うもの |
|---|---|
| `checks.json` | CRC-16（transports §1）、dmseq の CRC-8 |
| `cobs.json` | COBS の符号とシリアルの口のフレーム全体。復号が受け入れるもう一つの形も含む（transports §1） |
| `headers.json` | 要求と答えのヘッダ、TLV の符号（§2.2、§4.1、§4.2） |
| `confirm.json` | confirm のやりとり（§7.1） |
| `discovery.json` | list（§7.2。fn 0 を載せないので、インターフェースの無い例の probe では空）、fn 0 の describe（§7.3、§7.5）、終わりを越えた describe、ヘッダの断り unknown_function / unknown_operation（§4.3 の順 1） |
| `refusals.json` | §2.3 と §4.3 の断り方（理由が 1 つだけ当たる状態）と、無視される知らない TLV について、要求とそのとおりの答え。§4.3 の順 4 で理由が 2 つ以上当たる要求は、どれで断ってもよいので（意図した単純化）、ベクタは持たず、試験はどれか 1 つを受ける |
| `sessions.json` | セッションの場面: 判定の表（§6.2）、送り直しの表（§5.2。送り直した end）、end での解放と no_session（§9）、force、session_id 0（§4.1）、セッションが無いときと開いているときの clock（§7.7）。決めた初めの状態から順に送る要求と答え |
| `ops_encoding.json` | describe の共通の tag ops の値の境（最短、最長、長さの誤り、op 0xFF の境、同じ集合の別の符号）と、正しい値が表す op の集合（§7.4） |
| `ops.json` | op ごとのバイト列: 要求、それが前提とする probe の状態、答え（`oep.probe.restart`、`oep.probe.plan`、`oep.probe.link`、gpio、rvswd、riscv-dm、console、probe.config、logic の一部）。並びの答えは要素の長さ無しの `count × 要素`（§2.3） |

実装は JSON を読み、自分の符号器、復号器、答えをバイト単位で比べる。ベクタが文書と registry に合っているかを確かめるには:

```sh
python3 tools/oepvectors1.py --check      # 規則が与えるものとファイルが違えば exit 1
cd tests && uv run pytest vectors          # 別のコード（binascii）でのベクタの確認と、tool の --check
```

**host のための偽の probe。** [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python) は、この仕様のとおりに答える
probe を pty（シリアルの口）か TCP（どちらのフレームでも）で出す。再送と回復を試すための故障（答えを落とす、CRC を壊す、雑音）も入れられる:

```sh
python -m oep_client.fake_serve --pty     # 最初の行が開く先。profile と故障は --help
```

**probe を見る。** 同じパッケージの `oep dump --port <port>` が、すべてのインターフェースの list と describe を見せる。そのクライアントの
試験も、ベクタを自分のコードと偽の probe に対して確かめる。

**まだ扱っていないもの。** probe のための自動の適合試験は無い。ベクタが扱うのは符号、一部の断り方、いちばん小さな probe の発見、セッションの場面、一部の op
で、ページ送りの続き、plan の取り合い、インターフェースの多くの op と状態の移り変わりはまだ扱わない。TCP の流れを任意の所で分けたりまとめたりした受け取り、複数の TCP の接続とセッション / ロックの取り合い、経路ごとに違う max_frame、中継のブローカーを通した restart も、共有の道具では確かめていない（偽の probe と実機の試験で確かめる）。時間（待ち、lease、max_op_ms、フレームの途切れ、port_speed の戻る条件）は共有の道具では確かめていない。電気的な規則（idle の状態、wire が答えない間の線、cs_setup_ns）と実機での
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
