# OEP v1 の規則の変更の提案（2026-10-06）

[English](v1-rule-change-proposal-2026-10-06.md)

状態: **peers が合意し、適用済み（規範ではない）**: すべての項目が規範の文に入った（b4b08f1、40291a4）。ガイドは 5cae93f。この文書は英語版が正で、日本語版はその訳。
読む人: ch32rv（Rust の host と broker）、WireSkein（キャプチャの記録）、bench（HIL の治具）。
元: oep-spec 2e70f40（必須と任意の op）。出典: [3 回目のゼロベース点検](v1-zero-base-review-3-2026-10-02.ja.md)。そこでまだ残っている、規則が変わる指摘（規則）すべてと、必須の op の変更（2e70f40）が扱わなかった C-21 の残りと、ガイドを書くときに見つかった N-1（4bf464d、f951bd8）。

前提は点検と同じ。会ったことのない人が、見たことのない OS、USB スタック、MCU、debug の線、target で、本文だけを読んで probe と host を作る。各項目は、その利用者の場面から書き始める。

**答え方。** 項目ごとに、賛成、反対、条件つきの賛成のどれか。合意の後の作業の順は、これまでと同じく spec → fake → probe → client。

**「今」の言葉。**
- *probe*: oep-probe-arduino の `src/` と例。
- *fake*: oep-client-python の `endpoint.py`（`fake.py`、`fake_serial.py`、`fake_serve.py` とともに）。
- *Python*: oep-client-python の残り。
- *JS*: oep-client-js の `src/`。
- *WireSkein*: wireskein（probe へは Python を通して届く）と、その web の viewer。
- Rust の host は見ていない（ch32rv: 動きが違うところを教えてほしい）。

**壊す** = 今の本文か今の参照のコードに従う実装が、線の上の動きを変えなければならない。

## 答え

ch32rv はすべての項目に賛成し、WireSkein は異議なし、bench も何も挙げなかった（2026-10-06）。ch32rv の注: C-20 と C-47 は自分の側では小さな変更（確かめを足す）。その host は C-36、C-38、C-41、N-1 にすでに従う。C-19 では、最後の session_id での open に resumed = 0 が返ったら、名前 → fn のキャッシュを消す。どの項目も書いたとおりに適用した。ほかに 1 つ、それに伴う直しがある: debug §3 の attach の reset TLV は、もう自分を「reset の op の NRST」と呼ばない（○2）。

## 索引

| id | 場所 | 重さ | 一言 | 壊す | 状態 |
|---|---|:---:|---|---|---|
| C-19 | core §6.5 | ○ | boot_id: 乱数源の無い probe が値をどこから取るかを書く | probe（1 つの代わりの道） | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-20 | core §7.1 | ○ | confirm: max_inflight ≥ 1、window ≥ max_frame と、外れた値を host がどう扱うか | いいえ（host が確かめを足す） | 合意。適用 b4b08f1。ガイド 5cae93f |
| ○2 | debug §4.3、common §1.3 | ○ | reset の method 0 は revision 1 では ndmreset。reset の op はリセットの線を動かさない | いいえ | 合意。適用 40291a4、b4b08f1（registry）。ガイド 5cae93f |
| C-31 | core §2.6a | ○ | 時計は同じ boot_id の間戻らない | probe（1 つのプラットフォームの枝） | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-21（残り） | core §4.3 | ○ | payload の中で指す fn をどこで見るか: 順 5 の終わり | probe、fake（順だけ） | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-36 | core §2.4、§4.1、§4.2 | △ | 見出しより短い message と、向きの違う role は捨てる | host（短い応答 = 壊れた応答） | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-38 | core §5.2 | △ | 送り直しにも答えが無いとき、host はその経路が失敗したとして立て直す | Python、JS（COBS のリンク） | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-39（残り） | core §7.2 | △ | list は同じ boot_id の間変わらない。一致の数を超える first は count 0 | いいえ | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-40 | core §2.6 | △ | 「半分より十分小さく」を数にする: 幅の 4 分の 1。資源の番号は §2.6 から外す | いいえ | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-41 | core §7.5 | △ | transport の interface: CDC は通信の interface。UART bridge は 0xFF | probe（CDC で 0xFF を送る例） | 合意。適用 b4b08f1。ガイド 5cae93f |
| C-47 | core §4.4、§7.5 | △ | max_op_ms に上限（600000 ms）。host が何日も待たない | いいえ（host が確かめを足す） | 合意。適用 b4b08f1。ガイド 5cae93f |
| N-1 | core §4.4 | ○ | 最初の confirm の応答の前の転送時間は min_max_frame（64）を使う | いいえ | 合意。適用 b4b08f1。ガイド 5cae93f |
| △5 | fixture §3 | △ | i2c-target は予約のアドレスを断る（unsupported） | probe、fake | 合意。適用 40291a4。ガイド 5cae93f |
| △6 | fixture §2、§4 | △ | spi の arm の count > length は malformed。TX の無い uart の write は unavailable cause 6 | fake（uart の write） | 合意（console の部分は取り下げ）。適用 40291a4 |
| △9 | capture §1.2 | △ | 符号付きの結果を出す変換器は offset binary で送る | いいえ | 合意。適用 40291a4 |
| △10 | debug §3、registry | △ | rvswd / swio の scan の entry は kind 1 だけ | いいえ | 合意。適用 40291a4、b4b08f1（registry） |
| △12 | core §8 | △ | 起動から、最初の応答の前に、すべての channel を空きの状態にする | probe（1 つの firmware） | 合意。適用 b4b08f1。ガイド 5cae93f |
| PC-9（残り） | probe-config §3.3 | △ | storage_* はページごと。host は最後のページを使う。揃いにはロックが要る | いいえ | 合意。適用 40291a4 |

取り下げ: 上の項目には無い。△6 のうち console の部分（mechanism 0xFF の open）は取り下げる: console §1 がすでに知らない mechanism を unsupported で断り、両方の実装がそうしている。

ついでに見つけたこと（規則の変更ではない。実装の担当へ）:
- probe: plan_apply は role_assignment の fn 0 に unknown_function で答えるが、core §8 の表では malformed（OepEndpoint.cpp の plan_apply のループ）。
- probe: classic ESP32 のアナログの frontend で、範囲が 0 V より上から始まるのに zero を 0 で送る（OepAnalog.cpp:301-304、min_mv を無視）。
- probe: `Oep.h:92` は時計を「一周しない」と書くが、ESP32 / RP2 以外の枝は一周する（C-31）。
- fake: `now_ns` は ms の分解能で、`reboot()` で戻らない。模した再起動の後は「起動から」にならない。
- Python と JS: どの host もハートビートの出来事を読まない。コメントには、ハートビートの boot_id を見ると書いてある。

---

### C-19 ○ 乱数源の無い probe の boot_id

**前提。** 利用者が、ハードウェアの乱数の無い小さな MCU で probe を作る。§6.5 の「不揮発の記憶も乱数源も無い probe も、起動の時間のばらつきなどから、必ず値を変える」を読み、起動のコードの決まった場所でタイマーを読む。タイマーは毎回同じ値を返すので、boot_id は繰り返す。fn の対応を boot_id で覚える host（Python、JS がそう）は、違うインターフェースの並びで書き直された probe にもその対応を使い続け、dmi を違う fn に送る。制約: 本文は、作れないハードがある値を約束できない。だから、どの素をどの順で使ってよいかを書き、host に 2 つ目の手がかりを与える。

**提案する文**（core §6.5。「32 bit の乱数でよい」から「0 はふつうの値」までの文を置き換える）:

> probe は boot_id を、次の好ましい順に取る: ハードウェアの乱数源（32 bit）。不揮発の記憶に置き、起動ごとに変える値（数え上げ、または保存した乱数）。どちらも無ければ、起動ごとに変わる値を混ぜたもの（初期化していない RAM、ADC の入力の変換の雑音、最初の USB や UART の動きなど外からの出来事が来たときの、止まらないタイマーの数）。起動のコードの決まった場所で読んだタイマーは、そうした値ではない。最後の素しか持たない probe は boot_id を繰り返しうるし、host はその確率を受け入れる。0 はふつうの値。
>
> host は open からも再起動を知る: 最後に使った session_id での open に resumed = 0 が返れば、probe はそのセッションをもう知らない（再起動か、間に別の host のセッションがあった）。host は、覚えた fn の対応を使う前に list をやり直す（§7.2）。

**変わること。**
- probe: ESP32 / RP2 以外のプラットフォームは、setup() の中で `micros()` を取る（`platformRandom32`、OepPlatform.h:246-254）。これが「決まった場所」の場合。初期化していない RAM と ADC の読みを混ぜるか、flash に数え上げを置く。`setBootId` を呼ばない sketch は毎回 0 を送る（OepEndpoint.h:192）: ライブラリが自分で値を選ぶようにする。
- fake: 固定の 0x1234ABCD（endpoint.py:538）。試験は `reboot()` に値を渡す。変える必要はない（fake は起動する probe ではない）が、`fake_serve` は乱数を引いてもよい。
- host: Python と JS は、confirm と open で boot_id が変わるとキャッシュを消し、resumed = 2 を掃除済みとして扱う。足す: 自分の最後の session_id に resumed = 0 → list をやり直す。

**今。** ESP32（`esp_random()`）と RP2（`hwrand32()`）の build はハードウェアの素を使う。ほかのプラットフォームは上の決まった場所の場合。

**勧め。** 採る。素の順は実装する人に要るもので、resumed = 0 の規則は host にとってつなぎ直すごとの list 1 回で済む。

---

### C-20 ○ confirm の値の範囲

**前提。** 利用者の probe が、max_frame = 1024 で window = 256（書き間違い）や、max_inflight = 0 を送る。ある host は空かない余地を待って止まり、別の host はかまわず送り、3 つ目は丸める。この応答はどの host も最初に読むもので、host を書く人はそれぞれ推し量ることになる。制約: confirm の固定部分はどのプロトコルの revision でも同じ（§7.1）なので、範囲もどの revision でも成り立たなければならない。

**提案する文**（core §7.1、「flags は予約（0）。」の後）:

> max_frame は 64 以上（§3.3）、window は max_frame 以上、max_inflight は 1 以上。この範囲を外れた confirm の応答を受けた host は、その経路を使えないものとして扱う: そこにはもう何も送らず、値を知らせる。host は flags のビットを無視する（予約、§2.4）。

**変わること。** probe: なし（出しているどの sketch も範囲の中。いちばん小さいのは SwioDebugProbe の window = max_frame = 512）。ライブラリは、範囲を外れた `Limits` を作るときに断ってもよい。fake: なし（window 1 << 18、max_inflight 4）。Python、JS: 確かめを足す（今はどちらも max_inflight 0 を 1 に丸め、window < max_frame を受ける。JS は、64 未満でも、どの max_frame にもフレームの上限を下げる）。

**今。** どの host も、magic と revision のほかは確かめない。

**勧め。** 採る。

---

### ○2 reset の method 0 とリセットの線

**前提。** 利用者が riscv-dm の reset を実装する。method 0 は「probe が選ぶ」で、common §1.3 の mark reset の detail には「probe が選んだとき」の「2 NRST」がある。そこで method 0 でリセットの線を引くようにする。debug §3 は、違う線を引くと target や治具を傷めうるので、リセットの線に既定は無いと言う。利用者の probe はちょうどそれをしている。制約: どの線が動くかを host が知らなければならないので、reset の op が自分で線を選ぶことはできない。

**提案する文。**

debug §4.3、TLV 0x01 method:

> TLV 0x01 method（u8）: 0 probe の既定、revision 1 では ndmreset。1 ndmreset。2 は予約（target のシステムリセットに共通の手順は無いので、host が dmi で組む）。2 以上の method は、この probe が扱えない値（core §2.3: critical で送られれば rejected unsupported、そうでなければ ignored）。**reset の op はリセットの線を動かさない**: リセットの線が動くのは、attach の reset TLV（§3）か、host が自分で治具のインターフェースを使うときだけ。

common §1.3、mark reset の detail:

> 方法（`mark_detail_reset`: 1 ndmreset（reset の op）、3 attach の reset TLV。2 は予約）

registry: `mark_detail_reset.nrst = 2` は予約のコメントにする。

**変わること。** なし。probe と fake: method 0 と 1 はどちらも ndmreset を行い、reset の op はいつも detail 1 を付け、detail 2 は送られない（OepTarget.cpp:773-813、endpoint.py:2087-2097）。

**今。** 上のとおり。

**勧め。** 採る。皆がしていることを書くだけ。ほかの道（method 0 に線を選ばせる）は debug §3 とぶつかる。

---

### C-31 ○ 時計は戻らない

**前提。** 利用者が、時計が 32 bit の µs の数を ns に直したものである probe で、長いキャプチャを記録する。71.6 分で一周する。WireSkein は 2 つの start_ns を引き算してアナログのトラックを置く（`oep.py:402-404`）ので、トラックは 71.6 分ずれる。web の viewer もトリガを引き算で置く。boot_id は変わらないので、host には何も知らされない。制約: §2.6a は時計を「起動からの ns（u64）」と呼び、注意深い読み手は減らないと読むが、そうとは書いていない。そして §2.6 はインターフェースの時刻の一周を許す。

**提案する文**（core §2.6a、最初の文の後）:

> 時計は、同じ boot_id の間、減らず、一周しない。ハードウェアの数え器が 64 bit より狭い probe は、ソフトウェアで広げ（一周の数を数える）、一周を見逃さないだけの頻度で読む。

**変わること。** probe: ESP32 / RP2 以外のプラットフォームの `nowNs`（Oep.h:95-103）は、32 bit の `micros()` で `micros() * 1000`。一周の数で広げる（main loop は 71 分に 1 回よりずっと多く読む）。fake: 単調（`time.monotonic()`）、変えない。host: 変えない。

**今。** ESP32 と RP2 は 64 bit の数え器を使う。ほかの枝は 71.6 分で一周する。

**勧め。** 採る。

---

### C-21（残り）○ payload の中で指す fn をどこで見るか

**前提。** 利用者の host が、fn の無い role_assignment と、長さの壊れた別の割り当てを持つ plan_apply を送る。ある probe は unknown_function、別の probe は malformed で答える。1 つの理由を期待する適合の試験は、半分の probe で落ちる。§4.3 は「payload の中で指す fn が無いときは unknown_function を使い回す」と言うが、順のどこかは言わない。制約: §4.3 の順は、probe に要求全体の書式の確かめ（順 5）を順 6 の前に終えさせているので、fn の確かめは新しい走査なしにその間に入る。

**提案する文**（core §4.3、順 5 に足す）:

> 5. …。書式が正しければ続けて: payload の中で指す fn（describe、subscribe、unsubscribe、plan_apply、probe.config の項目）が無い → unknown_function。

そして「payload の中で指す fn が無いときは、unknown_function を使い回す。」は「…使い回す（順 5 の終わりで）。」にする。

**変わること。**
- probe: fn を項目ごとに、各項目のほかの確かめと混ぜて見る。plan_apply は長さのループの中で TLV ごとに fn を見る（そして fn 0 に unknown_function で答えるが、§8 では malformed）。probe.config の set は各項目を確かめ終えてから次へ進むので、前の項目の unknown_function や unsupported が、後の項目の malformed に勝つ（OepConfig.cpp:626-656）。どちらも malformed の走査を先にする。
- fake: plan_apply は知らない critical の tag（unsupported）を unknown_function の前に、いくつかの malformed をその後に見る（endpoint.py:1383-1388）。probe.config の set は dict の順で混ぜる（endpoint.py:2926、2962、3064-3120）。同じ変更。
- describe と subscribe は、どちらも提案の順にすでに従う。

**今。** 上のとおり。どの理由が先に来るかに頼る host は無い。

**勧め。** 採る。ほかの道: 長い payload では「要素ごとに順に」を許す。勧めない: §4.3 の順 5 / 6 の規則が payload によって変わり、適合のベクタが壊れる。

---

### C-36 △ 短い message と、向きの違う role

**前提。** 利用者の host に虫があって 4 byte の要求を送る、または bridge が probe の応答を probe へ返してしまう。§2.4 は知らない role を捨てるが、0x02 は知っている role。probe が受け取った応答をどうするか、fn と op を入れられないほど短い要求をどうするかは書かれていない。host の側では、5 byte の見出しより短い応答に、Python と JS は壊れた応答として扱わず、要求から例外を投げる。制約: corr を入れられないほど短い message には答えられず、session_id の無い要求は §5.2 で確かめられないので、いちばん簡単な規則は捨てること。

**提案する文**（core §2.4、「知らない role のフレームは捨てる。」の後に足す）:

> - probe は、role が要求の role（0x01、0x81）でない message と、見出し（6 byte、session_id つきなら 10 byte）より短い要求を、答えずに捨てる。host は、role が要求の role の message を捨てる。
> - host は、5 byte より短い応答と、見出しより短い出来事やデータのフレームを、壊れたフレームとして扱う（§5.1、§5.2）。

**変わること。** probe: なし（どれも捨てる、OepEndpoint.cpp:388-395）。fake: なし（経路が捨てる）。Python、JS: corr が合う 3 か 4 byte の応答は `ShortPayload` を投げる。壊れたものとして扱う（送り直す、§5.2）。

**今。** 上のとおり。probe からの向きの違う role は、どちらの host も捨てる。

**勧め。** 採る。ほかの道: corr を読めるなら malformed で答える。勧めない: 適合する host はそうした message を送らず、session_id の無い 0x81 の要求への応答は §5.2 の表に入れられない。

---

### C-38 △ 送り直しにも答えが無いとき

**前提。** 利用者の probe が、COBS のシリアルの口で要求が出ている間にリセットする。host の待ち時間が過ぎ、1 回送り直し（§5.2）、送り直しにも答えが無い。§5.2 はそこで終わる。Python と JS はタイムアウトを投げ、何もなかったように口を使い続ける。次の要求は、再起動した（新しい boot_id、セッションなし）か、今は別の速さで動く probe に届くかもしれない。制約: COBS は区切りを自分で取り戻すので、§5.1 は今は当てはまらないが、ここでの原因は区切りではない。

**提案する文**（core §5.2、最初の項目の後）:

> - 送り直しの待ち時間も答えなしに過ぎたら、host はその経路が失敗したとして扱う: その要求の結果は分からず、その経路で出ている要求もいっしょに失敗する。そこで何かを送る前に、host は §5.1 の confirm で立て直す（COBS を含むどの種類のフレームでも: 入力が静かになってから、自分の corr を持つ応答が返る confirm）か、経路を閉じて開き直す。その confirm で boot_id が変わっていれば再起動（§6.5）。立て直した後、host は状態を変える要求を繰り返す前に状態を読む。

**変わること。** probe、fake: なし。COBS のリンクの Python と JS: 今は例外を投げて口を保つ。confirm を足す。長さで区切るリンクでは、どちらもすでに区切りを取り戻す。（JS と Python は、上げた port_speed から先に戻る。それは残す、§3.5。）

**今。** 上のとおり。

**勧め。** 採る。

---

### C-39（残り）△ list は起動の間変わらない。ページの終わり

**前提。** 利用者が、モジュールを差すとインターフェースが現れる probe を書く。host は、§7.2 が許すとおり、同じ boot_id の間 名前 → fn を覚える（Python、JS がそう）。新しいインターフェースは見えず、外したものは宙に浮いた fn を残す。§7.2 は起動の間 fn が変わらないとは言うが、list が変わらないとは言わない。そして §7.3 の「ページの終わり」の規則は describe や state などを挙げるが list は挙げないので、一致の数を超える first で list を聞いた host は、何が返るかを知れない。

**提案する文**（core §7.2、最後の項目を置き換える）:

> - list の応答（どのインターフェースがあるか、その fn、instance、revision、名前）は、同じ boot_id の間変わらない。インターフェースが増えたり減ったりする probe は再起動する（新しい boot_id）。host は、同じ boot_id の間、名前から fn への対応を覚えてよい。
> - first が一致する entry の数以上なら、応答はその total と count 0。

**変わること。** probe: どの sketch も setup() でインターフェースを足す。ライブラリは後の `add()` もまだ受ける（OepEndpoint.cpp:58-63）: 最初の `poll()` の後は断る。fake: 作るときに決まる。どちらもすでに、本当の total と count 0 で答える。host: 変えない。

**今。** 上のとおり。

**勧め。** 採る。

---

### C-40 △ 一周する値: 「半分より十分小さく」を数に

**前提。** 利用者が u32 の serial と輪で marks を実装し、生きている 2 つの serial がどこまで離れてよいかを問う。§2.6 は「その幅の半分より十分小さく」と言い、確かめられる数ではない。また資源の番号を挙げるが、どの規則も資源の番号を大小で比べない（§9 は代わりに使い回しの距離を使う）。制約: 上限は、どの probe も自分のバッファで守れるものでなければならず、資源の番号は §9 だけで決まるままにしなければならない。

**提案する文**（core §2.6、段落を置き換える）:

> seq（u16）と、インターフェースが定める連番と時刻のうち一周すると定めたものは、同じ幅 w の符号付きの値として差を取って比べる（連番の算術）。そうした 1 つの空間の値のうち、probe が同時に持つもの（まだ読める marks、まだ解放されない区画、まだ読まれない置き場）では、いちばん新しいものからいちばん古いものを引いた差は 2^(w−2)（幅の 4 分の 1）未満。一周しない値は u64（ストリームの位置、標準インターフェースの時刻など）。資源の番号（§9）は等しいかどうかだけを比べ、使い回しは §9 で決まる。

**変わること。** 線の上では無い。probe: marks の serial（u32）と置き場（u8）は上限のずっと内側。`OepStream.h:66, 90` は `serial_ < mark_capacity_` を一周の算術なしに比べ、キャプチャの区画の serial は `<` で比べる（start ごとに戻る）: どちらも 2^32 の前には届かないが、直す価値がある。fake: マスクで一周する。資源の番号は 1〜65535 で、生きているものを飛ばす。

**今。** 上のとおり。

**勧め。** 採る。ほかの道: 文を消す。勧めない: marks を比べる host には上限が要る。

---

### C-41 △ transport がどの USB の interface を指すか

**前提。** 2 台の probe をつないだ計算機の上で、利用者の host が、シリアルの口と describe の transport の entry を対応させたい（どの口が UART bridge かを知るため、§4.4 の転送時間）。USB CDC の機能は interface を 2 つ持ち（通信と data）、よく使われる host では OS は最初のもの（通信の interface）で口に名前を付ける。§7.5 は「USB の interface 番号」と言うだけで、どちらかを言わない。また UART bridge（別の USB のチップ）は host にとっては USB だが、probe にとってはそうでない。制約: probe が自分の descriptor から値を知れなければならない。

**提案する文**（core §7.5、行 0x49 transport の interface の欄）:

> interface（u8）: USB CDC（kind 2）は CDC の通信の interface の bInterfaceNumber（その機能の最初の interface）。内蔵の USB シリアル（kind 3）は、ハードウェアが見せるその同じ番号、probe が知れなければ 0xFF。vendor bulk と HID はその interface の番号。UART bridge（kind 1）と TCP は 0xFF。

**変わること。** probe: ESP32-P4 は 2（CDC の組の通信の interface）を、RP2 の firmware は 0 を送り、どちらも提案のとおり。番号を渡さない例（RP2 の MinimalProbe、FixtureProbe、RvswdDebugProbe）は、CDC の transport に 0xFF を送る: 番号を渡す。fake: CDC は 2 / 0、UART bridge と TCP は 0xFF で、提案のとおり。host: JS は値を読むが、まだだれも使わない。

**今。** 上のとおり。

**勧め。** 採る。

---

### C-47 △ max_op_ms の上限

**前提。** 利用者の probe が max_op_ms = 0xFFFFFFFF（初期化し忘れた定数）を宣言する。Python の `run(timeout_ms=None)` は約 49.7 日待つ。JS は 4.29e9 ms を `setTimeout` に渡し、あふれて約 1 ms になるので、要求は送り直され、すぐに失敗する。どちらでも利用者には止まったか、わけの分からない失敗に見え、§4.4 は待ち時間を下限にしているので、host は短くできない。制約: 上限は、probe が正当に取りうるいちばん長い 1 つの操作（長い run、flash への保存）を覆わなければならない。

**提案する文。**

core §7.5、行 0x4D max_op_ms、「**必須。**」の後:

> 1〜600000（`max_op_ms_max`、10 分）。

core §4.4、「この下限より長く待つのはいつでもよい。」の後:

> max_op_ms が 0 か `max_op_ms_max` を超えると読んだ host は、その probe を適合しないものとして扱い、使わない。

registry: `limits.max_op_ms_max = 600000`。

**変わること。** probe と fake: 10000、変えない。Python、JS: 確かめを足す。

**今。** どの host も待ち時間に上限を置かない。

**勧め。** 採る。ほかの道: host が自分の上限で待ち時間を切ってよいとする。勧めない: 切った待ち時間は、probe がまだ実行しているかもしれない状態を変える要求の結果を、分からないままにする。

---

### N-1 ○ 最初の confirm の応答の前の転送時間

**前提。** 利用者が UART bridge のための host を書く。core §4.4 は、最初の confirm を含むどの要求の待ち時間にも、(L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud の転送時間を足させるが、max_frame は confirm の応答の値で、host はまだ持っていない。ある host は 65535 と推し量り、115200 baud で最初の confirm に 17 s 待つ。別の host は 0 を使い、早くあきらめる。制約: 経路での最初の confirm の前に host が送ってよい message は 64 byte まで（§3.3）で、前のセッションから残った通知の束と重なった confirm は、長い待ち時間ではなく、§3.3 と §3.5 の繰り返す confirm で覆われる。

**提案する文**（core §4.4、「転送時間は …」の中、「baud は口の今の速さ。」の後）:

> その経路で confirm の応答を受け取るまで、host は max_frame として `min_max_frame`（64）を使う。その後は、そこでのいちばん新しい confirm の応答の max_frame を使う。

**変わること。** なし。Python（`link.py:291`、`self.max_frame = reg.MIN_MAX_FRAME`）と JS（`link.js:203`、`probeMaxFrame` は `reg.MIN_MAX_FRAME` から始まる）はすでにそうしている。probe と fake: 関わらない。

**今。** 上のとおり。

**勧め。** 採る。

---

### △5 i2c-target: 予約のアドレス

**前提。** 利用者が、DUT の general call を試すために i2c-target をアドレス 0x00 で、あるいは誤って 0x78 で configure する。この番号を断る I2C の target の周辺回路もあれば、バスの上のすべての general call やすべての 10 bit の見出しに答えて、DUT のほかの target を乱すものもある。今の本文はそれらを受け、何も言わない。制約: 7 bit の欄はそれらを許し、後の revision は general call を望むかもしれないが、それは revision を変えずに features のビットで足せる（§2.7）。

**提案する文**（fixture §3、configure の項目、「address が 0x7F を超えれば rejected malformed。」の後）:

> 0x00〜0x07 と 0x78〜0x7F のアドレス（I2C の仕様が予約するもの: general call、start byte、10 bit の前置きなど）は rejected unsupported（payload `0x00`）。

**変わること。** probe（OepP4I2cTarget.cpp:294）と fake（endpoint.py:2505）: 今はどちらも受ける。確かめを足す。

**今。** 上のとおり。

**勧め。** 採る。

---

### △6 spi の arm の count > length。TX の無い uart の write

**前提。** 利用者の host が、送る 8 byte と length 4 で spi-target を arm する、あるいは plan が RX だけの fixture.uart に write する。本文は「count ≤ length」と言うだけで、TX の無い write には何も言わないので、ある probe は切り詰め、別の probe は受けてバイトを捨て、3 つ目は断る。制約: count > length は要求の中の食い違い（§4.3 の順 5 で malformed）。TX の無い write は plan の状態（unavailable、cause 6）。

**提案する文。**

fixture §4、arm の項目: 「（count ≤ length。足りない分は 0）」を次にする:

> （count ≤ length。count > length は rejected malformed。足りない分は 0）

fixture §2、TX の線の項目の後:

> - plan に TX の無い fn への write は rejected unavailable（cause 6）。

（指摘の console の部分、mechanism 0xFF の open は取り下げる: console §1 がすでに知らない mechanism を unsupported（payload `0x00`）で断り、両方の実装がそうしている。）

**変わること。** probe: どちらもすでに（OepP4SpiTarget.cpp:303、OepFixture.cpp:400）。fake: spi はすでに malformed（endpoint.py:2631）。uart の write は TX なしでも受ける（endpoint.py:2488-2490、2268-2273）: 確かめを足す。

**今。** 上のとおり。

**勧め。** 採る。

---

### △9 符号付きの変換の結果

**前提。** 利用者が、結果が 2 の補数である差動の ADC でアナログの probe を作る。capture §1.2 は slot のビットを「変換の結果（符号なし）」と言うので、「この probe は OEP のアナログの probe になれない」と読めるか、利用者が 2 の補数を送り、どの host も誤って換算する（Python、JS、WireSkein とそのファイルの形は、どれも符号なしで読む）。制約: host は 1 つの換算、(value − zero) × scale_nv を保たなければならず、slot の配置は probe が DMA の記録をそのまま送れるようにしている。値ごとの処理は、速い rate では CPU を食う。

**提案する文**（capture §1.2、規則 1 に足す）:

> 結果が符号付き（b bit の 2 の補数）の変換器は offset binary で送る: probe は各値の bit b−1 を反転し（2^(b−1) を足して 2^b で割った余り）、返す zero はその分を含む（0 V の値）。

**変わること。** 今は無い（符号付きの変換器を持つ probe は無い）。将来の probe は値ごとに XOR を 1 回払う。

**今。** probe: 符号なしの 12 bit の値、zero 0。fake: 符号なしの 12 bit。host: 符号なしだけ。

**勧め。** 採る。ほかの道: configure の応答に「符号付き」の欄を置き、DMA の記録を変えずに出せるようにする。勧めない: どの host も扱わなければならない固定部分の欄を、どれも持たない場合のために足すことになり、値ごとの XOR は転送に比べれば小さい。

---

### △10 rvswd / swio の scan の kind

**前提。** 利用者が debug §3 を読む: rvswd と swio の scan の entry の kind は「1 = riscv-dm、2 = arm-adi」。2 線や 1 線の線から arm-adi の connection ができるのか、できるなら swd の非対称（§5: slot も console も乗らない）がそれにも効くのかを問う。どちらの実装もそうせず、この線の上で ADI を話す target も無い。制約: ADI を運ぶ後の線は、自分の文書を持つ新しい線（§0）なので、ここを閉じても何も失わない。

**提案する文。**

debug §3: 「scan の kind は `scan_kind`: 1 = riscv-dm、2 = arm-adi。`id` は線の種類で決まる生の識別子（riscv-dm なら DMSTATUS、arm-adi なら DPIDR）。」を次にする:

> rvswd と swio の scan の entry の kind は 1（riscv-dm）で、id は DMSTATUS。その connection を使うのは `oep.target.riscv-dm` と `oep.target.console`。

registry: `oep.wire.rvswd` と `oep.wire.swio` の `scan_kind` の enum から `arm_adi = 2` を外す（`oep.wire.swd` の下には残す）。

**変わること。** なし。probe: scan は kind 1 だけを書く（OepTarget.cpp:403）。arm-adi は swd の connection だけを受ける（OepSwd.cpp:516-518）。fake: kind 1 だけ（endpoint.py:1815）。JS は kind をそのまま渡す。

**今。** 上のとおり。

**勧め。** 採る。

---

### △12 起動からのピンの状態

**前提。** 利用者が `oep.probe.config` を持たない probe を作り、DUT につなぐ。core §8 は解放したピンが何をするかを、probe-config は保存した設定が起動時に何をするかを言うが、起動から plan がピンを取るまでピンが何をするかは、どこにも無い。リセットから出たときにプルの付いたピンを持つ MCU では、DUT は最初の plan まで引かれた線を見る。別の MCU では、firmware が周辺回路の出力を入れたままにする。制約: 電源を入れてから firmware が動くまで、ピンは MCU のリセットの状態で、本文はそれを変えられない（probe-config §5 がそう言う）。また、いくつかのピンは probe 自身のもの（`reserved`）。

**提案する文**（core §8、解放したピンの項目の後）:

> - **起動時**、probe は最初の要求に答える前に、reserved（§7.5）でないすべての channel を空きの状態にする（上: 設定が idle を定めればその idle、そうでなければ Hi-Z: 入力、プルなし）。それまでピンは MCU のリセットの状態（参考: 誤った水準が害になる線には外付けのプルが要る、[probe の設定](../interfaces/oep-if-probe-config.ja.md) §5）。

**変わること。** probe: RP2 と classic ESP32 の firmware、FixtureProbe / ProbeConfig の例は、起動時にすべての channel を浮いた入力にしまい、提案のとおり。ESP32-P4 の firmware は、ピンをチップが起動したときのままにする（Esp32P4.h:193）: しまう呼び出しを足す。設定で disable にした channel は、probe-config §1 のとおり触らない。fake: ピンが無い。

**今。** 上のとおり。

**勧め。** 採る。

---

### PC-9（残り）△ state のページングと storage_*

**前提。** 利用者の見張りの host が、ロックなしで probe.config の state をページで読み、その間に別の host が保存する。1 ページ目は storage_state 0、2 ページ目は新しい hash で 1 と言う。本文は、どちらを信じるか、ページの間で slot の行がずれうることを言わない。制約: state はわざとロックなし（§3.3）で、probe には読み手のために写しを持つ余地が無い。

**提案する文**（probe-config §3.3、ページングの項目の後）:

> - 各ページは、storage_state、storage_hash、unreadable_reason を、そのページに答えたときの値で運ぶ。ページの間で違いうるし、host は最後のページのものを使う。slot と bind もページの間で変わりうる（ロックを持つ側の set や save、自動の attach）。ページをまたいで slot と bind の組が変わらないことが要る host は、ロックを持ってページを読む（slot の状態はそれでも変わりうる）。

**変わること。** なし。probe と fake はページごとに値を取る。JS は最後のページの値を保つ（Python は見ていない）。

**今。** 上のとおり。

**勧め。** 採る。
