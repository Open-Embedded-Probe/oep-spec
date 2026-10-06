# v1 構成の見直し案: core と標準インターフェース（2026-10-06）

Status: **applied**（非規範の記録）。方向は利用者が決め（下の「決まったこと」）、peers（ch32rv、WireSkein、bench）の条件（§6）とともに日本語の作業の文に入れた（§7）。

## 0. 背景

外部の再レビュー（[external-spec-review-2026-10-06](external-spec-review-2026-10-06.ja.md)）は、§3.4 で「probe 自身の restart は core の線引きに合わない」と指摘した。利用者はこれを受けて、core と標準インターフェースの区別が名前と文書から分かりにくいことを、全体で見直すよう求めた。

判断の前提:

- 凍結の前なので、互換は気にしない（名前と番号はすべて変えてよい）。
- 今の機能だけでなく、今後増えるもの（JTAG の線、ARM のコンソール、別の系統の線、新しい治具の機能）を足したときに自然かで決める。
- 名前は host の選び方と保存した設定が指す、永続する識別子である。時間とともに変わりうる性質（どれだけ広く使われているか）は名前に入れない。

## 1. 決まったこと

1. **core は名前を持たない。** core はプロトコルそのもので、fn 0 で話す。list に載らず、版は confirm のプロトコルの revision だけで決まる。今の `oep.core` という名前は、見つける、版を決める、設定が指す、のどれにも使われていなかった。
2. **core は必須のものだけ。** 任意の機能はすべて名前つきのインターフェースにする。区別は「仕様が必須と決めたか」という、後から変わらない事実で決まる: core はすべて実装し、ほかは list で見つけて要るものだけ使う。
3. **名前は `oep.<層>.<名前>`。拡張の区分は作らない。** 汎用か 1 系統専用かは名前に入れない（SWD もはじめは 1 社のものだった。広まり方は時間で変わり、線引きはぶれる）。どの系統向けかは registry と各文書の冒頭に書く。第三者のインターフェースは今と同じ逆 DNS。
4. **購読は、送り出すインターフェース自身の op にする。heartbeat は無くす**（再レビュー §3.1 の矛盾はこれで消える）。core は通知のフレームの形と購読の規則と、subscribe / unsubscribe の共通の op 番号を持つ。送り出すインターフェースだけがその op を ops に立てる。何が届くか（出来事の kind、データの意味）はインターフェースが決める。
5. **probe の今の時刻は必須の応答で読む。** heartbeat が運んでいた uptime_ns を、必須の応答（confirm の応答の TLV が案）に足す。マークや区画の時刻（probe の時計）を host の時刻と突き合わせるのに要る。probe が生きているかは応答の待ち時間で、再起動は boot_id で分かるので、heartbeat が無くても困らない。WireSkein の条件: (a) confirm はセッションの途中でもいつ送ってもよく、セッションとロックに影響しないと明記する（キャプチャの前後で読んで時計のずれを測るため）。(b) probe は uptime_ns を答えを作る直前に取る（突き合わせの不確かさを往復の半分に抑えるため）。
6. **文書は同じリポジトリの中で分ける**: `docs/` に core と経路、`interfaces/` に標準インターフェース。リリースは 1 つの tag。

## 2. 名前の一覧

| 層 | 名前 | 中身 | 今の置き場所 |
|---|---|---|---|
| core | （名前なし、fn 0） | 経路とフレーム、メッセージ、セッションとロック、送り直し、発見、資源の一般の規則、通知のフレームの形、拡張の規則 | core |
| probe | `oep.probe.plan` | plan_apply、plan_release、plan_roles | core §8 |
| probe | `oep.probe.restart` | restart、restart_max_ms | core §6.6、§7.5 0x4F |
| probe | `oep.probe.link` | 線の試験、port_speed | `oep.link` |
| probe | `oep.probe.config` | 設定 | そのまま |
| wire | `oep.wire.swd`、`oep.wire.rvswd`、`oep.wire.swio` | 線と connection | そのまま |
| target | `oep.target.riscv-dm`、`oep.target.arm-adi`、`oep.target.console` | デバッグ、コンソール | そのまま |
| fixture | `oep.fixture.gpio`、`uart`、`i2c-target`、`spi-target`、`logic`、`analog`、`capture-group` | 治具の機能 | そのまま |
| 第三者 | 逆 DNS | 独自のもの | そのまま |

今後の例: `oep.wire.jtag`（RISC-V の DM も ARM の ADI もその上で動く）、ARM のコンソールは `oep.target.console` の mechanism を足す、別の系統の線は `oep.wire.<線の名前>`、系統専用の書き込みの手順は `oep.target.<それが何かを表す名前>`。

## 3. core に残るもの、出るもの

### 3.1 残るもの

- 経路とフレーム（[経路](oep-transports.ja.md)）、メッセージ、TLV、番号の空間、知らない値の扱い。
- セッション、ロック、lease、送り直しと重複排除、boot_id、「probe が再起動するとすべて失う」一般の規則。
- 発見: confirm、list、describe。fn 0 の describe の probe 全体の宣言（unit_id、model、firmware、transport、max_op_ms、discoverable、chip）。
- **channel**: probe のピンの番号の空間と、その宣言（channels、reserved、label、profile）。wire の attach のように plan を使わずにピンを選ぶインターフェースも使うので、plan の有無に関係なく core に置く。describe の共通の tag（ops、role_channels、channel_group、clock など）も core。
- 資源の寿命と取り合いの一般の規則（§8.1、§9）、起動時のピンの空きの状態。
- **通知**: フレームの形（role 0x05 / 0x06、seq）、host の振り分けの義務、送り出す probe の義務、購読の規則（ロックと一緒に終わる、1 つの fn に 1 つ、送り直しは置き換え、seq は 0 から、まとめる条件はデータだけ）、どのインターフェースでも使う subscribe / unsubscribe の op 番号（今の 0x30 / 0x32 をインターフェースの op の空間で予約する案）。購読の op の要求は相手の fn を持たない（その fn 自身への要求なので）。
- **probe の今の時刻**（uptime_ns）: 必須の応答に置く（§1 の 5）。
- 拡張の規則（インターフェースの書き方）。

### 3.2 出るもの

- **plan → `oep.probe.plan`**: plan_apply、plan_release、plan_roles の宣言。role_assignment は今と同じく (fn, role, channel) で、他の fn を引数で指す（インターフェースどうしの関係は文書が定める、core §0 の 5）。
- **購読の op → 送り出すインターフェース**: fn 0 の subscribe(fn, …) / unsubscribe(fn) を無くし、送り出すインターフェースが共通の番号の op として持つ（今は capture の logic、analog、capture-group）。
- **heartbeat を無くす**: fn 0 の出来事 kind 0x01、registry の `heartbeat_default_ms`、`heartbeat_min_ms`。
- **restart → `oep.probe.restart`**: restart と restart_max_ms。経路の文書のブローカーの restart の特則は消し、「probe への経路が無くなったとき」の一般の規則で扱う。応答が先、再起動までの上限、host の待ち方は、このインターフェースの文書が定める。
- **core の文から標準インターフェースの名前を消す**: 設定が残すもの（plan、idle、slot、bind）は「インターフェースが定める保存した設定」と一般に書く。§4.4 の `oep.link` への言及も一般化する。
- **core §13 の 8 を書き直す**: 「特化したものは名前で分かるように」を「どの系統向けかは registry と文書の冒頭に書く」に替える。汎用のインターフェースに特定のチップの手順を入れず、別のインターフェースにする、という中身の規則は残す。

## 4. 同時に直す再レビューの指摘

- **§3.2 `ops` の符号化の範囲**: value は 2〜33 byte（bitmap 1〜32 byte）、`base + 8 × bitmap_bytes <= 256`、bit 0 が立ち、最後の byte が 0 でない（1 つの op の集合に 1 つの符号）。条件を満たさない ops を受けた host は、その fn を使わない（fn 0 なら probe を使わない）。
- **§3.3 通知をまとめる条件**: min_bytes と max_delay_ms はデータ（role 0x06）だけに掛かる。出来事（role 0x05）は、先に送る応答を送り終えたらすぐ送る。heartbeat は無くなる（§1 の 4）。

## 5. 影響

- **probe / Python / JS / ch32rv / WireSkein / bench**: list の結果から fn 0 が消える。plan と restart の op が fn 0 からそれぞれのインターフェースの fn に、購読の op が送り出すインターフェースに移る（op の番号はインターフェースの中で振り直す）。`oep.link` の名前が変わる。wire、target、fixture の名前と op は変わらない。
- **ch32rv**: ブローカーが restart を (fn 0, 0x14) ではなく `oep.probe.restart` の fn で見分ける。restart_max_ms はそのインターフェースの describe だけで読む。
- **保存した設定**: 影響しない。保存は、指すインターフェースを (name、instance、revision) で持ち、起動のたびに今の list で fn を読み替える（[probe の設定](../interfaces/oep-if-probe-config.ja.md) §2）。設定が指すのは plan の fn、スロットの wire_fn、bind の UART、uart の fn で、どれも名前が変わらない。
- **試験のベクタ**: list、describe、plan、購読、restart のものを作り直す。

## 6. peers の条件（2026-10-06）

- **ch32rv**:
  - subscribe / unsubscribe の op 番号（0x30 / 0x32）は、すべてのインターフェースの op の空間で予約する。中継のブローカーは、どの fn でもその番号で購読を断れる（どのインターフェースが送り出すかを知らずに済む）。
  - restart を一般の規則に任せてよい。ただし次の 2 文は残す。
    - リンクの host の義務 6 を一般に書く:「応答の後に probe が再起動する op の応答を受けたら、起動時の速さに戻す」（`oep.probe.restart` を名指さない）。無いと、host は待ち時間が切れるまで待ってから戻すことになる。
    - `oep.probe.restart` に:「中継する host は、restart をほかのロックの要る op と同じに中継する」。
  - confirm に自分で答えるブローカーは、probe の uptime_ns を、最後に probe から受けた confirm の値とその後の経過から作って答えてよい、と明記する（値は、答えを作った時の probe の時刻で、中継の転送時間の分だけ不確か）。または、新しい時刻が要るときは confirm を中継する、と書く。
  - §4 の ops の符号化は、ch32rv の broker_wch はすでに満たす。host の側（不正な ops の fn は使わない）は ch32rv が足す。
- **WireSkein**: §1 の 5 の (a)(b)。
- **bench**: 名前の変化は無い（wire と fixture の名前は今のまま）。

## 7. 適用（2026-10-06）

利用者の選択: 自分で confirm に答える中継のブローカーは推定の uptime_ns を返してよく、正確な時刻が要る host は probe と直接話すか、ブローカーが confirm を中継する。op の番号は `oep.probe.plan` の plan_apply 0x01、plan_release 0x02、`oep.probe.restart` の restart 0x01。`oep.probe.link` は op を変えない。

| commit | 中身 |
|---|---|
| f249685 | §1 の 6: 名前が `oep.` で始まるインターフェースの文書を `interfaces/` に移し、索引（README）を置く。core §14 を消す。リンクを直す |
| 2e5dc4c | §1 の 1〜3、§3: core は名前を持たない。`oep.probe.plan`、`oep.probe.restart` を新しく作り、`oep.link` を `oep.probe.link` にする。経路のブローカーの restart の特則を消す。リンクの host の義務 6 を一般に書く。core の文からインターフェースの名前を消す。§13 の規則 8 と registry の `target` |
| 0bce222 | §1 の 4、5、§4 の §3.3: 購読は送り出すインターフェースの op（0x30 / 0x32 をすべての op の空間で予約）、heartbeat を無くす、まとめる条件はデータだけ。confirm の uptime_ns、confirm はいつでも、ブローカーの推定 |
| c475dad | §4 の §3.2: ops の符号と、その境のベクタ |
| f48ebe0、18ad0d0 | 利用者の追加の決定: 「標準インターフェース」という区分を無くす。名前は逆 DNS で、project 自身のものだけが短い `oep.` を使う |
