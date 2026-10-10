# OEP v1 への適合

状態: **ガイド**（規範ではない）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。規則を足さない。各行は規則を持つ規範の文書を指し、この文書と規範の文書が食い違えば規範の文書が
正しい。答える問いは一つ: probe と host が OEP v1 に適合するには何をするか、実装者はそれをどう確かめるか。
適合の条項そのものは [core](oep-core.ja.md) §1.2 である。

## 適合検査の3段階

仕様を先に定め、それから独立した検査を作る。コアを固めた後に共通インターフェース契約、標準 OEP インターフェース固有契約を固め、実装の追従は別段階で行う。

| 段階 | 適用対象 | 検査するもの |
|---|---|---|
| コア準拠 | OEP を話す全端点と host | transport/framing、見出し、拒否の順序、TLV の拡張規則、session、再送、時刻、資源の所有・寿命。本書 §1/§2 |
| インターフェース準拠 | 標準・独自の全インターフェース | 名前/revision/instance、describe/ops、宣言と状態の分離、適用される共通のページング・資源・購読・通知規則。core §7/§9/§11/§13 と [common](../interfaces/oep-if-common.ja.md) |
| OEPインターフェース固有準拠 | その標準インターフェースを実装する端点 | 各 op の payload、動作、副作用、競合、時間上限、拒否と failed/partial、異常系。本書 §3 と各規範 |

最初の2段階は独自拡張にも使う。3段階目は、規範の条項から「初期状態 → 要求 → 応答 → 観測可能な副作用 → 後始末」の検査を作り、独自拡張の試験にも使える雛形として保守する。固有の op や配線は adapter が与え、共通の合否条件へ実装固有の期待値を混ぜない。

結果には段階、条項、case ID、実行範囲、SPEC commit/tag、registry hash、実装版、transport、個体、条件、要求/応答と観測を残す。PASS は実行した case の成功であり、全準拠の意味にはしない。未検査、適用外、設備不足、前提失敗で実行できなかった項目を分ける。仕様違反、設定不備、実装未追従を設備不足として skip しない。

コアを確定する前に、少なくとも次を独立に検査できる形にする。ベクタの自己整合、仮想端点の動作、実機の動作、電気的な観測は別の証拠である。

| コアの契約 | 正常・境界・異常の検査 |
|---|---|
| framing/transport | 分割・結合、CRC/COBS/count/length破損、frame gap、過大frame、TCP切断・再接続、未知role/待っていないcorr、複数経路の独立性 |
| confirm/discovery | confirm前の64byte、revision範囲の境界、frame/window/inflight、transport照合、list/describeの末尾・ページ進行・不変性・必須宣言 |
| 見出し・拒否・TLV | 短い要求の無応答、corr 0、未知fn/op、session_required、拒否優先順、長さ/値域、未知非critical/critical、ID 0、0x7F、応答の補助情報 |
| session | lease最小/最大/既定、keepalive、owner、他IDとの排他、end/期限切れ/force、session 0の無副作用、boot_idの変化 |
| 再送 | openを含む同一要求の結果、内容の違う同corrの拒否、cache eviction/保持サイズ上限とresult_lost、rejectedの保持、同ID open後の履歴、終了後の履歴、重複によるlease/通知の変更禁止 |
| corrと寿命 | u16半周を越える増加、65535での終了と新IDへの移行、旧経路の未解決応答、資源IDの非再利用/枯渇、終了時の解放、古いIDと他種/他fnのIDの拒否 |

実機でも端点の状態変更を独立に観測する。二重実行の検査は、同じ応答が返るだけでなく、時計・資源・通知などの副作用が重複しないことを確かめる。資源を作る方法はインターフェース adapter に依存しても、その所有・解放・非再利用の合否はコアの契約で決める。

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
- TCP で待ち受けて自分を広告するなら、DNS-SD の `_oep._tcp` を mDNS で広告し、TXT に `unit_id=<unit_id>` を載せる（port は SRV、transports §3）。
- USB: probe が選べる口では シリアル番号 = unit_id（transports §3）。vendor bulk と HID は transports §3 の形で、それぞれ一つまで。
- 自分で OEP の要求に答える端点は、後ろに何があっても probe である。中継する broker は transports §1 と core §5.2 に従う（probe への transport が無くなったら終わることを含む）。

**メッセージ、断り方、TLV**

- 要求と答えのヘッダ（§4.1、§4.2）。要求一つに答え一つ、来た transport へ、来た順に（§4.2、§4.4）。
- rejected は受け付けなかったものだけ。受け付けて失敗したものは completed failed / partial（§4.2）。
- 断りの順序: 見出し、送り直しの表、セッションの順。それ以外は何も変える前にすべて確かめ、当てはまる理由のどれか 1 つで断る（§4.3）。
  payload は §4.3 のとおり（unavailable の TLV、unsupported の tag）。
- role が要求の role でないメッセージと、10 バイトのヘッダより短い要求は、答えずに捨てる（§2.4）。ロックが要る op で session_id 0: session_required（§4.1）。
- fn 0 とすべての fn の describe は ops（0x07）を載せる: 必須の op はすべて立て、任意の op は持つときに限り立てる（§1.2、§7.4）。ops に立っていない op は unknown_operation、probe が持つ op の任意の機能は unsupported（§1.2）。インターフェースの表の op は、文書が任意と書かない限り必須。
- ops の値は base と 1 byte 以上の bitmap で、`base + 8 × bitmap の byte 数 ≤ 256`（§7.4）。
- 要求の TLV: 知らない critical TLV は unsupported、知らない非 critical TLV は無視する。実装する TLV は bit 7 によらず、長さが定義と違えば malformed、
  扱わない値は unsupported（§2.2、§2.3）。
- TLV の形は `tag len(u16) value` の一つ（§2.2）。並びは要素の長さを持たない `count × element`、固定の形はどれも定義のとおりで、末尾を延ばさない（§2.3）。
- window / max_inflight は transport ごと（§4.4）。
- 一周する値: 1 つの空間で同時に持つ値の広がりは幅の 4 分の 1 未満（§2.6）。

**セッションとロック**

- ロックは一つ、§6.2 の判定表、lease の再開始と実行中は数えないこと（§6.1）。
- open / end / keepalive / lock_state / force / owner（§6.4）。lease は 1000〜60000 ms に丸める（§6.4）。session_id 0 は断る（§6.1）。
- 再送の表: 少なくとも max_inflight 件、rejected の答えも覚える、異なる ID の新規 open が成功したときだけ置き換える。同じ ID の open は履歴を保つ、probe に一つ（§5.2）。
- ロック不要の op は状態を変えない（§6.3）。boot_id は起動のたびに変わるように、§6.5 の素をその順に使って選ぶ（§6.5）。
- 時計: 起動からの ns で、同じ boot_id の間、減らず一周しない（§2.6a）。
- セッションが作ったものはすべて、そのロックが終わるとき end、期限切れ、force のどれでも同じに解放し、再送された open では残す（§9）。再開は無い（§6.4）。資源の番号（1〜65535、起動後の最初は 1、0 は割り当てない、§9）。閉じたコンソールの stream とバッファは解放し、番号は同じ boot_id の間に再利用しない（コンソール §2）。

**fn 0（本体。名前を持たず、list に載らない）**

- 必須の op: core §12 の行（confirm、list、describe、clock、open、end、keepalive、lock_state）。
- confirm: revision の選び方、transport TLV、扱える範囲つきの断り。max_frame は 64 以上、window は max_frame 以上、
  max_inflight は 1 以上（§7.1）。
- list: fn 0 を載せない、instance の番号、boot_id が同じ間は答えが変わらない、first が total 以上なら total と count 0（§7.2）。
- describe: ページ送り、first が数以上なら more 0 だけで TLV 無し、宣言だけで boot_id が同じ間は変わらない（§7.3）。経路によらないので、各 TLV は応答の見出し 5 byte と more 1 byte を足しても、max_length はその op の要求と応答で、probe のどの経路の max_frame にも収まる（§7.3、§7.4）。
- clock: boot_id と uptime_ns（要求を受けてから応答を送るまでの間に読んだ時計）。ロック不要で、session_id 0 ならセッションが無くても、ほかのセッションが
  ロックを持っていても答え、セッション、ロック、lease に触れない。broker 自身の OEP 端点も同じ契約を実装する（§7.7、transports §1）。
- fn 0 の describe の必須の tag: unit_id、transport（transport ごとに一つ、interface の欄は §7.5 のとおり）、channel を持つなら channels（番号は 0〜channels − 1）、max_op_ms（1〜
  `max_op_ms_max`）（§1.2、§7.5）。unit_id の一意性と不変性、transport の index の不変性（§7.5）。
- channel: 解放したピンは空きの状態へ、起動したら最初の答えの前に自分で使う channel を除くすべての channel を空きの状態へ、ピンを取ってもピンは変わらない、資源の取り合いは何も変えずに断る（§8、§8.1）。
- 通知（送り出すインターフェースがあれば）: その fn の subscribe（0x01）/ unsubscribe（0x02）を ops に立てる、送り出さない fn は持たない、seq、データだけをまとめ出来事は先の答えの後すぐ送る、答えを先に送ることと溜める量の上限（§11.2〜§11.4）。
**時間の上限**（値は `registry/oep-v1.toml`）

- `probe_frame_gap_ms`（transports §2）。宣言した max_op_ms より長い要求はなく、超えうる op は断る（§7.5）。lease の範囲
  （§6.4）。port_speed の verify_ms、`port_speed_idle_ms` と戻る条件（[リンク](../interfaces/oep-if-link.ja.md) §3）。attach、scan、riscv-dm の reset は max_op_ms のうちに答える
  （[線とデバッグ](../interfaces/oep-if-debug.ja.md) §1、§3、§4.3）。同じ transport で confirm にまた答えるまでの、宣言した restart_max_ms（[再起動](../interfaces/oep-if-restart.ja.md) §1、§2）。

## 2. host のチェックリスト

- **フレーム**: フレームは何回の書き込みに分けても、ほかのフレームとまとめてもよく、受ける側はその区切りに頼らない。TCP 以外では、送るフレームの途中で `probe_frame_gap_ms` 止めない（transports §2）。COBS の受け方（transports §1）。confirm の答えの前は
  64 バイトを超えて送らず、後は max_frame を超えて送らず、65535 バイトまで受けられる（transports §3）。vendor bulk の長さ 0 の転送（transports §1）。
- **見つけ方**: USB の自動識別は project の VID:PID `1209:4F45` だけ、名指しの probe は unit_id で、それ以外は
  利用者が選ぶ（transports §3）。TCP の接続先は `_oep._tcp` で見つけたものか利用者が明示したものだけで、TXT の unit_id は describe で確かめる（transports §3）。試し方の規則: confirm だけを送り、正しい答えがなければ閉じる（transports §3）。OEP の probe と分かった機器の中の口の選び方（transports §3）。
  transport を試す順（transports §3）。排他で開く（transports §3）。DTR / RTS を立てる（transports §4）。
- **confirm と revision**: 扱える範囲を送り、その後は使っている revision を `min_rev = max_rev` で送る（§7.1）。revision を知らない
  インターフェースは使わない（§2.7）。
- **待ち**: すべての要求に §4.4 の下限、自分のリンクの要求も含む。UART ブリッジでの転送時間、その transport での最初の confirm の
  答えまでは `min_max_frame` で（§4.4）。attach、scan、riscv-dm の reset の引数の時間は max_op_ms（[線とデバッグ](../interfaces/oep-if-debug.ja.md) §1、§4.3）。
- **再送と回復**: 送り直しは同じ corr で（§5.2）。corr は session_id ごとに増やし、0 を使わず、一周させない（§4.1）。TCP の区切り破損は再接続、vendor bulk / HID の再同期では最後に書いてから `probe_frame_gap_ms` より長く待つこと（transports §5）。再送にも答えが無ければその transport は失敗した: そこで何かを送る前に、transports §5 の手順で立て直すか開き直し、状態を変える要求を繰り返す前に状態を読む（§5.2）。
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
- **Wi-Fi の passphrase**: 表示せず、ログに書かない。get の pass_len 0xFF は「ある」の印で、送り返せば今のものを保つ（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §1.4）。
- **ロジックのキャプチャ**: layout の w は 1〜128 のどの整数も読む。w が 8 の倍数でなければサンプルはバイトの境目をまたぐ（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.1）。
- **multirate**（[キャプチャ](../interfaces/oep-if-capture.ja.md) §5）: 使うときは multirate の TLV に critical の bit を付けて送り（0xE0。キャプチャのほかの要求の TLV は付けない）、壊れた宣言（min_d < 2 など、§5.1）は使わず、応答の layout と block で区画ごとに block の格子を区画の base sample 0 から切って読む。数（samples、trigger_index など）は base sample。
- **アナログのキャプチャ**: host が電圧を示すときは、値 0 と 2^b − 1 を電圧ではなく振り切れ（低い端以下、高い端以上）として示す
  （[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.2 規則 6）。

## 3. 名前が `oep.` で始まるインターフェース

`oep.` の名前を list に出す probe は、そのインターフェースの文書全体に従う。必須のものの短い一覧:

| インターフェース | 必須 | 任意（宣言するもの） |
|---|---|---|
| 位置つきのストリーム（[共通部品](../interfaces/oep-if-common.ja.md) §1） | それを使う各インターフェースで §1 の read、marks（§1.3 の通し番号のページング: from_serial を含む、押し出されていれば一番古いものから、next なら空）、clear、mark、write。§3 の status の値 | — |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`（[線とデバッグ](../interfaces/oep-if-debug.ja.md)） | attach（pins、max_speed 必須）、detach、connections。資源はセッション所有。暗黙の join / eviction をしない。§1 の attach の規範と max_op_ms。§2 の再試行と寿命 | scan（候補 count ≥ 1、有限探索）、attach の reset TLV |
| `oep.target.riscv-dm`（§4） | dmi、halt、resume | reset、read_block / write_block、run、step: ops。reset があれば、ndmreset を解いた後に DM を待つ（§4.3、max_op_ms のうち）。read_block / write_block があれば max_length。自分の op で使った DATA0 / DATA1 を戻す（§4）。step が ok でなければ moved と dpc を 0、run の elapsed_us は resumereq から（§4.2、§4.4） |
| `oep.target.arm-adi`（§6） | transfer（n = 0 は success、ack 0）、read_block、write_block。max_length は必ず出す | — |
| `oep.target.console`（[コンソール](../interfaces/oep-if-console.ja.md)） | §1 の op。describe の mechanisms は必ず出す。mechanism 1 か 2 を持てば write を送りの列で受ける（§2）。§3 の読みの順（要求の実行中と hart が止まっている間は読まない、要求の後は DMSTATUS を先に読む）。方式 2 の枠は [dmseq](../interfaces/target-console-dmseq.ja.md) のとおり | どの方式か（describe の mechanisms） |
| `oep.fixture.gpio`（[fixture](../interfaces/oep-if-fixture.ja.md) §1） | set、read。describe の modes に mode 0 | 出力の強さ（§1.1） |
| `oep.fixture.uart`（§2） | §2 の op。describe の formats に 8N1 | ほかの format |
| `oep.fixture.i2c-target`（§3） | stretch を除く §3 の op（書き込み 1 回が 1 フレーム、読み出しは preload_tx の置き場から、ns はフレームを終えた STOP か次の START の時刻） | stretch（ops、max_stretch_us とともに）。プルアップ（features bit2） |
| `oep.fixture.spi-target`（§4） | §4 の op。data のビットの置き方（バイトの途中で終わった転送も、来なかったビットは 0）、bits は 0xFFFFFFFF で止める、ns は CS が無効になった時刻。MISO をソフトウェアで駆動するなら cs_setup_ns | LSB first（features bit0） |
| `oep.fixture.logic`、`oep.fixture.analog`（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1〜§3） | query と force を除く §3.2 の op。§3.3 の configure と query の契約（mode と rate は必須、mode ごとに送れる TLV、type 0 の trigger の role は見ない、0 の samples / segments / rate は malformed、mode 3 の pretrigger は max_pretrigger で縛る、挙げていない値は unsupported、応答の必須の行）。区画の通し番号のページング（[共通部品](../interfaces/oep-if-common.ja.md) §1.3）。出来事の世代、世代は 0 を飛ばして一周。区画を連続に保てなければその区画を出さず、エラーで止まる（§2.2。隙間は置き場が無くて区画を丸ごと取らないときだけ、state 6 に入るときは必ず stopped reason 3、エラーの後の write_pos はその区画の先頭）。host はエラーの後、受けたデータの write_pos から先を捨てる。§3.5 の describe。calibration はアナログだけ | query、force（ops）。通知: subscribe / unsubscribe（ops）。ロジックの multirate（§5。describe の multirate: 方針、d の範囲。宣言すれば §5 の断り、L の倍数の samples、block の layout、base sample での数え方とトリガ） |
| `oep.fixture.capture-group`（§4） | force を除く §4.1 の op（start の応答は組の世代と、bind の順の各トラックの世代）。組の pretrigger は trigger_track のものを時間として全トラックが残す（P_k）、持てなければ bind を断る。出来事の組の世代。トラックがエラーで止まれば組の stopped は reason 3 とその error、ほかのトラックは stop と同じに止まる。§4.3 の describe | force（ops）。通知: subscribe / unsubscribe（ops） |
| `oep.probe.plan`（[plan](../interfaces/oep-if-plan.ja.md)） | plan の役割を持つインターフェースがあれば list に出す。plan_apply（fn ごとに不可分）、plan_release、§2.5 の断り方、設定の plan は preset。上限があれば describe の plan_roles | — |
| `oep.probe.restart`（[再起動](../interfaces/oep-if-restart.ja.md)） | restart。describe の restart_max_ms。ロックの要る op として断る。答えは completed success で、それを先に送る。答えの後は再起動するまでどの transport の要求にも答えず、target を reset しない。再起動の後は電源を入れたときと同じ（新しい boot_id、保存した設定だけが残る）。答えが transport を出てから restart_max_ms のうちに、同じ transport で confirm にまた答える | — |
| `oep.probe.link`（[リンク](../interfaces/oep-if-link.ja.md)） | source、sink | port_speed（ops）: その状態と戻る条件（§3） |
| `oep.probe.config`（[probe の設定](../interfaces/oep-if-probe-config.ja.md)） | 設定を扱う probe だけが list に出す。get、set、unset、state。設定が変われば変わる hash。起動時に disable と idle を先に掛ける。§4 の describe | save / erase（ops、storage の tag とともに。無ければ unknown_operation）。slot（配線の preset）。wifi（describe の wifi_max、どの経路でも max_frame 112 以上、state の wifi の TLV、index の順に試す、passphrase は書くだけで hash もそれから作らない、§1.4） |

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
| `ops.json` | op ごとのバイト列: 要求、それが前提とする probe の状態、答え（`oep.probe.restart`、`oep.probe.plan`、`oep.probe.link`、gpio、rvswd、riscv-dm、console（marks の通し番号のページング、streams の最後のページ）、logic（configure の契約、即時の trigger の role を見ない query、samples 0 の malformed、segments の空のページ、区画の中で落としたときの status / segments / read と stopped、ストリーミングで落とした区画に入りかけたデータのフレーム（`data`）とその後の status、multirate の describe、configure / query と断り、segments、capture-group の bind）、riscv-dm の失敗した step、arm-adi の n = 0 の transfer、spi-target の部分の byte（MSB / LSB が先）、capture-group の start と組の pretrigger を持てないトラックの bind、キャプチャの出来事のフレーム（`events`、世代）、probe.config（wifi の set（いちばん長い 112 byte のものを含む）/ get / unset と state を含む）、logic のほかの一部）。並びの答えは要素の長さ無しの `count × 要素`（§2.3） |
| `logic_layout.json` | ロジックのキャプチャのストリーム（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.1）: layout の w と pos、チャネルのレベル、区画のバイト列。2 の冪でない w（w = 3、サンプルがバイトをまたぐ） |
| `multirate.json` | multirate のストリーム（[キャプチャ](../interfaces/oep-if-capture.ja.md) §5）: 役割ごとの multirate の TLV、layout と L、区画ごとの base sample のレベルとバイト列。§5.7 の例、L·w が 8 の倍数でない、w = 3、D = 1 のチャネルが無い、縮約のチャネルがバイトをまたぐ、phase のある sample の最後の block、any_active の active-high、edge_latch（区間の最初の立ち上がり、区間全体、block の境目をまたぐ、base sample 0）、pretrigger で短い最初の区画と次の区画 |

実装は JSON を読み、自分の符号器、復号器、答えをバイト単位で比べる。ベクタが文書と registry に合っているかを確かめるには:

```sh
python3 tools/oepvectors1.py --check      # 規則が与えるものとファイルが違えば exit 1
cd tests && uv run pytest vectors          # 別のコード（binascii）でのベクタの確認と、tool の --check
```

host は独立した仮想ベンチと実機の両方に対して試験し、probe は独立した host で list、describe と各 op を検査する。具体的な tool と起動方法は、それを提供する実装リポジトリに置く。

共有ベクタは、そのファイルが挙げる符号と場面だけを検査し、適合全体を証明しない。各実装は §1〜§3 の全項目について、状態遷移、競合、再送、時間条件を自身のリポジトリで試験する。電気的な規則と実機でしか生じない条件は、対応する hardware で確認する。

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
