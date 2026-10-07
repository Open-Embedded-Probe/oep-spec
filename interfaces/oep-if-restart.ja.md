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
| 0x40 | restart_max_ms | u32。**必須**。restart の応答が経路を出てから、probe が同じ経路で confirm にまた答えるまでの最長の時間（ms）。USB の経路では列挙し直す時間を、TCP の経路では待ち受け直す時間を含む。値は probe が決める |

## 2. restart

- **ロックが要る**（core §6.3）。restart は要求の TLV を定めない（要求の TLV は core §2.3 のとおり）。
- **応答が先**: 受け付けた restart に、probe は completed success で答える（payload は無い）。restart は completed failed / partial を返さない。
- **応答の後**: probe は、その応答を送った後、再起動するまで、どの経路の要求にも答えず（同じ経路で restart の後ろに来ていた要求も同じ）、通知を送らない。
- **target**: 再起動は target を reset せず、止めていた hart を止めたままにする（connection を閉じるときと同じ、[線とデバッグ](oep-if-debug.ja.md) §2）。
- **再起動の後**は、OEP については電源を入れたときの起動と同じである: boot_id は新しい値（core §6.5）で、前の起動のものは何も残らない（core §9 の
  「probe の再起動」の行）。シリアルの口の速さは起動時の速さ（[経路](../docs/oep-transports.ja.md) §4）。
- **経路**: 再起動のあいだ probe は経路に答えない。USB の経路では device が bus から外れて列挙し直してよく、TCP の接続は閉じてよい。
- **戻るまでの時間**: probe は、restart の応答が経路を出てから restart_max_ms のうちに、その応答を送った経路で confirm にまた答える（USB の経路では
  列挙し直したうえで、TCP の経路では待ち受け直したうえで）。中継のブローカー（[経路](../docs/oep-transports.ja.md) §1）の client には、この時間は掛からない:
  probe が再起動するとブローカーの probe への経路が無くなってブローカーは終わり、client は経路が閉じたときと同じにやり直す（経路 §1）。

host の待ち方と開き直し方は [host 開発ガイド](../docs/host-development-guide.ja.md) §5.2。
