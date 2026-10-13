# OEP v1 への適合

状態: **ガイド**（規範ではない）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。規則を足さない。各行は規則を持つ規範の文書を指し、この文書と規範の文書が食い違えば規範の文書が
正しい。答える問いは一つ: probe と host が OEP v1 に適合するには何をするか、実装者はそれをどう確かめるか。
適合の条項そのものは [core](oep-core.ja.md) §1.2 である。

## 適合検査の3段階

仕様を先に定め、それから独立した検査を作る。コアを固めた後に共通インターフェース契約、標準 OEP インターフェース固有契約を固め、実装の追従は別段階で行う。

| 段階 | 適用対象 | 検査するもの |
|---|---|---|
| コア準拠 | OEP を話す全端点と host | transport/framing、見出し、拒否の順序、TLV の拡張規則、session、再送、時刻、資源の所有・寿命。本書 §1/§2 |
| インターフェース準拠 | 標準・独自の全インターフェース | 名前/revision/instance、describe/ops、宣言と状態の分離、適用される共通のページング・資源・購読・通知規則。core §7/§9/§10/§12 と [common](../interfaces/oep-if-common.ja.md) |
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
| 再送 | openを含む保持した同一要求の結果、保持した要求と内容の違う同corrの拒否、0件cache/eviction/保持サイズ上限とresult_lost、rejectedでも進む順序状態、同ID open後の履歴、終了後の履歴、重複によるlease/通知の変更禁止 |
| corrと寿命 | u16循環/zero飛ばし、半周の境界、未解決要求の前進制限、セッション間の旧応答排出、再接続時のqueue破棄、旧経路の未解決応答、資源IDの非再利用/枯渇、終了時の解放、古いIDと他種/非対応の作成元のIDの拒否、定義されたfn間の資源利用 |

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
- 自分で OEP の要求に答える端点は、後ろに何があっても probe である。中継する broker は transports §1 と core §5.1 に従う（probe への transport が無くなったら終わることを含む）。

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
- 要求が収まっても固定結果がmax_frameへ収まらなければ、実行前にunsupportedで断る。短縮/prefix/ページングは個別の定義に従う（§4.4）。
- 一周する値: corr以外の1つの空間で同時に持つ値の広がりは幅の4分の1未満（§2.6）。corrは§4.1/§5.1の半周規則。

**セッションとロック**

- ロックは一つ、§6.2 の判定表、lease の再開始と実行中は数えないこと（§6.1）。
- open / end / keepalive / lock_state / force / owner（§6.4）。lease は 1000〜60000 ms に丸める（§6.4）。session_id 0 は断る（§6.1）。
- 再送の順序状態は必須、byte記録は0件でもよい。rejectedの新規要求も最後のcorrを更新し、記録が無い旧要求はresult_lostで断る。
  異なるIDの新規openが成功したときだけ順序状態を置き換える。同じIDのopenは履歴を保つ、probeに一つ（§5.1）。
- ロック不要の op は状態を変えない（§6.3）。boot_id は起動のたびに変わるように選ぶ（§6.5）。生成方法の優先順位は要求しない。
- 時計: 起動からの ns で、同じ boot_id の間、減らず一周しない（§2.7）。
- セッションが作ったものはすべて、そのロックが終わるとき end、期限切れ、force のどれでも同じに解放し、再送された open では残す（§9）。再開は無い（§6.4）。資源の番号（u32、1〜0xFFFFFFFF、起動後の最初は 1、0 は割り当てない、§9）。閉じたコンソールの stream とバッファは解放し、番号は同じ boot_id の間に再利用しない（コンソール §2）。

**fn 0（本体。名前を持たず、list に載らない）**

- 必須の op: core §11 の行（confirm、list、describe、clock、open、end、keepalive、lock_state）。
- confirm: revision の選び方、transport TLV、扱える範囲つきの断り。max_frame は 64 以上、window は max_frame 以上、
  max_inflight は 1 以上（§7.1）。
- list: fn 0 を載せない、(name, revision)内のinstanceの一意性と欠番、fn順からの独立、boot_id が同じ間は答えが変わらない、first が total 以上なら total と count 0（§7.2）。製品のfirmware更新をまたぐinstance維持は、保存した組を新しいlistで解決して確認する。
- describe: ページ送り、first が数以上なら more 0 だけで TLV 無し、宣言だけで boot_id が同じ間は変わらない（§7.3）。各TLVは応答の見出し5byteとmore 1byteを足しても全経路のframeへ収める。
  max_lengthは機能上限として扱い、実際の要求・結果はその経路へ収める。分割できない外部RXの宣言値には個別操作の全経路条件も適用する（§7.3、§7.4）。
- clock: boot_id と uptime_ns（要求を受けてから応答を送るまでの間に読んだ時計）。ロック不要で、session_id 0 ならセッションが無くても、ほかのセッションが
  ロックを持っていても答え、セッション、ロック、lease に触れない。broker 自身の OEP 端点も同じ契約を実装する（§7.6、transports §1）。
- fn 0 の describe の必須の tag: unit_id、transport（transport ごとに一つ、interface の欄は §7.5 のとおり）、channel を持つなら channels（番号は 0〜channels − 1）、max_op_ms（1〜
  `max_op_ms_max`）（§1.2、§7.5）。unit_id の一意性と不変性、transport の index の不変性（§7.5）。
- channel: 解放したピンは空きの状態へ、起動したら最初の答えの前に自分で使う channel と設定が使用・設定を禁止する channel を除くすべての channel を空きの状態へ。
  ピンを取ってもピンは変わらない。出力idleの取得はインターフェースが明記する場合だけ許す（それ以外はcause 5）。同時使用の資源・処理能力不足は何も変えずにcause 2で断る（ピンの取り合いはcause 1。§8、§8.1）。
- 通知（送り出すインターフェースがあれば）: その fn の subscribe（0x01）/ unsubscribe（0x02）を ops に立てる、送り出さない fn は持たない、seq、データだけをまとめ出来事は先の答えの後すぐ送る、答えを先に送ることと溜める量の上限（§10.2〜§10.4）。
- 購読の保持量不足はunavailable cause2で断り、以前の購読の条件・送り先・seqを保つ。通知保持量の上限を必須queue容量として扱わず、送り始めたframeには別frameを挟まない（§10.3〜§10.4）。
- 購読の置換/解除では旧購読の未送信通知を捨て、送り始めたframeは同じ経路への操作の応答前に完了する。別経路の応答は待たず、閉じた経路の残りを新経路へ持ち越さない（§10.3〜§10.4、transports §3）。
**時間の上限**（値は `registry/oep-v1.toml`）

- fn 0 の keepalive / lock_state / clock は、要求全体を min(max_op_ms, core_quick_op_max_ms) 内で処理する。
  hostの再送待ちはこの上限 + host_wait_add_ms + 転送の時間。open / endにはmax_op_msを使う（§4.4）。

- `probe_frame_gap_ms`（transports §2）。宣言した max_op_ms より長い要求はなく、超えうる op は断る（§7.5）。lease の範囲
  （§6.4）。port_speed の verify_ms、`port_speed_idle_ms` と戻る条件（[リンク](../interfaces/oep-if-link.ja.md) §3）。attach、scan、riscv-dm の reset は max_op_ms のうちに答える
  （[線とデバッグ](../interfaces/oep-if-debug.ja.md) §1、§3、§4.3）。Probe内部の再起動・初期化までのrestart_max_ms（OSの列挙や外部のネットワーク接続は除く）（[再起動](../interfaces/oep-if-restart.ja.md) §1、§2）。

## 2. host のチェックリスト

- **フレーム**: フレームは何回の書き込みに分けても、ほかのフレームとまとめてもよく、受ける側はその区切りに頼らない。TCP 以外では、送るフレームの途中で `probe_frame_gap_ms` 止めない（transports §2）。COBS の受け方（transports §1）。confirm の答えの前は
  64 バイトを超えて送らず、後は max_frame を超えて送らず、65535 バイトまで受けられる（transports §3）。vendor bulk の長さ 0 の転送（transports §1）。
- **見つけ方**: USB の自動識別は project の VID:PID `1209:4F45` だけ、名指しの probe は unit_id で、それ以外は
  利用者が選ぶ（transports §3）。TCP の接続先は `_oep._tcp` で見つけたものか利用者が明示したものだけで、TXT の unit_id は describe で確かめる（transports §3）。試し方の規則: confirm だけを送り、正しい答えがなければ閉じる（transports §3）。OEP の probe と分かった機器の中の口の選び方（transports §3）。
  transport を試す順（transports §3）。排他で開く（transports §3）。DTR / RTS を立てる（transports §4）。
- **confirm と revision**: 扱える範囲を送り、その後は使っている revision を `min_rev = max_rev` で送る（§7.1）。revision を知らない
  インターフェースは使わない（§2.8）。
- **待ち**: すべての要求に §4.4 の下限、自分のリンクの要求も含む。UART ブリッジでの転送時間、その transport での最初の confirm の
  答えまでは `min_max_frame` で（§4.4）。状態変更前にmax_op_msを取得し、操作が要求全体の短い上限を定めない限りmax_op_msを使う。
  DMIの明示的な待ちの和やrunのtimeout_msだけで内部再試行・準備・後始末の時間を省かない（§4.4）。
- **再送と回復**: 送り直しは同じ corr で（§5.1）。corr は session_id ごとに循環して前進し、0 を使わず、未解決要求との距離を半周未満に保つ（§4.1）。TCP の区切り破損は再接続、vendor bulk / HID の再同期では最後に書いてから `probe_frame_gap_ms` より長く待つこと（transports §5）。再送にも答えが無ければその transport は失敗した: そこで何かを送る前に、transports §5 の手順で立て直すか開き直し、状態を変える要求を繰り返す前に状態を読む（§5.1）。
- **セッション**: 0 でない乱数の session_id（§6.1）。答えの lease_ms が正で、keepalive が延ばす（§6.4）。no_session /
  locked への対応（§4.3、§6.2）。no_session の後は新しいセッションを開いて設定し直す。boot_id が（confirm でも open でも）変われば自分の状態は無効で、
  list し直す（§6.5）。一つのセッションの要求は一つの transport で（transports §3）。セッションの要らないロック不要の要求は session_id 0 で（§4.1）。
- **probe の時刻**: probe の時刻を自分の時刻に写すときは clock で読み、送った時と受けた時の中点に当て、不確かさを往復の半分とする（[host 開発ガイド](host-development-guide.ja.md) §12）。
- **答えの読み方**: role が要求の role のメッセージは捨てる。5 バイトより短い答えと、ヘッダより短い出来事やデータのフレームは
  壊れたフレーム（§2.4）。知らない TLV と tag を飛ばす、繰り返された tag は最初を使う、0 でない真偽値は真と読む（§2.1、§2.3）。知らない
  値は §2.4 のとおり。role と corr で振り分ける（§10.1）。効かなければ意味が無いか害のある TLV には
  critical の印を付ける（§2.3）。
- **文字列**: 答えの文字を見せる前に制御文字と不正な UTF-8 を置き換える（§2.1）。unit_id とシリアル番号、unit_id どうしは ASCII の
  大文字小文字を区別せず比べる（transports §3）。`x-` の unit_id でまとめたり、名指したり、何かを覚えるキーにしたりしない（§7.5）。iProduct と
  インターフェースの文字列は表示だけ（transports §3）。
- **restart**（`oep.probe.restart`）: 答えの後は、probe が新しい起動で confirm に答えるまで何も答えないものとして扱い、新しく開くのと同じに開き直して boot_id で確かめる（[再起動](../interfaces/oep-if-restart.ja.md) §2。手順は [host 開発ガイド](host-development-guide.ja.md) §5.2）。UART bridge では起動時の速さに戻す（[リンク](../interfaces/oep-if-link.ja.md) §3 の host 2）。
- **port_speed**: host が使うときは [リンク](../interfaces/oep-if-link.ja.md) §3 の host 1 と 2（試すの答えの後 `port_speed_switch_wait_ms` 以上待ってから新しい速さで送る、戻す・end・異なるsession_idへのforce open・再起動するopの成功応答で起動時の速さに戻る）。対応Hostは必要なframe/処理時間も含めて復帰待ちを決める。全Hostへ4秒待ちを要求しない。新しいcorrのport_stateで現在のphaseを読み、再送履歴と区別する（transports §4）。
- **ロジックのキャプチャ**: layout の w は 1〜128 のどの整数も読む。w が 8 の倍数でなければサンプルはバイトの境目をまたぐ（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.1）。
- **アナログのキャプチャ**: host が電圧を示すときは、値 0 と 2^b − 1 を電圧ではなく振り切れ（低い端以下、高い端以上）として示す
  （[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.2 規則 6）。

## 3. 名前が `oep.` で始まるインターフェース

`oep.` の名前を list に出す probe は、そのインターフェースの文書全体に従う。必須のものの短い一覧:

| インターフェース | 必須 | 任意（宣言するもの） |
|---|---|---|
| 位置つきのストリーム（[共通部品](../interfaces/oep-if-common.ja.md) §1） | 採用するopだけに共通の形・非消費read・寿命を適用する。marksがあれば通し番号でページングし、from 3を扱う | marks/clear/mark/write。markがあればmarksも提供 |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`（[線とデバッグ](../interfaces/oep-if-debug.ja.md)） | attach（固定部分method/pins/max_speed、method 0必須）、detach、connections。資源はセッション所有。暗黙の join / eviction をしない。§1 の attach の規範と max_op_ms。§2 の再試行と寿命 | scan（候補count ≥ 1、有限探索）、attachのreset TLV、RISC-Vのmethod 1（features bit0） |
| `oep.target.riscv-dm`（§4） | dmi | halt/resume/reset、read_block / write_block、run/step: ops。reset があれば、ndmreset を解いた後に DM を待つ（§4.3、max_op_ms のうち）。read_block / write_block があれば max_length。successは一時的な値の後始末を済ませた場合だけ。失敗時もmax_op_msのうちに試み、後始末できなければ失敗を返してconnectionとstreamを閉じる（§4）。step が ok でなければ moved と dpc を 0、run の elapsed_us は resumereq から（§4.2、§4.4） |
| `oep.target.arm-adi`（§6） | transfer（n = 0 は success、ack 0）。対応するwireのconnectionを明示して使う | read_block/write_blockは組でopsへ宣言。提供時だけmax_lengthが必須 |
| `oep.target.console`（[コンソール](../interfaces/oep-if-console.ja.md)） | open/read/close/streams。describeのmechanismsはcount付きで必須。§3の読みの順と採用方式のframing | marks/clear/mark/writeはops。marksなしでもdmseqの同期・重複排除を行う。writeなしでは空の答えだけを返し、SDIへのwriteはunsupported |
| `oep.fixture.gpio`（[fixture](../interfaces/oep-if-fixture.ja.md) §1） | set、read。describe の modes に mode 0 | — |
| `oep.fixture.uart`（§2） | configure/read/status。describeのformatsに8N1。明示configureまでstatusはbaud 0で受信しない。planの解放時にbufferと設定を解放し、同boot内の位置は戻さない。同じplanを再指定しても設定を変えない | marks/clear/mark/write、ほかのformat。markはmarksが必要。writeなしではTX roleを宣言しない |
| `oep.fixture.i2c-target`（§3） | stretch を除く §3 の op（書き込み 1 回が 1 フレーム、読み出しは preload_tx の置き場から、ns はフレームを終えた STOP か次の START の時刻） | stretch（ops、max_stretch_us とともに）。プルアップ（features bit2） |
| `oep.fixture.spi-target`（§4） | §4 の op。data のビットの置き方（バイトの途中で終わった転送も、来なかったビットは 0）、bits は 0xFFFFFFFF で止める、nsの任意TLVはCSが無効になった時刻。modesで1つ以上の対応modeを宣言し、非対応configureはunsupportedで状態不変。同時負荷で保証を保てなければ後からの操作を副作用前にunavailableで断れる。MISOをソフトウェアで駆動するならcs_setup_ns | LSB first（features bit0） |
| `oep.fixture.logic`、`oep.fixture.analog`（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1〜§3） | §3.2の必須op。releaseはmode2で必須、calibrationはアナログで任意。§3.3 の configure と query の契約（mode と rate は必須、mode ごとに送れる TLV、type 0 の trigger の role は見ない、0 の samples / segments / rate は malformed、mode 3 の pretrigger は max_pretrigger で縛る、挙げていない値は unsupported、応答の必須の行（アナログのfrontend_used/referenceは任意））。区画の通し番号のページング（[共通部品](../interfaces/oep-if-common.ja.md) §1.3）。出来事の世代。世代は1〜0xFFFFFFFFを再利用せず、枯渇したstartは副作用前に拒否。区画を連続に保てなければその区画を出さず、エラーで止まる（§2.2。隙間は置き場が無くて区画を丸ごと取らないときだけ、state 6 に入るときは必ず stopped reason 3、エラーの後の write_pos はその区画の先頭）。host はエラーの後、受けたデータの write_pos から先を捨てる。§3.5 の describe。readのmax/lenはu16。開始で通信を止める有限な処理はstart要求の中に含め、max_op_ms/leaseの通常規則で扱う。 | query、force、アナログのcalibration（ops）。通知: subscribe / unsubscribe（ops）。mode3のdataは毎frameにgeneration/segment_infoを付け、1区画内だけに収める。未確定の末尾byteを返さない |
| `oep.fixture.capture-group`（§4） | bind/start/stop/status、ops/tracks宣言。全trackは即時triggerかつ同じmode。bindの全検証とstart応答のframe容量、全世代の空きを開始前に確認。開始/停止/エラーとgroup/track世代の区別。 | 通知subscribe/unsubscribeとstoppedだけ。連動trigger/pretrigger/force/multirateはv1に含めない。 |
| `oep.probe.plan`（[plan](../interfaces/oep-if-plan.ja.md)） | planの役割を持つインターフェースがあればlistに出す。plan_applyは要求全体を検証し、残る割当・機能状態を保つ。動作中の割り当て（role, channel）の集合の変更/束ねられた資源変更は拒否。plan_releaseも全対象を先に検証。上限があればplan_roles | — |
| `oep.probe.restart`（[再起動](../interfaces/oep-if-restart.ja.md)） | restart。describe の restart_max_ms。ロックの要る op として断る。答えは completed success で、それを先に送る。答えの後は再起動するまでどのtransportの要求にも答えず、意図したtargetのreset/resumeは行わない。MCUのリセット状態と外部回路によるtarget変化は保証しない。再起動の後は電源を入れたときと同じ（新しい boot_id、保存した設定だけが残る）。答えがtransportを出てからrestart_max_msのうちにProbe内部が通信を受けられる状態へ戻る。OSの列挙/ネットワーク接続/Hostの開き直しは別 | — |
| `oep.probe.link`（[リンク](../interfaces/oep-if-link.ja.md)） | source、sink | port_speedとport_state（ops）。frame境界で変更し、pipelineを先に解決。通知だけのHostも正常要求でidleを延長する。要求処理中のtimerと所有session終了後の取消禁止（§3） |
| `oep.probe.config`（[設定](../interfaces/oep-if-probe-config.ja.md)） | get/set/unsetとitems宣言。count付き項目と末尾TLVの区別。変更カウンタはboot内非再利用、no-opは世代/ピン不変。変更は全検証の後に適用。 | disable/idle/labelの対応範囲。save/erase/stateは保存とともに採用しmax_bytesを宣言。起動時に有効項目だけを適用しdisableを先に掛け、部分適用はstateで示す。 |

## 4. 確かめ方

**試験のベクタ**（[`tests/vectors/`](../tests/vectors/)）。`tools/oepvectors1.py` が規範の文書から計算する。ベクタと文書が
食い違えば文書が正しく、ベクタを直す。扱う範囲:

| ファイル | 扱うもの |
|---|---|
| `checks.json` | CRC-16（transports §1）、dmseq の CRC-8 |
| `cobs.json` | COBS の符号とシリアルの口のフレーム全体。復号が受け入れるもう一つの形も含む（transports §1） |
| `headers.json` | 要求と答えのヘッダ、TLV の符号（§2.2、§4.1、§4.2） |
| `core_extensions.json` | open/keepalive/end/clock と拒否の固定部分の後ろに未知応答 TLV を足す例。固定部分が空でも拡張規則は同じ（§2.3、§4.3） |
| `confirm.json` | confirm のやりとり（§7.1） |
| `discovery.json` | list（§7.2。fn 0 を載せないので、インターフェースの無い例の probe では空）、fn 0 の describe（§7.3、§7.5）、終わりを越えた describe、ヘッダの断り unknown_function / unknown_operation（§4.3 の順 1） |
| `refusals.json` | §2.3 と §4.3 の断り方（理由が 1 つだけ当たる状態）と、無視される知らない TLV について、要求とそのとおりの答え。§4.3 の順 4 で理由が 2 つ以上当たる要求は、どれで断ってもよいので（意図した単純化）、ベクタは持たず、試験はどれか 1 つを受ける |
| `sessions.json` | セッションの場面: 判定の表（§6.2）、送り直しの表（§5.1。送り直した end）、end での解放と no_session（§9）、force、session_id 0（§4.1）、セッションが無いときと開いているときの clock（§7.6）。決めた初めの状態から順に送る要求と答え |
| `ops_encoding.json` | describe の共通の tag ops の値の境（最短、最長、長さの誤り、op 0xFF の境、同じ集合の別の符号）と、正しい値が表す op の集合（§7.4） |
| `ops.json` | op ごとのバイト列: 要求、それが前提とする probe の状態、答え（`oep.probe.restart`、`oep.probe.plan`、`oep.probe.link`、gpio、rvswd、riscv-dm、console（marks の通し番号のページング、streams の最後のページ）、logic（configure の契約、即時の trigger の role を見ない query、samples 0 の malformed、segments の空のページ、区画の中で落としたときの status / segments / read と stopped、ストリーミングで落とした区画に入りかけたデータのフレーム（`data`）とその後の status、segments、capture-groupの即時bindと非対応trigger/将来critical selectorの拒否）、riscv-dm の失敗した step、arm-adi の n = 0 の transfer、spi-target の部分の byte（MSB / LSB が先）、capture-groupのstartと非即時trackのbind拒否、キャプチャの出来事のフレーム（`events`、世代）、probe.config（count付きget/set/unset、任意state、最大長label、部分適用、変更カウンタの枯渇）、logic のほかの一部）。並びの答えは要素の長さ無しの `count × 要素`（§2.3） |
| `logic_layout.json` | ロジックのキャプチャのストリーム（[キャプチャ](../interfaces/oep-if-capture.ja.md) §1.1）: layout の w と pos、チャネルのレベル、区画のバイト列。2 の冪でない w（w = 3、サンプルがバイトをまたぐ） |

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
  revision 1（core §2.8）についてで、任意の機能を含むことは意味しない。
- 線の上の形を変える実装、仕様が許さない答え方をする実装、自分のインターフェースや tag を `oep.` の名前の下に置く実装は
  適合しない（core §12 規則 1 と 7）。自分のインターフェースは逆ドメインの名前を使う。
- 適合は project の USB VID:PID を使う許可を与えない。それは [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino)
  の PID-USE の条件（そのライブラリから作る、ソースを公開する、仕様どおりに OEP を話す、正直に名乗る、など）のもとで別に与えられる。
  ほかの実装は自分の USB ID を使う。host は利用者がそれを名指すか口を選んだときに開く（transports §3）。
- 適合しても probe が自動で識別されるようにはならず、扱える target のチップ、速さ、規範の文書が求める以上の電気的な振る舞いについては何も言わない。
