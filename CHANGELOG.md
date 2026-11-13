# Changelog

## Unreleased

OEP v1は凍結前。現行の規範文書とregistryが仕様を定め、実装は対応するcommit/tagを明記する。core/transportsの変更方針と正式凍結の手続きは[版と安定性](docs/versioning.ja.md)に従う。

- **どの日本語の文書にも英語の URL を置いた（版と安定性 §2）**: `X.ja.md` ごとに `X.md`。英訳ができるまでは、見出しと日本語版へのリンクだけを持つ（試験が中身を確かめる）。英語のリンクを今から張れる。
- **broker の相乗りと見つけ方を決めた（host ガイド §7.1、§7.2）**: 相乗りは名前つきの拡張 `oep.probe.share`（critical、data は空）。
  中身は 1 つ（broker が 1 つの持ち主として probe のロックと lease を持ち、session と資源は client ごと、要求は届いた順、force で全員が外れる）。
  broker は利用者ごとの `oep/brokers/<unit_id>.json`（endpoints の種類、受ける share の名前、pid、起動時刻、実装）で自分を公開し、
  `<unit_id>.lock` で起動を 1 つにする。`.lock` は消さず、残った `.json` は次にロックを取った broker だけが消す。道具は `OEP_BROKER`、
  ファイル、直接の順に試し、つないだら describe の unit_id を必ず確かめる。
- **op の名前と形を describe で示す共通タグを足した（core §7.4、任意）**: op_name（0x0A: op、flags、名前。flags は form と lock_free）と
  op_field（0x0B: op、part、type、名前）。form を立てた op は、要求と completed success / failed の応答の固定部分の欄を順に示す。型は
  u8〜u64、i8〜i64、bool、bytes、text（長さ付き）と、数の型の並び（type の bit 7、count(u16) 付き）。host はインターフェースを
  知らなくても、名前で op を選び、要求を組み立て、応答を読める。形の正は今までどおり名前と revision。
- **USB の経路の組を選ぶ本体の項目 `usb.transports` を足した（transports §3.1、任意）**: enum、restart。probe は自分の USB device で
  開始できる組だけを選択肢に並べ、名前は経路の短い名前を describe の順に `-` でつなぎ、2 つ以上の種類に数を付ける（`bulk-hid-cdc2`）。
  どの組も vendor bulk か HID を含む。開始できない組は、その起動では既定の組にする。
- **キャプチャの形式 1 を、区間ごとに決まったビット数の縮約に替えた（oep-if-capture §1.3）**: 線ごとに運び方と区間 D を選ぶ。
  運び方は raw、sample（区間の先頭の 1 サンプル）、any_high（区間の OR）、any_low（区間の AND）、change_latch（区間末のレベル＋区間の中の
  変化の有無、2 ビット）。5 以上は予約。ブロックは raw の部分（形式 0 の詰め方）と、縮約の部分（change_latch の線ごとにブロックの前のレベル 1 ビット、続けて値をビットで詰める）。どのブロックも単独で読め、帯域は信号によらず決まる。
  前の形式 1（変わった刻みだけ出来事を送る events、fallback、start_level の見出し）は消した: 費用が線の動きで約 10 倍ぶれ、最悪を保証できる
  速さが低かった（ESP32-P4 で 3 本全速＋5 本 1/64 が約 1.5 MHz）。WireSkein と相談して決めた。
- **キャプチャの rate は「取り込めるか」で決め、送り出しが間に合うかでは下げない（oep-if-capture §3.3）**: 取り込みの回路とメモリへ移す
  経路が動かない値だけを断る（丸める）。USB などの帯域、host の読み、ほかの機能と同時の CPU は環境で変わるので、probe はそれを理由に
  rate を下げたり断ったりせず、間に合わなければ隙間にする。ストリーミングの応答に data_rate（0x16、byte/s）を足し、mode 3 で必ず返す
  （形式 3 を除く）。余裕は host と利用者が決める。
- **reset はシステムリセット（oep-if-debug §4.3、§2、§4 の表）**: reset の op は、hart だけでなく周辺も既定の値に戻す。ndmreset で周辺が
  戻らない target（CH32）では、probe はその target のシステムリセット（PFIC の SYSRESET）を、debug module の command の外で、線にフレームを
  出していない間に起こす。mode 1 はその後で最初の命令の前に止める。システムリセットのために使った RAM は戻す。CH32 の ndmreset だけでは、
  前のイメージの SysTick や USART が動いたまま新しいイメージが起動し、その割り込みで止まっていた。
- **メモ欄の使い方の推奨（oep-if-memo §4、規範ではない）**: 名前は `<持ち主>/<残り>` で、持ち主は自分の逆 DNS の名前か、形を定める
  インターフェースの名前。名前は版を持たず、形を変えるときは新しい名前にする。口や target は小文字にそろえて入れる。中身は
  UTF-8 の JSON、書き直しは同じセッションで読んでから書き、知らないメンバーを残す。project の形として口の記録
  `oep.probe.memo/port/<口>`（`target`、`part`、`note`）を足した。
- **第三者レビューの 6 件を直した**:
  - fixture §6 の SPI の transfer と §7 の PWM の set の応答の頭に `n(u8)` を足した（core §2.3: 並びは要求の知識なしに終わりが分かる）。ベクタも直した。
  - PWM はセッションの終わりで止まる（plan はセッションの資源）。「セッションが終わっても出力を続ける」を消した。
  - core §11 の表の set と unset を §13.5 に合わせて「値を変えさせるなら必須」にした。
  - capture 形式 1 の fallback は、出来事が L / 8 byte を超えるブロックだけにした（最悪の帯域の式が上限になる）。
  - メモ欄の最後の write の crc の不一致は completed failed で、そのオブジェクトは無くなる（rejected は何も変えない）。
  - メモ欄の max_objects を u16 にした（list の first で全部を指せる）。
  - fixture §6 の max_length の答えの大きさの式に n の 1 byte を入れ、capture のベクタの説明から任意の fallback の記述を消した。
- **消えた保存は storage_state 0 でよい（core §13.7）**: 電源断で保存が何も残らず、保存が無いのと見分けられないときは 0 と答えてよい。
  どちらでも probe は何も使わず、host がすることも同じ。完全か確かめられない保存を使わず 2 と答えることは必須のまま。
- **メモ欄を出す probe の経路の max_frame は 128 以上（oep-if-memo 冒頭）**: 名前が 64 byte の write の固定の部分は見出しを含めて 89 byte で、
  64 byte の max_frame には収まらなかった。
- **必須を見直し、品質だけにかかわる規則を推奨にした**: 破ると相互運用、ピンの安全、secret、host の判断を損なう規則だけを必須に残した。
  推奨にしたもの: 設定の保存の電源断での原子性（壊れた保存を使わず storage_state 2 で示すことは必須のまま）、同じ内容の保存を書き直さないこと、
  保存を名前で持ち firmware を越えて読めること（保存した値を別の項目・key・channel に当てはめないことは必須）、保持できる量が足りないときの
  disable のほかの使う順、起動時にぶつかる label のどれを使うか（1 つだけ使うことは必須）、内容の変わらない set で generation とピンを変えないこと
  （core §13.5、§13.7）。固有の番号の無い probe が乱数の unit_id を保存すること（core §7.5）。debug の閉じた後の線の保持（保持する probe は
  holds に出し、設定を持つなら `channel.{}.hold` を宣言する。debug §2）。自動の判定と保持を設定で OFF にできることは、設定を持つ probe だけの
  規則にした（core §8、§12 規則 8）。host が経路を vendor bulk、HID、シリアルの順に試すことと、シリアルの口と HID を排他で開くこと（経路 §3）、
  設定の入れ直しの前の利用者の確認（設定のファイル §4）。
- **メモ欄（新しいインターフェース `oep.probe.memo`）**: host が probe ごとの記録（つないだ target、治具の配線など）を probe に置き、
  別の host からも読めるようにする任意のインターフェースを足した（oep-if-memo）。オブジェクトは名前（1〜64 byte）、データ、CRC-32 で、
  持ち主の区別は無い。probe は中身を使わず、OEP のどの規則も中身に頼らない（probe の振る舞いを決める値は設定、core §13）。
  op は list、read、write（offset の順に分けて書く）、delete。量は describe の max_object と max_objects でprobe ごとに宣言し、下限は無い。
  電源断で壊れうるのは書いていたオブジェクトだけで、probe は不可分にしなくてよい。壊れたものは crc が合わないので host が見つけて書き直す。
- **凍結とタグ（版と安定性 §2、§6）**: 凍結は `v1.0.0` の正式リリースで行い、その前の `v0` のタグは付けない。英訳は `v1.0.0` の前に作る。
  凍結の前の実装は、実装する仕様の commit を示す。
- **capture の実装の無い任意の機能を外した（削除）**: どの実機の probe も持たず、仮想ベンチにだけあった機能を v1 から外した。
  データの外部の経路（旧 §3.9: configure の data_path と overflow、describe の external_data、OEPX の印、落ちうる経路の見出し、enum
  `external_kind` / `external_mux` / `data_path`）、名前付きのデータの形式（format 0xFF、configure と応答の format_name、describe の
  format_names）、前段の設定（ロジックの threshold、アナログの coupling、offset、bandwidth、impedance、resolution、oversample と、その
  応答）。どれも任意の機能で、要るときに実機で確かめてから revision を上げずに足せる（capture §3.6）。外した番号は凍結前なので使い直せる。
  §3.8 は「グリッチフィルタと外部クロック」になり、グリッチフィルタの群は 0（全チャネル）だけにした（群の中身を threshold の宣言に
  頼っていた。今の probe と仮想ベンチの扱いのとおり）。トリガの記録は §3.10 から §3.9 になった。外部の経路のベクタを消した。
- **節の参照（文言）**: ほかの文書の節を指す `§N` には、どれも文書の名前を付けた（`core §4.3`、`capture §1.3`）。適合のガイドの
  表の行のように、文脈で決まっていた番号だけの参照も同じ。fixture と capture の頭（§1 の前）に `§0` の見出しを付け、そこを指していた
  `§0` の参照が見出しを指すようにした。用語集の `settings §13` は `core §13`、ベクタの無い節 `oep-if-restart §3` は消した。規則は変わらない。
- **適合のガイドの誤り（文言）**: キャプチャの必須の項目の stopped reason を 2 に直した（3 と書いていた。capture §3.4 と registry のとおり）。
  i2c-target の内部プルアップを features の bit0 に直した（bit2 と書いていた。fixture §3 のとおり）。拡張例の calibration の節を capture §3.7 に直した。
- **用語集の誤り（文言）**: role の出来事とデータを 0x03 と 0x04 に直した（0x05、0x06 と書いていた）。tag の文脈、revision を上げるとき、
  線の名前の慣行、リセットの後の待ちの節を、core と debug と host ガイドの今の形に合わせた。古い「label（firmware）」の行を消した。
- **probe ガイドのストリーミングの見出しの大きさ（文言）**: データの通知の見出しを、capture §3.4 の必須の TLV を含めた 49 byte に直した
  （17 byte と書いていた）。それに合わせて、勧める max_frame を 256 以上から 1024 以上にした。
- **host ガイドの直し（文言）**: §9 の断りの表の unavailable の cause に、core §4.3 の 7（方針で許されない）と host がすることを足した。
  §7 の「core の 5 個の op だけを特別扱いする端点にはしない」を、fn 0 の一部の op だけを自分で答える端点にはしない、に直した（数が今の
  fn 0 の op と合わなかった）。
- **capture §3.3 の critical の bit（文言）**: 「この表の TLV は critical を付けずに送る」を、表の「送るか」の欄が critical と書かない TLV に
  限った。欄が critical と書く任意の機能（format の 0 以外、format_name、data_path の 1、carriage、trigger_opts）は critical で送る。規則は変わらない。
- **capture の状態の遷移の表（誤りの訂正）**: エラーで state 6 に入るときの stopped を `stopped 3` と書いていたのを `stopped 2` に直した。
  本文（§2.2、§3.2 のエラー）と registry の `stopped_reason`（2 error、3 は無い）のとおりで、規則は変わらない。
- **規範の中の製品名（文言）**: capture の出来事の作り方と式の費用の説明から、特定の probe（ESP32-P4）の名前と性能の話を外した。probe
  ガイドの、取り込みのリングの例からも、実装の名前と測った値を外した（やり方だけを書く）。
- **空けたままの reject reason 0x05（文言）**: core §2.5 の「凍結前は欠番を作らない」の例外として、なぜ空けるか（本体の番号は
  暫定確定、版と安定性 §2.1、で動かさない）を書いた。

- **ブローカーの相乗り（host ガイド §7、明確化）**: broker が自分の道具どうしに 1 つのロックを相乗りさせるのは、その broker の
  名前つき拡張を critical で open に付けた client だけ。付けない client には core のとおり（1 つのロック、再送履歴、lease、force）。
  相乗りは 1 つの持ち主で、force はそれを奪う。

- **要求の中の重複した tag（壊す変更）**: 要求で、probe が実装する、繰り返すと定義が言わない tag が 2 つ以上あれば rejected malformed
  （core §2.3）。probe は 2 つ目以降の値を検証しなくてよい。知らない tag は数えない。応答、出来事、データの読み手は、これまでどおり最初のものを使う。
  共有ベクタ refusals.json に、正しい値の idle_clock を 2 回入れた attach を足した。

- **debug の線の設定の項目名（壊す変更）**: `rest.{}` を `channel.{}.rest`、`hold.{}` を `channel.{}.hold` にした（debug §2、§3.1）。
  channel ごとの値は、本体の `channel.{}.label` と同じ「もの.名前.性質」の並びにそろえる。持ち主はカテゴリ（`oep.wire.rvswd/0` など）で分かる。

- **アドレスの経路（host ガイド §5.3、追加）**: アドレスに `?via=<経路>` を1つ添えて、同じ probe へ届く経路を選べるようにした
  （`usb`、`bulk`、`hid`、`cdc`、`net`、`tcp:<host>:<port>`、`tty:<path>`）。場所の書き方は変えない。どの経路でも unit_id を確かめる。
  比べるときと機器の排他の鍵では `via` を除く。知らない query は断る。

- **label にピン（host ガイド §5.3、追加）**: 口の線の label に、つながる target のピンを `@P` で添えられるようにした
  （`x035.nrst@pa21`）。役目の無い線は `S@P`（`x035@pb6`）。役目の探し方は `@` より前の `S.N` で、今の label はそのまま使える。
  同じピンが設定で役目を変える target（CH32X035 の PA21 など）は、役目と `@P` の両方を書き、役目が効くかは host が target の設定で確かめる。

- **周辺の試験の層（ガイド）**: [周辺の試験の層と probe の機能](docs/peripheral-testing.ja.md)。試験を、論理、DUT の中、物理的な IF の
  観測、汎用の相手、専用の相手、実物の層に分け、MCU の周辺ごとにどの層で何を試すかを例で示した。OEP の probe が受け持つ観測と汎用の相手
  の層で、標準の機能で行える試験、標準に無い機能が要る試験、原理的に難しいものを整理した。規則は変わらない。

- **capture §3.7 の残り（表記）**: describe の frontend から減衰が外れた後も、§3.7 が「frontend ごとの減衰」を describe の frontend にあると
  書いていた。測れる範囲（入力ピンの電圧）だけを指すように直した。規則は変わらない。

- **PWM、counter、DAC（追加）**: `oep.fixture.pwm`（fixture §7: 周波数とデューティを指定した方形波、出した値を返す）、
  `oep.fixture.counter`（§8: ゲートのうちのエッジの数と実際の時間。聞くだけでほかの機能のピンと共有してよいので、同じ probe の
  出力を配線なしで数えられる）、`oep.fixture.dac`（§9: アナログの値、公称の範囲を describe で示す）。
- **I2C と SPI の controller（追加）**: `oep.fixture.i2c-controller`（fixture §5）と `oep.fixture.spi-controller`（§6）。probe が主側になり、
  DUT の target を試す。I2C は repeated START でつないだ区切りの並びと STOP を出さない終わり方、ACK / NACK と stretch の打ち切りを result で
  返す。SPI は CS の時間（gap_ns、setup_ns、hold_ns）を指定した転送の並びを 1 回の要求で続けて行い、実際に守った時間を返す。
  clock_hz はどちらも頼んだ値以下の出せる値を選んで返す。ArduinoCore-CH32RV の Wire のスレーブと SPI のスレーブの試験のため。
- **設定を本体へ移す（壊す変更）**: `oep.probe.config` を無くし、設定を core §13（任意）にする。カテゴリは本体（fn 0）かインターフェース（名前と instance）で、項目はその持ち主が名前を付けて宣言する（describe の共通 tag setting 0x08、setting_choice 0x09）。値は出どころ（fixed / default / user）を持ち、fn 0 の任意の op get / set / unset / save / state（0x20〜0x24）で読み書きする。erase は無い（全部 unset して save）。secret は誰にも読ませない。保存の形式は決めず、名前で持つ・電源断で原子的・宣言済みの項目だけを使う、を決める。
- **target は名前ごとに 1 つ（壊す変更）**: connection を使う `oep.target.*` と `oep.target.console` は、名前ごとに probe に 1 つで、
  wire の定義が対応させたすべての wire の connection を受ける（common §2）。どの instance がどの wire の connection を受けるかを host が
  知る手段が無かった（2 本の wire に console を 1 つずつ持つ probe で、host は開いて断られるまで分からなかった）。
- **名前と初期値（壊す変更）**: 設定の値の出どころ（fixed / default / user）を無くし、get の値の origin(u8) を外す（値の固定部分 7 byte、
  wifi_min_max_frame 82）。firmware の初期値は保存の無い起動で本体が置き、その後はほかの値と同じ（core §13.4）。set / unset は値を変えさせる
  probe だけが持つ（初期値だけの probe は get だけ）。channel.{}.label は probe の中で ASCII の大小文字を区別せずに一意で、書いたとおりの大小文字で保つ
  （core §13.8）。口は `S.N` の label で名付けたものだけ、アドレスはいつも全部を書き `any` を無くす、表示は書き方のまま・比べるときは大小文字を区別しない
  （host ガイド §5.3）。設定のファイルは全部の値を書き出す。ch32rv と合意。
- channel に名前（データシートのピン名）を持たせる（fn 0 の describe channel_name 0x44、必須）。wire の番号は起動の間だけで、保存と書き出しは名前で指す。経路の index の不変性を外し、経路は kind と順の名前（`cdc0`）で指す。fn 0 の describe の label（0x46）を無くし、設定の `channel.{}.label` の fixed の値に移す。
- ネットワークの項目（`wifi.{}.*`、`ipv4.{}.*`）と network（fn 0 の 0x25）、netif（fn 0 の describe 0x45）を transports §7 へ。rvswd の `rest.{}`、各線の `hold.{}` を debug へ、シリアルの口の素通しを fixture §2.1 とコンソール §2.1 へ、それぞれの持ち主の項目として移す。
- 設定のファイル（docs/oep-settings-file.ja.md、規範）: 書き出しと入れ直しの JSON の形と手順。共有ベクタ settings_file.json。
- core §12: 最小の拡張は固有操作か設定の項目の 1 つでよい（設定だけのインターフェースを認める）。
- 明確化（既存契約を保つ。wireskein と合意）: core §10.3 の「両方 0 ならあるだけすぐ送る」は、経路が塞がっている間に溜まった分をまとめてよい（max_frame を超えない）。transports §1 の長さ 0 のフレームは何にも数えず lease を延ばさない、USB の転送を閉じるのに使える。キャプチャ §2.2 のリング・キューのあふれは、区画の外に置ける作りなら隙間を推奨、置けない作りはエラーでよい（置き場が無い場合は従来どおり隙間）。
- キャプチャ §3.3 / §4.4: configure / query の応答の judge_latency_ns（0x15、任意）。組の出来事の元の条件を判定するトラックが、条件の成り立ったサンプルから出来事と知るまでの最大の時間を、この設定で返す。追う側の溜める量を host が bind の前に計算できる（wireskein と合意）。
- キャプチャ §2.2: 隙間とエラーを、失ったサンプルがすでに区画に入っていたかで分ける。取り込みのリングやキューのあふれでも、まだ区画にしていないサンプルなら隙間（position を飛ばし、取得は続く）。§2.1 の規則 1、適合の確かめ方、probe の開発ガイド（P4 の例）も合わせる（wireskein と合意）。
- TLVの重複時の検証、ピン候補の合成、通知のまとめ条件とframe分割を明確にする。
- ストリーミング停止時の端数を送信対象にし、末尾到達と欠落のない受信を区別する。capture-groupの再start拒否と開始失敗時の状態・世代を定める。
- I2Cの送信末尾、SPIの空の受信結果、累計カウンタの飽和を定める。configのsave/erase失敗時の応答と保存状態、初回保存と消去中の電源断を明確にする。
- fixtureのconfigure失敗時の応答と未設定への復帰を定める。UARTの受信済みデータは保ち、受理した再configureでは未送信TXを持ち越さない。
- calibrationの情報が要求経路のframeへ収まらない場合はunsupportedとし、情報を省いた成功応答と区別する。
- consoleを閉じたraw DMI手順の分割、共通target_idの採用範囲、captureの拡張時の番号所有権を明確にする。
- 共通streamの通知欠落と保持データの消失を区別し、serialから欠落数を判断する条件を明確にする。runの停止位置だけで未実行と判断できるという説明を修正する。
- 開発ガイドの実装方法と規範の要件を区別し、任意機能・autoexec・出力強度調整への過剰な要求を取り除く。仕様レビューと検査・実装反映の工程を分ける。
- 機能・wireの番号と幅を維持し、重複説明と中間設計の経緯を整理する。境界条件の共有ベクタと適合確認項目を追加する。
- hostガイドの購読の送り先を core §6.2/§10.3 に合わせる（同じ id の open では移らず、経路を開き直したら subscribe し直す）。走り直す host の後始末に、前の実行より先の corr の保存が要ることを書く。
- 共有ベクタ interface_profiles の spi-target の max_length を core §7.4 の u16 で生成する。
- port_speed の phase 3（復帰保留）は理由によらず取り消さない。受信中の frame とその応答を終えた境界で戻り、新しい要求を受け続けても復帰を延ばさない（idle の保留だけを取り消す規則と、その取消後の step の扱いを削除）。
- 適合の確かめ方に、OEP の要求に自分で答えるブリッジやブローカーも probe として検査の対象であること、host が任意の op を前提にしないことを最小構成の probe で確かめることを明記する。
- 適合のチェックリストと host ガイドに、任意の op はその fn の describe の ops に立っているときだけ使う、を host の項目として明記する（ch32rv のブローカーとモニタで、最小構成の console で止まった事例）。
- probe.config に任意の項目 console_passthrough を足す。セッションの無い間、probe が止めない attach で debug のコンソールを読み、target の出力を口へ素通しする（UART を空けられない target のため）。
- probe.config に任意の項目 passthrough（シリアルの口の素通し）を足す。セッションがその口・fn・ピンを使っていない間、fixture UART が受けたバイトをフレームの外で口へ送る（transports §4 で許す）。UART bridge しか口の無い probe で、普通のシリアルモニタが target の出力を見られる。
- riscv-dm に、結果を確かめられなかったときに host がやり直してよい dmi の群を定める（hart の停止中に DM の作業用レジスタと、値のほかに作用の無いレジスタ（GPR、dpc、dcsr）だけを読み書きする群）。common §3 の再実行の禁止はそれ以外に掛かる。
- registryの未使用の`fields`予約を削除し、生成器も文書化したopキーだけを受け付ける。registryの値は変更せず、注記変更に伴う生成物のhashを更新する。

中間の設計経緯はGit履歴で確認できる。正式凍結・リリースは未実施。最初のリリース以後は、公開版間の変更と互換性情報をここへ記録する。
