# v1 の 3 回目のゼロベース点検（2026-10-02）

状態: **記録**（規範ではない。点検）。対象は oep-spec 82e6b9f。直すかどうか、どう直すかは、この後にユーザーと peers（ch32rv / WireSkein / bench）で決める。

## 対応の状態（2026-10-06）

各指摘の見出しの下（△ の表は「状態」の列）に、今の規範の文（英語版 `.md`）と registry で確かめた状態を書いた。対応済み = 規範に入った（commit と節）、決着 = ユーザーが決めた、取り下げ = 直さないと決めた、未対応 = まだ。規則の変更は [規則の変更の提案](v1-rule-change-proposal-2026-10-02.md) の index（applied）とも突き合わせた。

| 部 | 対応済み | 決着 | 取り下げ | 未対応 | 計 |
|---|---:|---:|---:|---:|---:|
| 1 部（core、registry） | 35 | 2 | 0 | 10 | 47 |
| 2 部（標準インターフェース） | 29 | 0 | 2 | 6 | 37 |
| 3 部（probe-config、ガイド、OSS） | 17 | 4 | 0 | 14 | 35 |
| 計 | 81 | 6 | 2 | 30 | 119 |

数は ★ / ○ / △ のすべての指摘（見出しの 94 件と、△ の表の 25 件）。

**未対応**（第三者のレビューの前に残っている仕事。★ が先）:

| id | 部 | 重さ | 一言 |
|---|---:|:---:|---|
| O-8 | 3 | ★ | 適合の確かめ方（第三者の probe を点検する手順と道具） |
| C-19 | 1 | ○ | boot_id の「必ず値を変える」は乱数源も保存も無い MCU では作れない |
| C-20 | 1 | ○ | confirm の値の制約（max_inflight ≥ 1、window ≥ max_frame、外れた応答の扱い） |
| C-21 | 1 | ○ | payload の中の fn の unknown_function を §4.3 の順のどこで見るか |
| C-31 | 1 | ○ | 時計は同じ boot_id の間減らない（規則と判断、peers へ） |
| ○2 | 2 | ○ | reset の method 0「probe が選ぶ」と「reset の線に既定は無い」がぶつかる |
| G-1 | 3 | ○ | 最小の host / probe までの道（手順、バイト列、チェックリスト） |
| G-2 | 3 | ○ | host ガイドに断りごとの動き、通知、probe.config の手順、fake |
| G-3 | 3 | ○ | ガイドからチップ固有の話と実測を記録へ移す |
| G-4 | 3 | ○ | probe ガイドの古い記述（仮置き、115200 固定、日付） |
| G-5 | 3 | ○ | probe ガイドに識別子と宣言の選び方 |
| G-6 | 3 | ○ | host / probe ガイドの英語版 |
| O-7 | 3 | ○ | 版と凍結の方針を独立の文書に、タグ、CHANGELOG |
| O-12 | 3 | ○ | 安全とセキュリティ（参考）の節 |
| O-13 | 3 | ○ | 用語集（ja / en） |
| R-1 | 3 | ○ | 実装の README の spec への入口（oep-client-python ほか） |
| C-36 | 1 | △ | 見出しより短い message と向きの違う role の扱い（規則と判断、peers へ） |
| C-38 | 1 | △ | 送り直しにも答えが無いときはリンクの失敗（規則と判断、peers へ） |
| C-39 | 1 | △ | list が同じ boot_id の間変わらないこと、first ≥ total（§7.2「ports」は済み。残りは規則と判断、peers へ） |
| C-40 | 1 | △ | §2.6「十分小さく」に値が無い（規則と判断、peers へ） |
| C-41 | 1 | △ | CDC の transport の interface 番号はどちらか（規則と判断、peers へ） |
| C-47 | 1 | △ | host は自分の上限で待ち時間を切ってよい（規則と判断、peers へ） |
| △5 | 2 | △ | i2c-target の予約のアドレスの断り方（規則と判断、peers へ） |
| △6 | 2 | △ | spi arm の count > length、TX の無い uart の write などの断り方（規則と判断、peers へ） |
| △9 | 2 | △ | 符号付きの ADC の値の表し方（規則と判断、peers へ） |
| △10 | 2 | △ | rvswd / swio の scan_kind 2（arm-adi）の扱い（規則と判断、peers へ） |
| △12 | 2 | △ | probe-config の無い probe の起動時のピンの状態を core §8 に（規則と判断、peers へ） |
| PC-9 | 3 | △ | state のページング: ページの間の storage_*（2 つの first は済み。残りは規則と判断、peers へ） |
| PC-10 | 3 | △ | boot_reset の保持の時間を伸ばす道をガイドに（ガイドの担当へ渡した） |
| G-7 | 3 | △ | ガイドの節番号を揃える（ガイドの担当へ渡した） |

決着のうち O-6 は、特許の非主張と「OEP」を名乗る条件がまだ決まっていない（ユーザーの判断）。対応済みのうち ★4（P2-★4）は、凍結の前に bench が cold attach を 1 回計る条件が残っている。

前提（ユーザーの指定）: OEP を OSS の共通仕様として公開し、会ったことのない多くの人が、見たことのない環境（ほかの OS、USB スタック、MCU、
debug の線、target、ブラウザ、CI）で、本文だけを読んで probe と host を作って使う。判断の基準は今の仮の bench ではなく、その人たちに何が要るか。
この点検の後に第三者のレビューを受ける。

重さ: ★ 第三者のレビューの前に直す / ○ 直したほうがよい（凍結の前が望ましい）/ △ あるとよい。
種類: 規則 = 規則が変わる（peers に先に送る）/ 文言・文書 = 書き方だけ / 判断 = ユーザーが決める方針。

| 部 | 対象 | ★ | ○ | △ |
|---|---|---|---|---|
| 1 | core、registry、generated | 15 | 20 | 12 |
| 2 | 標準インターフェース（common、debug、console、fixture、capture） | 7 | 17 | 13 |
| 3 | probe-config、開発ガイド、OSS の準備 | 6 | （本文の表） | （本文の表） |

## ユーザーの判断が要るもの

- 3 部 O-1: 申請の資料（docs/pid-codes-application/）を第三者のレビューの前に木から外すか、案内しないだけにするか。履歴を書き換えるか。
  **決着: 木から外し、案内も消す。VID:PID は取得してから書く（2026-10-02、ユーザー）。** 7ff4dce で外した（履歴は書き換えていない）。
- 1 部 C-11: USB の自動の見分けを、プロジェクトの VID:PID だけにしたまま（第三者のハードは自動では見つからない）でよいか。
  **決着: 今のまま（2026-10-02、ユーザー）。**
- 3 部 O-4: 変更の手順と、誰が決めるか（`oep.` の名前、enum の値、errata）。
  **決着: spec のリポジトリが唯一の正で、変更はそこへの直接の編集か pull request（2026-10-02、ユーザー）。** CONTRIBUTING（en / ja）に書いた（6bcf7e3）。
- 3 部 O-6: 仕様の文のライセンス（MIT のままか）、特許の非主張、「OEP」を名乗る条件。
  **決着: 仕様は MIT のまま（2026-10-02、ユーザー）。** README に書いた（6bcf7e3）。特許の非主張と「OEP」を名乗る条件は、まだ決めていない。
- 1 部 C-14 / 3 部 O-10: 日本語と英語のどちらを正とするか。
  **決着: 英語が正、日本語は訳。規範の文書はすべて英語版を持ち、英語が完全であること（2026-10-02、ユーザー）。** README、review-guide、core §0（en / ja）に書いた（78137fb、6bcf7e3）。


---

## 3 回目のゼロベース点検: core（oep-core.ja.md / oep-core.md）、registry、generated

点検日: 2026-10-02。対象: oep-spec HEAD（82e6b9f）の `docs/oep-core.ja.md`（英語版 `oep-core.md` と突き合わせ）、`registry/oep-v1.toml`、
`generated/oep-v1/*`。前提: OSS の共通仕様として公開し、まだ会ったことのない実装者が、本文だけを読んで probe と host を作る（ほかの OS や
USB スタック、MCU、target、ブラウザ、CI）。先に review-guide、v1-freeze-decisions（§0、§A/§B）、v1-zero-base-review-2026-10-02 を読んだ。
決まった点（§0.3 の固定の表、☆1〜☆8、購読にロックが要ること、DFU を OEP の外に置くこと、§3.5 を握手だけにしたこと）は、
前提によって答えが変わるもの（C-11 だけ）を除いて、もう一度は挙げない。

重さ: ★ 第三者のレビューの前に直す / ○ 直したほうがよい / △ あるとよい。
「規則」は規則が変わる（peers の ch32rv / WireSkein / bench に相談する）、「文言」は文言だけの修正（そのまま入れてよい）。

`oepgen1.py --check` は exit 0。ja と en の数（hex、数、§）は行ごとに一致し、意味の食い違いも見つからなかった（C-14 の言語の扱いは別に挙げる）。

---

#### ★ 第三者のレビューの前に直す

#### C-01 ★ §2.2 / §8 / registry: tag の bit 7 と registry の書き方が揃っていない（規則の明確化。実装はすでにこの形なので peers には確認だけ）

状態: 対応済み（d48ca6d、core §2.2 tag の番号は下の 7 bit、§7.4 / §8 は 0x10（0x90 で送る）、registry `role_assignment = 0x10`）

- **問題**: registry の書き方が場所によって違う。`plan_apply.role_assignment = 0x90` は critical の bit を含めた値で、`attach.max_speed = 0x01  # critical`
  は bit を含めない値になっている。生成物も `kTlv…RoleAssignment = 0x90` と `kTlv…MaxSpeed = 0x01` で、第三者には、max_speed は 0x81 で送り、
  role_assignment はそのまま送る、ということが読み取れない。本文にも「tag の同一性は下の 7 bit」という定めが無い。0x10 と 0x90 が同じ TLV なのか、
  応答の中の 0x80〜0xFE をどう扱うのか、ignored と unsupported の payload に bit 7 を付けるのか（unsupported は「受け取ったまま」）も決まっていない。
  参照の client も probe も `tag & 0x7F` で比べていて、本文より実装が先にある。
- **案**（§2.2 に足す）:
  > - **tag の番号は下の 7 bit（0x01〜0x7E）**。bit 7 は要求の中でだけ使う critical の印で、番号の一部ではない（0x10 と 0x90 は、critical でない
  >   ものと critical のものの、同じ TLV）。応答、出来事、データの TLV の bit 7 は 0 にする。読む側は bit 7 が 1 の TLV を知らない tag として飛ばす。
  > - ignored の値には bit 7 を外した番号を並べる。rejected unsupported の payload の tag は受け取ったままの byte にする（bit 7 を含む）。
- registry には bit 7 を外した番号だけを書き、critical で送るものには `critical = "required"` を付ける（`role_assignment = 0x10` に直す）。
  §8 の「0x90」は「0x10（critical、0x90 で送る）」に直す。ゼロベース再点検の「plan_apply の TLV 0x91〜」も「0x11〜」に読み替える。

#### C-02 ★ §4.3 の順 5 / §2.4: 「未定義の値 → malformed」と、後から値を足す道がぶつかる（規則）

状態: 対応済み（d48ca6d、fb44490、core §4.3 順 5 / 6 と「Contradictions and undefined values」、§2.4、§2.5 末尾。各インターフェースの未定義の値も unsupported）

- **問題**: 順 5 は「未定義の値（`mode > 3` など）」を malformed にする。ところが凍結の後の伸ばす道（v1-freeze-decisions §0.4、再点検 (a)）は、
  gpio の mode 8〜、i2c の mode 4〜、cause 7〜、step 3〜 のように**同じ欄に後から値を足す**。その後で、新しい host が新しい値を古い probe に
  送ると malformed（host の誤り）が返り、新しい probe でその値を持たないものからは unsupported が返る。host から見ると同じ状況に理由が 2 つでき、
  原則 8 に反する。要求の flags の予約のビット（list の flags、confirm の flags など）を立てたときの扱いも決まっていない。
- **案**（§4.3 の順 5 と順 6 を差し替え、§2.4 に足す）:
  > 5. **書式の誤り**（長さ、数と中身の食い違い、形が許さない値: 予約と定めた値（0xFF の無効など）、欄の型が許さない範囲（`address > 0x7F`
  >    のように、仕様が将来も使わないと定めた値））→ malformed。
  > 6. **この probe が持たない値**（**後から定めうる範囲の値**: enum の未使用の値、要求の flags の予約のビット、宣言に無い mode / format / rate、
  >    知らない critical の TLV、ピンの組）→ unsupported（payload の tag は、固定部分の値なら 0x00、TLV の中の値ならその TLV の tag）。
  >
  > §2.4 に足す: 応答の flags の予約のビットと、知らない enum の値（cause、holder_kind など、失敗を表さないもの）は、host は無視するか「不明」として見せる。
- 各インターフェースの「未定義の mode（8 以上）は malformed」（fixture §1 L39、§3 L126、§4 L172、probe-config L98 など）は、この規則に合わせて
  unsupported に直す。将来も使わない値を残したいときは、registry にその範囲を `invalid` として書く。

#### C-03 ★ §2.2 / §2.3: 繰り返してはいけない tag の繰り返し、知っている TLV の長さの誤り、critical の値の知らない後ろ（規則）

状態: 対応済み（d48ca6d、core §2.3 の繰り返し・短い値・要求の TLV を後ろに伸ばさない）

- **問題**: (a) 「同じ tag の繰り返しは並びを表す」だけで、繰り返すと定めていない TLV（attach の critical の max_speed など）が 2 つ来たとき、最初を
  使うのか、最後を使うのか、malformed なのかが決まっていない。実装ごとに違う値を使うと、安全のための項目で事故になる。
  (b) 知っている TLV の値が、定めた形より短いときと、値域の外のときに、critical でなければ ignored に入れるのか malformed なのかが決まっていない
  （§2.3 の「扱えなければ…ignored」と順 5 の「長さ」がぶつかる）。(c) §2.3 の「知っている長さより後ろを読み飛ばす」が要求の TLV にも当たるので、
  host が critical の TLV の値の後ろに新しい欄を足すと、古い probe はその欄を黙って飛ばしたまま実行する。critical の意味が崩れる。
- **案**（§2.3 に足す）:
  > - 定義が繰り返しを許さない tag が 1 つの要求に 2 つ以上あれば rejected malformed（critical かどうかを問わない）。応答で同じことが起きたら、
  >   host は最初のものを使う。
  > - 知っている TLV の値が定義の形より短いか、定義が許さない値なら、critical かどうかを問わず rejected malformed。定義の中の値でこの probe が
  >   扱えないものだけが、critical なら unsupported、そうでなければ ignored になる。
  > - **要求の TLV の値は後ろに伸ばさない**（新しい欄は新しい tag にする）。probe は、要求の TLV の値が知っている長さより長ければ、critical なら
  >   rejected unsupported（その tag）、そうでなければ値全体を無視して ignored に載せる。応答、出来事、probe が覚えて読み返す値は、今のとおり後ろに伸ばしてよい。

#### C-04 ★ §2.3 ignored: 並べる数に上限が無い（既知の未決: 参照の probe は 16 で黙って切り、入らなければ黙って落とす）（規則）

状態: 対応済み（cd15f53、core §2.3 ignored は 16 個まで、0x00 の印、落とさない。registry `ignored_max_entries`）

- **問題**: §2.3 は「無視した TLV ごとに 1 つ並べる」と定めたが、上限も、応答に入らないときのことも書いていない。参照の probe
  （`Oep.h` の `RequestIgnored::kMax = 16`、`append` は入らなければ何も付けない）は、17 個目からを黙って捨て、応答に入らないと ignored を
  まるごと落とす。host には「全部効いた」ように見える。gpio set の drive のように要素ごとに繰り返す TLV では、16 は簡単に超える。
- **案**（§2.3 の ignored の文の後ろに足す。registry `limits.ignored_max_entries = 16`）:
  > - ignored の値は、無視した TLV の番号（bit 7 を外したもの）を**要求に現れた順に**並べる。並べるのは多くて 16 個（registry
  >   `ignored_max_entries`）。無視した TLV が 16 を超えるときは、15 個を並べて 16 個目に **0x00**（「ほかにも無視した」の印。tag 0x00 は TLV に
  >   使わない、§2.2）を置く。host は 0x00 を見たら、並んでいない tag も無視されたものとして扱う。
  > - probe は ignored を落とさない。応答の可変の部分（data、並び）を縮めて ignored の場所（多くて 18 byte）を空ける。固定部分だけで場所が
  >   足りなければ、入る数まで並べて最後を 0x00 にする（少なくとも `0x7F 0x01 0x00` の 3 byte は入れる）。
- **なぜこの形か**: 最新の決定（2026-10-02、3cc50c8「無視した数だけ並べる」）を壊さずに、応答の大きさの上限を 18 byte に抑え、切ったことが
  host に分かる。順番を決めるので、適合試験で byte ごとに比べられる。別の案として「異なる tag を 1 回ずつ（多くて 126 byte）」もあるが、
  3cc50c8 を戻すことになり、64 byte の max_frame には入らない。
- 合わせて直す（似た仕組み）: 参照の probe の console / capture / sampler の `reserve = 2 + kMaxIgnored` は、今の上限 16 と同じ数なので、この案のままで足りる。
  落としているのは `RequestIgnored::append` の `if (… > capacity) return result;` だけ。

#### C-05 ★ §3.5 port_speed の `port`: host は自分のいる経路の index を知る方法が無い（規則）

状態: 対応済み（48b8cbe、案 A: core §7.1 confirm の応答の TLV 0x01 transport、§3.5 port、§3.1 TCP と中継の broker）

- **問題**: 要求の `port(u8)` は「この要求の来た口」でなければならない（違えば unavailable 6）。ところが host は、describe の transport
  （§7.5）から「今どの index の経路で話しているか」を知る方法が無い。参照の client は「最初の UART bridge」を選んでいる（`link.py`
  `_speed_port` が `bridges[0]` を返す）ので、UART bridge が 2 つある probe では、2 つ目の口から上げられない。
- **案**（どちらか。A を勧める）:
  - A: confirm の応答に TLV `0x01 transport_index(u8)` を足し、probe はいつもこれを付けて、その要求の来た経路の index を返す（§7.1）。
    ほかにも「どの口のことか」が要る所（bind、§3.4 の止まった口の診断）で使える。confirm の応答は 64 byte に収まる（3 byte 増える）。
  - B: `port = 0xFF` を「この要求の来た口」と定める。
- registry の `[interface.tlv.confirm_answer]` に足す。

#### C-06 ★ §4.4 host の待ち時間: 遅い口の転送時間が入っていない（規則・時間）

状態: 対応済み（f7d6d21、d24cdd6、3c6691a、core §4.4 転送の時間、前の応答から数える、すべての要求に効く下限）

- **問題**: 待ち時間は「引数の時間 + 1000 ms、ただし max_op_ms + 1000 ms を超えない」。§7.5 の max_op_ms の行には「線を通る時間を足した値
  以上を待つ」とあり、§4.4 の上限とぶつかる。115200 bps の UART bridge では、max_frame = 4096 の応答 1 つで約 0.36 s、65535 byte なら約 5.7 s かかる。
  さらに、応答の前に送りかけの通知（max_frame × 2、§11.4）と、同時数 n 個ぶんの前の応答が並ぶ。決めた待ち時間で正しい応答を待ち切れず、
  host は送り直しに進む。遅い口ほど誤った判断になる。
- **案**（§4.4 を差し替え）:
  > 待ち時間 = その要求の引数で決まる時間（無ければ 0）+ 1000 ms（`host_wait_add_ms`）+ **転送の時間**。転送の時間は、シリアルの口では
  > (要求の長さ + 前に並んだ未解決の要求の応答の上限の和 + max_frame × (1 + `notify_pending_max_frames`)) × 10 / 口の baud 秒、
  > 長さつきのフレームの口では 0 としてよい。引数で決まる時間の部分は max_op_ms を超えない（超える要求は §7.5 で unsupported になる）。
- §7.5 の max_op_ms の行の「線を通る時間を足した値以上を待つ」を「§4.4 の待ち時間で待つ」に揃える。

#### C-07 ★ §3.1 / §3.2 / §5.1: 長さつきのフレームの口で、probe 側の受け方と立て直しの時間が噛み合わない（規則・時間）

状態: 対応済み（48b8cbe、0bb10e8、core §3.1 長すぎる length、§3.2 TCP ではやり直さない、§5.1 `host_resync_wait_ms`）

- **問題**:
  1. §3.2「probe はフレームの途中で 200 ms 途切れたら最初から読み直す」は、**TCP** では間違った動きになる。トンネルや Wi-Fi では 200 ms の遅れは
     ふつうにあり、区切りを持たない長さつきのフレームの読みを途中からやり直すと、残りのバイトを次の長さとして読んで同期を失う
     （TCP は区切りを失わないので、やり直す理由も無い）。
  2. §5.1 の host の立て直しは「入力が 50 ms 静かになったら confirm」で、**host が自分で最後に書いてからの時間**を見ていない。host の書き込みが
     途中で切れた（前の host のプロセスが落ちた、書き込みの途中で取り消した）とき、probe は 200 ms たつまで前のフレームの続きを待っている。
     そこへ 50 ms 後に送った confirm はその続きとして読まれ、立て直しが決まって失敗する。新しい host が口を開いた直後の最初の confirm も同じ。
  3. probe が受けた length が max_frame を超えたとき、length 0 以外の壊れた長さのとき、HID の count が report より大きいときに probe がどうするかが無い。
- **案**:
  > §3.2: 「probe は、**シリアルの口、vendor bulk、HID** で、フレームの途中で 200 ms 入力が途切れたら読み取りを最初からやり直す。**TCP では
  > やり直さない**（壊れた TCP の流れは接続を閉じて立て直す）。」
  > §3.1（長さつきのフレームの probe の受け方）: 「length が max_frame を超えたら、probe はそのフレームを捨て、入力が `probe_frame_gap_ms` 途切れる
  > まで読み捨ててから次のフレームを待つ（応答は返さない）。HID の count が report の長さから 2（report ID があれば 3）を引いた値を超える
  > report は捨てる。」
  > §5.1: 「host は、立て直しの confirm を送る前と、長さつきのフレームの口を開いて最初の confirm を送る前に、自分が最後に書いてから
  > `probe_frame_gap_ms` + 50 ms（registry `host_resync_wait_ms = 250`）待つ。」
- TCP では §5.1 の手順の代わりに「接続を閉じて開き直す」でよい、と書く。

#### C-08 ★ §4.4 / §3.3: window、max_inflight、max_frame は経路ごとか probe で 1 つか（規則の明確化）

状態: 対応済み（48b8cbe、core §4.4 max_frame / window / max_inflight は経路ごと）

- **問題**: 複数の経路は「セッションとロックを 1 つ共有する」が、confirm の上限が経路ごとのものかどうかは書いていない。probe で 1 つなら、
  CDC にいる監視の host（ロックなしの describe や link_source）が window を使い切り、vendor bulk でセッションを持つ host の要求が
  window_exceeded になるか、黙って失われる。互いを知らない 2 つの host には、守りようが無い。
- **案**（§4.4 に足す）:
  > confirm の max_frame、window、max_inflight は**その confirm が来た経路の**上限で、経路ごとに独立に数える。probe は、ある経路の未解決の
  > 要求のために、ほかの経路の受けの余地を使わない。§5.2 の表（最後のセッションの要求）は経路をまたいで 1 つ（§3.3 の「0x81 は 1 つの経路で」のまま）。

#### C-09 ★ §3.4 / §3.5: UART bridge の線の設定（速さ、8N1、流れの制御）と DTR / RTS が規範に無い（規則。決めたことを規範に上げる）

状態: 対応済み（48b8cbe、core §3.4 UART bridge の線・line coding・制御線、§3.5 起動時の速さ。registry `uart_bridge_boot_baud`）

- **問題**: 規範は「起動時の速さはボードの profile が決める」とだけ書いている。115200 bps に固定することは probe 開発ガイド §3.5
  （2026-09-29 の決定）と host 開発ガイド §1.5 にしか無い。データビット、パリティ、ストップビット、流れの制御は、どこにも書いていない。
  CDC の line coding（host が設定した baud）を probe が無視することも、DTR を probe が見ないことも規範に無い（参照の環境の 1 つは、
  DTR が下りている間は出力を止める）。本文だけを読んだ host は、知らない probe の UART bridge を開けない。
- **案**（§3.4 の冒頭に足す）:
  > - **UART bridge の線**: 起動時の速さは **115200 bps**（registry `uart_bridge_boot_baud`）、8 データビット、パリティなし、1 ストップビット、
  >   流れの制御なし。§3.5 の port_speed で変えるのは速さだけ。
  > - **USB CDC と USB-Serial/JTAG**: probe は host が設定した line coding（速さなど）を無視し、どの値でも OEP を受けて返す。
  > - probe は DTR / RTS / line state の値で OEP の受けと送りを止めない。host は DTR と RTS を立てて口を開く（UART bridge の自動リセット回路を
  >   動かさないため。DTR を下ろす順番は host 開発ガイド §1）。
- §3.5 の「起動時の速さ: ボードの profile が決める」を「§3.4 の 115200 bps」に直す。

#### C-10 ★ 新しい節「適合」: 必ず持つものと任意のもの、規範の語（文言 + 規則の確認）

状態: 対応済み（4e62116、core §1.1 規範の語、§1.2 適合、§12 Required の列、§0 規則 4 は tests/vectors（e21a9a2）を指す）

- **問題**: probe が必ず実装する core の op が、1 か所にまとまっていない。本文から拾えるのは、confirm / list / describe / open / end /
  keepalive / lock_state、fn 0 の subscribe / unsubscribe（§11.3「どの probe も」）、port_speed は任意、ということ。link_source / link_sink、
  plan_apply / plan_release（plan を使うインターフェースが無い probe）、ハートビートが必須かどうかは読み取れない。host が最小限で
  実装しなければならないもの（知らない TLV を飛ばす、通知を role で捨てる、待ち時間）も同じ。日本語の「〜する／〜してよい／できれば」と、
  英語の does / may / preferably が、MUST / SHOULD / MAY のどれに当たるかも書いていない。§0 の「project が適合試験を持つ」が指す先も無い。
- **案**: §1 の後ろに「§1.1 規範の語」と「§1.2 適合」を足す。
  > 規範の語: 「〜する／〜しない」= MUST / MUST NOT、「〜してよい」= MAY、「できれば〜する」= SHOULD（RFC 2119 / 8174）。英語版はこの語で書く。
  > probe が必ず持つもの: §3 のどれか 1 つの経路、§4〜§6、op 0x01〜0x03、0x10〜0x13、0x30 / 0x32（fn 0）、0x40 / 0x41、describe の必須の tag
  > （unit_id、transport、max_op_ms）。plan_apply / plan_release は、plan の role を宣言するインターフェースを 1 つでも持つ probe だけが必ず持つ
  > （持たない probe は unknown_operation）。任意: port_speed、fn 0 以外の通知。
  > host が必ず守るもの: §2.3（飛ばす）、§2.4、§3.2、§3.3 の探りの規則、§4.4、§5.2、§11.1。
- 適合試験の置き場（fake か、別のリポジトリか）を決め、§0 から指す。決まらないなら §0 の「適合試験を持つ」を消す。

#### C-11 ★ §3.3 の自動の見分け: 第三者のハードウェアは見つけられない（規則。**今日決めた点だが、前提で答えが変わる**）

状態: 決着（2026-10-02、ユーザーの判断）: 今のまま。自動の見分けはプロジェクトの VID:PID だけ（core §3.3）

**決着: 今のまま（2026-10-02、ユーザー）。** 自動の見分けはプロジェクトの VID:PID だけで、それ以外は利用者が probe を名指すか口を選ぶ。

- **問題**: 2108125（2026-10-02）で、自動で見分けるのはプロジェクトの VID:PID だけになった。取り違えを避ける理由は正しい。けれど OSS の
  共通仕様では、(1) 自分の VID を持つ会社や、自分の PID を取った別のプロジェクトが作る OEP の probe は、**規範のどの道でも**自動で見つからない
  （名指すか、利用者が選ぶしかない）。(2) 第三者がプロジェクトの VID:PID を使ってよいのか（適合した実装なら誰でも使える共用の ID なのか、
  参照の firmware だけのものなのか）が書いていない。VID:PID の割り当ては普通は 1 つのプロジェクトのものなので、これが決まらないと、
  第三者の実装者は「OEP の probe を作っても自動では見つからない」と読む。(3) 規範の自動の道は、VID:PID が registry に載るまで空なので、
  レビューの間は自動の発見が本文だけでは作れない（host ガイド §1.7 の暫定の手がかりに頼る）。
- **案**（どちらかを、ユーザーと peers に選んでもらう。番号は書かない）:
  - A（勧める）: 自動の見分けに、**名前空間として予約した interface の形**を足す: 「class 0xFF / subclass 0x4F / protocol 0x45 の interface、または
    usage page 0xFF4F / usage 0x45 の HID を持つ device は OEP の probe の**候補**とし、§3.3 の探りの規則（confirm だけ、64 byte、答えが無ければ
    閉じる）で確かめてから probe として扱う」。プロジェクトの VID:PID は、確かめの前から probe とみなせる（候補を開かずに一覧に出せる）、
    という差だけにする。偶然に重なったときの害は、探りの規則で confirm 1 つに抑えられる。
  - B: プロジェクトの VID:PID の使い方を規範に書く: 「プロジェクトの VID:PID は、この仕様に適合する probe なら誰の firmware でも使ってよい。
    使う probe は serial number を unit_id にする（§7.5）」。そのうえで、自分の VID:PID を使う probe は自動では見つからない、と明記する。
- どちらでも、registry の `discoverable` の意味（C-12）を合わせて直す。

#### C-12 ★ registry `discoverable` のコメントが core と食い違う（文言）

状態: 対応済み（78137fb、registry `discoverable` のコメントを core §3.3 / §7.5 に揃えた）

**対応済み**（78137fb）: 案のとおりに直した。

- registry L202: `discoverable = 0x4A  # u8: 1 = the probe also enumerates as a USB device whose iProduct starts with "OEP" (core §3.3)`。
  core §7.5 は「プロジェクトの USB の VID:PID でも列挙している」で、§3.3 は「iProduct は見分けに使わない」と書いている。registry は
  「唯一の定義」なので、第三者はコメントを信じる。
- **案**: `# u8: 1 = the probe also enumerates with the project's USB VID:PID (core §3.3); 0 until that VID:PID is listed in [usb]`。

#### C-13 ★ §7.4 / §7.5: bitmap のビットの順が無い（文言）

状態: 対応済み（78137fb、core §2.1 bitmap のビットの順と長さ）

**対応済み**（78137fb）: 実装（oep-probe-arduino `Oep.h` の roleChannels / describeCore、oep-client-python `catalog.py`）はどちらも bit i = byte ⌊i/8⌋ の bit (i mod 8)、LSB が先、長さは値の残り。そのとおりに core §2.1 に書き、0x44 reserved にも「bit i が立っていれば」を足した。

- role_channels と reserved の `base(u16)、bitmap` は「bit i が立っていれば channel base+i」とだけあり、byte の中のビットの順（LSB が先か）と、
  bitmap の長さ（TLV の長さ − 3）が書いていない。実装によって逆に読める。
- **案**（§2.1 に足す）: 「**bitmap** は byte の並びで、bit i は byte ⌊i/8⌋ の bit (i mod 8)（bit 0 = LSB）。長さは、それを含む値の残り全部。」

#### C-14 ★ 言語: 規範の dmseq に英語版が無く、英語の core はどちらが原文かを書いていない（文言・文書）

状態: 決着（2026-10-02、ユーザーの判断）: 英語が正、日本語は訳。core §0「Language」（78137fb）、dmseq の英語版 target-console-dmseq.md（cdd26b4）

**決着: 英語が正、日本語は訳（2026-10-02、ユーザー）。** core §0 に書いた（78137fb）。dmseq の英語版は cdd26b4。

- `target-console-dmseq.ja.md` は規範（v1-freeze-decisions §0.1）なのに英語版が無く、en の core §14 は日本語版を指している。どちらが原文かは
  review-guide にしか書いていない（core の ja / en のどちらにも無い）。
- **案**: core の冒頭（状態の行の後）に、ja と en の両方で「この文書の原文は日本語版で、食い違えば日本語版が正しい」と書く（英語を原文に
  するなら、そう決める）。第三者のレビューの前に `target-console-dmseq.md` を作る。

#### C-15 ★ §7.1 / §2.7: プロジェクトの revision の交渉の範囲と、confirm の形の不変（規則。凍結の約束に関わる）

状態: 対応済み（929bbb7、core §7.1 confirm は不変、revision は経路ごと、断りに TLV 0x01 supported）

- **問題**: 凍結の範囲は「本体の形を変えるのはプロジェクトの revision（confirm で交渉）」で、将来の道を閉じないことを理由にしている。けれど本文は、
  (a) 選んだ revision が何に効くのか（その経路のその後の全部か、confirm を送った host だけか、次の confirm までか）、(b) confirm 自身と、
  confirm の前の 64 byte の約束が、どの revision でも変わらないこと、(c) 範囲に無いときの unsupported の payload を書いていない。
  これが無いと、revision 2 の host は、revision 1 の probe に安全に話しかけられない。
- **案**（§7.1 に足す）:
  > - confirm の要求と応答の固定部分、`OEP?` / `OEP!`、§3.3 の confirm の前の約束（64 byte、§3.1 のフレーム）は、**どの revision でも変えない**。
  > - probe が選んだ revision は、**その confirm が来た経路で**、次の confirm まで、両方向のすべての message に効く。経路ごとに別の revision でよい。
  > - 範囲に扱えるものが無いときは rejected unsupported、payload の tag は 0x00、後ろに TLV `0x01 supported(u8 min, u8 max)`（probe が扱える範囲）。
  >   min_rev > max_rev は malformed。

---

#### ○ 直したほうがよい

#### C-16 ○ §5.2: rejected の応答も表に覚えるか、最も新しい corr を進めるか（規則）

状態: 対応済み（fc17225、core §5.2 rejected も表に覚える、TCP にも効く、中継の broker の corr の対応）

- 順 2（送り直し）より後で rejected になった 0x81 の要求（window_exceeded、malformed、unavailable など）を表に覚えるかが書いていない。
  覚える probe では同じ corr の送り直しで同じ rejected が返り、覚えない probe では実行される。
- **案**: 「順 2 を過ぎた最後のセッションの要求は、rejected も completed も表に覚え、最も新しい corr を進める。host は rejected を受けた要求を
  直して送るときは新しい corr を使う」。

#### C-17 ○ §6.1 / §6.4: lease の延び方と丸め（文言 + 規則）

状態: 対応済み（fc17225、core §6.1 lease の数え直し、§6.4 応答の lease_ms は 1000〜60000）

- 「完了するたびに延びる」は、「その応答を送った時から lease_ms を数え直す」と書く。rejected の 0x81（自分のセッションの malformed など）でも
  数え直すのかを決める（案: 順 3 を過ぎた要求は rejected でも数え直す）。
- 「範囲の外は probe が丸める（幅は probe が決める）」は、応答の lease_ms が 1000〜60000 に入るのか、外もあり得るのかが分からない。案: 「応答の
  lease_ms は `lease_min_ms`〜`lease_max_ms` の中に入れる」。

#### C-18 ○ §6.1 / §4.1: session_id の選び方と、open を 0x81 で送ったとき（規則）

状態: 対応済み（fc17225、core §6.1 session_id は予測できない乱数で 0 を使わない、§6.4 open は role 0x01 だけ）

- 「乱数でよい」だと、固定の値（1 や、プロセスの名前のハッシュ）を使う host どうしが互いのセッションを黙って再開する（§6.2「自分が持つ、
  同じ open → resumed = 1」）。session_id 0 を使ってよいかも書いていない。
- **案**: 「host は session_id をセッションごとに 32 bit の乱数（予測できない値）から選ぶ。固定の値を使わない。0 は使わない（probe は open の
  session_id 0 を malformed で断る）」。open は role 0x01 で送る、0x81 の open は malformed（ヘッダとペイロードの session_id の食い違いを作らない）。

#### C-19 ○ §6.5 boot_id: 「必ず値を変える」は作れない場合がある（文言）

状態: 未対応（core §6.5 はまだ「乱数源の無い probe も必ず値を変える」。案の緩め方は入っていない）

- 不揮発の記憶も乱数源も無い MCU は、起動の時間が決まっていて、毎回同じ値になりうる。
- **案**: 「乱数の素（ADC の雑音、初期化していない RAM、起動の時刻の差など）か、不揮発の数え上げで作る。どれも無い probe は、同じ値になる確率を
  減らせないことを受け入れる。host は再起動を boot_id だけでなく、open の resumed と no_session でも知る」。

#### C-20 ○ §7.1 confirm の値の制約（文言）

状態: 未対応（一部だけ: max_frame ≥ 64 は core §3.3、flags の扱いは §2.4、unsupported の payload は §7.1。max_inflight ≥ 1 と window ≥ max_frame、外れた応答の扱いが無い）

- 「max_inflight ≥ 1、max_frame ≥ 64、window ≥ max_frame。外れた応答は壊れた応答として扱う」。「flags の知らないビットは host が無視する」。
  C-15 の unsupported の payload もここに書く。

#### C-21 ○ §4.3: payload の中の fn と、任意の op の断り方の位置（文言）

状態: 未対応（後半は core §1.2「実装していない op は unknown_operation、任意の機能は unsupported」で済み。payload の中の fn の unknown_function を §4.3 の順のどこで見るかが無い）

- 「payload の中で指す fn が無いときは unknown_function」が、順のどこで見るかが無い（plan_apply の表は malformed の後）。案: 「順 5 と順 6 の間」。
- 0x0B の「任意の op の機能」と、port_speed の「OFF は unknown_operation」がぶつかって見える。案: 「実装していない op は unknown_operation、
  実装した op の中の任意の機能（mode など）は unsupported」と書き分ける。

#### C-22 ○ §2.1 文字列と真偽値の検証（規則）

状態: 対応済み（fc17225、core §2.1 真偽値と text）

- text の UTF-8 が壊れているとき、制御文字（ANSI のエスケープを含む）が入っているときの扱いが無い。owner はほかの利用者の端末に見せる値なので、
  端末を操る列を差し込める。真偽値の u8 で 0 / 1 以外の値（resets_on_open、force、port_speed）の扱いも無い。
- **案**: 「text は正しい UTF-8 で、C0 の制御文字（0x00〜0x1F）と 0x7F を含めない。probe はそうでない要求の text を malformed で断る。host は
  そうでない応答の text を、見せる前に置き換える（U+FFFD など）」。「u8 の真偽値は 0 が偽、1 が真。要求でほかの値なら malformed、応答では真」。

#### C-23 ○ §7.2 / §13 / §7.5: 名前、model、chip の文法（規則）

状態: 対応済み（fc17225、core §13 規則 1 の label の文法、§7.5 model の接頭と chip の文法）

- インターフェースの名前は `a-z 0-9 - .` だけで、空の label（`a..b`）、先頭か末尾の `.`、`-` で始まる label が許されるかが無い。案:
  「label は 1 文字以上の `a-z 0-9 -` で、`-` で始めない・終えない。名前は 2 つ以上の label」。
- model は「同じ種類で同じ値」だけで、会社をまたいだ重なりを防ぐ手段が無い。host が model ごとに既知の扱い（速さの表など）を持つと、
  重なった model を取り違える。案: 「プロジェクト以外の probe の model は、作る者を表す接頭（逆 DNS を `-` でつないだもの、例
  `com-example-probe1`）で始める」。または `.` を model に許して逆 DNS にする。
- chip の `<型番> v<リビジョン>` の文字と、リビジョンが分からないときの形が無い。案: 「`[a-z0-9]{1,24}` + 空白 + `v` + `[0-9]+(\.[0-9]+)*`。
  分からなければ型番だけ」。

#### C-24 ○ §7.5 unit_id の一意性: ビルドの定数は害が大きい（規則）

状態: 対応済み（fc17225、core §7.5「Uniqueness of unit_id」の保存した乱数と `x-`）

- 「固有の番号も保存も無い probe はビルド定数でよい」では、同じ firmware の probe が 2 台あると、§3.3 の名指し（serial で開く）と、
  transport を unit_id でまとめる規則が、別の probe を 1 つにまとめてしまう。
- **案**: 「保存があれば、初めて起動したときに乱数で作って保存する。固有の番号も保存も無い probe は unit_id を `x-` で始め（一意でない印）、
  host は `x-` で始まる unit_id で経路をまとめず、名指しにも使わない」（または describe に「一意でない」の tag を足す）。

#### C-25 ○ §3.3 / §3.4: 同じ口を使うほかのソフトウェアと、OS ごとの USB の差（規則 + 実務の文書）

状態: 対応済み（fc17225、core §3.3 末尾の排他で開く・HID の output・WinUSB。udev / ModemManager / brltty の host ガイドの話は未）

- host が口を排他で開くことが規範に無い。Linux の tty は複数のプロセスが同時に開け、HID の hidraw も同じで、2 つの host の書き込みが
  フレームの途中で混ざる（HID ではフレームが report をまたぐ）。§7.5 の「口を排他で開けた時点で前の持ち主はいない」は、排他で開いたことが前提。
  案: 「host はシリアルの口と HID を排他で開く（OS が許す限り。Linux は TIOCEXCL など）」。
- HID の output を interrupt OUT で送るのか SET_REPORT で送るのかが無い。案: 「probe は interrupt OUT の endpoint を持ち、SET_REPORT(Output) でも
  受ける」。
- Windows で vendor bulk を使うには WinUSB の driver が要る（MS OS 2.0 の記述子）。§0 は「記述子の細部は OEP の外」としているが、相互運用には効く。
  案: §3.3 に「vendor bulk を出す probe は、その interface に MS OS 2.0 の compatible ID `WINUSB` を付ける（任意ではなく、できればする）」。
  Linux の udev の権限、ModemManager や brltty が新しい口を開いて生のバイトを書く件は host 開発ガイドに書く（規範ではない）。

#### C-26 ○ §3.4 / §11.1: 共用の口のロックなしの答えは、target の出力で偽造できる（文言）

状態: 対応済み（5d02a6f、core §3.4 の（参考）: 生の転送の止まっていない口ではロックなしの答えを target の出力で偽造できる。信じる要求は生の転送の止まった口か長さつきのフレームの口で）

- ロックを持っていない間は、口に target の生のバイトが流れる。corr は 1 ずつ進むので予測でき、target の firmware（試験中のもの、壊れたもの）が
  CRC の合ったフレームを出せば、host は describe などの答えとして受けてしまう。
- **案**: §3.4 に「ロックなしで送る要求の答えは、生のバイトと区別できないことがある。答えの中身を信じる必要のある host は、ロックを持ってから
  送る（生の転送が止まる）か、長さつきのフレームの口を使う」。

#### C-27 ○ registry に無い、規範の文の数（registry）

状態: 対応済み（5d02a6f、registry `port_speed_switch_wait_ms`、`port_speed_confirm_extra_ms`、`port_speed_broken_max`、`resend_max`、`model_max_bytes`、`host_serial_inflight_max_bytes`、`host_serial_min_bytes_max`、`heartbeat_min_ms` など。confirm の 1000 ms は `host_wait_add_ms` と明記。本文 core §3.3 / §3.4 / §3.5 / §5.2 / §7.5 / §11.3 が名前を引く）

- registry は「数の唯一の定義」と言っているが、次の数は本文にしか無い: §3.4 の 6 KiB（未解決の要求の応答の見込み量）と 2 KiB（min_bytes）、
  §3.5 host の義務 2 の 20 ms、戻る条件 4 の 3 つ、§3.3 の confirm の待ち時間 1000 ms（`host_wait_add_ms` の流用であることを明記）、
  §5.2 の送り直しの 1 回、§7.5 の model の 32 byte、C-04 の 16、C-07 の 250 ms、C-09 の 115200。
- **案**: `[limits]` / `[timing]` に足す: `host_serial_inflight_max_bytes = 6144`、`host_serial_min_bytes_max = 2048`、
  `port_speed_switch_wait_ms = 20`、`port_speed_broken_run = 3`、`model_max_bytes = 32`、`resend_max = 1` など。

#### C-28 ○ registry のコメントの誤り（文言。「似た仕組みも確かめる」の結果）

状態: 対応済み（78137fb、registry `swept`、`result_lost` のコメント）

**対応済み**（78137fb）: `swept`、`result_lost` を案のとおりに直した。似たコメントでは、`mark_detail_closed.expired`（期限切れ / force）は正しいのでそのまま。`notify_pending_max_frames` の置き場（△）は生成物の名前が変わるので残した。

- `resumed.swept = 2  # the same session id after expiry / force` は誤り。force で奪われた側の ID はもう最後の ID ではないので、resumed 2 は期限切れの
  後だけ（core §6.2、§9）。★9（`expired` のコメント）と同じ誤り。案: `# the same session id after its lease expired: resources were removed`。
- `result_lost = 0x0C  # … whose result was too large to keep` は、表から落ちた古い corr の場合（§5.2）が抜けている。案: `# a resend whose
  answer is not kept (fell out of the table, or too large): read the state again`。
- 似た所の確かめ: `mark_detail_closed.expired = 2`（期限切れ / force）は正しい。`[timing] notify_pending_max_frames` は時間ではない（`[limits]` へ、△）。

#### C-29 ○ registry と生成物の約束（規則の明確化）

状態: 対応済み（fc17225、core 冒頭: 凍結の後キーは改名しない、REGISTRY_HASH は wire の互換を表さない、registry `[reference]`）

- 凍結は「registry のすべての数」を止めるが、キーの名前（生成物の識別子 `kTlvDescribeDiscoverable` など）を止めるかが無い。`oep_pid` →
  `discoverable` のような改名は、写して使う第三者のコードを壊す。案: 「凍結の後、registry のキーの名前は変えない（足すだけ）」。
- `REGISTRY_HASH` はコメントを直すたびに変わる。版の一致の判定に使う実装が出る。案: 生成物に「hash は生成の同期を確かめるためだけで、wire の
  互換を表さない」と書くか、コメントを除いた値の hash にする。
- `max_op_ms_reference` が `[limits]`（"values the spec text states"）にある。凍結から外した値なので `[reference]` の表に分ける。

#### C-30 ○ §2.7 / §7.2: 古い revision を別の fn で並べるときの instance（規則）

状態: 対応済み（fc17225、core §7.2 instance は (name, revision) ごと）

- 「できれば古い revision も別の fn で」と「同じ名前のものを fn の昇順に 0 から振る」を合わせると、rev 1 と rev 2 を並べた probe が後の版で rev 1 を
  消したとき、instance がずれる（「名前の順を版を越えて保つ」に反する）。保存した設定は (name, instance, revision) で指す。
- **案**: 「instance は (name, revision) ごとに振る」。または「並べる古い revision は、新しい revision の後ろの fn に置き、instance は新しい
  revision のものから数える」と書く。

#### C-31 ○ §2.6a 時計: 単調であること（文言）

状態: 未対応（規則と判断: peers に先に送る。oep-probe-arduino の nowNs は ESP32 / RP2040 以外で micros() の u32（約 71.6 分で一周）に頼り、同じ boot_id の間に減る。すべての実装がすでに守っているとは言えない）

- 「起動からの ns」に「同じ boot_id の間、減らない」を足す。

#### C-32 ○ §3.5 port_speed: baud の誤差と verify_ms 0（規則）

状態: 対応済み（fc17225、core §3.5 ±2 %、応答の baud は実際の値、try の verify_ms 0 は malformed）

- 「baud を作れない」の基準（誤差の許し）が無い。案: 「作れる値の誤差が ±2 % を超えるなら unsupported。応答の baud は実際の値」。
  verify_ms = 0 の扱いが無い（idle_ms は 0 を最長と定めている）。案: 「verify_ms 0 は malformed」か「最長と同じ」。

#### C-33 ○ §11.3 ハートビートの周期の下限（規則）

状態: 対応済み（fc17225、core §11.3 100 ms に丸めてよい）

- max_delay_ms = 1 で 1 kHz のハートビートを頼める。案: 「probe は 100 ms より短い周期を 100 ms に丸めてよい」。

#### C-34 ○ §13: 凍結の後に標準の名前と番号を足す手続き（文言）

状態: 対応済み（6bcf7e3、CONTRIBUTING「Adding an `oep.` name or a registry value」の手順と試作の扱い。インターフェースの op 0xF0〜0xFF の実験用は core §2.5 にある）

- `oep.` の新しいインターフェースや、標準のインターフェースの新しい tag を、第三者が誰に、どう頼むかが無い。試作の間の番号の使い方も無い。
  案: 「標準の番号は registry への変更（公開のリポジトリへの提案と project の確認）でだけ割り当てる。試作は独自の名前か、op 0xF0〜0xFF で
  行う。0xF0〜0xFF はどのインターフェースでも出荷する probe では使わない」（core の op だけでなく、インターフェースの op も揃える）。

#### C-35 ○ 規範の文に残る今の環境（文言）

状態: 対応済み（78137fb、core §6.4 owner の例、§7.5 chip の例、transport kind 3 を性質で）

**対応済み**（78137fb）: owner の例を "flash-tool pid 1234"、chip の例を `abc123 v1.0` にし、kind 3 を「内蔵の USB シリアル」と性質で書いた（registry のキー `usb_serial_jtag` は生成物の識別子なので残し、コメントで意味を書いた）。

- §6.4 owner の例「"ch32rv monitor pid 1234"」→「"flash-tool pid 1234"」。
- §7.5 chip の例 `esp32p4 v1.3`、`rp2350 v2`、§7.5 model の例は、実在のチップ名。例は形だけ見せればよいので `abc123 v1.0` にする。
- transport kind 3 の名前「USB-Serial/JTAG」（registry `usb_serial_jtag`）は 1 つの MCU 系統のペリフェラルの名前。性質で定める: 「USB の
  シリアル（記述子を probe が選べない、内蔵のもの）」。番号はそのまま、名前と §3.3 の説明だけ直す（registry のキーの改名は C-29 の前に）。
- §3.4 の「（[リンクの計測] §1.1）」は記録への参照として残してよい（数は規範の値）。
- 対象の外だが同じ仕組み: registry の `target_id_scheme.wch_dmi_7f` は会社の名前を含む。target の識別の scheme の名前としては筋が通る
  （その DM の固有の場所）ので、そのままでよい（報告だけ）。

---

#### △ あるとよい

| id | 節 | 問題 | 案 | 種類 | 状態 |
|---|---|---|---|---|---|
| C-36 | §4.1 / §2.5 | 見出しより短い message（corr を読めない 3 byte 未満、fn を読めない 6 byte 未満）と、向きの違う role（host から 0x02）の扱いが無い | 「corr を読めなければ捨てる。読めて見出しが足りなければ malformed（順 1 より前）。向きの違う role は応答せずに捨てる」 | 規則（小） | 未対応（規則と判断: peers に先に送る。見出しより短い message と向きの違う role の扱いが無い） |
| C-37 | §3.1 | host の受けの上限: 65535 + CRC + COBS の分を超えた候補を、どこまでためるか | 「host は 65800 byte を超える候補を捨てる」 | 文言 | 対応済み（5d02a6f、core §3.1 の（参考）: 正しい COBS のフレームは 65796 byte まで、registry `cobs_frame_max_bytes`） |
| C-38 | §5.2 | 送り直しにも答えが無いときの次（シリアルの口） | 「リンクの失敗として扱う（§5.1 か口を閉じる）」 | 文言 | 未対応（規則と判断: peers に先に送る。送り直しにも答えが無いときの host の動きを決めることになる） |
| C-39 | §7.2 / §7.3 | list の内容が同じ boot_id の間変わらないこと。§7.2 の「同じ名前の口の順」の「口」は「インターフェース」の誤り。list の first ≥ total は count 0 | 書き足す | 文言 | 未対応（一部だけ: §7.2 の「ports」は 5d02a6f で「interfaces」に。list が同じ boot_id の間変わらないことと、list の first ≥ total は規則と判断: peers に先に送る） |
| C-40 | §2.6 | 「十分小さく」は値が無い | 「同時に意味を持つ値の差を、幅の 1/4 以下に保つ」など数にするか、消す（資源の番号は §9 の 1024 で足りている） | 文言 | 未対応（規則と判断: peers に先に送る。値を決めるのも消すのも probe の義務が変わる） |
| C-41 | §7.5 transport | CDC は interface が 2 つ（通信と data）あり、どちらの番号かが無い | 「CDC は通信の interface の番号」 | 文言 | 未対応（規則と判断: peers に先に送る。transport の interface の値を決める） |
| C-42 | §3.1 TCP | 既定の port と発見は定めない、と明記する | 「TCP の port と発見はこの仕様の外」 | 文言 | 対応済み（5d02a6f、core §3.1 TCP の経路: port と発見はこの仕様の外） |
| C-43 | §3.4 bind | 0x00 を含む二進の流れは、0x00 ごとに最長 200 ms 止まる | 「bind は文字の流れ向き（0x00 を含む二進の流れは遅れる）」と参考に書く | 文言 | 対応済み（5d02a6f、core §3.4 生のバイトの行き先の（参考）） |
| C-44 | generated | C++ だけで C の header が無い（C の firmware、Zephyr、Rust の build.rs）。SPDX の行が無い | `oep_v1_registry_c.h`（`#define`）か JSON を足す。`// SPDX-License-Identifier: MIT` を付ける | 文言 | 対応済み（5d02a6f、`generated/oep-v1/oep_v1_registry_c.h`（`#define OEP_V1_…`）、すべての生成物に SPDX の行、tests と review-guide、README） |
| C-45 | 冒頭 | 状態の行が「候補、2026-09-26」のままで、英語版は日本語の提案を指す | 公開の前に「v1（凍結）」と版の日付に直す。registry の 1 行目の「2026-09-25, working toward the freeze」と「C++ header and the Python module」（JS が抜けている）も直す | 文言 | 対応済み（5d02a6f、core と各インターフェースの状態の行を「v1、凍結の前」に。registry の 1 行目も。版の日付は凍結のときに書く） |
| C-46 | §6.4 owner | owner は lock_state でだれでも読め、プロセスの番号や利用者の名前を出す | 「owner には秘密を入れない」と書く | 文言 | 対応済み（5d02a6f、core §6.4 owner の（参考）） |
| C-47 | §4.4 | host が max_op_ms をそのまま信じると、壊れた値（0xFFFFFFFF）で何日も待つ | 「host は自分の上限で待ち時間を切ってよい（切ったらリンクの失敗）」 | 文言 | 未対応（規則と判断: peers に先に送る。§4.4 の待ちの下限より短く切ることを許すことになる） |

---

#### 要約

| id | 節 | 重さ | 一言 | 規則 / 文言 |
|---|---|---|---|---|
| C-01 | §2.2、§8、registry | ★ | tag の番号は下の 7 bit。registry の 0x90 と 0x01（critical）の書き方が違う | 規則の明確化（実装は既にこの形） |
| C-02 | §4.3 順 5/6、§2.4 | ★ | 後から定めうる値は unsupported（malformed にしない）。予約のビット | 規則 |
| C-03 | §2.2、§2.3 | ★ | 繰り返せない tag の繰り返し、知っている TLV の長さの誤り、要求の TLV の値を後ろに伸ばさない | 規則 |
| C-04 | §2.3 ignored | ★ | 16 個まで、超えたら 0x00 の印、落とさない（既知の未決） | 規則 |
| C-05 | §3.5 port | ★ | host は自分の経路の index を知れない → confirm の応答の TLV | 規則 |
| C-06 | §4.4 | ★ | 待ち時間に遅い口の転送時間を入れる | 規則（時間） |
| C-07 | §3.1、§3.2、§5.1 | ★ | TCP で 200 ms のやり直しをしない。立て直しは自分が書いてから 250 ms 待つ。長すぎる length | 規則（時間） |
| C-08 | §4.4 | ★ | window などは経路ごと | 規則の明確化 |
| C-09 | §3.4、§3.5 | ★ | 115200 8N1、流れの制御なし、line coding と DTR を見ない（決めたことを規範に） | 規則 |
| C-10 | 新 §1.1/§1.2 | ★ | 必須と任意、規範の語、適合試験の置き場 | 文言 + 確認 |
| C-11 | §3.3 | ★ | 第三者のハードウェアは自動で見つからない。プロジェクトの VID:PID を誰が使えるか（前提で再提起） | 規則（ユーザー判断） |
| C-12 | registry 0x4A | ★ | discoverable のコメントが iProduct のまま | 文言 |
| C-13 | §2.1、§7.4 | ★ | bitmap のビットの順 | 文言 |
| C-14 | 冒頭、§14 | ★ | dmseq に英語版が無い、原文の言語を本文に書く | 文言・文書 |
| C-15 | §7.1、§2.7 | ★ | revision の効く範囲、confirm の形は不変 | 規則 |
| C-16 | §5.2 | ○ | rejected も表に覚える | 規則 |
| C-17 | §6.1、§6.4 | ○ | lease の数え直しと丸めの範囲 | 規則 + 文言 |
| C-18 | §6.1、§4.1 | ○ | session_id は乱数（0 は使わない）、open は 0x01 | 規則 |
| C-19 | §6.5 | ○ | boot_id の「必ず」 | 文言 |
| C-20 | §7.1 | ○ | confirm の値の制約 | 文言 |
| C-21 | §4.3 | ○ | payload の fn の位置、unknown_operation と unsupported の書き分け | 文言 |
| C-22 | §2.1 | ○ | UTF-8 と制御文字、真偽値 | 規則 |
| C-23 | §7.2、§13、§7.5 | ○ | 名前の文法、model の名前空間、chip の文法 | 規則 |
| C-24 | §7.5 | ○ | ビルド定数の unit_id | 規則 |
| C-25 | §3.3、§3.4 | ○ | 排他で開く、HID の output、WinUSB | 規則 + ガイド |
| C-26 | §3.4 | ○ | ロックなしの答えは偽造できる | 文言 |
| C-27 | registry | ○ | 本文にしか無い数を registry に | 文言（registry） |
| C-28 | registry | ○ | `swept`、`result_lost` のコメント | 文言 |
| C-29 | registry、生成物 | ○ | キーの名前を止める、hash の意味、reference の置き場 | 規則の明確化 |
| C-30 | §2.7、§7.2 | ○ | 古い revision を並べたときの instance | 規則 |
| C-31 | §2.6a | ○ | 時計は減らない | 文言 |
| C-32 | §3.5 | ○ | baud の誤差、verify_ms 0 | 規則 |
| C-33 | §11.3 | ○ | ハートビートの下限 | 規則 |
| C-34 | §13 | ○ | 凍結の後の番号の割り当ての手続き、0xF0〜 を揃える | 文言 |
| C-35 | §6.4、§7.5、kind 3 | ○ | 今の道具・チップの名前を規範から外す | 文言 |
| C-36〜C-47 | 各所 | △ | 短い message、受けの上限、送り直しの後、list、§2.6、CDC の interface、TCP、bind、C の header、状態の行、owner、max_op_ms | 主に文言 |

★ は 15 件（規則が変わるのは C-02、C-03、C-04、C-05、C-06、C-07、C-09、C-11、C-15。明確化で peers に確認だけのものは C-01、C-08、C-10。
文言だけは C-12、C-13、C-14）。peers への相談は、規則の 9 件をまとめて 1 つの diff にするのがよい。C-11 は今日決めたことをもう一度問うので、
先にユーザーに判断してもらう。

---

## 標準インターフェースの点検（第三者レビュー前、2026-10-02）

対象: oep-spec `docs/oep-if-common`、`oep-if-debug`（wire / target）、`oep-if-console`、`oep-if-fixture`（gpio / uart / i2c-target /
spi-target）、`oep-if-capture`（logic / analog / capture-group）の ja と en、`registry/oep-v1.toml` の該当する節。probe-config は対象外
（関係する所だけ相互参照として挙げる）。前提として review-guide、v1-freeze-decisions（§0 の固定表を含む）、v1-zero-base-review-2026-10-02 を
読んだ。決まっている点（☆1〜☆8、§0.3 の固定、9 つの選択）は、前提（不特定の第三者が文書だけで実装する）で答えが変わるもの以外は再び挙げていない。

前提: 見たことのない MCU、デバッグの線、target、試験の構成のために、不特定の人が文書だけで probe と host を作る。判断の基準は今の bench ではなく、その人たちが何を要るか。

重さ: ★ 第三者レビューの前に直す / ○ 直すべき / △ 直すとよい。
「規則」= 規則が変わるので peers（ch32rv / WireSkein / bench）への相談が要る。「文言」= 言い回しの修正だけ。

ja と en: 5 文書とも行の対応は 1 対 1 で、数値・hex の字句は一致した（ja だけの「1」「2」は「1 つ」などの和文の数詞）。拾い読みした所（線切れ、
max_length、MISO、trigger の type）に意味の食い違いは無かった。en の規範の文書は**日本語版しか無い記録**（logic-capture、link-measurements）に
リンクしているため、下の ★6 は英語の読み手にとってさらに重くなる。

---

#### ★ 第三者レビューの前に直す

#### ★1 scan の count = 0 が、空いているピンの組をすべて駆動する（idle の出力のピンも）

状態: 対応済み（0517c2f、18d7eac、debug §1「Channels with an idle item」と（Informative）の 1 文、core §4.3 holder_kind 7。label の channel を外す案は取り下げ）

- **場所**: oep-if-debug §1「ピンの組」、probe-config §1 idle（相互参照）
- **問題**: role_channels で宣言した線では、count = 0 は「role 1 の候補 × role 2 の候補」のうち「今ほかのもの（plan、ほかの線の接続、設定の資源）が
  持っている」ものを除いたすべての組を試す。idle の項目（特に mode 3 / 4。probe-config には「target の電源のスイッチなど」のためとある）は
  「plan にも接続にも使われていないピンの状態」で、何かに**持たれている**わけではない。だから count = 0 の scan は、電源のスイッチを駆動している
  ピンを SWCLK / SWDIO として動かし、target の電源を入れ切りしたり、出力どうしをぶつけたりしうる。ほかの機能（gpio、uart）は plan を取らないと
  動かないが、scan の count = 0 は配線を知らないまま、空いているピンをすべて動かせる唯一の op である。不特定の治具では、空いたピンが何に
  つながっているか分からない。
- **直す**:
  1. debug §1: 「count = 0 の並びと pins の無い attach の候補には、**設定の idle を持つ channel**（どの mode でも）と、fn 0 の describe の label を
     持つ channel を入れない」（disable と同じ扱い。利用者や firmware が「これは何かにつながっている」と言ったピンだから）。
  2. 組を並べた scan や attach の pins に、idle が mode 3 / 4 の channel があれば rejected unavailable（cause 5、holder_kind に 7「設定の idle」を
     足す）。または、少なくとも出力の idle は scan で動かさない、と書く。
  3. 規範の 1 文: 「count = 0 は、宣言した候補のうち空いているピンを順に駆動する。配線の分からない治具では、host は利用者の同意なしに
     count = 0 を送らない（参考）」。
- **区分**: 規則（holder_kind の追加、候補から外す規則）→ peers に相談。

#### ★2 spi-target: CS が無効な間、MISO を駆動するかが決まっていない

状態: 対応済み（0517c2f、73a0c37、fixture §4 MISO は CS が有効な間だけ、SCK / MOSI / CS は入力、describe の cs_setup_ns）

- **場所**: oep-if-fixture §4（arm、「MISO は tx の外では 0」）
- **問題**: 「MISO は tx の外（未 arm、tx を使い切った後）では 0」とあり、CS が無効な間の MISO の状態が書かれていない。素直に読むと、probe は
  ずっと MISO を low に駆動してよいように読める。SPI のバスに target が複数つながっている DUT（よくある形）では、選ばれていない target が
  MISO を駆動すると、選ばれた target とぶつかる（電気的にも、データとしても）。configure の前（state 0）と、plan を取った直後のピンの
  状態も書かれていない。
- **直す**: §4 に「**CS が無効な間と state 0 の間、probe は MISO を駆動しない**（Hi-Z。core §8 の空きの状態でもなく、plan が持ったまま
  入力にする）。『0 を出す』は CS が有効な間の、tx の外のビットのこと。SCK、MOSI、CS は常に入力」を足す。
- **区分**: 規則（決まっていなかった所を決める）→ 相談。参照の実装はたぶんすでにそうなっているので、確かめるだけで済むはず。

#### ★3 i2c-target: SDA / SCL の駆動の方式とプルアップが決まっていない

状態: 対応済み（0517c2f、18d7eac、fixture §3 オープンドレインだけ、内蔵のプルアップは features bit2 と pullup_ohms で宣言、state 0 は ACK しない）

- **場所**: oep-if-fixture §3
- **問題**: probe が SDA / SCL を**オープンドレインでしか駆動しない**こと（high に押し上げない）が書かれていない。内蔵のプルアップを入れるかも
  書かれていない。push-pull の実装は、controller やほかの target と短絡する。内蔵のプルアップは、外部のプルアップのある DUT では電圧の分け方を
  変え、プルアップの無い DUT では、それだけで動いてしまい、DUT の不具合を隠す。state 0（configure の前）にピンがアドレスに ACK するかも
  決まっていない。
- **直す**: §3 に「SDA と SCL は**オープンドレインだけ**で駆動する（low に引くか、離す）。probe は内蔵のプルアップを入れない（入れられる probe は
  describe の features に bit を足して、宣言してから configure の TLV で選ぶ。v1 では入れない）。state 0 では、どのアドレスにも ACK しない
  （線を離したまま）」を足す。
- **区分**: 規則 → 相談。

#### ★4 線切れの 1000 ms、reset の後の待ち、attach の速さの探索に、host の待ち時間との釣り合いが無い

状態: 対応済み（3a88ec9、f7d6d21、18d7eac、debug §1 attach / scan の budget、§2 要求の中の 200 ms と線切れの実時間 1000 ms、core §4.4。bench の cold attach の計測は凍結の前に未）

- **場所**: oep-if-debug §2（線切れ）、§1（attach、scan の 500 ms）、core §4.4（host の待ち時間 = 引数の時間 + 1000 ms）
- **問題**:
  - 「最遅の速さで再試行しても 1000 ms 続けて応答が無い」で線切れとし、「要求の中で判定したら、その要求を status line で返す」。この 1000 ms が
    1 つの要求の中なのか、要求をまたぐ実時間なのかが書かれていない。1 つの要求の中なら、dmi（引数の時間 0）の host の待ち時間は 1000 ms
    ちょうどで、probe の答えと host の時間切れが**同時になる**。パイプラインで後ろに並んだ要求は、それより先に時間切れになる（probe は順に処理する）。
  - 「reset の線の解放から target の debug が戻るまでの時間は数えない」には上限が無い。この間、要求はいつまでも返らないことがありうる。
  - attach の「読むだけで速さを選ぶ」探索にも、時間の上限が無い（scan には 500 ms がある）。
  - probe が max_op_ms を 1000 ms より小さく宣言したとき、1000 ms の判定はどの要求にも収まらない。
- **直す**（案）: debug §2 を次に替える:「1 つの要求の中で線の再試行に使う時間は **200 ms まで**（registry `limits.wire_retry_ms`）とし、使い切ったら
  その要求を status line で返す。**線切れ**は、status line の失敗（要求の中でも、コンソールの読みの中でも）が、間に成功を挟まず
  **実時間で 1000 ms 続いた**とき（`limits.wire_lost_ms`）。reset の後の数えない時間は、hold_ms の解放から 1000 ms まで」。attach にも scan と同じ
  「1 回の応答に掛ける時間は 500 ms 以下」（速さの探索を含む）を付ける。scan の 500 ms は min(500, max_op_ms) とする。
- **区分**: 規則 → 相談（probe の実装、fake、client の待ち時間）。

#### ★5 許していないピンの組の断り方が、core §4.3 の順とほかの文書に反している

状態: 対応済み（78403b2、debug §1「A combination the declaration ... does not allow is rejected unsupported」）

- **場所**: oep-if-debug §1「許していない組は、何も実行せずに rejected unavailable」
- **問題**: core §4.3 の断り方の順 6 は「定義にはあるが、この probe が持たない（…、**ピンの組**）→ unsupported」と書いている。同じ考え方で、
  plan_apply（channel が role_channels に無い → unsupported）、attach の reset の channel（宣言に無い → unsupported、tag 0x05）、probe-config の
  slot（「その線が許す組でなければ rejected unsupported」）は unsupported を使っている。debug §1 だけが unavailable で、host は同じ誤りに
  2 つの理由を受けうる（原則 8 に反する）。
- **直す**: debug §1:「宣言（channel_group / role_channels）で許していない組は rejected unsupported（attach は tag 0x03 pins、scan は tag 0x00 と
  並びの位置の TLV index）。**持たれている組**（plan、接続、設定、disable）は rejected unavailable（cause 1 / 5）」。en も同じ。
- **区分**: 規則（断りの理由が変わる）→ 相談（probe、fake、client の例外の対応表）。

#### ★6 capture の意味の一部が、規範ではない記録（logic-capture）にしか無い

状態: 対応済み（a35acb0、18d7eac、capture §2.1 モードとストリーミングの決めごと、§3.5 mode の background）

- **場所**: oep-if-capture 冒頭（「モードの意味は設計 §2.4、レートの決め方は同 §2.10」）、§3.5（describe mode の `background(u8)`）、
  §3.3（「宣言は目安」）、§3.4（ストリーミング）
- **問題**: 文書だけで実装できない。
  - describe の mode の `background(u8)` は、規範のどこにも意味も値も無い（logic-capture §2.4 の「バックグラウンドのフラグ」にだけある。
    値の 0 / 1 もそこには無い）。blocking_ms との関係も書かれていない。
  - ストリーミングの決めごと（送り先が無いときは**新しい**データを捨てる、stop の後も送り残しを送る、送ったデータを read で読み直せる
    とは限らない、購読がロックと一緒に終わる）は logic-capture §2.4 にだけある。common §1.5 は「送ったデータを read で読み直せるかは
    インターフェースが決める」と言うが、capture は決めていない。
  - logic-capture は記録の文書で、チップ名（P4、PARLIO、ESP32 の ADC）、日付、試作の commit を持ち、日本語しか無い。en の読み手はたどれない。
- **直す**: capture §2 に「モード」の節を置き、logic-capture §2.4 の表の「動き」と、ストリーミングの決めごと 5 項目を規範の文として写す。
  §3.5 の mode に「background: 0 = 取っている間 probe は要求に答えない（start の応答の blocking_ms が 0 でない）、1 = 答える（blocking_ms は 0）。
  2 以上は予約」を足す。§3.3 の「宣言は目安、configure の応答が正」は、理由のリンクを外して、規範の 1 文として残す。logic-capture へのリンクは
  「（理由: …）」の形に限る。
- **区分**: background の値を決めるのは規則 → 相談。ほかは決まっていることを写すだけなので文言。

#### ★7 新しい wire / target を足す道が書かれていない（ほかの debug の線、JTAG、ほかの 1 線のプロトコル）

状態: 対応済み（78403b2、18d7eac、debug §0「What every wire shares, and what a new wire defines」、probe-config §1.1 slot）

- **場所**: oep-if-debug §1〜§3、common §2、registry（wire ごとの `pin_role`、`scan_kind`、`target_id_scheme`）、probe-config §1.1 の slot（相互参照）
- **問題**: 第三者が最初に持ち込むのは、RISC-V の JTAG DTM（RISC-V の標準の debug transport）、cJTAG、ARM の JTAG-DP、ほかのベンダーの 1 線の
  プロトコルのどれかになりそうだ。ところが今の文書では:
  - 「全 wire」の規則（§1、§2）が、具体的なピン（swdio / swclk）、レジスタ（DMSTATUS、DPIDR）、「3 線で 1 つの形」で書かれていて、どれが
    どの wire にも効く約束で、どれが今の 3 線の形なのかが分からない。
  - scan / attach / connections の固定部分は 2 本のピンの組（swdio(u16)、swclk(u16)）で、4〜5 本の JTAG は入らない。新しい wire が自分の形を
    決めてよいのか、op の番号と意味は揃えるべきなのかが書かれていない。
  - probe-config の slot の固定部分も `swdio、swclk` で、wire_fn は rvswd / swio に限られている（凍結すると、新しい wire は新しい item tag でしか
    slot に載らない）。
  - 「見つかった」の判定（DMSTATUS.version が 2 か 3）、`target_id_scheme` の番号の付け方、新しい wire が作る connection に console や slot が
    乗るかを、誰がどこで決めるかが無い。
- **直す**: oep-if-debug に「§0 wire の共通の約束と、新しい wire が定めるもの」を置く。
  1. どの wire にも効く約束（今の §1 / §2 から、ピンの名前を「role 1 / role 2 の channel」に替えて抜き出す）: 書き込む前に速さを確かめる、
     count = 0 の意味と候補の除き方（★1）、席と max_connections、時間の上限（★4）、閉じるときの不変条件、ピンの解放（○14）。
  2. 新しい wire が文書で定めるもの: pin_role、ピンの指し方（2 本でない wire は pins TLV と scan / connections の entry を `n × (role(u8)、channel(u16))`
     の形で自分で定める。op の番号 0x01 scan、0x02 attach、0x03 detach、0x05 connections と意味は揃える）、速さの選び方、「見つかった」の判定、
     scan_kind、target_id の scheme（○5 の 1 つの空間から取る）、線切れの見つけ方、どの `oep.target.*` に connection を渡すか、console と slot が
     乗るか。
  3. probe-config の担当に: slot のピンを `n × (role、channel)` にするか、凍結の前に「2 本でない wire の slot は新しい item tag」と決めて書く。
- **区分**: 2 の「entry の形を wire が決める、op 番号は揃える」と 3 は規則 → 相談。1 は文言（抜き出すだけ）。

---

#### ○ 直すべき

#### ○1 「見つかった」を DMSTATUS.version 2 / 3 に限っている

状態: 対応済み（78403b2、debug §1「What scan writes」: version ≥ 2 かつ ≠ 15）

- **場所**: debug §1 scan
- **問題**: Debug Spec の新しい版（version 4 以降）の DM を、scan が「無い」と答える。
- **直す**: 「version が 2 以上 15 未満（0 = DM なし、15 = 準拠しない、1 = 0.11 は扱わない）」。
- **区分**: 規則（小さい）→ 相談。

#### ○2 reset の method 0「probe が選ぶ」と「reset の線に既定は無い」がぶつかる

状態: 未対応（debug §4.3 の method 0 はまだ「the probe chooses」、common §1.3 も「probe が選んだとき」のまま）

- **場所**: debug §4.3 TLV method、common §1.3 mark reset の detail（「probe が選んだときは実際に使った方法」に 2 NRST がある）
- **問題**: method 0 で probe が NRST を選べるなら channel の指定が要り、§3 の「reset の線に既定は無い」に反する。選べないなら、method 0 と 1 は同じ
  になる。
- **直す**: 「v1 の method 0 は ndmreset と同じ（probe は NRST を選ばない。NRST は attach の reset TLV か gpio で host が channel を示す）」。
- **区分**: 文言（今の意味を明らかにするだけ）。ただし NRST を選ぶ実装があるなら規則になる。

#### ○3 dmi の待ちの和に、回数で決まる 0x03 が入っている

状態: 対応済み（3a88ec9、debug §4.1 和に入れるのは 0x04 と 0x05 だけ）

- **場所**: debug §4.1（「待ち（0x04 の us、0x03 / 0x05 の上限）の和は max_op_ms を超えてはならない」）
- **問題**: 0x03 の上限は max_reads（回数）で、時間に直す方法が無い。probe と host で計算が合わない。
- **直す**: 「和に入れるのは 0x04 の wait_us と 0x05 の max_us。0x03 は和に入れず、probe は要求の中で max_op_ms を使い切ったら、その手順を
  status timeout で終える」。
- **区分**: 文言に近い規則 → 相談。

#### ○4 halt / step が失敗したときに、target に何を残すか

状態: 対応済み（78403b2、18d7eac、debug §4.2 halt の timeout で haltreq を下ろす、step の step_left、§4 の表）

- **場所**: debug §4 の表、§4.2
- **問題**: step が 100 ms 以内に戻らないと status state だが、そのとき hart は走っているかもしれない（dcsr.step は立っているのか、下ろすのか）。
  halt の timeout で haltreq を残すのかも書かれていない。「op の境界の不変条件」から読み取れない。
- **直す**: 「step が戻らないとき、probe は haltreq を 1 回出して 100 ms 待ち、止まれば dcsr.step を下ろし、DATA を戻して status state。止まらなければ
  dcsr.step は戻せないので、応答の TLV で知らせる（または status state と、新しい flags）」。halt の timeout:「haltreq を下ろして返す」か「立てたまま
  返す」のどちらかに決める。
- **区分**: 規則 → 相談。

#### ○5 target_id の scheme が wire ごとの表に分かれているのに、番号は 1 つの空間として使われている

状態: 対応済み（78403b2、18d7eac、debug §1 target_id の scheme は probe で 1 つの空間、registry `[common.enum.target_id_scheme]`）

- **場所**: registry `[interface.enum.target_id_scheme]`（rvswd / swio は 1、swd は 2）、debug §1「wire ごとに registry が定める」、probe-config の
  slot の lock_scheme
- **問題**: 「wire ごと」なら、新しい wire の scheme 1 と rvswd の scheme 1 が衝突してよいことになる。slot の錠は scheme の番号だけで比べる。
- **直す**: registry に `[common.enum.target_id_scheme]` を 1 つ置き（1 wch_dmi_7f、2 swd_targetsel、3 以降は新しい wire が足す）、debug §1 を
  「scheme は probe 全体で 1 つの空間（registry）。wire はどれを使うかを定める」に。
- **区分**: registry の形と文言（番号は変わらない）。

#### ○6 console の規則が、DATA0 を使う方式と riscv-dm を前提にしている

状態: 対応済み（78403b2、console §2「Each mechanism defines」、§3 に 0〜2 の方式の値）

- **場所**: oep-if-console §2、§3 冒頭
- **問題**: 「1 つの connection に生きているストリームは 1 つ（3 方式とも DATA0 を郵便受けにする）」、「読みを止めるのは riscv-dm の要求の間と
  hart が止まっている間」、「DMSTATUS を見る間隔は 20 ms 以下」が、インターフェース全体の規則として書かれている。ARM の target でよく使う
  コンソール（メモリのリングを MEM-AP で読む方式、semihosting、SWO）を新しい mechanism として足すと、これらの規則を書き直すことになる
  （今は swd の connection への open は cause 6）。
- **直す**: §2 を「どの mechanism にも効く規則」（番号、寿命、閉じたストリームを読めること、write の意味）と「mechanism が定めるもの」（使える
  connection の種類、target のどの資源を使うか、読みを止める条件、1 つの connection に何本開けるか、見る間隔）に分け、今の 3 方式の値は §3 に
  移す。
- **区分**: 文言（構成を変えるだけ。3 方式の意味は変えない）。peers にも差分を見せる。

#### ○7 未定義の値の断り方が、インターフェースごとに違う

状態: 取り下げ（C-02 と逆向き。console と capture の unsupported が正しく、fixture の方を unsupported に直した: fb44490）

- **場所**: console §1（知らない mechanism → unsupported）、capture §3.3（宣言に無い trigger の type → unsupported。未定義と、定義にあるが宣言に無い、を
  区別していない）、それに対して gpio（未定義の mode → malformed）、uart（format の未定義のビット → malformed）、i2c（mode 0 / 4 以上 → malformed）
- **問題**: core §4.3 の 5（未定義の値 → malformed）と 6（定義にあるが持たない → unsupported）を、console と capture が混ぜている。
- **直す**: console:「registry に無い mechanism は malformed、定義にあるが mechanisms に無いものは unsupported」。capture の mode と trigger の type も
  同じ書き方にする（0x40 以降の「別の定義」の値は、このインターフェースでは未定義 → malformed）。
- **区分**: 規則（断りの理由が変わる）→ 相談。

#### ○8 capture の configure: どの TLV を critical で送るかが決まっていない

状態: 対応済み（a35acb0、3c6691a、capture §3.3「Sent critical」の列と文、samples は critical でない）

- **場所**: capture §3.3
- **問題**: 「critical を立てた TLV を扱えなければ断る、立てていなければ無視して ignored に載せる」。でも、どの tag を critical で送るべきかが
  書かれていない。ストリーミングを持たない probe に mode = 3 を critical なしで送ると、probe は mode を無視して既定のモードで configure し、
  host が ignored を見落とすと、違うモードのまま進む。rate や trigger の type のように、critical に関係なく断ると書かれている tag もあって、
  ばらばらになっている。
- **直す**: 表に「host は critical で送る」の列を足す（mode、trigger、pretrigger、frontend、samples は必ず。segments は任意）。あるいは「知っている
  tag の扱えない値は、critical に関係なく unsupported」と 1 文で決める（rate と同じ）。
- **区分**: 規則 → 相談。

#### ○9 blocking_ms の間に、host と probe が何をするか

状態: 対応済み（a35acb0、capture §3.2 blocking_ms の間はどの経路にも送らない、後は §5.1）

- **場所**: capture §3.2（start の blocking_ms、「blocking の間は lease を数えない」）、§4.1 group の start
- **問題**: probe がほかの経路でも答えないのか、届いたフレームを捨てるのか、host はいつ送ってよいのかが無い。UART の probe では、その間に届いた
  バイトが失われ、host は送り直しを使い切りうる。
- **直す**: 「start の応答の後 blocking_ms の間、probe はどの経路でも受けたフレームを処理しない（失ってよい）。host はその間、その probe の
  どの経路にも送らない。終わった後、host は §5.1 の立て直し（静かになるのを待って confirm）から始めてよい。lease はその間に加えて
  host_wait_add_ms を数えない」。
- **区分**: 規則 → 相談。

#### ○10 capture-group に状態の遷移表が無い

状態: 対応済み（a35acb0、capture §4.1 束ねていない組、start の確かめ、組の state）

- **場所**: capture §4.1
- **問題**: 束ねていない組への start / stop / force、トラックごとの状態がそろわないとき（片方は 5、もう片方は 3）の組の state、ストリーミングで
  トラックが購読されていないときの組の start が、どれも決まっていない。
- **直す**: §3.2 と同じ形の表を足す（例: 束ねていない start → unavailable 6、stop / force → 何もせず成功。組の state はトラックの state の
  「最も進んでいない値」、エラーが 1 つでもあれば 6。ストリーミングで購読の無いトラックがあれば start は unavailable 6、payload に fn）。
- **区分**: 規則 → 相談。

#### ○11 位置つきのストリームの read: まだ無い位置と、1 回の量の上限

状態: 対応済み（a35acb0、common §1.2 書き込み位置より先、len の上限、from 3 の arg > 0xFF）

- **場所**: common §1.2
- **問題**: arg がまだ書かれていない位置（今の書き込み位置より先。古い boot の位置を持ったままの host など）のときの start と flags が無い
  （capture §3.2 は「まだ取れていない位置なら、あるところまで返す」と書いている）。max が 1 フレームに入る量より大きいときに切ってよいことも
  書かれていない。from 3 の arg が 0xFF を超えたときも決まっていない。
- **直す**: 「arg が書き込み位置より先なら、start = arg、len 0、gap 0（そこから先のデータはそこに来る）」か「start = 書き込み位置、len 0」の
  どちらかに決める。「len は max と、応答が max_frame に入る量の小さい方」。「from 3 の arg > 0xFF は malformed」。
- **区分**: 規則（小さい）→ 相談。

#### ○12 I/O の電圧（target の電圧）を宣言する所が無い

状態: 取り下げ（任意の describe の tag は凍結の後も revision を変えずに足せる、core §2.7。番号は level shifter を持つ probe と一緒に決める）

- **場所**: core §7.5（fn 0 の describe）。fixture §1、debug §1 の「何を駆動してよいか」に関係する
- **問題**: probe は何 V で駆動するのか（3.3 V 固定、1.8〜5 V に追従する level shifter、VTref を読む）を host が知る方法が無い。
  不特定の target（1.8 V の MCU、5 V の治具）では、host や利用者が電圧の合わない駆動を防げない。市販の debug probe の多くは VTref を持っている。
- **直す**: fn 0 の describe の任意の tag `io_voltage`（channel の範囲ごとに: kind(u8: 0 固定、1 VTref に追従、2 設定できる)、min_mv(u32)、max_mv(u32)）を
  凍結の前に名前と番号だけでも決める。VTref を読む op は後からでよい（core §0.4 の伸ばす道で足せる）。
- **区分**: 規則（tag を足す。壊すものは無い）→ 相談。凍結の後でも足せるので ○。

#### ○13 plan を取ったピンが、configure の前と、聞くだけの機能で、どの電気の状態になるか

状態: 対応済み（0517c2f、18d7eac、3d51d4a、core §8「Taking a plan does not change a pin's electrical state」、capture §1.2、fixture §2〜§4）

- **場所**: capture §1.2「ピンの共有」、fixture §2〜§4、gpio §1（「最初の set までそれまでの状態を保つ」）
- **問題**: gpio は「plan を取っても level は変わらない」と書いている。logic / analog / i2c-target / spi-target は書いていない。idle が mode 3 / 4
  （target の電源を出している）のピンを logic の plan に取ると、probe がそれを入力に替えて電源を切ってしまう、という実装を止める文が無い。
  analog は pad をアナログに替えるので、必ず駆動が止まる。
- **直す**: core §8 か各文書に「plan を取っただけでは、ピンの電気の状態を変えない。変わるのは、そのインターフェースが動かすとき（uart の TX は
  plan を取った時点で high、i2c / spi は configure から）」。analog:「idle が mode 3 / 4 の channel の analog の plan は rejected unavailable（cause 5）」。
  logic:「聞くだけで、出力の駆動を止めない」。
- **区分**: 規則 → 相談。

#### ○14 接続が閉じたときの線のピンの状態

状態: 対応済み（0517c2f、debug §2「When a connection closes, the channels ... go to the idle state of core §8」）

- **場所**: debug §1（「接続が無くなれば放す」）、§2
- **問題**: scan では「外れた組のピンは core §8 の空きの状態に戻す」と書いているが、connection が閉じたときは「放す」だけで、空きの状態
  （idle、または Hi-Z）にするとは書いていない。SWCLK を low のまま駆動し続ける実装も許してしまう。
- **直す**: 「connection が閉じたら、その組の channel は core §8 の空きの状態にする（idle_clock の駆動も止める）」。
- **区分**: 文言（core §8 の「どの経路で解いても」と同じ意味）。

#### ○15 registry: analog の trigger の enum が文と合わない

状態: 対応済み（a35acb0、18d7eac、registry analog の trigger から level / edge を外した。capture §3.3 と一致）

- **場所**: registry `oep.fixture.analog` の `[interface.enum.trigger]`（level = 1、edge = 2 がある）、capture §3.3「1〜2 はロジック、3〜4 はアナログ」
- **直す**: analog の enum から level / edge を外すか、文を「analog は 1 / 2 も宣言してよい（o / b で切り出した値の 0 / それ以外）」に替える。
  どちらにするか決める。
- **区分**: 外すなら文言。analog で level / edge を許すなら規則。

#### ○16 規範の数のうち、registry に無いもの

状態: 対応済み（5d02a6f、registry `console_dmstatus_poll_ms`、`uart_baud_tolerance_pct`、`uart_default_baud`、`tar_rewrite_bytes`、`block_frame_overhead_bytes`、`fixture_count_max`、`scan_tried_max`、capture の enum `jitter_kind`、`rate_accuracy_how`、`reference_how`、error の 0x40〜 probe 固有はコメントに。本文が名前を引く）

- **場所**: registry `[limits]`、`[timing]`
- **問題**: review-guide は「registry は番号と数の唯一の定義」と言うが、規範の文にしか無い数がある: 線切れの 1000 ms と scan の 500 ms（debug §1 / §2）、
  コンソールで DMSTATUS を見る間隔の 20 ms（console §2）、uart の ±5 % と既定の 115200 8N1（fixture §2）、TAR の 1 KiB（debug §6）、max_length ≤
  max_frame − 24（debug §4.5）、i2c / spi の pending / queued を 255 で止めること。enum が comment にしか無いもの: capture の timing の jitter_kind
  （0 / 1 / 2）、rate_accuracy の how、reference の how、error の 0x40 以降を probe 固有にすること。
- **直す**: `[limits]` / `[timing]` と、各インターフェースの enum に足す。
- **区分**: 文言（registry に写すだけ。値は変えない）。

#### ○17 rvswd / swio の線のプロトコルそのものが、どこにも定められていない

状態: 対応済み（7392817、e9cd891、debug §3.1 RVSWD の frame、§3.2 SWIO の frame。外を指す代わりに規範に定めた。ch32rv のレビュー済み）

- **場所**: debug §3 冒頭の表
- **問題**: OEP は API の層を決め、線の bit の並びは決めない。SWD は ARM の公開の仕様を指せるが、RVSWD / SWIO には公開の仕様が無い。
  第三者は「文書だけで」`oep.wire.rvswd` を実装できない。
- **直す**: 「線の bit 単位の手順は OEP の外」と明記し、参考として、公開している観測の記録（wch-protocols など）を指す（規範ではない）。
- **区分**: 文言。

---

#### △ 直すとよい

| id | 場所 | 問題 | 直す | 区分 | 状態 |
|---|---|---|---|---|---|
| △1 | debug §3 表（「WCH の 2 線 / 1 線」）、console §3.1「WCH の SDI printf」、§3.2「minichlink の framing」、debug §3 の target_id scheme 1「WCH の DM の DMI 0x7F」 | 規範の文にベンダーやツールの名前がある（spec-writing-rules） | 規範の文は方式の定義だけにして、名前の由来は「（参考）」の注に移す。registry の識別子 `wch_dmi_7f` はそのままでよい | 文言。対応済み（78137fb）: 名前は「（参考）」の注へ。gdb は「デバッガ」に | 対応済み（78137fb、debug 冒頭と console §3.1 / §3.2 の（Reference）） |
| △2 | debug §1 / §3 / §4.2 / §4.5 / §4.6 の「[リンクの計測] §3」6 か所、§4.2 の「target によっては…」、capture §3.7 の「44642/1 など（設計 §7.4）」 | 規範の文の中に、記録への理由のリンクと実例の話がある | 「（理由: …）」の形にまとめて、規範の文から切り離す | 文言 | 対応済み（5d02a6f、debug §1 / §3 / §4.2 / §4.5 / §4.6 を「(reasons: …)」に、§4.2 の「target によっては」を（参考）に。似た所: core §3.4 と capture §3.7 の例も） |
| △3 | registry `[limits]` の dm_wait_ms と dmi_busy_retries のコメント「(oep-if-debug §1)」、logic の `[interface.tlv.configure]` のコメント（応答の tag 0x55、0x57〜0x59 が挙がっている） | 節の番号と tag の誤り | §4 にする。configure の tag は 0x47 だけを挙げる | 文言。対応済み（78137fb） | 対応済み（78137fb、registry のコメント） |
| △4 | debug §1「§8.1 のとおり」 | どの文書の §8.1 か書いていない（debug に §8 は無い） | 「core §8.1」 | 文言 | 対応済み（5d02a6f、debug §1 と §3 reset の「§8.1」を「core §8.1」に） |
| △5 | fixture §3 configure の address | 予約のアドレス（0x00〜0x07、0x78〜0x7F。general call、10 bit の前置き）を受けてよいかが無い | 「予約のアドレスは rejected unsupported（宣言で許す probe だけ受ける）」など | 規則（小さい） | 未対応（規則と判断: peers に先に送る。予約のアドレスの断り方） |
| △6 | spi arm の count > length、uart の TX の無い plan での write、console open の mechanism 0xFF | 断り方が書かれていない | malformed / unavailable 6 / malformed と書く | 文言に近い | 未対応（規則と判断: peers に先に送る。書かれていない場合の断り方を決める） |
| △7 | common §1.3 marks | マークのリングがあふれたとき、host がどう知るかが書かれていない（serial が連続しているので、飛びで分かる） | 「serial の飛びが、押し出されたマークの数」と 1 文足す | 文言 | 対応済み（c6cc1f8、common §1.3 marks） |
| △8 | debug §2 の状態機械（lease 切れでは hart に触らない） | host が死ぬと target は止まったままになる（モーターを動かしている target などで危ない）。gdb の detach に慣れた利用者は、走り出すと思いやすい | 規則はそのままで、「安全の注意: lease 切れでは target は止まったまま。host は end の前に resume する」を規範の注に | 文言 | 対応済み（5d02a6f、debug §2 の状態機械の後の（参考、安全）） |
| △9 | capture §1.2 | 符号付きの ADC（2 の補数で値を出す差動の ADC）を表す方法が書かれていない | 「符号付きの値は、probe が 2^(b−1) を足して符号なしにし、zero をそれに合わせる」と 1 文 | 文言 | 未対応（規則と判断: peers に先に送る。符号付きの値の表し方を決める） |
| △10 | debug §3 の scan_kind（rvswd / swio に 2 = arm-adi） | 2 線や 1 線で arm-adi の connection ができるのか、できるなら swd §5 の非対称（slot、console が乗らない）が効くのかが分からない | rvswd / swio の kind を 1 に限るか、arm-adi になる場合の扱いを書く | 文言か規則 | 未対応（規則と判断: peers に先に送る。rvswd / swio の kind を限るか、arm-adi の扱いを決める） |
| △11 | debug §1「速さを確かめ終えるまで書き込まない」と、scan の dmactive の書き込み、swd の固定の速さ | 順番が読み取りにくい | 「scan も attach も、読みで速さを確かめた後にだけ dmactive を書く。swd は速さを確かめられないので、min(max_speed, max_clock_hz) から始める（例外）」 | 文言 | 対応済み（78403b2、debug §1「Writes before the speed is verified」に順を書いた） |
| △12 | core §8（相互参照） | probe-config を持たない probe の、起動時のピンの状態が core に無い | core §8 に「起動時はすべての channel を空きの状態にする」 | 規則（小さい） | 未対応（規則と判断: peers に先に送る。probe-config を持たない probe の起動時の状態は、core §8 にも probe-config にも今は無い。足すと新しい義務になる） |
| △13 | debug §4.5 | read_block は hart が止まっていないと status state。system bus を持つ DM では走ったままでも読める | v1 はそのままでよい。後から features のビットで「走っていても読む」を足せることを、伸ばす道に書く | 文言 | 対応済み（c6cc1f8、debug §4.5 前提の（参考）） |

---

#### まとめ

| id | 文書と節 | 重さ | 要点 | 区分 |
|---|---|---|---|---|
| ★1 | debug §1 scan count = 0 | ★ | 空いているピンをすべて駆動する。idle の出力（電源）も動く | 規則 |
| ★2 | fixture §4 spi-target | ★ | CS が無効な間も MISO を駆動しうる（バスの衝突） | 規則 |
| ★3 | fixture §3 i2c-target | ★ | オープンドレインだけで駆動すること、プルアップ、state 0 の振る舞いが無い | 規則 |
| ★4 | debug §1 / §2、core §4.4 | ★ | 線切れの 1000 ms と host の待ち（+1000 ms）が同時になる。reset の後の待ちと attach の探索に上限が無い | 規則 |
| ★5 | debug §1 | ★ | 許していない組を unavailable で断る（core §4.3 と probe-config は unsupported） | 規則 |
| ★6 | capture 冒頭、§3.3〜§3.5 | ★ | モード、background、ストリーミングの決めごとが記録の文書（日本語だけ）にしか無い | background は規則、ほかは文言 |
| ★7 | debug 全体、common §2、registry、probe-config slot | ★ | 新しい wire / target の足し方が無い。2 本のピンとレジスタの名前が「全 wire」の規則に入っている | 一部は規則 |
| ○1 | debug §1 | ○ | DMSTATUS.version を 2 / 3 に限っている | 規則 |
| ○2 | debug §4.3、common §1.3 | ○ | method 0 と「reset の線に既定は無い」 | 文言 |
| ○3 | debug §4.1 | ○ | 待ちの和に、回数で決まる 0x03 が入っている | 規則 |
| ○4 | debug §4、§4.2 | ○ | step / halt が失敗したとき、target に何を残すか | 規則 |
| ○5 | registry、debug §1 | ○ | target_id_scheme を 1 つの空間に | 文言 / registry |
| ○6 | console §2、§3 | ○ | 規則が DATA0 と riscv-dm を前提にしている | 文言 |
| ○7 | console §1、capture §3.3 | ○ | 未定義の値の断り方が、ほかのインターフェースと違う | 規則 |
| ○8 | capture §3.3 | ○ | critical で送る tag が決まっていない | 規則 |
| ○9 | capture §3.2、§4.1 | ○ | blocking_ms の間に何をするか | 規則 |
| ○10 | capture §4.1 | ○ | capture-group に状態の遷移表が無い | 規則 |
| ○11 | common §1.2 | ○ | まだ無い位置の read、1 回の量、from 3 の arg | 規則 |
| ○12 | core §7.5（fixture、debug） | ○ | I/O の電圧の宣言が無い | 規則 |
| ○13 | capture §1.2、fixture §2〜§4 | ○ | plan を取ったピンの電気の状態（聞くだけの機能、configure の前） | 規則 |
| ○14 | debug §1 / §2 | ○ | 接続が閉じたピンを空きの状態にする | 文言 |
| ○15 | registry analog、capture §3.3 | ○ | trigger の enum が文と合わない | 文言か規則 |
| ○16 | registry `[limits]` / enum | ○ | 規範の数と enum が registry に無い | 文言 |
| ○17 | debug §3 | ○ | rvswd / swio の線のプロトコルを参照する先が無い | 文言 |
| △1〜△13 | 上の表 | △ | 名前、記録へのリンク、節の誤り、細かい断り方、安全の注意 | 主に文言 |

ja と en の食い違い: 数値と hex では見つからなかった（拾い読みでも意味の食い違いは無かった）。registry と文の食い違い: ○15（analog の trigger）、
○16（registry に無い数）、△3（コメントの節の番号と tag）。番号の衝突は無い。

peers に相談するもの（規則）: ★1〜★5、★6 の background、★7 の 2 / 3、○1、○3、○4、○7〜○13、△5、△12。
すぐ入れてよいもの（文言）: ★6 の写し、★7 の 1、○2、○5、○6、○14、○16、○17、△1〜△4、△6〜△9、△11、△13。

---

## 第 3 回の点検: probe-config、開発ガイド、OSS の共通仕様としての準備（2026-10-02）

対象は oep-spec の 82e6b9f（main）。読むだけで、どのリポジトリも変えていない。

前提（ユーザーの指定）: OEP は OSS の共通仕様として公開する直前。会ったことのない多くの人が、見たことのない環境で実装して使う。この後に第三者のレビューがある。判断は今の仮の bench ではなく、そうした人に何が要るかで行う。

先に読んだもの: review-guide（.ja / .md）、v1-freeze-decisions（.ja / .md）、v1-zero-base-review-2026-10-02、v1-zero-base-proposal の該当部分。
決まった点（9 つの選択、☆1〜☆8、#2 保存の読み替え、swd をスロットに載せないこと、describe は宣言だけ、など）は、前提で答えが変わる所だけ挙げる。

重さ: ★ = 第三者のレビューの前に直す、○ = 直したほうがよい（凍結の前が望ましい）、△ = あるとよい。
種類: **規則** = 規則が変わる（ch32rv / WireSkein / bench に先に送る）、**文書** = 文書・文言だけ（差分は peer が見る）、**判断** = ユーザーが決める方針。

---

#### A. oep-if-probe-config（.ja.md / .md）

英語版は日本語版と同じ commit（3cc50c8）まで追従していて、確かめた所（0x7E、unset の宣言していない tag、last_try_at_ns、idle の変更が効く時）は一致している。規範の文には日付・チップ名・逸話がほとんど無い（状態の行の日付だけ）。形は全体によく閉じている。以下は、知らない人が一から実装するときに迷う所。

#### PC-1 ○ §1.3 線の名前を、firmware の固定のラベルからは探せない（規則）

状態: 対応済み（20967d7、probe-config §1.3 の探し方 (c) firmware の label 0x46）

- **場所**: §1.3「探すのは設定の label の項目（§1）だけで、core の describe の label（0x46）やほかの名前は探さない」、§3.1 のリセットでのやり直し、host ガイド §8.1。
- **問題**: 一般の利用者がいちばん多く使うのは、配線の決まった市販の probe（リセットのピンが基板で決まっている）。この形の firmware は自分のリセットの線を describe の 0x46（`NRST` など自由な文字列）でしか言えず、§1.3 の決まりには乗らない。そうなると、(1) boot_reset は利用者が label を set して保存するまで効かない。(2) host は「この probe のリセットの線はどれか」を規範の手段で知れず、自由な文字列の照合か、ガイド §4.6 の総当たりになる。「設定の既定の値は持たない」（§1 冒頭）は守るとしても、**固定の配線の宣言**は宣言そのもの（原則 5 に反しない）。
- **直し方**: §1.3 の探し方に 1 段足す。(a) 設定の `S.N`、(b)（スロットが 1 つ以下のとき）設定の `N`、(c) 同じ規則で describe の 0x46 の text。同じ段で一致が 2 つ以上なら無し、は今のまま。設定の label は (c) より強い。0x46 の text には、§1.3 の比べ方（ASCII の大文字と小文字を区別しない）を当てる。代わりに、fn 0 に線の宣言の tag（`line`: channel(u16)、name）を新しく足し、名前は §1.3 の表から取る形でもよい。
- **種類**: 規則（peer に送る）。

#### PC-2 ○ §1.3 表に無い名前の扱いと、名前を足す道が無い（規則）

状態: 対応済み（20967d7、probe-config §1.3 表に無い名前、registry `[line_names]`、`x-`）

- **問題**: `nrst` / `power_hi` / `power_lo` の 3 つだけで、次のことが書かれていない。(1) 表に無い名前（`boot0`、`vref`、`swo` など）は意味を持たないのか。(2) 標準の名前を後から足すときは revision を上げるのか。(3) 独自の意味を持たせたい人はどうするのか。第三者の firmware や host が `boot0` に独自の意味を付けると、後に標準で足したときにぶつかる。
- **直し方**: §1.3 に「表に無い名前は線の役目を表さない（ただの名前）。標準の名前は registry の `[line_names]` に足し（revision は変えない。§2.7 の任意の追加）、独自の役目は `x-` で始める（例 `x-acme.boot0`）」と書く。表は registry に移し、文書はその写しにする。
- **種類**: 規則。

#### PC-3 ○ idle の mode 1 / 2（pull）を持たない channel の断り方が無い（規則の明示）

状態: 対応済み（20967d7、probe-config §1 idle の pull の無い channel は unsupported、mode 5 以上も unsupported（C-02））

- **場所**: §1 の idle の項、§2 の断り方の表。
- **問題**: 「出力として駆動できない channel への mode 3 / 4 は unsupported」はあるが、pull-up や pull-down を持たないピン（そういう SoC はよくある）への mode 1 / 2 の扱いが無い。未定義の mode（5 以上）も、表の「形の誤り」から読むしかない。core §4.3 の順から推せはするが、2 人の実装者が違う理由を返しうる。
- **直し方**: idle の項に「その channel がその pull を持たない probe では、mode 1 / 2 は rejected unsupported。mode 5 以上は malformed」と書き、断り方の表の unsupported と malformed の行に足す。どのピンが pull や出力を持つかを host が先に知る手段は、gpio の無い probe には無い。そのことを（参考）として書く。
- **種類**: 規則の明示（core §4.3 から導けると peer が見るなら文言）。

#### PC-4 ○ 「firmware が宣言していない channel」が何かを決めていない。「idle と同じ」の参照先も無い（規則の明示）

状態: 対応済み（20967d7、probe-config §1「The channel of an item」）

- **場所**: §1 の disable「firmware が宣言していない channel の disable は rejected unsupported（idle と同じ）」。
- **問題**: idle の項には、宣言していない channel の規則が書かれていない（参照先が無い）。何をもって「宣言した」とするか（fn 0 の `channels`（0x43）未満か、どれかの role_channels / channel_group にあるか）も決まっていない。label の channel にも同じ問題がある。
- **直し方**: §1 の冒頭に定義を 1 つ置く。「channel を持つ項目（label、idle、disable）の channel は fn 0 の channels（0x43）未満でなければならず、外れれば rejected unsupported（payload の tag は項目の tag）」。idle と label にも当て、表に入れる。
- **種類**: 規則（小さいが、probe の返す値が変わりうる）。

#### PC-5 ○ label の text に長さと文字の決まりが無い（規則）

状態: 対応済み（20967d7、probe-config §1 label の text 1〜32 byte、registry `label_max_bytes`）

- **問題**: slot の name（1〜32 byte）や owner（1〜32 byte）には上限があるが、label の text には無い。mixed の印（`[name] `）、保存の max_bytes、host の表示が上限を持てない。空の text、壊れた UTF-8（core §2.1 は UTF-8）の扱いも無い。
- **直し方**: 「text は 1〜32 byte の UTF-8（registry の `limits.label_max_bytes`）。0 byte、上限の超え、UTF-8 として壊れたものは rejected malformed」。§1.3 の名前は ASCII だけなので影響しない。
- **種類**: 規則。

#### PC-6 ○ get の応答の「…」が何かを決めていない（文言）

状態: 対応済み（20967d7、probe-config §2 get の項目は payload の終わりまで、0x7E は置かない）

- **場所**: §2 の表、get の応答「more(u8)、hash(u32)、項目の並び（今の設定）、…」。
- **問題**: 項目の並びは TLV の並びで、応答の TLV（ignored など）と同じ形をしている。「…」が何を指すのか、読む側がどこで項目を読み終えるのかが文から決まらない（0x7E の予約が §1 にあるだけ）。
- **直し方**: 「…」を消し、「payload の終わりまでが項目の並び。tag 0x7E は応答のメタ情報のために予約する（v1 の probe は置かない）。要求に TLV は置かない（core §7.3）」と書く。英語版も同じにする。
- **種類**: 文言。

#### PC-7 △ hash の正規形の細部（文言）

状態: 対応済み（20967d7、e21a9a2、probe-config §2 hash の正規形、tests/vectors に正規形と hash）

- **問題**: (1) 正規形の TLV の tag は critical の bit を外した値か（probe は外して持つ、と §2 にあるので、そう読める）。(2) 「キーの昇順」は、数としての比較か、little endian のバイト列の比較か（u16 では順が違う）。(3) plan の (fn, role, channel) は前のフィールドから比べるのか。
- **直し方**: 「正規形の tag は critical の bit を 0 にした値。キーは数として比べ、組は前のフィールドから比べる」を 1 文で足す。registry か tests に正規形と hash の例を 1 つ置く（O-8 の試験ベクトル）。
- **種類**: 文言。

#### PC-8 ○ bind の port（transport の index）は保存の読み替えの外で、読み替えの理由 3 の意味も曖昧（規則）

状態: 対応済み（20967d7、core §7.5「Invariance of transport indexes」、probe-config §2 起動時の bind と理由 3 は保存全体）

- **場所**: §1.2 の port「firmware の更新で USB の構成が変わると index も変わりうる（bind を見直す）」、§2 の保存の読み替え、§3.3 の unreadable_reason 3。
- **問題**: fn は (name、instance、revision) で読み替えるのに、port は数のまま保存される。firmware を更新すると、保存した bind は黙って別の口を指すか、シリアルの口でない口を指す。この記述は「利用者が見直す」としか言っていない。一般の利用者は配布元の firmware を更新するだけで、bind を見直さない。そのうえ起動時に適用が断られたとき（reason 3）、保存の全部を適用しないのか、断られた項目だけを外すのかが書かれていない（読み替えの理由 2 では全部を適用しない）。
- **直し方**: (a) 保存は port と一緒に transport の kind を持ち、起動時に同じ index の kind が違えば理由 2 と同じに扱う。または (b) ★5（unit_id の不変）と同じく「transport の index は firmware の版を越えて変えない」を core §7.5 に書く。どちらの場合も、§2 に「起動時の適用で断られたものがあれば、保存全体を適用しない（理由 3）」と、全部か一部かを決めて書く。
- **種類**: 規則。

#### PC-9 △ state のページング（文言）

状態: 未対応（一部だけ: 2 つの first は c6cc1f8 で「first_slot に n_slots、first_bind に n_binds」に。ページの間で storage_* が変わったときの扱いは規則と判断: peers に先に送る）

- **場所**: §3.3「more = 1 なら続きがあり、host は first に受け取った数を足してもう一度聞く」。
- **問題**: first は 2 つある（first_slot と first_bind）。storage_state / storage_hash がページの間で変わったときの扱いも無い。
- **直し方**: 「first_slot に n_slots を、first_bind に n_binds を足す。storage_* はどのページでもその時の値（ページの間で変わりうる。host は最後のページの値を使う）」。
- **種類**: 文言。

#### PC-10 △ boot_reset の保持の時間を変えられない（文書）

状態: 未対応（ガイドは別の作業の担当。ガイドに入れる文の案を渡した）

- **問題**: hold_ms は registry の 20 ms に固定。NRST に大きな容量や監視 IC を持つ基板では足りないことがある。
- **直し方**: 今は変えなくてよい（boot_reset の後ろは足し場所）。ガイドに「長い保持が要るなら、boot_reset の後ろに hold_ms を足すのが道（そのときは任意のフィールド、revision は変えない）」と書いておく。
- **種類**: 文書。

#### PC-11 ○ 設定が線を駆動することの安全の注意がまとまっていない（文書）

状態: 対応済み（5d02a6f、probe-config §5 安全（参考）: 設定は host 無しで線を駆動する、設定の前はリセットの状態で外付けの pull が要る、disable は保護でない、認証が無い）

- **問題**: 保存した設定は起動のたびに、host の居ないところで出力を駆動する（mode 3 / 4 の idle、at boot の attach、boot_reset のリセット）。注意は host ガイド §8 と §9.2 に散っていて、仕様の側には無い。たとえば、(1) リセットから firmware が idle を掛けるまで、DFU の間、firmware が壊れたときは、ピンは SoC のリセットの状態にある。電源のスイッチの線には、切れる側に固定する外付けの pull が要る。(2) disable は、ロックを取った host が unset すれば外れる。保護ではなく利用者の宣言である。(3) 設定は、ロックを取ったどの host からでも変えられる（認証が無い）。
- **直し方**: probe-config の末尾に「（参考）安全」の小節を置くか、O-12 の安全の節に probe-config の項を作る。規範の文は増やさない。
- **種類**: 文書。

---

#### B. host / probe 開発ガイド: 知らない人が host / probe を書くのに足りるか

**結論: 足りない。** どちらのガイドも中身は濃いが、実装した人の「踏んだ罠と実測の記録」が中心で、初めての人が順に読んで最小の実装を組める形になっていない。規範（core と oep-if-*）は、実装に要るものを文としてほぼ持っている。それでも「どこから書き始め、何が必須で何が任意か、合っているかをどう確かめるか」の道が無い。

#### G-1 ○ 最小の実装までの道が無い（文書。必須 / 任意の表は O-16 で規則）

状態: 未対応（両ガイドに最小の host / probe までの道が無い。状態の行の書き方だけ 6bcf7e3 で直した）

- **host ガイドに足すもの**（§0「最初の host」）: 口を開く（§1 の DTR / RTS）→ COBS で confirm（corr、待ち時間 1000 ms）→ list → describe のページング → boot_id で cache → open（session_id の乱数、lease）→ 要求 1 つ（例 gpio の read）→ keepalive の間隔 → end。各段に core の節番号と、**実際のバイト列**（16 進）を付ける。
- **probe ガイドに足すもの**（§0「最小の probe」）: 必ず答える op（confirm / list / describe / open / end / keepalive / lock_state）、必ず出す describe の tag（unit_id、transport、max_op_ms など、core §7.5 の「必須」）、送り直しの表（core §5.2 の大きさ）、断り方の順（§4.3）、時計（§2.6a）、lease の数え方、boot_id の作り方を、チェックリストにする。任意のもの（plan、subscribe、port_speed、probe.config、各インターフェース）の一覧も付ける。
- oep-probe-arduino の `examples/01.Basics/Minimal`、`docs/guide/writing-a-probe.md`、`docs/guide/getting-started.md` にはすでにこの役の文書がある。oep-spec のガイドからリンクする（今はリンクが無い）。

#### G-2 ○ host ガイドに無い話題（文書）

状態: 未対応（host ガイドに断りごとの動き、通知、probe.config の手順、fake の節が無い）

足すもの（どれも規範はあり、host の実務の書き方が無い）:
- reject reason ごとの host の動き（malformed = 自分の誤り、unsupported = 宣言を見直す、unavailable = cause と holder、no_session / expired / locked、result_lost）を 1 つの表にする。今は §2.5 と §3 に一部があるだけ。
- revision の確かめ（知らない revision のインターフェースは使わない）、知らない非 critical の TLV と ignored の扱い、並びの要素の知らない後ろの読み飛ばし（core §2.3）。
- 通知: subscribe、seq の抜け、min_bytes / max_delay_ms の選び方（★6 の host の規則）。
- **probe.config の使い方**: 欲しい設定から正規形の hash を計算し、get の hash と比べる → 違うときだけ set → **save は変わったときだけ**（flash の消耗）→ state で slot_state / bind_state を見る。firmware を更新した後に storage が「読めない」（理由 2）になったら、host 側に持っている設定のファイルから set し直す。今のガイドには §6 の 1 行（idle を保存する）しか無い。
- 開発中の相手として **fake の probe**（`python -m oep_client.fake_serve`、pty / TCP）を使えること。今のガイドは fake に触れていない。
- 経路が複数あるときの選び方と、同じ probe を unit_id でまとめること（§3 の発見の段の中に埋もれている）。

#### G-3 ○ ガイドに target 固有の話と日付つきの実測が混ざっている（文書）

状態: 未対応（チップ固有の話と日付つきの実測がガイドに残る。host §2.5 の「（必須）」も残る）

- **host ガイド**: §4.5（CH32 の書き込みの方式の表、RP2350 の C_MASKINTS）、§4.6 の L103 の逸話、§8.5 / §8.6 の実験、§9.3 / §9.4 の ESP32-P4 と CH32V003。
- **probe ガイド**: §4 の大半（RVSWD の休ませ方の表、WCH-LinkE の観察、LinkE の個体の serial `FC928F068181`、未解決の原因の推測）。
- **問題**: 初めての人には、どれが一般の規則でどれが特定のチップの話かが分からない。規則としては「ローダーは命令セットで選ぶ」「debug の線は弱い強さで駆動する」の 1 文ずつで足りる。
- **直し方**: 一般の規則を 1〜2 文で残し、チップごとの事実と実測は target-scan-notes などの記録に移してリンクする。もう 1 つ、規範でないガイドが「（必須）」を見出しに書いている（host §2.5）。必須なのは core §5 なので、「core §5.1 / §5.2 が求めること」と書き換える。

#### G-4 ○ probe ガイドに古い記述が残っている（文書）

状態: 未対応（probe ガイド §3 の「仮置き」、§3.5 の「115200 固定」の見出し、状態の行の 2026-09-26 が残る）

- §3「COBS + CRC-16/CCITT-FALSE、**仮置き**」「V1 の endpoint に `Framing::kCobsCrc` を渡す」。core §3.1 で確定しているので「仮置き」は誤り。v0 の検討の文書（uart-reliability-model）を根拠にしている所もある。
- §3.5 の見出し「UART bridge の速さは 115200 固定」は、port_speed（core §3.5）を入れた今は「起動時の速さは 115200」が正しい。
- 状態の行が、どちらのガイドも「2026-09-26 に合わせて更新」のまま（その後 10-01 / 10-02 の変更が入っている）。

#### G-5 ○ probe ガイドに、識別子と宣言の選び方が無い（文書）

状態: 未対応（probe ガイドに unit_id、index、宣言、窓、保存の原子性の作り方が無い）

- unit_id の作り方（チップの固有の番号を小文字の 16 進にする、保存した乱数を使う、の利点と欠点）と、版を越えて変えないこと（★5）。transport の index を変えないこと（PC-8）。model / firmware / chip の文字列。role_channels と channel_group の選び方。max_frame / window / max_inflight の決め方（今の §2 は ESP32 の例だけ）。save の原子性（前の保存か新しい保存のどちらかが読める）を NVS / flash でどう作るか。

#### G-6 ○ 2 つのガイドに英語版が無い（文書）。O-10 に含める。

状態: 未対応（両ガイドの英語版が無い）

#### G-7 △ 節の番号が不揃い（文書）

状態: 未対応（ガイドは別の作業の担当。振り直しの注意を渡した）

1、1.5、1.6、1.7、2、2.1、2.5、3、… の並びを整える。外から節番号で参照されているので、変えるなら一度にまとめて変える。

---

#### C. oep-spec 全体の OSS / 共通仕様としての準備

#### O-1 ★ 決まっていない VID:PID と申請の状態がリポジトリにある（文書）

状態: 決着（2026-10-02、ユーザーの判断）: 申請の資料を木から外し、案内も消す。VID:PID は取得してから書く。7ff4dce（履歴は書き換えない）

**決着: 木から外し、案内も消す（2026-10-02、ユーザー）。** 7ff4dce: ディレクトリ、review-guide §3 の行、memo（en / ja）の割当元の調査と申請の手順と参照を消した。
- **場所**:
  - `docs/pid-codes-application/`（申請の状態と番号を書いた資料一式）。
  - `docs/review-guide.ja.md` / `.md` の §3 の行「`docs/pid-codes-application/` … pid.codes への申請の資料」。
  - `docs/v1-freeze-review-2026-10-01.ja.md` L127 のプロジェクトの VID:PID の番号。
  - `docs/v1-zero-base-proposal.ja.md` L127、L275、L441 のプロジェクトの VID:PID の番号。
  - `memo.ja.md` / `memo.md` の pid.codes の調査と「共通PIDを申請…」の項（L47、L163）。
- **問題**: 番号と申請の状態は、取得が決まるまで書かない、というユーザーの決まりに反する。第三者には「この番号を使ってよい」と読める。これらはすでに origin/main にある。
- **直し方**: ディレクトリを木から外す（必要なら手元か非公開の場所に移す）。記録の中の番号は「プロジェクトの VID:PID」に置き換える。review-guide の行を消す。memo の該当部分も消すか一般化する。履歴を書き換えるかはユーザーが決める。
  - 同じ仕組みの他の箇所: core §3.3、registry `[usb]` のコメント、usb-identity、ガイド §1.7 / §3.8、README、PID-USE.md は「取得したら registry に載せる / 切り替える」という書き方で、番号も状態も無い。今の決まりの中にある。△ として、「切り替える予定」をやめて core と同じ言い方（「registry に載ったものを使う」）に揃えるとよい。
- **種類**: 文書（判断: 履歴）。

#### O-2 ★ 記録の文書が、今の規範と逆の USB の識別を「決定」として書いている（文書）

状態: 対応済み（769ffeb、v1-freeze-decisions（ja / en）などの置き換えた決定に core §3.3 への注）

**対応済み**（769ffeb）: v1-freeze-decisions（ja / en）、v1-zero-base-review ★11 と表の 11、v1-zero-base-proposal 3.4(d) / 表の 7 / 12、v1-freeze-review の 16 の案に、置き換えの注と core §3.3 へのリンクを付けた（本文は書き換えていない）。
- **場所**: v1-freeze-decisions（.ja / .md）の冒頭「3(b)（iProduct `OEP`）は恒久の規範になり」、§3(b)「iInterface が `OEP` で始まる」、§3(d)「host の発見は iProduct の `OEP` で見るので」。v1-zero-base-review ★11「iProduct `OEP` 接頭は恒久（core §3.3）」。
- **問題**: core §3.3 は今「自動で見分けるのはプロジェクトの VID:PID だけ、iProduct は見分けに使わない」。review-guide は freeze-decisions を **2 番目に読む文書**としていて、レビューをする人はまずこの食い違いに当たる。
- **直し方**: 該当の行に「（2026-10-02 に置き換え: core §3.3。iProduct と interface の文字列は見分けに使わない。暫定の手がかりは host ガイド §1.7）」と注を付ける（ja / en）。あわせて、置き換えた決定に印を付ける決まりを作る（O-11）。
- **種類**: 文書。

#### O-3 ★ 入口の README.md（英語）が古く、中で食い違っている（文書）

状態: 対応済み（6bcf7e3、README（en / ja）を書き直し、project-concept.md を今の文に）

**対応済み**（6bcf7e3）: README（en / ja）を書き直し、project-concept.md を今の合意の文に揃えた。
- **問題**: 次のように書いてある。「Only the project name is settled at this time. Everything … is an exploratory draft」「The other English documents below predate the v1 candidate」「Language rules … remain undecided」「governance … undecided」。これは v1 の候補と凍結の範囲（§0）と食い違う。`docs/project-concept.md` も「Exploratory upstream draft. Only the project name is settled」のまま（review-guide も「英語版は古い」と言っている）。英語の README は文書の一覧をほとんど持たない。
- **直し方**: README（en / ja）を書き直す。中身は、OEP とは何か（3 行）、今の状態（v1 の候補、凍結の約束へのリンク）、**文書の地図を状態ごとに**（規範 / 実務 / 記録 / 経緯）、実装の始め方（spec → registry → generated → fake → tests）、貢献のしかた（O-4）、license（O-6）。project-concept.md は今の .ja.md に合わせて訳し直すか、冒頭に「古い」と書く。
- **種類**: 文書。

#### O-4 ★ 貢献と変更の手順が無い（判断 + 文書）

状態: 決着（2026-10-02、ユーザーの判断）: spec のリポジトリが唯一の正で、変更は直接の編集か pull request。CONTRIBUTING（en / ja、6bcf7e3）

**決着: spec のリポジトリが唯一の正で、変更はそこへの直接の編集か pull request（2026-10-02、ユーザー）。** CONTRIBUTING（en / ja、6bcf7e3）。
- **問題**: CONTRIBUTING も、issue のひな形も、誰が決めるか（governance）も無い。第三者が次のことをどうすればよいか分からない。(1) 誤りを報告する。(2) 新しい `oep.` インターフェースや、標準インターフェースへの任意の TLV を提案する。(3) enum の値（mechanism、transport kind、target_id_scheme など）を取る。(4) 凍結の後の errata。
- **直し方**: CONTRIBUTING（ja / en）に手順を書く。issue → 案の文書 → peer（ch32rv / WireSkein / bench と外部）のレビュー → registry の PR（`oepgen1.py --check`、tests/registry_v1）→ fake → 実装。誰が決めるか、凍結の後の変更は revision の規則（core §2.7）と CHANGELOG に記録すること、「規範の文は実装できる文だけ」（spec-writing rules）もここに置く。
- **種類**: 判断（誰が決めるか）+ 文書。

#### O-5 ○ 第三者のための番号の空間が、op 以外に無い（規則）

状態: 対応済み（d48ca6d、core §2.5「Experimental values」u8 の enum の 0xF0〜0xFE）

- **問題**: op には実験用の 0xF0〜0xFF があるが、u8 の enum（console の mechanism、transport kind、target_id_scheme、probe.config の項目の tag、unavailable の cause / holder_kind、capture の trigger type など）には実験用の範囲も、取り方も無い。新しいコンソールの framing や経路を試作する人は、衝突しない番号を使えない。core §13-7 で標準インターフェースに独自の tag を混ぜられないため、独自の framing は独自のインターフェースにするしかない。そうすると bind（slot の mechanism）に乗れない。逆 DNS の名前に、登録の要らないことは README（probe-arduino）にしか書かれていない。
- **直し方**: core §2.5 に「u8 の enum は、定義が別に決めない限り 0xF0〜0xFE を実験用（出荷する probe は使わない）とする」を足し、registry の各 enum に `reserved` として入れる。標準の値の取り方は O-4 の手順に置く。必要なら「知られている拡張の一覧」（登録ではなく、見つけるための表）を README に置く。
- **種類**: 規則。

#### O-6 ○ 仕様の文の license、特許、名前の使い方（判断）

状態: 決着（2026-10-02、ユーザーの判断）: 仕様は MIT のまま（README、6bcf7e3）。特許の非主張と「OEP」を名乗る条件はまだ決めていない

**決着: 仕様は MIT のまま（2026-10-02、ユーザー）。** 特許と名前の使い方は未決。
- **問題**: LICENSE は MIT（文の対象は "Software"）で、README は「リポジトリの中身は MIT」と書く。仕様の文にも当たるとは読めるが、仕様の文書でよく使う形ではない。特許の扱い（実装者が特許の主張を受けない約束）が無い。project-concept の「非互換な派生を OEP として識別しない」原則があるのに、「OEP 準拠」を名乗る条件（O-8）と名前の扱いの決まりが無い（PID-USE.md は PID の条件だけ）。
- **直し方**: ユーザーが決める。候補は、文書は CC-BY-4.0、コード（tools、generated）は MIT とし、README に明記する。特許については、貢献者の非主張の 1 段落（または既存の仕様の特許方針を採る）を入れる。名前については「OEP の名前を、仕様に従わない実装に使わない。準拠の確かめ方は O-8」を置く。
- **種類**: 判断。

#### O-7 ○ 版と凍結の約束が、決定の記録の中にしかない。spec のタグも無い（文書 + 判断）

状態: 未対応（凍結の範囲は v1-freeze-decisions §0 の中のまま。タグ、CHANGELOG、独立した版の方針の文書が無い）

- **問題**: 何を止め何を止めないかは v1-freeze-decisions §0 によく書けている。ただしそれは、日付つきの 13 項目の決定の記録（一部は置き換え済み、O-2）の中にある。spec には git のタグも release も無く（「commit で指す」）、凍結の後に revision を変えずに足したもの（任意の TLV、op、出来事）を実装者が見分ける版の印も無い。
- **直し方**: §0 を独立した「安定性と版の方針」（ja / en）に移し、README からリンクする。レビューの版にタグ（例 `v1.0.0-rc.1`）を付け、凍結で `v1.0.0` を付ける。凍結の後の追加は CHANGELOG に日付と commit で残す。registry に版の文字列（`[registry] edition`）を置くかは peer と決める（registry の変更）。
- **種類**: 文書（タグはユーザーの判断。registry に足すなら規則）。

#### O-8 ★ 適合の確かめ方が無い。core が「適合試験を持つ」と言っているのに、それが存在しない（文書 + 道具）

状態: 未対応（一部だけ: tests/vectors（e21a9a2）と core §0 規則 4（4e62116）、README に fake と `oep dump`（6bcf7e3）。第三者の probe を確かめる点検の手順と道具がまだ無い）

- **場所**: core §0 の線引きの規則 4「project が適合試験を持つことだけである」。
- **事実**:
  - `oep-client-python/tests/hw` は参照の firmware と参照のボード（`OEP_HW_BOARDS`、焼くところから）の試験で、第三者の probe には当てられない。
  - fake（`fake.py`、`fake_serve`）は「動く spec」と呼ばれているが、client のリポジトリの中にあり、host の確かめ方としてはどこにも書かれていない。
  - 試験ベクトル（COBS + CRC のフレーム、TLV の長い形、正規形の hash、断り方の順の例）が spec に無い。core の CRC の "123456789" の確かめ値だけがある。
- **直し方**（レビューの前の最小限）:
  1. oep-spec に `tests/vectors/`（機械で読める形。confirm / list / describe の要求と応答の 16 進、COBS の境界、TLV の長い形、probe.config の正規形と hash、各 op の malformed / unsupported の例）を置く。
  2. README とガイドに「host の確かめ方: fake_serve に当てる」「probe の確かめ方: client の読むだけの点検（confirm / list / describe / ページング / 送り直し / 断り方の順）を任意の口に当てる」を書く（道具が無ければ作る。oep-client-python に `oep check <address>` など）。
  3. それが揃うまでは、core §0 の規則 4 を「project が registry を持ち、適合の試験を用意する」と、今の状態に合わせて書き換える。
- **種類**: 文書 + 道具（core の文言の変更は peer に見せる）。

#### O-9 ★ 規範の dmseq に英語版が無く、文に製品名・逸話・日付が入っている（文書）

状態: 対応済み（cdd26b4、67863b1、target-console-dmseq.md が英語の規範、理由と実測は target-console-dmseq-notes へ）

- **場所**: `docs/target-console-dmseq.ja.md`（規範。target の firmware を書く人が読む）。L6「ch32rv 側のレビュー 2 回を経て合意済み（2026-09-24）」、L10（ArduinoCore-CH32、minichlink）、L15、L19、L39（WCH-LinkE の 0.4 ms）、L64、L74、L102-103、L145-149（V006 / X035、日付、wch-protocols）。v0 の owner / id への言及もある。
- **問題**: 規範の文書で、ただ 1 つ英語版が無い（README もそう明記している）。spec の書き方の決まり（規範の文にチップ名・逸話・互換の注を置かない）にも反している。ほかの規範の文書は、例としての名前（chip の `esp32p4 v1.3` など）を除けば満たしている。
- **直し方**: 理由と実測を記録の文書（`experiments/dm-console-seq` か新しい記録）に移し、規範の文だけを残してから英語版を作る。どの文が規範かは peer（ch32rv）に差分で見せる。
- **種類**: 文書（差分は peer が見る）。

#### O-10 ○ 英語で読めるもの（文書 + 判断）

状態: 決着（2026-10-02、ユーザーの判断）: 英語が正、日本語は訳。規範の文書はすべて英語版を持つ。README、review-guide、core §0（78137fb、6bcf7e3）。ガイドの英語版は G-6

**決着: 英語が正、日本語は訳。規範の文書はすべて英語版を持ち、英語が完全であること（2026-10-02、ユーザー）。**
- **規範**: dmseq（O-9）以外はある。
- **初めての人に要るのに英語が無いもの**: host / probe 開発ガイド、usb-identity（README.md がリンクしているのは .ja.md）、release-testing、用語集（O-13）。project-concept.md は古い（O-3）。記録と経緯は日本語のままでよい。
- **英語版の冒頭**: 今は「Japanese」へのリンクだけで、「食い違えば日本語が正しい」とは書いていない（README にだけある）。各英語版の状態の行に 1 文で書く。
- **判断**: 凍結の後も「日本語が正」を続けるか、英語を同格にするかを決めて README に書く。今の README は「Whether this becomes a formal project rule remains undecided」のまま。

#### O-11 ○ 記録と規範が同じ所に並び、状態の書き方も揃っていない（文書）

状態: 対応済み（6bcf7e3、すべての文書の冒頭を 規範 / ガイド / 記録 に。ディレクトリは分けず、地図は README と review-guide §5.1）

**対応済み**（6bcf7e3）: `docs/` のすべての文書の冒頭を「規範 / ガイド / 記録」の 3 つの形にした。ディレクトリは分けていない（地図は README と review-guide §5.1）。
- **事実**: `docs/` に 80 の文書が平らに並ぶ。状態の行が無いもの: console-stream、hardware-source-review-2026-09-26、link-measurements、review-answer-portability-2026-09-26、v1-open-issues-research-2026-09-26、v1-operation-test-audit-2026-09-26（review-guide は太字の状態が無い）。状態の言葉も揃っていない。
  - 「決定」が release-testing（実務）と v1-freeze-decisions（記録）の両方に付いている。
  - v1-zero-base-proposal は「採用・規範に反映済み」で、規範と取られうる。
  - 「合意済みの概念モデル」「検討中の要求案」もある。
  - README.ja には「（未対応）」のレビューの一覧がある。
  - `memo.ja.md`（作業のメモ、ユーザーのメモの控え）がリポジトリの根にある。
- **直し方**:
  - (a) 状態の言葉を 5 つに決める（**規範 / 実務 / 記録 / 経緯 / 置き換え済み**）。全文書の 1 行目に、同じ形で書く。
  - (b) ディレクトリを分ける（`docs/spec/`、`docs/guide/`、`docs/records/`、`docs/history/`）。動かすとリンクが切れるので、リンクの検査と一緒に行う。分けない場合は、README の地図（en / ja）を状態ごとにする。
  - (c) memo は history に移すか、外す。
- **種類**: 文書。

#### O-12 ○ 安全とセキュリティの考え方が 1 か所に無い（文書）

状態: 未対応（core に「安全とセキュリティ（参考）」の節が無い）

- **事実**: 断片はあるが、散らばっている。core §3.1（TCP は信頼できる接続でだけ、認証なし）、§6.4（force は認証ではない）、§3.3（知らない device を開く時は confirm だけ）、probe-config の disable、host ガイド §9.2（ピンを探す時の安全）、§4.5（読み出しの保護）。
- **直し方**: core の末尾に「安全とセキュリティ（参考）」の節（ja / en）を置き、次をまとめる。
  - 信頼のモデル（同じ PC のプロセスと USB は信頼する。認証も暗号も無い）。
  - TCP の扱い。どの local プロセスでもロックを取れること（force）。
  - 知らない device を開くこと。
  - 線の駆動による物理的な害（起動時の出力、電源とリセットの線、PC-11）。
  - target の読み出しの保護は host の責任であること。
  - firmware の更新は OEP の外で、署名を持たないこと。
  - 受ける側の上限（65535 byte、壊れた長さ）。
  - unit_id がチップの固有の番号を外に出すこと（プライバシー）。

  規範の文は増やさない。増やすなら peer に送る。
- **種類**: 文書。

#### O-13 ○ 用語集が無い。日本語の造語と英語の対応も無い（文書）

状態: 未対応（用語集が無い）

- **事実**: core §1 に 12 語、review-guide §9 に別の 9 語。規範には独自の言葉が多い（シリアルの口、錠、線、出来事、断り、空きの状態、握手、口の位置）。英語版はそれぞれ訳語を選んでいるが、対応の表が無い。slot / bind / label / idle / unit_id / boot_id / corr / critical / outcome / stream / mark が 1 か所で引けない。
- **直し方**: `docs/glossary`（ja / en の 2 列、定義の節へのリンク付き）を 1 つ作り、core §1 からリンクする。
- **種類**: 文書。

#### O-14 ○ 要求の強さの言葉を定義していない（文言。peer に見せる）

状態: 対応済み（4e62116、core §1.1 Normative words、RFC 2119 / 8174）

- **問題**: 規範は「〜する / 〜しない / 〜してよい」で書き、「（参考）」「目安」「例」は規範ではない、と review-guide §10 が言っている。core 自身はそれを定めていない。英語版は小文字の must / may で、RFC 2119 の言葉と同じかどうかが分からない。
- **直し方**: core §0 か §1 に、言葉の表（する = MUST、しない = MUST NOT、してよい = MAY、することを勧める = SHOULD、（参考）と例 = 規範ではない）を置く。英語版で RFC 2119 / 8174 を使うかを決める。
- **種類**: 文言（意味の取り方が変わりうるので peer に見せる）。

#### O-15 ○ probe が最低限持つものを、core が 1 か所で言っていない（規則の明示）

状態: 対応済み（4e62116、core §1.2 Conformance、§12 の Required の列）

- **問題**: core §12 の op の表は「任意」を port_speed にしか書いていない。plan_apply / plan_release（ピンを持たない probe）、subscribe（通知を持たない probe）、link_source / link_sink が必須かどうかは文から決まらない。describe の必須の tag は §7.5 に散っている。
- **直し方**: §12 の表に「必須 / 任意（条件）」の列を置く（例: plan_* は、plan の role を持つインターフェースがあれば必須。subscribe は、出来事か通知のデータを出す probe で必須。link_* は必須）。任意のものに当たったときの断り方（unsupported）も書く。G-1 の probe のチェックリストはこの表を写す。
- **種類**: 規則（今の実装の振る舞いを書くだけでも、peer に確かめる）。

---

#### D. 実装のリポジトリの README（spec をどう見せているか、だけ）

#### R-1 ○ 3 つの README の、spec への入口（文書）

状態: 未対応（oep-client-python の README はまだ review-guide.ja.md と oep-core.ja.md を指す。spec の外のリポジトリ）

- **oep-probe-arduino README.md**:
  - spec の入口は `review-guide.ja.md`（日本語、レビューのための地図）と `oep-core.ja.md`。英語版があるのに「Japanese first; English follows once it settles」と書いている（古い）。
  - 冒頭の「**The protocol is fixed**」は、同じ README の「until the v1 freeze every release may break」と食い違って読める。意図は「形は決まっていて、能力は開いている」。
- **oep-client-python README.md**: 「start with oep-spec's docs/review-guide.ja.md」と、日本語の規範を指している。
- **oep-client-js README.md**: spec の地図へのリンクが無い。port_speed の手順の長い段落が冒頭近くにあり、初めての人には重い。
- **直し方**: 3 つとも「Specification: oep-spec の README（英語）から」とする。規範は英語版（`oep-core.md` など）へ、日本語版は「原文」としてリンクする。凍結前であることの書き方を揃える。

#### R-2 △ 良い所を spec 側から使う（文書）

状態: 対応済み（5d02a6f、README（en / ja）の参照の実装から oep-probe-arduino の getting-started と writing-a-probe へ。ガイドからのリンクはガイドの担当に渡した）

oep-probe-arduino の `docs/guide/getting-started.md` と `writing-a-probe.md`、client の fake は、初めての人に要る道そのもの。oep-spec の README とガイドからリンクする（G-1、O-8）。

---

#### 要約の表

| id | 場所 | 重さ | 何が | 直し方（短く） | 種類 |
|---|---|:---:|---|---|---|
| PC-1 | probe-config §1.3 | ○ | firmware の固定のリセットの線を名前で探せない | 探し方の 3 段目に describe 0x46（または fn 0 の線の宣言の tag） | 規則 |
| PC-2 | probe-config §1.3 | ○ | 表に無い名前の意味と、名前を足す道が無い | 表に無い名前は意味なし、registry `[line_names]`、独自は `x-` | 規則 |
| PC-3 | probe-config §1 idle、§2 表 | ○ | pull の無い channel の mode 1 / 2、mode ≥ 5 の断り方 | unsupported / malformed を明記し表に | 規則の明示 |
| PC-4 | probe-config §1 disable | ○ | 「宣言していない channel」の定義が無い、参照先が無い | channels（0x43）未満と定義、label / idle / disable に | 規則の明示 |
| PC-5 | probe-config §1 label | ○ | text の長さと文字の決まりが無い | 1〜32 byte の UTF-8、ほかは malformed | 規則 |
| PC-6 | probe-config §2 get | ○ | 応答の「…」が未定義 | 項目は payload の終わりまで、0x7E は予約で置かない | 文言 |
| PC-7 | probe-config §2 hash | △ | 正規形の tag の bit とキーの比べ方 | critical の bit 0、数として比較、例を vectors に | 文言 |
| PC-8 | probe-config §1.2 / §2 / §3.3 | ○ | bind の port は読み替えの外、理由 3 が全部か一部か | port に kind を添える か index の不変を core に、理由 3 の範囲を決める | 規則 |
| PC-9 | probe-config §3.3 | △ | 2 つの first、ページ間の storage | 足し方と値の扱いを 1 文 | 文言 |
| PC-10 | probe-config §3.1 | △ | boot_reset の保持が 20 ms 固定 | 伸ばす道をガイドに | 文書 |
| PC-11 | probe-config 全体 | ○ | 設定が線を駆動することの安全の注意が無い | （参考）安全の小節、O-12 と合わせる | 文書 |
| G-1 | 両ガイド | ○ | 最小の host / probe までの道が無い | §0 に手順とバイト列、probe のチェックリスト、arduino のガイドへのリンク | 文書 |
| G-2 | host ガイド | ○ | 断りごとの動き、revision / TLV、通知、probe.config の手順、fake が無い | 節を足す | 文書 |
| G-3 | 両ガイド | ○ | チップ固有と実測が一般の規則に混ざる、「（必須）」の見出し | 記録へ移し規則を 1〜2 文に、core を引く | 文書 |
| G-4 | probe ガイド §3 / §3.5、状態の行 | ○ | 「仮置き」、v0 の名前、115200 固定の見出し、古い日付 | 今の規範に合わせる | 文書 |
| G-5 | probe ガイド | ○ | unit_id、index、宣言、窓、保存の原子性の作り方が無い | 節を足す | 文書 |
| G-6 | 両ガイド | ○ | 英語版が無い | 訳す（O-10） | 文書 |
| G-7 | 両ガイド | △ | 節番号が不揃い | まとめて振り直す | 文書 |
| O-1 | pid-codes-application/、review-guide、freeze-review、zero-base-proposal、memo | ★ | 決まっていない番号と申請の状態 | 木から外す、番号を「プロジェクトの VID:PID」に、履歴はユーザーが決める | 文書 / 判断 |
| O-2 | v1-freeze-decisions（ja / en）、zero-base-review ★11 | ★ | iProduct を恒久の規範とする記述が core と逆 | 置き換えの注、置き換えの印の決まり | 文書 |
| O-3 | README.md / .ja.md、project-concept.md | ★ | 入口が古く食い違う | 書き直し（状態、地図、始め方、貢献、license） | 文書 |
| O-4 | リポジトリ全体 | ★ | 貢献・変更・番号の取り方・errata の手順が無い | CONTRIBUTING（ja / en）、誰が決めるか | 判断 + 文書 |
| O-5 | core §2.5、registry の enum | ○ | op 以外に実験用の範囲が無い | u8 の enum に 0xF0〜0xFE の実験用、取り方は O-4 | 規則 |
| O-6 | LICENSE、README | ○ | 仕様の文の license、特許、名前の使い方 | CC-BY / MIT の分け、特許の非主張、名乗る条件 | 判断 |
| O-7 | v1-freeze-decisions §0、タグ | ○ | 版の約束が記録の中、タグと CHANGELOG が無い | 方針を独立の文書に、rc のタグ、CHANGELOG、（registry の edition は peer と） | 文書 / 判断 |
| O-8 | core §0 規則 4、tests | ★ | 適合試験が無いのに「持つ」と言う、試験ベクトルが無い | tests/vectors、fake と点検の道具を案内、それまで文言を今に合わせる | 文書 + 道具 |
| O-9 | target-console-dmseq | ★ | 規範で唯一英語が無い、製品名・逸話・日付 | 理由を記録へ、規範だけを残して訳す、peer が差分を見る | 文書 |
| O-10 | ガイド、usb-identity、release-testing、英語版の冒頭 | ○ | 初めての人に要る英語が無い、言葉の正の決め | 訳す、冒頭に 1 文、方針を決める | 文書 / 判断 |
| O-11 | docs/ 全体、memo | ○ | 状態の行が無い・揃わない、平らな配置 | 状態の言葉を 5 つに、ディレクトリか地図、memo を移す | 文書 |
| O-12 | core（新しい節） | ○ | 安全とセキュリティが散らばる | 「安全とセキュリティ（参考）」の節 | 文書 |
| O-13 | core §1、review-guide §9 | ○ | 用語集と ja ↔ en の対応が無い | glossary（ja / en） | 文書 |
| O-14 | core §0 / §1 | ○ | 要求の強さの言葉を定義していない | 言葉の表、RFC 2119 を使うかの決め | 文言（peer） |
| O-15 | core §12 | ○ | 必須 / 任意の op が 1 か所で分からない | 表に必須 / 任意（条件）の列 | 規則の明示 |
| R-1 | 3 つの実装の README | ○ | 入口が日本語のレビューの地図、古い文、食い違う文 | oep-spec の README（英語）へ、規範の英語版へ | 文書 |
| R-2 | oep-spec から arduino のガイドと fake へ | △ | 良い入口がつながっていない | リンクする | 文書 |

**第三者のレビューの前に（★）**: O-1、O-2、O-3、O-4、O-8、O-9。どれも規則を変えない（O-4 は誰が決めるかをユーザーが決める。O-8 の core の文言と O-9 の差分は peer に見せる）。
**peer に送る規則**: PC-1、PC-2、PC-3、PC-4、PC-5、PC-8、O-5、O-15（それに O-14 の言葉の表）。まとめて 1 本の案にできる。
