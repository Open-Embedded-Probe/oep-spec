# OEP 標準インターフェース: リンク v1

[English](oep-if-link.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](versioning.ja.md) §6）。本体は [OEP core](oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.link` | 1 | 経路を試し（線の試験）、セッションの間だけ UART bridge の口の速さを上げる（port_speed） |

- `oep.link` は任意の標準インターフェースである。port_speed を持つ probe はこれを list に出す。線の試験だけのために出してもよい。probe が
  list に出す `oep.link` は高々 1 つ。
- その op は、port_speed が変える口の速さのほか、probe の状態を変えない。

## 1. 操作

| op | 名前 | 要求 | 応答 | ロック | 必須 |
|---:|---|---|---|---|---|
| 0x01 | source | length(u32)、[TLV] | len(u16)、data、[TLV] | 不要 | 必須 |
| 0x02 | sink | count(u16)、data、[TLV] | — | 不要 | 必須 |
| 0x03 | port_speed | port(u8)、baud(u32)、step(u8: 0 試す、1 決める、2 戻す)、verify_ms(u16)、idle_ms(u32)、[TLV] | baud(u32: 実際に掛かる速さ)、[TLV] | 必要 | 任意 |

port_speed は任意で、describe の ops で宣言する（core §1.2、§7.4）。それを持たない probe は unknown_operation で答える。

## 2. 線の試験（source、sink）

source と sink は経路の速さを測るためのもの。状態を変えない。

- **source**: data は len バイトで、k バイト目（k は 0 から）は k & 0xFF。len は length と、要求の来た経路の max_frame の 1 つの message に応答の
  ほかの部分と一緒に入る最大の data の、小さいほう（core §4.4）。length 0 なら len 0。
- **sink**: count の後ろに、値が任意の count バイトが続く。count が後ろに続くバイトより大きければ rejected malformed。応答は completed success で、
  payload は空（ignored を除く、core §2.3）。
- host はその応答を、ほかの要求と同じように待つ（core §4.4）。confirm のようには繰り返さない。

## 3. port_speed

port_speed は、UART bridge の口で、セッションの間だけリンクの速さを起動時の速さより上げる。用途は大きな書き込み、キャプチャ、
コンソール（線の block op の時間はデバッグの線の往復で決まり、リンクでは変わらない）。probe の
fixture UART の速さは別（そのインターフェースの configure と設定）。この節が決めるのは**握手**だけである。どの速さを候補にするか、
通ったとみなす基準、使っている間に戻す基準は host が決める（参考の手順:
[host 開発ガイド](host-development-guide.ja.md) §17）。

**語の定義**

- **起動時の速さ**: 115200 bps（transports §4）。probe のすべての戻り先。
- **候補**: host が試す速さの並び。probe は候補を宣言しない（通る速さは変換チップと OS で決まり、probe には分からない）。この仕様は
  候補も既定も決めない。
- **流し方**: 向き（probe → host、host → probe、両方向）と同時数 n の組。host の確かめと記録の語として使う（この仕様は流し方を
  決めない）。
- **壊れ**（probe 側）: transports §4 の受け方で、0x00 で閉じた候補のうち解けないか CRC の合わないもの。0x00 だけの区切りと、0x00 の外で来た
  バイトは数えない。

**probe**

- 対象は transport kind 1（UART bridge）の口だけ。
- port: この要求の来た経路の index（core §7.5）（confirm の応答の transport TLV、core §7.1）。
- 断り: port がこの要求の来た口でない → rejected unavailable（cause 6）。UART が作れる最も近い速さが要求と 2 % より大きく違えば rejected unsupported。応答の baud は実際に掛けた速さ。
  step 0（試す）の verify_ms 0 は rejected malformed。step 1（決める）と step 2（戻す）では verify_ms に意味は無く、どの値も受ける。
  step が 3 以上なら rejected unsupported（payload の tag 0x00、core §2.5）。
  ロックが無い・違うときの断りは core §4.3 の順（session_required、no_session、locked）。
- 状態は口ごとに **起動時 / 試し / 決めた** の 3 つ。
  - **試す**（step 0、起動時の状態で受ける）: 応答を今の速さで送り終えてから、応答の baud に切り替えて**試し**になる。verify_ms を
    この要求の値で始める。
  - **決める**（step 1、試しの状態で、同じ baud、新しい速さで受ける）: **決めた**になる。idle_ms をこの要求の値で始める（最長
    port_speed_idle_max_ms = 3000 ms。0 とそれより長い値は最長として扱う）。
  - **戻す**（step 2、試し・決めたのどちらでも）: 応答（baud は起動時の速さ）を今の速さで送ってから起動時の速さに戻る。
  - 状態に合わない step（起動時の状態で決める、決めた後に決める、起動時の状態で戻す、試し・決めたの口で試す、試している baud と違う baud で
    決める）は rejected unavailable（cause 6）。probe は同時に 1 つの口だけ上げる: 上げている口がある間に別の口で試すが来たら、その応答を
    送ってから上げていた口を起動時の速さに戻し、新しい口を試しにする。
- **probe が自分で起動時の速さに戻る条件**（戻ったことは知らせない）:
  1. 試しのまま verify_ms が過ぎた。
  2. 試しの状態で、新しい速さで正常なフレームを 1 つ受けた後、その口に壊れが 1 つ来た（切り替えの直後、新しい速さで最初の正常な
     フレームが来るまでの壊れは数えない）。
  3. 決めた後、その口に正常なフレームが idle_ms 来ない。idle_ms は正常なフレームを受けた時と応答を送った時から数え直す（要求を実行して
     いる間は進まない。lease と同じ、core §6.1）。
  4. 決めた後、正常なフレームを挟まず壊れが 3 つ続いた（registry の `port_speed_broken_max`）。
  5. セッションが終わった（end、lease の期限切れ、force で持ち主が替わった）。end と force は応答を送ってから戻る。
- 試しと決めるの間、セッションの資源とロックは変わらない。生の転送（transports §4）はセッションの間止まっている。

**host の義務**

1. UART bridge（transport kind 1）の口から、ロックを持って送る。
2. 試すの応答を受けたら、要求した baud（作れなければ応答の baud）に切り替え、20 ms 以上（registry の `port_speed_switch_wait_ms`）待ってから confirm で新しい速さを確かめる。
3. verify_ms のうちに決めるを送るか、送らずに probe が戻るのを待つ（verify_ms 経過後に起動時の速さで confirm）。
4. 上げている間は keepalive か他の要求を idle_ms の半分より短い間隔で送る。
5. 上げた速さで応答が待ち時間（core §4.4）に来なければ、起動時の速さに戻して confirm を繰り返す（port_speed_idle_max_ms + 1000 ms を上限。registry の `port_speed_confirm_extra_ms`）。
   probe がまだ上げた速さに居ても、起動時の速さの confirm は probe に壊れとして届き、正常を挟まず 3 つで戻る（戻る条件 4）ので収束する。
   通れば（boot_id が同じなら戻っただけ、違えば再起動）そのセッションでは起動時の速さで続ける。上限の間 confirm が通らなければ
   リンクの失敗（上げた速さに戻って待ち直すことはしない）。
6. 戻すの応答を受けたら、または end の応答を受けたら、起動時の速さに切り替える。
7. どの速さを候補にするか、確かめの流し方、通ったとみなす基準、使用中に戻す基準は host が決める（参考: [host 開発ガイド](host-development-guide.ja.md) §17）。

UART bridge の口を開くどの host も、port_speed を使うかどうかにかかわらず、transports §4（「上げた速さの後」）のとおりそこで confirm を繰り返し、前の host が上げた速さを待ち切る。

上の待ち（新しい速さを確かめる confirm の前の 20 ms 以上、verify_ms、idle_ms、confirm の繰り返し）は要求と要求の間の時間で、応答を
待つ時間ではない。その間に送るどの要求についても core §4.4 の host の待ち時間を縮めない。host の義務 5 の confirm は、それぞれ新しい corr の
新しい要求で、送り直しではない（core §4.4）。
