# 外部仕様レビュー（2026-10-07 再確認）への回答

状態: **記録**（規範ではない）。[外部仕様レビュー](external-spec-review-2026-10-06.ja.md)（3bca24c の再確認、6c22f12）の指摘ごとの判断と、
それを入れた commit。判断の基準: 仕様は簡単で小さく伸ばせること。規則は、それが無いと独立した host と probe がつながらないか、target や
データを黙って害するときだけ規範に残す。ぶつかるときは守るものを決め、それだけを守る 1 つの簡単な規則にする。規則は足すより消す。
日本語の作業の文だけを直した（英語版は凍結のときに作り直す）。

| 指摘 | 判断 | 理由 | commit |
|---|---|---|---|
| 3.1 分けてよい転送と「1 回の書き込み」の矛盾 | 採る | 書き込みの回数は線に残らず確かめられない。線で見える規則 1 つにした: フレームは書き込み、転送、report、TCP の segment にどう分けても、まとめてもよく、受ける側は区切りに頼らない。TCP 以外では送る側（host も probe も）はフレームの途中で `probe_frame_gap_ms` 止めない。vendor bulk の文と HID の規則 2 はこれに含まれるので消した | af3d52b |
| 3.2 max_length と経路ごとの max_frame | 採る | describe は経路によらないので、宣言はどの経路でも使えなければならない。describe の TLV と max_length は、どの経路の max_frame（いちばん小さいもの）にも収まる。debug の read_block / write_block の文も同じに直した | 4f6d464 |
| 3.3 ブローカーと restart | 変えて採る | 隠す（list を書き換える）のも端から端の約束を定めるのも規則が増える。今の規則（probe への経路が無くなればブローカーは終わり、client の接続を閉じる）で振る舞いは決まっているので、restart_max_ms が中継のブローカーの client に掛からないことだけを 1 文で書いた | af3d52b |
| 3.4 fn 0 と固定の形の決まり方 | 採る | 文言の直し。fn 0 の固定の形はプロトコルの revision で決まる | 4f6d464 |
| 3.5 channel の数と番号の範囲 | 採る（短くして） | channels の無いときの意味と番号の範囲が無いと、probe.config の範囲の確かめが読み分かれる。channel を持つ probe は channels を付け、無ければ 0 個、番号は 0〜channels − 1。範囲の外の要求は今の規則（宣言しない値は unsupported）で断れるので、要求、応答、出来事ごとの規則は足さない | 4f6d464 |
| 4.1 縮小の評価 | — | 指摘ではない | — |
| 4.2 clock を任意にするか | 採らない | clock は数行で、時刻を返すインターフェースはどれもこの時計に頼る。任意にすると「時刻を返すなら clock を持つ」という条件の規則と host の分岐が増え、消える規則は無い。時計を持たない probe の例も無い | — |
| 4.3 channel の規則を条件つきに | 採る | §1.2 は channels と §8 を channel を持つ probe にだけ求める | 4f6d464 |
| 5 仕様書だけからの実装 / 英語版 | 凍結のときに | 英語版は凍結のときに日本語から作り直す（今は触らない） | — |
| 6 拡張性 | — | 同意。変更なし | — |
| 7 / 7.1 / 7.2 ESP32 の TCP probe で確かめる | 変えて採る | 仕様の変更ではない。参照の probe の TCP の実装を今進めている。確かめる項目をリリース前の結合試験の 10 番に置いた | 249f6ef |
| 7.3 複数の client と状態の持ち主 | 採る（1 か所） | 接続ごとのもの（max_frame、window、max_inflight、revision、通知の送り先）は transports §1 にもうある。欠けていたのは接続が閉じたときで、そこでセッションを終える実装は、Wi-Fi の切れ目で target の接続を黙って外す。経路が閉じてもセッション、ロック、購読、送り直しの表は残り、閉じた経路への応答と通知は捨てる、と transports §3 に書いた | af3d52b |
| 7.4 発見、port、安全 | 変えない | port と発見は仕様の外のまま（mDNS などは要るときに別に決める）。TCP は信頼できる接続かトンネルの中だけ、は transports §1 と security にもうある | — |
| 8 前の指摘の反映 | — | 確認だけ | — |
| 9 試験の不足 | 変えて採る | TCP の流れを分ける / まとめる試験は実装（偽の probe、参照の probe）の試験で、この repo の道具は自分の復号器を試すだけになる。共有の道具で確かめていないものとして適合の文書に並べた | 249f6ef |
| 10 必須 1〜5 | 上の 3.1〜3.5 のとおり | — | af3d52b、4f6d464 |
| 10 core をさらに小さく 1（clock） | 採らない | 4.2 と同じ | — |
| 10 core をさらに小さく 2（channel） | 採る | 4.3 と同じ | 4f6d464 |
| 10 実装による凍結の判定 1〜6 | 変えて採る | 実装と結合試験の仕事。リリース前の結合試験の 10 番に置いた。broker を通した restart は 3.3 の規則で決まる | 249f6ef |
| 10 リリース前 1（英語版） | 凍結のときに | 5 と同じ | — |
| 10 リリース前 2（節の番号の抜け） | 凍結のときに | 番号を今振り直すと、実装と peers が引く節の番号が動く。英語版を作り直すときにまとめて振る | — |
| 10 リリース前 3（features の通知の例） | 採る | 通知は ops の subscribe / unsubscribe で宣言するので、例から消した | 4f6d464 |
| 10 リリース前 4（断りの理由が 1 つに決まらない） | 採る | core §4.3 は意図してそう決めている。適合の文書に、ベクタは 1 つだけ当たる場合だけを持ち、試験はどれか 1 つを受けると書いた | 249f6ef |
| 10 リリース前 5（同じタグに含める） | もうそうなっている | 文書、registry、生成物、ベクタは同じ repo の同じ git のタグに入る（版と安定性 §6） | — |

## 実装が追う変更

- **transports §2**: 送る側の「1 回の書き込み」は無い。フレームはどう分けて書いてもよい。TCP 以外では、送る側（probe も）はフレームの途中で
  `probe_frame_gap_ms`（200 ms）止めない。受ける側は書き込み、転送、report、TCP の segment / recv の区切りに頼らない。
- **transports §3**: 経路（TCP の接続を含む）が閉じても、セッション、ロック、購読、送り直しの表は残す。閉じた経路への応答と通知は捨てる。
  同じ id の open が新しい接続で来たら、今までどおり lease を始め直し、通知の送り先をその接続に替える（core §6.2）。
- **core §7.3 / §7.4**: describe の各 TLV と max_length は、probe のどの経路の max_frame にも収まる値にする。
- **core §7.5 / §1.2**: channel を持つ probe は channels を必ず付ける。番号は 0〜channels − 1。
- **restart §2**: 中継のブローカーの client には restart_max_ms は掛からない（ブローカーは終わり、client はやり直す）。

## 再々確認（764b110）への回答

[外部仕様レビュー](external-spec-review-2026-10-06.ja.md) の 764b110（TCP の発見と Wi-Fi の設定を足したもの）の再々確認（2b17990）。
判断の基準は上と同じ。日本語の作業の文だけを直した。

| 指摘 | 判断 | 理由 | commit |
|---|---|---|---|
| 1 結論 | — | 指摘ではない | — |
| 3.1 いちばん長い wifi の set が max_frame 64 に収まらない | 採る | 収まらなければ、有効な項目を送れない probe が適合になる。分ける形（ssid と鍵を別の項目に）は原子性と書くだけの扱いを増やし、鍵を 32 byte の PSK にしても見出しと合わせて 64 を超え、WPA3 の passphrase も運べない。規則 1 つ: items に wifi を宣言する probe は、どの経路でも max_frame 112 以上（10 + 3 + 99）。registry の `wifi_min_max_frame`、112 byte のベクタ、和を確かめる試験。同じ仕組みのほかの所: slot のいちばん長い set は 10 + 3 + 51 = 64 でちょうど収まり、label（47）、open と owner、list（63）も収まる | 29902a6 |
| 3.2 mDNS / DNS-SD を全 TCP probe の必須に | 変えて採る | MUST は、無くても相互運用は崩れない（利用者の明示したアドレスでいつもつながる）ので規範に残す理由が無い。SHOULD は確かめられない半端な規則になる。残すのはやり方だけ: 広告するなら `_oep._tcp` を mDNS で、広告しない probe は明示したアドレスで使う。一般の host は、見つけられたい probe をどれも同じやり方で見つけられ、USB（プロジェクトの VID:PID なら自動、ほかは利用者が選ぶ）と同じ形になる。参照の probe は広告する。別の文書の profile は作らない（同じことを 1 文で言える） | 3db3cee |
| 3.3 RFC 6762 / 6763 が参照の一覧に無い | 採る | transports §7 に足し、使う部分（問い合わせと応答、名前の衝突と付け直し、広告し直し、instance の名前、PTR / SRV / TXT、TXT の key=value）を書いた。従うのは広告する probe と browse する host | b3d9c81 |
| 3.4 適合の host の一覧に「1 回の write」 | 採る | 消し忘れ。transports §2 の文に直した | 89b2844 |
| 4 前の指摘の反映 | — | 確認だけ。ESP32 の結果は実装と結合試験の仕事（下の 9） | — |
| 5 core の再評価 | — | 同意。変更なし | — |
| 6 拡張性（発見は framing と別にする） | 変えて採る | 3.2 のとおり、広告を probe の選ぶものにした。文書は分けない | 3db3cee |
| 7.1 TCP の framing と接続の試験 | もうある | リリース前の結合試験の 10 番 | — |
| 7.2 Wi-Fi の設定の試験 | 変えて採る | いちばん長い set を各経路で送るのを 11 番にした。passphrase の長さごとの試し、get が秘密を返さないこと、応答が先に来ることは参照の probe の試験とベクタの範囲。誤った資格情報からの戻り方は、設定がどの経路でも同じ操作で行えるので USB かシリアルの口からでき、規則は足さない | 29902a6 |
| 7.3 mDNS の試験 | 変えて採る | 広告する probe だけの 12 番（見つかる、SRV の port、TXT と describe の unit_id、つなぎ直しと再起動の後）。衝突の付け直しと IPv6 は RFC と mDNS の実装の範囲で、足さない。複数の IPv4 の接続から問い合わせるのは host ガイド §4.1 にある | 3db3cee |
| 8 機械検証（いちばん長い set、mDNS の packet、TCP の分割） | 一部採る | いちばん長い set のベクタは足した。mDNS の packet は RFC の形で OEP のベクタではなく、TCP の流れの分け方はこの repo の道具が自分を試すだけになる（前回の 9 と同じ） | 29902a6 |
| 9 必須 1〜3 | 上の 3.1、3.4、3.3 のとおり | — | 29902a6、89b2844、b3d9c81 |
| 9 core / transport を小さく 1〜3 | 変えて採る | 3.2 と同じ | 3db3cee |
| 9 凍結の判定の実装条件 1〜5 | 変えて採る | 実装と結合試験の仕事。リリース前の結合試験の 10〜12 番 | 29902a6、3db3cee |
| 9 リリース前 1〜3 | 凍結のときに / もうそうなっている | 前回の 10 リリース前と同じ | — |
| 10 最終評価 | — | 同意 | — |

### 実装が追う変更（この回）

- **probe.config §1.4**（probe）: items に wifi を宣言する probe は、どの経路の confirm でも max_frame を 112 以上で答える
  （`LIMITS.wifi_min_max_frame`）。いちばん長い set（32 byte の ssid、64 文字の鍵）を受けられること。
- **host（Python / JS）**: wifi の set は項目 1 つなら必ず送れる。112 より小さい max_frame の経路で wifi を宣言する probe は仕様に反する
  （host は項目を分けず、その経路では送らずに誤りとして見せる）。生成物の LIMITS に `wifi_min_max_frame` が増えた。
- **transports §3**: TCP の probe の広告は任意になった。広告するなら今までどおり `_oep._tcp`、TXT `unit_id`、SRV の port。host は
  browse と、利用者の明示したアドレスと port の両方を持つ（今までどおり）。参照の probe（ESP32）は広告を続ける。
- **transports §7**: 広告する probe と browse する host は RFC 6762 / 6763 に従う（衝突のときの名前の付け直し、アドレスが変わったときの広告し直し）。
- ch32rv: wifi を宣言しないなら変更なし。

## core 再確認（0991759）への回答

[外部仕様レビュー](external-spec-review-2026-10-06.ja.md) の 0991759 の core 再確認（d8b4d9e）。判断の基準は上と同じ。日本語の作業の文だけを直した。
どれも今の意図を 1〜2 文で固定するもので、byte の並びは変わらない。

| 指摘 | 判断 | 理由 | commit |
|---|---|---|---|
| 1 結論 | — | 指摘ではない | — |
| 3.1 describe の 1 TLV が収まる条件に応答の見出しと more を含める | 採る | 経路の max_frame は message 全体の上限（§4.4）なので、TLV だけを比べると応答が 6 byte 超えうる。core §7.3 を「応答の見出し 5 byte と more 1 byte を足しても収まる（値は最小の max_frame − 9 byte まで）」にした。適合の一覧と registry の describe の注も同じ。同じ仕組みのほかの所: confirm（64 byte）、list（見出し込みで 63）、max_length（要求と応答の全体、§7.4）、debug の read_block / write_block（見出し 5 / 10 を数える）、common の read、capture の read、link の source / sink（見出し込み）、probe.config の wifi（見出し 10 込みで 112）、release testing 9、host ガイドの sink はどれも見出しを含んでいて変更なし。probe.config の get は項目ごとの上限を言わないが、その答えの見出し（5 + more 1 + hash 4 = 10）は set の要求の見出しと同じなので、set で送れた項目はどれも get の 1 ページに収まる | cbdea59 |
| 3.2 ページングの終わりの count 0 を「要素 0 個」に | 採る | describe と get は count の欄を持たない。core §7.3 を「要素を 0 個、more 0（要素の数の欄を持つ応答では、その欄は 0）」にした。答えの形ごとの確かめ: describe は more 0 だけ（既存のベクタ "describe fn 0 from beyond the last"、getting-started も同じ）、probe.config の get は more 0 と hash で項目なし、state は n_slots / n_binds が 0（wifi の TLV はどのページにも載る）、debug の connections と console の streams は more 0 と count 0（既存のベクタ "rvswd connections: first beyond the count"）、capture の segments は空の成功、list は more を持たず total と count 0（§7.2）。適合の一覧と用語集も同じ | cbdea59 |
| 3.3 資源の番号の 0 を割り当てないと明記 | 採る | 意図は「1 から、65535 の次は 1」で、console は「1 から進める」、probe.config の slot_state の connection は 0 を「無し」に使う。core §9 に「1〜65535、起動後の最初は 1、0 は割り当てない（インターフェースは 0 を無しに使える）」、§2.5 の表にも範囲を足した。0 を「無し」に使う資源の欄は slot_state の connection だけで、これと合う。console §1（1 から）はもう合っていた。共通部品 §2 の connection の番号、適合の一覧、用語集に「1 から、0 は割り当てない」を足した | cbdea59 |
| 3.4 editorial（fn の期間、§4.4 の「両方」、boot_id の定義） | 採る | fn は「同じ boot_id の間」（§7.2 と同じ）、§4.4 は「これらの上限」、§6.5 は「起動ごとに変わるように選ぶ値」にした。用語集と適合の一覧の同じ言い回しも直した | cbdea59 |
| 3.5 DNS-SD の service name `oep` は未登録 | — | 確認だけ。0991759 で済み | 0991759 |
| 4〜8 反映の確認、core の再評価、互換実装、拡張性、TCP / ESP32 | — | 同意。ESP32 の結果は実装と結合試験の仕事（前回と同じ） | — |
| 9 機械検証（3 点の例を足す） | 足さない | byte の並びは変わらない。範囲を越えた describe と connections の終わりはもうベクタがあり、最初の資源の番号 1 はベクタの connection 1 と合う。55 byte の値の TLV は probe の宣言の作り方で、決まった要求と応答の組ではない | — |
| 10 残作業: 仕様 1〜4 | 3.1〜3.4 のとおり | — | cbdea59 |
| 10 残作業: 仕様 5、実装、リリース前 | もう済み / 実装と結合試験の仕事 / 凍結のときに | 前回と同じ | — |
| 11 最終評価 | — | 同意 | — |

### 実装が追う変更（この回）

- **core §7.3**（probe）: describe の各 TLV は、応答の見出し 5 byte と more 1 byte を足しても、probe のどの経路の max_frame にも収まる大きさにする（値は最小の
  max_frame − 9 byte まで。max_frame 64 なら 55 byte）。長い text（firmware、model、chip、label）を出す probe は確かめる。
- **core §7.3**（probe）: 範囲を越えた first には要素 0 個と more 0。describe は more 0 の 1 byte だけで、余分な count の 0 を付けない。get は more 0 と hash だけ。
- **core §9**（probe）: 資源の番号は起動後の最初が 1 で、0 を割り当てない（65535 の次は 1）。0 から振る実装は直す。host は 0 を「無し」として読んでよい（slot_state の connection）。
- 文の言い回しだけの 3.4 には、実装の変更は無い。
