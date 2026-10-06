# OEP インターフェース: 再起動 v1

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作る。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.restart` | 1 | probe 自身を起動し直す | どの系統にも使う |

- host が、probe を抜き差しせずに、おかしな状態になった probe を立て直すためのもの。
- `oep.probe.restart` は任意のインターフェースである。probe が list に出す `oep.probe.restart` は高々 1 つ。

## 1. 操作

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x01 | restart | [TLV] | —（固定部分は無い。応答の後に probe が再起動する） | 必要 | 必須 |

describe（core §7.4 の共通の tag のほか）:

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | restart_max_ms | u32。**必須**。restart の応答が経路を出てから、probe が同じ経路で confirm にまた答えるまでの最長の時間（ms）。USB の経路では列挙し直す時間を、TCP の経路では待ち受け直す時間を含む。`restart_after_answer_ms`（100、registry）以上で、値は probe が決める |

## 2. restart

- **ロックが要る**（core §6.3）。restart は要求の TLV を定めない: 要求の TLV は core §2.3 のとおり（critical なら rejected unsupported、
  そうでなければ無視する）。
- **応答が先**: 受け付けた restart に、probe は completed success で答える（payload は無い）。restart は completed failed /
  partial を返さない。
- **応答の後**: probe は、その応答が経路を出てから（応答の最後の byte を経路に渡し終え、probe が分かる所ではそれが送られてから）再起動を始める。
  始めるのは、そこから多くても `restart_after_answer_ms`（100 ms、registry）のうち。応答を送ってから再起動するまで、probe はどの経路の要求も
  処理せず（答えない。同じ経路で restart の後ろに来ていた要求も同じ）、通知を送らない。
- **再起動の前に線の駆動をやめる**: probe はすべての connection を閉じ（target は必要以上に変えない: reset せず、止めていた hart は止めたまま。
  [線とデバッグ](oep-if-debug.ja.md) §2）、自分で使う channel を除くすべての channel を空きの状態（core §8）にする。
- **再起動の後**は、OEP については電源を入れたときの起動と同じである: boot_id は新しい値（core §6.5）。保存した設定は、どの起動とも同じに適用する
  （保存していない設定は残らない）。channel は core §8 の起動時のとおり空きの状態。シリアルの口の速さは起動時の速さ（[経路](../docs/oep-transports.ja.md) §4）。
  セッション、ロック、core §5.2 の表、購読、plan、connection、ストリームなど、前の起動のものは何も残らない（core §9 の「probe の再起動」の行）。
  前のセッションの id の要求は no_session で断られる。
- **経路**: 再起動のあいだ probe は経路に答えない。USB の経路では device が bus から外れて列挙し直してよく、TCP の接続は閉じてよい。host には
  それが、経路が閉じてまた開くことに見える。
- **戻るまでの時間**: probe は、restart の応答が経路を出てから restart_max_ms のうちに、その応答を送った経路で confirm にまた答える（USB の経路では
  列挙し直したうえで、TCP の経路では待ち受け直したうえで）。

## 3. host

- **待ち方**: restart の応答を受けた host は、その probe にどの経路でも何も送らずに経路を閉じ、少なくとも `restart_after_answer_ms` 待ってから、
  新しく開くのと同じに開き直す: 最初に送るのは confirm で（[経路](../docs/oep-transports.ja.md) §3 の探りの規則。UART bridge では起動時の速さ）、
  USB では device が列挙し直すのを待つ。開けないか confirm に正しい応答が無いあいだ、host は、restart の応答を受けてから restart_max_ms が
  過ぎるまで開き直しと confirm を繰り返す（その間に送った confirm の応答は core §4.4 のとおり待つ）。それまでに正しい confirm の応答が無ければ、
  host はその probe を無くなったものとして扱う: その probe の経路を閉じ、利用者が開き直すまで何も送らない。restart の応答を送った後の probe は
  何にも答えないので、その後に届いた confirm の応答は新しい起動のものである: host はその boot_id が restart の前と違うことを確かめ、core §6.5 の
  とおり覚えた状態をすべて捨てる。
- **応答が来なかったとき**: host は上と同じに開き直し、confirm の boot_id で確かめる（変わっていれば再起動した。同じなら restart は実行され
  なかったものとして扱う）。restart を同じ corr で送り直してもよい（core §5.2）: 再起動した後の probe はそれを no_session で断る（表もロックも無い）。
  その no_session も再起動のしるしで、host は上と同じに開き直して boot_id を確かめる。このときの restart_max_ms は、restart の応答の待ち（core §4.4。
  送り直したときは送り直した要求の待ち）が過ぎた時、または no_session を受けた時から数える。
- **中継する host**（[経路](../docs/oep-transports.ja.md) §1 の中継のブローカー）は、restart を、ほかのロックの要る op と同じに中継する。応答を
  client に返した後は、上の host と同じに probe への経路を閉じる。そこからは [経路](../docs/oep-transports.ja.md) §1 の、probe への経路が無くなった
  ときの規則が掛かる。
