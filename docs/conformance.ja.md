# OEP v1 への適合

[English](conformance.md)

状態: **ガイド**（規範ではない）。規則を足さない。各行は規則を持つ規範の文書を指し、この文書と規範の文書が食い違えば規範の文書が
正しい。答える問いは一つ: probe と host が OEP v1 に適合するには何をするか、実装者はそれをどう確かめるか。
適合の条項そのものは [core](oep-core.ja.md) §1.2 である。

## 1. probe のチェックリスト

probe は、自分が出す transport とインターフェースについてこの一覧のすべてを行うとき適合する。

**transport とフレーム**

- core §3.1 の transport を少なくとも一つ、そのフレームとともに（§1.2）。
- シリアルの口: 両側を 0x00 で囲んだ COBS + CRC-16 のフレーム（§3.1）、受け方と生バイトの規則（§3.4）、UART ブリッジの
  回線と起動時の速さ（§3.4）、DTR / RTS で何も決めない（§3.4）、セッションが口を持つ間の生転送の停止（§3.4）。
- vendor bulk と TCP: `length(u16) message`（§3.1）、vendor bulk の長さ 0 の転送の規則（§3.1）、TCP では途切れで読み直さない（§3.2）。
- HID: `count(u16)` と詰め物の report（§3.1）、出力 report を interrupt OUT と SET_REPORT の両方で受ける（§3.3）。
- max_frame を超える長さ: 捨てて待つ。TCP では閉じる（§3.1）。`probe_frame_gap_ms` の途切れで読み直す。TCP を除く（§3.2）。
- confirm の前でも 64 バイトまでのメッセージを受ける（§3.3）。max_frame を超えて送らない（§3.3）。
- USB: probe が選べる口では シリアル番号 = unit_id（§3.3）。vendor bulk と HID は §3.3 の形で、それぞれ一つまで。
- 自分で OEP の要求に答える端点は、後ろに何があっても probe である。中継する broker は §3.1 と §5.2 に従う。

**メッセージ、断り方、末尾**

- 要求と答えのヘッダ（§4.1、§4.2）。要求一つに答え一つ、来た transport へ、来た順に（§4.2、§4.4）。
- rejected は受け付けなかったものだけ。受け付けて失敗したものは completed failed / partial（§4.2）。
- 断りの順序。最初に当てはまる理由で断る（§4.3）。payload は §4.3 のとおり（unavailable の TLV、unsupported の tag）。
- 知らない op は unknown_operation、実装する op の任意の機能は unsupported（§1.2）。
- 要求の TLV: critical の印、知らない critical TLV は unsupported、知らない非 critical TLV は ignored、知っているより長い TLV、短い TLV、
  繰り返さない TLV の繰り返し、tag 0x7F / 0xFF（§2.2、§2.3）。
- ignored（tag 0x7F）を、それが要る completed の答えすべてに、要求の順で、最大 16 項目、16 番目は 0x00、置き場を必ず残して（§2.3）。
- TLV の符号は一意（§2.2）。要求の真偽値と文字を確かめる（§2.1）。出荷するものは実験用の値を使わない（§2.5）。
- window / max_inflight は transport ごと（§4.4）。

**セッションとロック**

- ロックは一つ、§6.2 の判定表、lease の再開始と実行中は数えないこと（§6.1）。
- open / end / keepalive / lock_state / force / owner（§6.4）。lease は 1000〜60000 ms に丸める（§6.4）。session_id 0 は断る（§6.1）。
- 再送の表: 少なくとも max_inflight 件、rejected の答えも覚える、成功した open のたびに捨てる、probe に一つ（§5.2）。
- ロック不要の op は状態を変えない（§6.3）。boot_id は起動のたびに変わる（§6.5）。
- end、期限切れ、force、開き直し、再起動でのセッションの資源の寿命（§9）。資源の番号（§9）。

**fn 0（`oep.core`）**

- 必須の op: core §12 で「yes」の行（confirm、list、describe、open、end、keepalive、lock_state、subscribe、unsubscribe、
  link_source、link_sink）。plan_apply / plan_release はどれかのインターフェースが plan の役割を持つとき。持たなければ unknown_operation（§1.2）。
  port_speed は任意。あるときは §3.5 のすべて（状態、戻る条件）と describe の tag 0x4E。
- confirm: revision の選び方、transport TLV、扱える範囲つきの断り（§7.1）。
- list: ラベル境界での一致、instance の番号、起動中は fn が変わらない（§7.2）。
- describe: ページ送り、宣言だけで boot_id が同じ間は変わらない、要求に TLV を置かない（§7.3）。
- fn 0 の describe の必須の tag: unit_id、transport（transport ごとに一つ）、max_op_ms（§1.2、§7.5）。plan に上限があれば plan_roles（§7.5）。
  discoverable は §7.5 のとおりに送る。unit_id の一意性と不変性、transport の index の不変性（§7.5）。
- plan: fn ごとに不可分、その断り方、設定の plan、解放したピンは idle の状態へ、plan を取ってもピンは変わらない（§8、§8.1）。
- 通知: subscribe / unsubscribe、seq、fn 0 の heartbeat、答えを先に送ることと溜める量の上限（§11.2〜§11.4）。

**時間の上限**（値は `registry/oep-v1.toml`）

- `probe_frame_gap_ms`（§3.2）。宣言した max_op_ms より長い要求はなく、超えうる op は断る（§7.5）。lease の範囲
  （§6.4）。heartbeat の周期（§11.3）。port_speed の verify_ms / idle_ms と戻る条件（§3.5）。各 wire の attach と scan の予算
  （[線とデバッグ](oep-if-debug.ja.md) §1）。

## 2. host のチェックリスト

- **フレーム**: 1 フレームを 1 回の write で送り、途中で 100 ms 以上止まらない（§3.2）。COBS の受け方（§3.1）。confirm の答えの前は
  64 バイトを超えて送らず、後は max_frame を超えて送らず、65535 バイトまで受けられる（§3.3）。vendor bulk の長さ 0 の転送（§3.1）。
- **見つけ方**: USB の自動識別は registry に載った後の project の VID:PID だけ、名指しの probe は unit_id で、それ以外は
  利用者が選ぶ（§3.3）。試し方の規則: confirm だけを送り、正しい答えがなければ閉じる（§3.3）。OEP の probe と分かった機器の中の口の選び方（§3.3）。
  transport を試す順（§3.3）。排他で開く（§3.3）。DTR / RTS を立てる（§3.4）。
- **confirm と revision**: 扱える範囲を送り、その後は使っている revision を `min_rev = max_rev` で送る（§7.1）。revision を知らない
  インターフェースは使わない（§2.7）。
- **待ち**: すべての要求に §4.4 の下限、自分のリンクの要求も含む。UART ブリッジでの転送時間（§4.4）。シリアルの口での受け取れる
  量（§3.4）。
- **再送と回復**: 同じ corr で一度まで（§5.2）。corr は要求ごとに 1 進め、0 を飛ばす（§4.1）。長さつきフレームの再同期と
  `host_resync_wait_ms`（§5.1）。
- **セッション**: 0 でない乱数の session_id（§6.1）。答えの lease_ms が正で、keepalive が延ばす（§6.4）。no_session / expired /
  locked への対応（§4.3、§6.2）。boot_id が変われば自分の状態は無効（§6.5）。一つのセッションの 0x81 の要求は一つの transport で（§3.3）。
- **答えの読み方**: 知らない TLV と tag を飛ばす、繰り返された tag は最初を使う、0 でない真偽値は真と読む（§2.1、§2.3）。知らない
  値は §2.4 のとおり。ignored とその 0x00 の項目を読む（§2.3）。role と corr で振り分ける（§11.1）。TLV が効かなければ意味のない要求では
  critical の印を付ける（§2.3）。
- **文字列**: 答えの文字を見せる前に制御文字と不正な UTF-8 を置き換える（§2.1）。unit_id とシリアル番号、unit_id どうしは ASCII の
  大文字小文字を区別せず比べる（§3.3）。`x-` の unit_id でまとめたり、名指したり、何かを覚えるキーにしたりしない（§7.5）。iProduct と
  インターフェースの文字列は表示だけ（§3.3）。`name#instance` と `oep://` のアドレス（§7.2、§7.6）。
- **port_speed**: host が使うときは §3.5 の host の義務 1〜8。

## 3. 標準インターフェース

`oep.` の名前を list に出す probe は、そのインターフェースの文書全体に従う。必須のものの短い一覧:

| インターフェース | 必須 | 任意（宣言するもの） |
|---|---|---|
| 位置つきのストリーム（[共通部品](oep-if-common.ja.md) §1） | それを使う各インターフェースで §1 の read、marks、clear、mark、write。§3 の status の値 | — |
| `oep.wire.rvswd`、`oep.wire.swio`、`oep.wire.swd`（[線とデバッグ](oep-if-debug.ja.md) §0〜§3、§5） | attach（max_speed は必須）、detach、connections。wire がピンを宣言するなら scan。§1 の attach の規範と予算。§2 の寿命と線の状態 | ピンのない wire の scan。attach の reset TLV |
| `oep.target.riscv-dm`（§4） | dmi、halt、resume | reset、read_block / write_block、run、step: features の bit 0〜3。read_block / write_block があれば max_length |
| `oep.target.arm-adi`（§6） | transfer、read_block、write_block。max_length は必ず出す | — |
| `oep.target.console`（[コンソール](oep-if-console.ja.md)） | §1 の op。describe の mechanisms は必ず出す。方式 2 の枠は [dmseq](target-console-dmseq.ja.md) のとおり | どの方式か（describe の mechanisms） |
| `oep.fixture.gpio`（[fixture](oep-if-fixture.ja.md) §1） | set、read。describe の modes に mode 0 | 出力の強さ（§1.1） |
| `oep.fixture.uart`（§2） | §2 の op。describe の formats に 8N1 | ほかの format |
| `oep.fixture.i2c-target`（§3） | stretch を除く §3 の op。mode 1 と 2 | stretch（features bit1、max_stretch_us とともに）。mode 3（bit0）。プルアップ（bit2、pullup_ohms とともに） |
| `oep.fixture.spi-target`（§4） | §4 の op。MISO をソフトウェアで駆動するなら cs_setup_ns | LSB first（features bit0） |
| `oep.fixture.logic`、`oep.fixture.analog`（[キャプチャ](oep-if-capture.ja.md) §1〜§3） | §3.2 の op。§3.5 の describe。calibration はアナログだけ | query（features bit0）、force（bit1）、通知（bit2） |
| `oep.fixture.capture-group`（§4） | §4.1 の op。§4.3 の describe | force（bit1）、通知（bit2） |
| `oep.probe.config`（[probe の設定](oep-if-probe-config.ja.md)） | 設定を扱う probe だけが list に出す。get、set、unset、state。hash。§2 の断り方。§4 の describe | save / erase（max_bytes が 0 なら unsupported で断る）。slot。bind（あれば bind_modes の bit 0 と 1） |

## 4. 確かめ方

**試験のベクタ**（[`tests/vectors/`](../tests/vectors/)）。`tools/oepvectors1.py` が規範の文書から計算する。ベクタと文書が
食い違えば文書が正しい（core §0 規則 4）。扱う範囲:

| ファイル | 扱うもの |
|---|---|
| `checks.json` | CRC-16（core §3.1）、CRC-32（§5.2）、dmseq の CRC-8 |
| `cobs.json` | COBS の符号とシリアルの口のフレーム全体。復号が受け入れるもう一つの形も含む（§3.1） |
| `headers.json` | 要求と答えのヘッダ、TLV の符号（§2.2、§4.1、§4.2） |
| `confirm.json` | confirm のやりとり（§7.1） |
| `probe_config_hash.json` | probe.config の正規形と hash（[probe の設定](oep-if-probe-config.ja.md) §2） |
| `refusals.json` | §4.3 の断り方と §2.3 の ignored の一覧について、要求とそのとおりの答え |

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

**まだ扱っていないもの。** probe のための自動の適合試験は無い。ベクタが扱うのは符号と一部の断り方で、セッションの表、再送の表、
ページ送り、plan、インターフェースの振る舞いは扱わない。時間（待ち、lease、max_op_ms、フレームの途切れ、port_speed の戻る条件、
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
  ほかの実装は自分の USB ID を使う。host は利用者がそれを名指すか口を選んだときに開く（core §3.3）。
- 適合しても probe が自動で識別されるようにはならず、扱える target のチップ、速さ、規範の文書が求める以上の電気的な振る舞いについては何も言わない。
