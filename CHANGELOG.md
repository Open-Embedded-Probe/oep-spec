# Changelog

## Unreleased

OEP v1は凍結前。現行の規範文書とregistryが仕様を定め、実装は対応するcommit/tagを明記する。core/transportsの変更方針と正式凍結の手続きは[版と安定性](docs/versioning.ja.md)に従う。

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
