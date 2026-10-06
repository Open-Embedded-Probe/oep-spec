# OEP v1 の安全とセキュリティの考え方

[English](security.md)

状態: **ガイド**（規範ではない）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。規則は足さない。規範の文がすでに持つ安全とセキュリティの考え方を、それぞれの節を添えて 1 か所に
集める。このページと規範が食い違えば規範が正しい。

## 1. 信頼のモデル

- OEP には**認証も暗号も無い**。probe の経路を開けるプログラムは何でもそれを使え、ロックを取れるプログラムは何でも状態を変えられる。
  ロックの force は認証ではなく、取り違えを防ぐだけ（core §6.4）。
- USB とシリアルの経路は、PC のほかの手元の装置と同じく信頼する。**TCP は信頼できる手元の接続か、認証したトンネルの中でだけ使う**
  （transports §1）。
- OEP の要求に自分で答える端点は、後ろに何があっても probe で、probe の規則すべてに従う。中継するだけのブローカーは probe に対して
  host（transports §1）。
- probe 自身の firmware の更新は OEP の外（core §0）。OEP は firmware を運ばず、署名もしない。
- target のメモリの読み出しと、その読み出しの保護は host のこと: probe は host の要求を実行し、target の知識を持たない（core §13 の
  規則 8、host ガイド §20）。

## 2. 壊れた入力

probe は:

- 動く前にすべての要求の長さと符号化を確かめ、malformed で断る（core §4.3 の順 5）: 合わない数、TLV の符号化の誤り、len が終わりを越える TLV
  （core §2.2）、tag 0x7F / 0xFF（core §2.3）、0 / 1 以外の真偽値、正しい UTF-8 でないか制御文字を含む文字列（core §2.1）;
- 実行の前に断る: 要求は core §4.3 の順で確かめ、すべてを通るまで何も動かさない（plan_apply と probe の設定の set は、全部が受け
  付けられなければ何も変えない: core §8、probe の設定 §2）;
- max_frame を超える長さのフレームは、次の途切れまでの入力と一緒に捨てる。TCP では接続を閉じる（transports §1）;
- フレームの途中で `probe_frame_gap_ms` 途切れたら、TCP 以外のどの経路でも読み直す（transports §2）;
- report が運べるより大きい count の HID の report は、次の途切れまでの流れの入力と一緒に捨て、report の詰め物は無視する（transports §1）;
- role が要求の role でないメッセージと、10 byte のヘッダより短い要求は、答えずに捨てる（core §2.4）。

host は:

- 候補を解き、解けないもの、CRC が合わないもの、role を知らないもの、待っていない corr のものを捨てる（transports §1、core §11.1）;
- role が要求の role のメッセージは捨て、5 byte より短い応答、ヘッダより短い出来事やデータのフレーム（core §2.4）、固定部分より短い
  応答は壊れたものとし、知らない tag は読み飛ばし、長さが定義と違う TLV の値は壊れたものとし、知らない status と reason は失敗とする（core §2.3、§2.4）;
- 送り直しにも答えが無ければ、その経路は失敗したとし、そこで何かを送る前に confirm で立て直す（か開き直す）（core §5.2）;
- 65535 byte までのメッセージを受けられる。正しい COBS のフレームは、2 つの 0x00 の間が `cobs_frame_max_bytes` より長くならない
  （transports §1、§3）;
- 応答の文字列は、見せる前に制御文字と不正な UTF-8 を置き換える（core §2.1）。

## 3. 資源を使い尽くさせないこと

- **待っている要求**: 経路ごとの max_frame、window、max_inflight が host の送れる量を決める。probe は window_exceeded で断ってよく、
  守らない host は要求を失う（core §4.4）。
- **送り直しの表**は少なくとも max_inflight 個を持つ。probe は覚える応答の大きさに上限を置いてよく、それより大きい応答の送り直しには
  result_lost で答える（core §5.2）。
- **ignored の並び**は多くて `ignored_max_entries` 個で、probe はいつもその余地を残す（core §2.3）。
- **通知**: 経路の送信のバッファで待つのは多くて max_frame × `notify_pending_max_frames` byte。残りは probe の中で捨てられ、seq の
  飛びに見える。probe は応答を先に送り、通知の書き込みでブロックしない（core §11.4）。ハートビートの周期は `heartbeat_min_ms` に
  丸めてよい（core §11.3）。
- **シリアルの口での host の受けの量**: host は待つ応答の量を `host_serial_inflight_max_bytes` 以下に、subscribe の min_bytes を
  `host_serial_min_bytes_max` 以下に保つ。OS のドライバが一度に来た量を黙って落とすことがあるため（transports §4）。
- **時間**: どの要求も宣言した max_op_ms より長くかからず、引数がそれを超えうる op は unsupported で断る（core §7.5）。attach と scan
  には `attach_budget_ms` と `scan_budget_ms` の予算があり、1 つの要求が線を試し直すのは多くて `wire_retry_ms`
  （[線とデバッグ](oep-if-debug.ja.md) §1、§2）。lease は `lease_min_ms` から `lease_max_ms` の間（core §6.4）。
- **番号**: 資源の番号は u16 で probe に 1 つの空間。閉じた番号は、最近閉じた `resource_reuse_distance` 個の中では使い回さない
  （core §9）。
- **ためるデータ**: 位置つきのストリームとキャプチャの区画は、古いものから押し出して失ったことを知らせる輪（common §1.1、
  [キャプチャ](oep-if-capture.ja.md) §2）。probe の設定は max_bytes が上限で、超えれば unavailable cause 3（probe の設定 §2）。

## 4. ロックの公平さ

- ロックは probe に **1 つ**。状態を変えられるのは、それを持つセッションだけ（core §6.1、§6.3）。ロック不要の要求は読むだけ
  （core §6.3、§13 の規則 5）。
- 持ち主が更新しなくなったロックは lease が空ける。期限切れでも end と同じく、そのセッションの資源は解放される（core §6.1、§9）。要求の実行中は lease を
  数えず、その長さは max_op_ms が抑える（core §6.1、§7.5）。
- locked で断られた host は残りの時間と、あれば持ち主の文字列を知る（core §4.3、§6.4）。lock_state はセッションなしで同じことを返す。
- session_id は host が選ぶ予測できない乱数で、probe は決して返さない。だから force なしにほかの host のセッションとして振る舞うことは
  できない（core §6.1、§6.4）。
- force はロックを取り、前のセッションの資源をその終わりと同じに解放する（core §6.4、§9）。セッションが作ったものは次のセッションに
  渡らないので、落ちた host の plan や接続がほかの host のものになることはない（core §9）。host がいつ使うか: host ガイド §6（利用者が
  頼んだときだけ。排他で開いたシリアルの口が唯一の経路の probe は別）。
- **ロックを持つ host は probe を再起動できる**（fn 0 の restart、任意で ops に宣言する、core §6.6）。ロックの持ち主はもともと線を駆動し
  設定を変えられるので、再起動も持ち主を信頼することの中にある。ロックの無い要求では再起動しない（session_required、no_session、locked）。再起動はすべての経路の、
  ほかの host のロック不要の読みも含めて途切れさせ、保存していない設定を捨て、connection を閉じる。probe は応答を先に送り、再起動の前に
  線を空きの状態にする（target は reset しない。止めていた hart は止めたまま）。restart を持たない probe は unknown_operation で答える。

## 5. target の出力で偽れるロック不要の応答

シリアルの口では、target の生のバイトは OEP の応答と同じ口で host に届く（transports §4）。host の role と corr の照合は、偶然できた
フレームは捨てるが、わざと作ったフレームは止めない: 生の転送が止まっていない口では、target の出力が、正しい CRC と、待っている
ロック不要の要求の corr（1 ずつ進むので予測できる）を持つフレームを含みうる。応答の中身を信じる必要のある host は、生の転送が
止まっている口（自分のセッションの要求がそこに届いた後）か、長さつきの口で要求を送る（transports §4 の参考の注）。

## 6. 電気の安全

probe は本物の線を駆動する。target、治具、probe 自身を傷めないための規則:

- **出力の強さ**: host が強さを選べるのは gpio の出力と出力の idle（mode 3 / 4）だけ。線と、uart、i2c-target、spi-target の線の強さは
  probe が決める（[fixture](oep-if-fixture.ja.md) §1.1）。実務: debug の線はタイミングが許すいちばん弱い強さで駆動し、target に給電する
  線は弱くしない（probe ガイド §12、host ガイド §18.5）。
- **出力の idle**: 解いたピンは空きの状態（設定の idle か Hi-Z）に戻る（core §8）。plan を取ってもピンは変わらず、読むだけの
  インターフェースは駆動しない（core §8、キャプチャ §1.2）。出力の idle は、ピンが空いている間ずっと、起動時から、host なしで level を
  駆動する。target の出力とぶつからないようにするのは配線の責任（[probe の設定](oep-if-probe-config.ja.md) §1）。idle の項目のある
  channel は count = 0 の scan と pins の無い attach から外れ、idle が出力の channel を名指せば unavailable cause 5、holder_kind 7
  （[線とデバッグ](oep-if-debug.ja.md) §1）。
- **保存した設定と起動**: 起動したら、probe は最初の応答の前に、reserved でないすべての channel を空きの状態にする（core §8）。
  保存した設定は起動のたびに host なしで線を駆動する。firmware が動いて設定が掛かる前のピンは MCU のリセットの状態なので、level を
  誤ると害のある線にはそれだけで保つ外付けの pull が要る。disable は宣言で、守りではない。設定に認証は無い（probe の設定 §5）。
- **逆給電**: やり取りが失敗してから、成功するか接続を失うまで、probe は線を駆動せずに休ませ、やり取りの最中だけ駆動する。電源の
  落ちた target をピンの保護ダイオード経由で給電しないため（[線とデバッグ](oep-if-debug.ja.md) §2）。接続が閉じたら、そのピンは空きの
  状態に戻る（debug §2）。
- **速さを確かめる前の target への書き込み**は、wake / 設定の手順と dmactive だけ。書き込みの確かめはスクラッチのレジスタだけを使い、
  元に戻す。別のデバッガ越しに attach する probe は、代わりに `attach_writes_unbounded` を宣言する（debug §1）。
- **count = 0 の scan** は空いている候補のピンを順に駆動する。配線の分からない治具に、利用者の同意なしに送らない（debug §1、参考）。
- **治具の線**: spi-target は CS が有効な間だけ MISO を駆動し（cs_setup_ns を除く）、ソフトウェアで MISO を出し始めるなら cs_setup_ns を
  宣言する（fixture §4）。i2c-target は SDA / SCL をオープンドレインでだけ駆動し、内部の pull-up は宣言し、バスの general call や 10 bit の見出しに
  答えないよう予約のアドレスを断る（fixture §3）。uart の plan は
  TX を UART の休みの level に保つ（fixture §2）。
- **リセットの線**はオープンドレインで引く（gpio の mode 5 / 6、attach の reset TLV）。riscv-dm の reset の op はリセットの線を
  動かさないので、線が動くのは host が名指した所だけ（debug §4.3）。接続を閉じても target をリセットしない（debug §2）。
- **probe のピンからの給電**は、ピンが流せる範囲でだけ。大きいものは外付けのスイッチを介す（host ガイド §18.2）。
- 分からない target の**ピンを探す**とき: host ガイド §19.2。

## 7. 同じ口のほかのソフトウェア

- host は、OS が許す所ではシリアルの口と HID を排他で開く（transports §3）。協力型のロックはほかの道具を止めない（host ガイド §6）。
- 見分けていない device や口には、host は confirm だけを送り、正しい応答が来なければ閉じる（探りの規則、transports §3）。probe でない
  device を乱さないため。class / subclass / protocol や usage page だけで probe とは決めない（transports §3）。
- probe は DTR、RTS、線の設定を何の判断にも使わず、1200 bps の touch と CDC の線の設定は何もしない（transports §4、probe の設定 §1.2）。
  host は自動リセットの回路を動かさないよう DTR と RTS を立てておく（transports §4、host ガイド §1）。
- 共用のシリアルの口の生のバイトは、その口に結んだ流れへ行き、セッションが口を使う間は生の転送が止まる（transports §4）。

## 8. probe が見せる情報

- **owner**（open の TLV 0x01）は、lock_state と locked の断りで、どの host にも返る: 秘密を入れない（core §6.4、参考）。
- **unit_id** はどの host も読め、USB の serial number でもある。チップの固有の番号から作れば、その番号を見せる（core §7.5。代わりの
  作り方は probe ガイド §10）。
- describe、list、設定の get と state、connections、streams、位置つきのストリームの read はロック不要: 口を開けるプログラムは何でも
  読める（core §6.3）。
