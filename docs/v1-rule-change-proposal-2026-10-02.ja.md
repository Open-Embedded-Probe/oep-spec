# OEP v1 の規則の変更の提案（2026-10-02）

[English](v1-rule-change-proposal-2026-10-02.md)

状態: **peers への提案。peers の答えを入れて改めた（規範ではない）**。この文書は英語版が正で、日本語版はその訳。
読む人: ch32rv（Rust の host と broker）、WireSkein（キャプチャの記録）、bench（HIL の治具）。
元: oep-spec 78137fb（dmseq は cdd26b4）。第 2 版は、初版（ad9f8be）への 3 つの peers の答えを入れた: ch32rv（自分の a3bf2fa で確かめた）、WireSkein、bench（測った値つき）。各項目に状態の行を付け、最後の答えは下の「決定」にまとめた。出典: [3 回目のゼロベース点検](v1-zero-base-review-3-2026-10-02.ja.md)。規則の変更（規則）のうち ★ と ○ の指摘すべてと、その後に出た dmseq の問い。
C-11（USB の見分け）は決まった（変えない）ので含めない。別に入れた文言だけの修正（78137fb の C-12、C-13、C-14、C-35 など）は繰り返さない。

前提は点検と同じ。会ったことのない人が、見たことのない OS、USB スタック、MCU、debug の線、target で、本文だけを読んで probe と host を作る。各項目は、その利用者の場面から書き始める。

**答え方。** 項目ごとに、賛成、反対、条件つきの賛成のどれか。番号の付いた問い（Q1〜Q32）に答える。合意の後の作業の順は、これまでと同じく spec → fake → probe → client。

**「今」の欄の言葉。**
- *probe*: oep-probe-arduino の `src/`。
- *fake*: oep-client-python の `endpoint.py`（`fake_serial.py` / `fake_serve.py` と合わせて）。
- *Python*: oep-client-python の残り。
- *JS*: oep-client-js の `src/`。
- Rust の host は確かめていない（ch32rv: 振る舞いが違う所を教えてほしい）。
- 「未確認」は見ていないこと。

**壊す** = 今の文か今の参照のコードに従う実装や保存した設定が、線の上での振る舞いを変えなければならないこと。

## 決定

**項目の状態。**
- **合意**: 3 つの peers が受け入れた。bench は「全体に OK」、ch32rv は「下の印の付いた項目を除いて OK」と答えた。WireSkein は話題 3 と 8（C-06、P2-★4、P2-★6、P2-○9、P2-○10、P2-○11、P2-○15、Q14、Q17、Q18）に答え、その後ほかのすべての話題に「異議なし」と確かめた（2026-10-02）。
- **条件付き合意**: 項目に書いた条件つきで受け入れた。条件は、まだ満たすべきと項目に書いていない限り、案の文に入れてある。
- **未決**: 決まっていない。足りないものは項目に書いた。

未決の項目: なし。P2-★4 の cold attach の測定は、ユーザーの判断で閉じた（2026-10-06: cold start には probe の USB を手で抜く必要があり、今の段階ではそこまで細かくしない）。温まった状態のデータを 1000 ms の上限の根拠とする: 0.0.28 は失敗 4 %、p90 519 ms。直したビルドは 400 回中 0 回の失敗で約 138 / 223 ms、1000 ms を超えた裾はリンクの時間だった。debug §3.1 / §3.2 の RVSWD と SWIO のフレーム（7392817。参照の probe から書いた規則の追加、上の項目には無い）: ch32rv が 2026-10-02 に見た。指摘は反映済み（休んだ後の同期の取り直しを参考に、85 区切りの状態の問い合わせを注記、SWIO の low の範囲を 240〜310 / 840〜1060 ns に広げた、swio の swclk ≠ 0xFFFF は attach と同じく scan でも unsupported）。

**最後の答え。**

| Q | 項目 | 答え |
|---|---|---|
| Q1 | C-01 | そうする: registry は `role_assignment = 0x10` と書き、生成する定数も変わる |
| Q2 | C-02 | そうする: 使っていない enum の値と要求の予約のビットはすべて unsupported。malformed は並べた値だけ |
| Q3 | C-03 | そうする: 要求の TLV は伸ばさず、新しい欄は新しい tag |
| Q4 | C-04 | そうする: 多くて 16 個、「もっと」は 16 個目の 0x00 |
| Q5 | C-06 | そうする: 式は下限。scan と attach の上限は引数の時間に数える（P2-★4） |
| Q6 | P2-★4 | 要求ごとの 200 ms と実時間の 1000 ms を採る。**attach の上限は 500 ms でなく 1000 ms**（bench の測定）。attach の応答に任意の TLV `search_retries`。「status line ⇒ connection が無くなった」に頼る host は無い。cold attach の測定はユーザーの判断でやめた（2026-10-06）。温まった状態のデータを根拠とする |
| Q7 | C-07 | 間（gap）まで捨てる |
| Q8 | C-09 | そうする: どの probe も 115200 |
| Q9 | C-05 | confirm の TLV。TCP の端点は listen している socket の index を言う。session の op に自分で答える中継の broker は 0xFF を言う（ch32rv が確かめた） |
| Q10 | C-15 | そうする: 経路ごと。TCP では接続ごと（C-05） |
| Q11 | P2-★1 | そうする |
| Q12 | P2-★2 | 選択肢の無い規則にする。測った: 1 つの probe はすでに満たし、もう 1 つは CS が high の間 MISO を low に駆動していて、直している |
| Q13 | P2-★3 | プルアップを宣言する（features bit2 + pullup_ohms）。禁じない |
| Q14 | P2-○13 | 規則にする |
| Q15 | P2-★7 | そうする: `n × (role, channel)` の形。足した: ピンの組を宣言しない線は scan を持たなくてよい（ch32rv が確かめた）。2026-10-06 に置き換えた: scan はどの線でも必須（debug §0。ピンの無い線の count = 0 はその 1 つの組を試す） |
| Q16 | P2-○4 | halt が時間切れのとき haltreq を下ろす |
| Q17 | P2-★6 | そうする: 0 = 止まる、1 = 答える |
| Q18 | P2-○8 | mode、rate、trigger、pretrigger、frontend は critical で送る。samples と segments は送らない: probe は samples を上限に丸め、応答の値を正とする。rate の critical は「範囲の中ならいちばん近い作れる値、範囲の外は unsupported」 |
| Q19 | PC-1 | firmware の label を (c) にする |
| Q20 | PC-3 | よい |
| Q21 | PC-5 | 足りる: 32 byte |
| Q22 | PC-8 | index の不変 |
| Q23 | C-10 | 現在形の約束を新しい §1.1 と一緒に残す |
| Q24 | C-10 | する: link_source / link_sink は必須 |
| Q25 | C-18 | broker は 0 でない乱数の session_id を使い、開き直しは同じ id、open はいつも 0x01: 適合している |
| Q26 | C-22 | probe の側で確かめる |
| Q27 | C-23 | これでよい |
| Q28 | C-25 | SHOULD |
| Q29 | C-32 | これでよい: ±2 %。verify_ms 0 を malformed にするのは step 0（try）だけ |
| Q30 | DS-1 | 短い待ちごとに出し直す（DS-1 を採る）。DS-8 の host の保険は、これと一緒にだけ消す |
| Q31 | DS-3〜DS-10 | ch32rv は DS-4 に合っている。DS-5 には ch32rv の細部（同期していない間は数が止まる）を入れた |
| Q32 | P2-★8 | 形 A。ABSTRACTAUTO = 0 は名指してよい。別の debugger を通して attach する probe は `attach_writes_unbounded` を立てる（ch32rv） |

## 一覧

| id | 話題 | 重さ | 一言 | 壊す | 状態 |
|---|---|:---:|---|:---:|---|
| C-01 | 1 断りの種類と伸ばし方 | ★ | tag の番号は下の 7 bit。registry は 0x90 でなく 0x10 と書く | いいえ（registry の定数は変わる） | 合意。d48ca6d で適用 |
| C-02 | 1 断りの種類と伸ばし方 | ★ | 後の revision が定めうる値 → malformed でなく unsupported | はい | 合意。d48ca6d（core、probe-config）、fb44490（インターフェース）で適用 |
| C-03 | 1 断りの種類と伸ばし方 | ★ | 要求の TLV の繰り返し、短すぎ、後ろへの伸ばし | はい | 合意。d48ca6d で適用 |
| O-5 | 1 断りの種類と伸ばし方 | ○ | u8 の enum の 0xF0〜0xFE は実験用 | いいえ | 合意。d48ca6d で適用 |
| C-04 | 2 ignored の上限 | ★ | ignored は多くて 16 個、0x00 は「ほかにも」、落とさない | はい | 合意。cd15f53 で適用 |
| C-06 | 3 時間 | ★ | host の待ち時間に UART の転送時間を足し、前の応答から数え始める | いいえ | 合意。f7d6d21 で適用 |
| P2-★4 | 3 時間 | ★ | 線の再試行は要求ごとに 200 ms、線切れは実時間 1000 ms、attach は 1000 ms まで、scan は 500 ms まで | はい | 条件付き合意。3a88ec9（debug）、f7d6d21（core）、18d7eac（registry）で適用。cold attach の測定はユーザーの判断で閉じた（2026-10-06）。温まった状態のデータで足りる |
| P2-○3 | 3 時間 | ○ | dmi: max_op_ms に数えるのは時間で決まる待ちだけ | いいえ | 合意。3a88ec9 で適用 |
| C-07 | 4 経路 | ★ | TCP では 200 ms のやり直しをしない。長すぎる length。立て直しは host が最後に書いてから 250 ms 待つ | はい | 合意。48b8cbe、0bb10e8（TCP での §5.1）で適用 |
| C-08 | 4 経路 | ★ | max_frame / window / max_inflight は経路ごと | いいえ | 合意。48b8cbe で適用 |
| C-09 | 4 経路 | ★ | UART bridge は 115200 8N1、流れの制御なし。line coding と DTR で OEP を止めない | いいえ | 合意。48b8cbe で適用 |
| C-05 | 4 経路 | ★ | confirm の応答は、どの経路で来たかを言う。TCP の端点も probe | いいえ | 条件付き合意。48b8cbe で適用 |
| C-15 | 5 revision の範囲 | ★ | プロトコルの revision が何に効くか。confirm は変わらない。断りに範囲を付ける | はい | 合意。929bbb7 で適用 |
| P2-★1 | 6 電気の安全 | ★ | scan の count = 0 は idle の項目のある channel を外す。出力の idle の channel は断る | はい | 合意。0517c2f（debug）、18d7eac（core、probe-config、registry）で適用 |
| P2-★2 | 6 電気の安全 | ★ | spi-target は CS が有効な間だけ MISO を駆動する | はい（1 つの probe の build。測った） | 合意。0517c2f で適用 |
| P2-★3 | 6 電気の安全 | ★ | i2c-target はオープンドレインだけ。内蔵のプルアップは宣言する | いいえ | 合意。0517c2f、18d7eac（registry）で適用 |
| P2-○13 | 6 電気の安全 | ○ | plan を取ってもピンは変わらない。ロジックのキャプチャは聞くだけ | はい | 合意。0517c2f（capture）、18d7eac（core、registry）、3d51d4a（インターフェースの名前を出さない core §8、fixture）で適用 |
| P2-★5 | 7 debug の線の一般化 | ★ | 宣言が許さない組 → unsupported | いいえ（probe はすでにそう） | 合意。78403b2 で適用 |
| P2-★7 | 7 debug の線の一般化 | ★ | どの線にも共通のことと、新しい線（JTAG など）が定めること。ピンを持たない線 | いいえ | 合意。78403b2（debug）、18d7eac（probe-config）で適用。ピンの無い線の scan は 2026-10-06 に必須にした（点検 3 の C-21、必須と任意の op） |
| P2-★8 | 7 debug の線の一般化 | ★ | 速さを確かめる前に probe が書いてよいもの。scan が書くのは wake / 設定の並びと dmactive だけ | いいえ | 条件付き合意。78403b2、18d7eac（registry）で適用 |
| P2-○1 | 7 debug の線の一般化 | ○ | 「見つかった」は DMSTATUS.version ≥ 2 かつ ≠ 15。op も同じ | はい | 合意。78403b2 で適用 |
| P2-○4 | 7 debug の線の一般化 | ○ | halt / step が失敗したとき target に何を残すか | はい | 合意。78403b2、18d7eac（registry）で適用 |
| P2-○6 | 7 debug の線の一般化 | ○ | コンソールの規則を「どの mechanism にも」と「DATA0 の mechanism」に分ける | いいえ | 合意。78403b2 で適用 |
| P2-○5 | 7 debug の線の一般化 | ○ | target_id_scheme は probe で 1 つの空間 | いいえ | 合意。78403b2、18d7eac（registry）で適用 |
| P2-★6 | 8 キャプチャ | ★ | モード、ストリーミングの決めごと、`background` を規範の文へ | いいえ | 合意。a35acb0、18d7eac（registry）で適用 |
| P2-○8 | 8 キャプチャ | ○ | configure のどの TLV を host が critical で送るか（samples は送らない） | はい（host） | 条件付き合意。a35acb0 で適用 |
| P2-○9 | 8 キャプチャ | ○ | blocking_ms の間に host と probe が何をするか | いいえ | 合意。a35acb0 で適用 |
| P2-○10 | 8 キャプチャ | ○ | capture-group の状態の表 | はい（fake） | 合意。a35acb0 で適用 |
| P2-○11 | 8 キャプチャ | ○ | 位置つきの read: 書き込み位置より先、量、from 3 | いいえ | 合意。a35acb0 で適用 |
| P2-○15 | 8 キャプチャ | ○ | analog の trigger の enum から level / edge を外す | いいえ | 合意。a35acb0、18d7eac（registry）で適用 |
| PC-1 | 9 probe-config | ○ | 線の名前を firmware の固定の label からも探す | はい（起動時） | 合意。20967d7 で適用 |
| PC-2 | 9 probe-config | ○ | 表に無い名前は役目を表さない。標準の名前は registry に。独自の名前は `x-` | いいえ | 合意。20967d7 で適用 |
| PC-3 | 9 probe-config | ○ | channel に無い pull の idle → unsupported | はい | 合意。20967d7 で適用 |
| PC-4 | 9 probe-config | ○ | label / idle / disable の channel は channels 未満で reserved でない | はい | 合意。20967d7 で適用 |
| PC-5 | 9 probe-config | ○ | label の text は制御文字を含まない 1〜32 byte の UTF-8 | はい | 合意。20967d7 で適用 |
| PC-6 | 9 probe-config | ○ | get の応答: 項目は payload の終わりまで（文言） | いいえ | 合意。20967d7 で適用 |
| PC-7 | 9 probe-config | △ | hash の正規形の細部（文言） | いいえ | 合意。20967d7 で適用。試験のベクタは e21a9a2 |
| PC-8 | 9 probe-config | ○ | transport の index は firmware の版を越えて変えない。起動時の bind | いいえ | 合意。20967d7 で適用 |
| C-10 | 10 適合 | ★ | 規範の語。どの probe と host も持つもの | いいえ | 合意。4e62116 で適用 |
| C-16 | 11 core のほかの規則 | ○ | rejected の応答も送り直しの表に覚える。§5.2 は TCP の端点も縛る | いいえ | 条件付き合意。fc17225 で適用 |
| C-17 | 11 core のほかの規則 | ○ | lease が数え直される時と、応答の lease_ms の範囲 | はい（fake） | 合意。fc17225 で適用 |
| C-18 | 11 core のほかの規則 | ○ | session_id は乱数で 0 でない。open は role 0x01 だけ | はい | 合意。fc17225 で適用 |
| C-22 | 11 core のほかの規則 | ○ | 真偽値は 0 / 1。text に制御文字を入れない | はい | 合意。fc17225 で適用 |
| C-23 | 11 core のほかの規則 | ○ | 名前、model、chip の文法 | はい | 合意。fc17225 で適用 |
| C-24 | 11 core のほかの規則 | ○ | 固有の番号も保存も無い probe の unit_id は `x-` | はい | 合意。fc17225 で適用 |
| C-25 | 11 core のほかの規則 | ○ | 排他で開く、HID の output、WinUSB | いいえ | 合意。fc17225 で適用 |
| C-29 | 11 core のほかの規則 | ○ | registry のキーを止める。hash の意味 | いいえ | 合意。fc17225 で適用 |
| C-30 | 11 core のほかの規則 | ○ | instance は (name, revision) ごとに数える | いいえ | 合意。fc17225 で適用 |
| C-32 | 11 core のほかの規則 | ○ | port_speed: baud の誤差 ±2 %、try の verify_ms 0 | はい | 条件付き合意。fc17225 で適用 |
| C-33 | 11 core のほかの規則 | ○ | ハートビートの周期は 100 ms に切り上げてよい | いいえ | 合意。fc17225 で適用 |
| DS-1 | 12 コンソールの dmseq | ★ | DATA0 = 0 は答えではない: 待ち続け、短い待ちごとに出し直す | はい（target） | 合意。67863b1 で適用 |
| DS-2 | 12 コンソールの dmseq | ★ | 持ち主の規則に、target が出し直す例外を書く | いいえ | 合意。67863b1 で適用 |
| DS-3 | 12 コンソールの dmseq | ★ | 待ち時間は実時間の下限。割り込みを止めても終わる数え方で数える | いいえ | 合意。67863b1 で適用 |
| DS-4 | 12 コンソールの dmseq | ★ | byte k はレジスタの bit 8k〜8k+7 | いいえ | 合意。67863b1 で適用 |
| DS-5 | 12 コンソールの dmseq | ○ | host の無効な語の数を何が 0 に戻すか | いいえ | 合意。67863b1 で適用 |
| DS-6 | 12 コンソールの dmseq | ○ | begin() のときの target の状態 | いいえ | 合意。67863b1 で適用 |
| DS-7 | 12 コンソールの dmseq | ○ | 「長く読んでも」を 3 s にして参考にする | いいえ | 合意。67863b1 で適用 |
| DS-8 | 12 コンソールの dmseq | ★ | host の任意の保険を消す（規則 0 は必須）。DS-1 と一緒に | はい（ch32rv の host） | 条件付き合意。67863b1 で適用 |
| DS-9 | 12 コンソールの dmseq | ○ | dmactive を下ろすと DATA0 が 0 に戻る*ことがある* | いいえ | 合意。67863b1 で適用 |
| DS-10 | 12 コンソールの dmseq | ○ | CRC-8 の確かめ値 | いいえ | 合意。67863b1 で適用。試験のベクタは e21a9a2 |

話題ごとの数:

| 話題 | 数 |
|---|---:|
| 1 断りの種類と伸ばし方 | 4 |
| 2 ignored の上限 | 1 |
| 3 時間 | 3 |
| 4 経路 | 4 |
| 5 revision の範囲 | 1 |
| 6 電気の安全 | 4 |
| 7 debug の線の一般化 | 7 |
| 8 キャプチャ | 6 |
| 9 probe-config | 8 |
| 10 適合 | 1 |
| 11 core のほかの規則 | 11 |
| 12 コンソールの dmseq | 10 |
| **計** | **60** |

外した指摘と理由は最後にある。その後に、確かめる途中で見つけた実装の誤りを並べた。

---

## 1. 断りの種類と伸ばし方

### C-01 ★ tag の番号は下の 7 bit

**状態: 合意.**

**問題。** 実装者は registry で `role_assignment = 0x90` を、`max_speed = 0x01  # critical` の隣に読む。それだけでは、0x90 がすでに critical の bit を含むと分からない。本文は、tag の番号が下の 7 bit だとどこにも書いていない。

**案の文**（core §2.2。「tag の bit 7 は critical」の項と差し替える）:

> - **tag の番号は下の 7 bit（0x01〜0x7E）**。bit 7 は critical の印。要求の中でだけ使い、番号の一部ではない。0x10 と 0x90 は同じ TLV で、印なしと印つきで送ったもの。応答、出来事、データでは bit 7 は 0 で、そこで bit 7 の立った TLV を読む側は知らない tag として飛ばす。tag 0x00 は予約（TLV に使わない。rejected unsupported の payload の印、§4.3）、0x7F は応答の ignored のための予約、0xFF は無効。
> - ignored には tag の番号（bit 7 を外したもの）を並べる。rejected unsupported の payload には、受け取ったままの tag の byte（bit 7 を含む）を置く。

core §7.4 と §8 は「role_assignment（0x10。critical で 0x90 として送る）」と書く。registry は `role_assignment = 0x10` とし、コメントに `# always sent critical (0x90)`。

**変わること。**
- probe、fake: なし。どちらも `tag & 0x7F` で比べている。
- Python、JS: registry の `role_assignment` の値をそのまま送るコードは、bit 7 を自分で立てる必要がある（どこかは未確認）。
- 生成物の定数は 0x90 から 0x10 に変わる。
- 保存した設定: なし（probe.config は critical の bit を外して tag を持つ）。

**今。** probe: `Tail::parse` が bit 7 を外す（Oep.h:204-223）。Python: core の補助関数が外す。`_speed_port` は 0x4E をそのまま比べるが、応答の bit 7 は 0 なので害は無い。

**Q1.** registry の `role_assignment` の値を 0x90 から 0x10 に変えてよいか。生成物の定数も一緒に変わる。勧め: 変える。registry のほかの tag は、すでに bit を外して書いている。

### C-02 ★ 後の revision が定めうる値は unsupported で断る

**状態: 合意.**

**問題。** 後の拡張（gpio の mode 8、i2c の mode 4、新しい drive の kind）のために書いた host を考える。古い probe は malformed（host の誤り）を返す。その値を持たない新しい probe は unsupported を返す。host は 1 つの状況に 2 つの理由を受け取り、「同じ状況に理由を 2 つ作らない」（core §4.3）に反する。要求の flags の予約のビット（list の flags）には規則がまったく無い。

**案の文**（core §4.3。順 5 と 6 を差し替える）:

> 5. **形** → malformed: 長さ、中身と合わない数、TLV の符号化の誤り、欄どうしの食い違い、そして欄の定義がどの revision でも使わないとする値（7 bit の `address > 0x7F`、0 / 1 以外の真偽値、定義が無効とする値、長さが分からず要求の残りを読めなくなる値。知らない dmi の step の kind など）。
> 6. **この probe が扱わない** → unsupported: 定義が使わずに残している値（enum の使っていない値、要求の flags の予約のビット）、定義にあるがこの probe が宣言していない値（mode、format、rate、trigger の type）、知らない critical の TLV、宣言が許さないピンの組。payload の tag は、固定部分の値なら 0x00、critical の TLV の中の値なら受け取ったままのその TLV の tag（critical でない TLV のそうした値は無視する、§2.3）。

core §2.5 に足す:

> 定義が別に言わない限り、enum の使っていない値と、要求の予約のビットは、すべて後から定めうる（§2.7）。probe はそれを §4.3 の順 6 で断る。

core §2.4 に足す:

> host は応答の flags の予約のビットを無視する。失敗を表さない応答の enum の知らない値（cause、holder_kind、scan の entry の kind）は「不明」として見せる。status と reason の知らない値は、これまでどおり失敗。

インターフェースの文で malformed → unsupported（payload 0x00）にするもの:
- gpio の mode ≥ 8。
- uart の format: bit0-1 = 2 / 3、bit2-3 = 3、bit5-7（configure と probe.config の uart の項目）。
- i2c-target の mode 0 と ≥ 4。
- rvswd / swio の attach の method ≥ 2。
- riscv-dm の reset の mode ≥ 3。
- port_speed の step ≥ 3。
- common §1.2 の from ≥ 4。
- probe.config の idle の mode ≥ 5 と、定義の無い lock_scheme。
- list の flags の bit 1〜7（今は無視している）。

drive の TLV の定義の無い kind（fixture §1.1）は、「要求全体を malformed」から §2.3 の規則（critical なら unsupported、そうでなければ無視）に移す。

malformed のまま残すもの: i2c の `address > 0x7F`、spi の mode > 3 と bit_order > 1（その欄にほかの意味が無い）、真偽値、boot_reset の 2 以上（真偽値）、dmi の kind（長さが分からない）、長さと数。

**変わること。**
- probe: OepFixture.cpp:89、:175-178 / :335、:362、OepP4I2cTarget.cpp:292（mode の部分）、OepTarget.cpp:366、OepSwd.cpp:210、OepEndpoint.cpp:597 と :913（list の flags）、OepConsole.cpp:157、OepConfig.cpp:255、:277-278、:328 の検査。
- fake: endpoint.py:2038-2043、2151、1413、1566、1781、2557。
- host: どれも、ここで malformed と unsupported のどちらかに頼っていない。Python が malformed を見るのは confirm のときだけ。
- 保存した設定: なし。そうした値は set で断られ、保存されていない。

**今。** 上に並べたとおり、処理ごとにばらばら。コンソールの mechanism > 2 と probe.config の bind の mode は、すでに unsupported。

**Q2.** 「後から定めうる」（→ unsupported）を、すべての enum の値と要求の予約のビットの既定にし、malformed は上に並べた値だけに残してよいか。勧め: そうする。

### C-03 ★ 要求の TLV の繰り返し、短すぎ、後ろへの伸ばし

**状態: 合意.**

**問題。** attach の max_speed のような安全のための項目が 2 回送られると、ある probe は最初の値を、別の probe は最後の値を読み、違う速さが掛かりうる。critical の TLV の値の後ろに欄を足した host は、それが効くと思っている。「知らない後ろを読み飛ばす」（§2.3）古い probe はそれを黙って無視し、critical の印の意味が崩れる。

**案の文**（core §2.3 に足す）:

> - 定義が繰り返すと言っていない tag は、1 つの要求に多くて 1 回。2 回以上あれば、critical かどうかを問わず rejected malformed。応答では host は最初のものを使う。
> - この probe が実装している TLV の値が定義より短いか、定義が除く値を持つなら、critical かどうかを問わず rejected malformed。定義の中の値でこの probe が扱えないものだけが、unsupported（critical）か無視（critical でない）になる。probe が実装していない TLV は、長さにかかわらず、その probe にとって知らない TLV。
> - **要求の TLV の値は後ろに伸ばさない。** 新しい欄は新しい tag にする。実装している要求の TLV の値が知っている長さより長いとき、probe は critical なら rejected unsupported（受け取ったままのその tag）、そうでなければ TLV 全体を無視して ignored に載せる。

「固定の形の伸ばし方」の最初の項は「**応答、出来事、データの TLV の値、または並びの要素**が固定の形を持つとき ……」にする。足す:

> probe が覚えて読み返す項目（probe.config）は、これまでどおり「後ろに足す」でよい。そうした項目の後ろに足す欄は、古い probe が読み飛ばしても安全なものに限る。

registry は、繰り返す要求の tag にコメント `# repeats` を付ける（role_assignment、gpio の set の drive）。

**変わること。**
- probe: `Tail` に、繰り返さない要求の tag の重なりの検査を足す（今の `Tail::find` は最後を返す）。知っている長さより長い値は unsupported / 無視にする（今は長さをちょうどで比べて malformed）。
- fake: 同じ 2 つ。今は `Take.tail` が最後の値を持ち、長さをちょうどで比べて malformed にしている。
- host: なし。Python の応答はすでに最初を使う（`Tail.get`）。
- 保存した設定: なし。

**今。** probe は要求の後ろを黙って飛ばすことが無い。どの処理も長さをちょうどで比べている。(c) の危うさは本文にだけあり、参照のコードには無い。

**Q3.** 「要求の TLV は伸ばさず、新しい欄は新しい tag」で、これから足す要求に困らないか。勧め: これでよい。TLV ごとの版を持たせるほうが tag 1 つより高くつく。

### O-5 ○ enum の実験用の値

**状態: 合意.**

**問題。** 新しいコンソールの framing、transport の kind、cause を試す人は、後の標準の値とぶつからない番号を使えない。実験用の範囲を持つのは op（0xF0〜0xFF）だけ。

**案の文**（core §2.5 に足す）:

> **実験用の値**: 定義が別に言わない u8 の enum では、0xF0〜0xFE を実験用とする。試すあいだは誰が使ってもよい。出荷する probe と公開した host は使わず、登録もしない。（tag の番号に実験用の範囲は無い。独自の情報は独自のインターフェースに置く、§13 の 7。）

registry は u8 の enum ごとにこの範囲を書く。0xF0 を超える今の値（mechanism の `none = 0xFF`）は範囲の外で、変わらない。

**変わること:** なし。**今:** どの実装も 0xF0〜0xFE を使っていない。

---

## 2. ignored の上限

### C-04 ★ ignored は多くて 16 個、落とさない

**状態: 合意.**

**問題。** host が、drive を掛けられない probe に、critical でない drive の TLV を 20 個付けた gpio の set を送る。probe は最初の 16 個を並べ、残りを黙って捨てる。応答に場所が無ければ ignored の TLV ごと落とす。host はすべての drive が効いたと思う。

**案の文**（core §2.3、ignored の文の後ろ。registry `limits.ignored_max_entries = 16`）:

> - ignored には、無視した TLV の番号（bit 7 を外したもの）を**要求に現れた順に**、無視した TLV 1 つにつき 1 つ、多くて 16 個（`ignored_max_entries`）並べる。無視した TLV が 16 を超えたら、最初の 15 個を並べ、16 個目に **0x00**（「ほかにも無視した」。0x00 は tag にならない、§2.2）を置く。0x00 を見た host は、並んでいない自分の要求の TLV をすべて、無視されたかもしれないものとして扱う。
> - probe は、ignored の要る応答から ignored を落とさない。応答に可変のデータ（data、並び）をどれだけ入れるかを決めるとき、ignored の場所（多くて 18 byte）を空けておく。固定部分だけで場所が足りなければ、入るだけ並べて最後を 0x00 にする。`0x7F 0x01 0x00`（3 byte）はいつでも入る。

**変わること。**
- probe: Oep.h:262（いっぱいなら 0x00 を置く）と :189（落とさずに入るだけにする）。`reserve = 2 + kMaxIgnored`（list、uart / コンソールの read と marks、キャプチャ、probe.config）は、すでに場所を空けている。
- fake: 印つきで 16 で止める。今は上限が無く、255 を超えると `bytes()` が落ちる。
- host: 0x00 を扱う。
- 保存した設定: なし。

**今。** probe: `kMax = 16` で、黙って捨てる。Python / JS: 並びを読むが、0x00 に意味を持たせていない。

**Q4.** 16 個と 0x00 の印でよいか。勧め: これでよい。別の案は異なる tag ごとに 1 つ（多くて 126 byte）。3cc50c8 の決定を戻すことになり、64 byte の max_frame にも入らない。

---

## 3. 時間

### C-06 ★ host の待ち時間に遅い口の転送時間を入れる

**状態: 合意.**

**問題。** 115200 bps の UART bridge で max_frame 4096 の利用者が、大きな応答の返る要求を送る。応答だけで線に約 0.36 s かかる。その前に、送り待ちの通知が max_frame の 2 つぶんまで並びうる（§11.4）。パイプラインでは前の応答も先に来る。「引数 + 1000 ms」ちょうどで待つ host は、正しい応答を時間切れにして送り直す。口が遅いほど悪くなる。

**案の文**（core §4.4。「host の待ち時間」と差し替える）:

> - **host の待ち時間**: 応答が無いことは時間切れでだけ決める（§3.1）。host は要求ごとに**少なくとも**次の時間を待つ: 要求の引数で決まる時間（run の timeout_ms、reset の hold_ms、dmi の待ちの和、save など。attach は `attach_budget_ms` にその reset TLV の hold_ms を足したもの。scan は `scan_budget_ms` + `attach_budget_ms`（debug §1）。無ければ 0。多くて max_op_ms）+ 1000 ms（`host_wait_add_ms`）+ 転送の時間。待ちは、要求を書き終えた時から数える。同じ経路で前の要求が未解決のあいだは、その 1 つ前の要求の応答が届いた時から数える（probe は順に答える）。転送の時間は、UART bridge でなければ 0。UART bridge では (L + max_frame × (1 + `notify_pending_max_frames`)) × 10 / baud 秒。L はその要求のフレームの線の上の長さ、baud は口の今の速さ。host はもっと長く待ってよい。待ち時間が過ぎたら §5.2 の送り直しに進む。

core §7.5 max_op_ms の「host はこの値に線を通る時間を足した値以上を待つ（§4.4）」は「host は §4.4 のとおりに待つ」にする。

1 つ前の応答から数え始めるので、前の応答の大きさを足さなくてよい。

**変わること。**
- host: 下限を計算する。Python と JS はすでにもっと長く（3 s、下）待っていて、そのままで適合する。
- probe、fake: なし。

**今。**
- Python: 応答ごとの期限をその応答を読む時に取るので、実際には前の応答から数えている。待ちは `max(口の timeout, expected + 0.5 s)` で、口の timeout は 3 s（TCP は 15 s）。max_op_ms + 1000 ms で止めていない。
- JS: 3 s。
- Rust: 決まった 3 s。長い要求では下限より短くなりうる。ch32rv は要求ごとに計算するようにする。

**答え。** WireSkein と ch32rv は賛成、bench は OK。P2-★4 の attach の上限が host の待ちと同じ時に切れないよう、scan と attach の上限を引数の時間に足した。

**Q5.** この式を下限にして（host はもっと長く待ってよい）よいか。勧め: そうする。直したいのは短すぎる待ち。

### P2-★4 ★ 線の再試行、線切れ、attach に、host の待ちに合う時間の上限を付ける

**状態: 条件付き合意。条件は閉じた** — cold attach の測定はユーザーの判断でやめた（2026-10-06: cold start には probe の USB を手で抜く必要があり、今の段階ではそこまで細かくしない）。温まった状態のデータを 1000 ms の上限の根拠とする: 0.0.28 は失敗 4 %、p90 519 ms。直したビルドは 400 回中 0 回の失敗で約 138 / 223 ms、1000 ms を超えた裾はリンクの時間だった。

**問題。** host が、線の不安定な target に dmi（引数の時間が無いので 1000 ms 待つ）を送る。probe が「1000 ms 答えが無い」を 1 つの要求の中で当てると、probe の答えと host の時間切れが同じ時になり、後ろに並んだ要求は先に時間切れになる。reset の解放の後の時間と、attach の速さの探索には、上限がまったく無い。

**案の文**（debug §2。「線は ……1000 ms 続けて応答が無いとき失われた」の項と差し替える）:

> - **1 つの要求の中の再試行**: probe が 1 つの要求の中で線の再試行に使う時間は多くて 200 ms（registry `limits.wire_retry_ms`）。遅い速さでの再試行も含む。使い切ったら、その要求を status line で終える。それだけでは線切れと決めない。attach の速さの探索（と scan の 1 組の試し）は、代わりに §1 の attach の上限で止める。
> - **線切れ**: ある connection の op が、線から答えの無い失敗（status line。要求の中でも、コンソールの読みの中でも）を、間に成功を挟まずに**実時間で 1000 ms** 続けたとき（`limits.wire_lost_ms`）、線は失われた。probe が reset を出している間、reset の線を持っている間（plan、attach の reset TLV）、それを放してから 1000 ms は数えない。要求の中で線切れと決めたら、その要求を status line で返してから、connection を閉じる。

debug §1、scan の上限の後ろに足す:

> - **attach の上限**: 1 回の attach の応答に probe が使う時間は多くて 1000 ms（registry `limits.attach_budget_ms`）。速さの探索とその再試行を含み、reset TLV の hold_ms は含まない。その中で使える速さが無ければ、completed failed、status line。
> - **scan の上限**: probe は、scan の要求が着いてから 500 ms（`limits.scan_budget_ms`）より後には新しい組を始めない（今と同じく、少なくとも 1 組は試す）。1 組の試しは attach の上限で止まる。だから 1 回の scan の応答は多くて `scan_budget_ms` + `attach_budget_ms`。
> - どちらの上限も max_op_ms を超えない。host の待ちは、これらを引数の時間に数える（core §4.4、C-06）。

attach の応答に、どの線にも足す（registry `[interface.tlv.attach_answer] search_retries = 0x12`）:

> TLV 0x12 search_retries（u16、任意）: speed_hz の速さを確かめるまでに、速さの探索で失敗した試しの数（0 = 最初の試しで通った。0xFFFF = 65535 以上）。host は記録に残して、失敗しかけている線を見つけてよい。

時間の数の釣り合い: 要求ごとの再試行（200 ms）< scan の上限（500 ms）< attach の上限（1000 ms）= 線切れと決める答えの無い時間（要求をまたいで実時間で 1000 ms）= host_wait_add_ms。attach と scan の host の待ちは、それぞれの上限を host_wait_add_ms に足すので、どの上限も host の待ちと同じ時には切れない。

**測定（bench、2026-10-02）。** RP2350 の probe（0.0.28）が RVSWD で L103 の target に attach、`max_speed` 1 MHz、0.2 s おきに温まった状態の attach を 16 回、2 回まわした: 通ったものはふつう 210 ms、遅いものは 240〜550 ms。速さはいつも約 679 kHz に落ち着いた。2 回目は 10 回のうち 4 回が 515〜739 ms の後に completed failed で終わった。500 ms の上限では通る attach を途中で切ってしまう。1000 ms なら、測ったすべての attach（通ったものも失敗したものも）が収まる。cold attach（target が最初の起こしを無視し、速さの探索に再試行が要った）はまだ測っていない。target の電源を入れ直す必要があり、bench が利用者に頼んでいる。

**変わること。**
- probe:
  - PHY の再試行に時間の枠を付ける（今は回数で止めている: RvswdPhy は 200 回と、多くて 14 回の立ち上げ。SwioPhy は 4 回）。
  - connection ごとに「失敗が始まった時刻」を持つ。今の `failure()`（OepTarget.cpp:562-570）は、1 つの要求の中で DMSTATUS を 3 回読んで（約 3 ms）線切れにしている。
  - attach に枠を付ける（今は回数だけ）。
  - attach の応答に `search_retries` を付ける（任意）。
  - コンソールはすでに実時間の 1000 ms（`kLostMs`）。
- fake: なし（時間の模型が無い）。
- host: status line がいつも「connection が閉じた」を意味するわけではなくなる。本文がすでに言うとおり、host は connections で確かめる。

**今。** 上のとおり。scan の 500 ms は組と組の間でだけ見ているので、1 組の attach は途中で切られない。

**Q6.** 要求ごとの 200 ms と実時間の 1000 ms でよいか。「status line ⇒ connection が無くなった」に頼っている host はあるか。勧め: 両方の数を採る。ch32rv と bench: reset の後にもっと長い上限の要る target があれば教えてほしい。

**答え。** WireSkein は OK。ch32rv と bench: 「status line ⇒ connection が無くなった」に頼る host は無い。bench が attach を測った（上）。500 ms では小さすぎるので attach の上限を 1000 ms にし、再試行の数を attach の応答の TLV にという bench の案を `search_retries` にした。条件（凍結の前に cold attach を 1 回、1000 ms に対して測る）は、2026-10-06 にユーザーの判断で閉じた。温まった状態のデータを根拠とする。

### P2-○3 ○ dmi: max_op_ms に数えるのは時間で決まる待ちだけ

**状態: 合意.**

**問題。** 「待ち（0x04 の us、0x03 / 0x05 の上限）の和」には 0x03 が入っているが、0x03 の上限は読む回数で、時間が無い。host と probe が同じ和を計算できない。

**案の文**（debug §4.1。和の項と差し替える）:

> - 0x04 の step の wait_us と 0x05 の step の max_us の和は max_op_ms を超えない（超えれば rejected unsupported）。0x03 の step は時間でなく回数で止まる。要求が実行中に max_op_ms に達したら、probe はその step でその要求を status timeout で終える（done = その step の位置）。

**変わること:** probe: 0x03 の繰り返しに max_op_ms の検査を足す（あるかどうかは未確認）。fake: 未確認。host: なし。
**今:** probe は 0x04 / 0x05 だけを足している（OepTarget.cpp:793-804）。案と同じ。

---

## 4. 経路

### C-07 ★ TCP、長すぎる length、立て直しの待ち

**状態: 合意.**

**問題。**
1. トンネルや Wi-Fi では、TCP のフレームの途中で 200 ms 止まることはふつうにある。そこで読みをやり直す probe は、フレームの残りを新しい length として読み、流れを失ったままになる。
2. 前の host が書き込みの途中で落ちると、probe はそのフレームの残りを 200 ms 待ち続ける。新しい host が入力が静かになって 50 ms で送った confirm は、その残りとして読まれ、立て直しが失敗する。
3. max_frame を超える length と、report より大きい HID の count を probe がどうするかが無い。

**案の文。**

core §3.2。2 つ目の項と差し替える:

> - シリアルの口、vendor bulk、HID では、フレームの途中で 200 ms（`probe_frame_gap_ms`）入力が止まったら、probe は読みを最初からやり直す。**TCP ではやり直さない。** TCP は区切りを失わず、流れの壊れた TCP の接続は閉じる。

core §3.1、長さつきのフレームの行の後ろに足す:

> - **max_frame を超える length**: probe はそのフレームと、次に `probe_frame_gap_ms` 止まるまでの入力を捨て、次のフレームを待つ。応答は返さない。TCP では代わりに接続を閉じる。report が運べる量（report の長さ − 2。report ID があれば − 3）より大きい count の HID の report は、まるごと捨てる。

core §5.1 に足す:

> 立て直しの confirm の前と、長さつきのフレームの口を開いて最初の confirm の前に、host は、50 ms 静かな入力に加えて、その口に自分が最後に書いてから `host_resync_wait_ms`（registry、250 ms = probe_frame_gap_ms + 50 ms）がたつまで待つ。TCP では、代わりに接続を閉じて開き直してよい。

**変わること。**
- probe: `FrameReader` は TCP に間の規則を当てない。今の `src/` に TCP の経路は無い。max_frame を超える length では間まで捨てる。今は 1 byte ずつずらしている（OepFrame.cpp:164-171）。HID の例（UsbStreams.h:44）は `count` を切り詰めているが、report を捨てる。
- fake: TCP は length を見ず、間の時計も持たない（TCP の規則に合っている）。
- Python: 最後に書いた時刻を覚える（今は入力が静かになるのを待つだけで、link.py:404-432、開いた後も待たない）。
- JS: confirm での立て直しがそもそも無い。止まったときと長すぎる length のときに受けの buffer を捨てるだけ（link.js:196-241）。これは別に直す。

**Q7.** 長すぎる length のとき、probe は間まで捨てる（勧め）か、1 byte ずつずらす（今）か。ずらすと、payload の中の偽の length に乗りうる。

### C-08 ★ 上限は経路ごと

**状態: 合意.**

**問題。** CDC で見張る host（ロックなしの describe、リンクの試験）と、vendor bulk でセッションを持つ host は、互いを知らない。window と max_inflight が probe 全体で 1 つなら、見張る側が使い切ってしまい、セッションの側の要求は断られるか失われる。どちらの host にも避けようが無い。

**案の文**（core §4.4 に足す）:

> - confirm の max_frame、window、max_inflight は、**その confirm が来た経路の**上限。経路ごとに別に数え、ある経路の未解決の要求はほかの経路の受けの余地を使わない。§5.2 の表は probe で 1 つのまま（セッションの 0x81 の要求は 1 つの経路で送る、§3.3）。

**変わること:** 今のコードにはなし。**今:** probe: すべての経路で `Limits` を 1 つ共有する。window と max_inflight は知らせるだけで守らせていない。要求は `poll()` の中で 1 つずつ処理し、経路ごとに読み手がある。fake: 同じ値で、守らせていない。

### C-09 ★ UART bridge の線、line coding、DTR / RTS

**状態: 合意.**

**問題。** 本文だけを読んで書いた host は、知らない probe の UART bridge を開けない。「起動時の速さはボードの profile が決める」とあり、データビット、パリティ、ストップビット、流れの制御は規範のどこにも無い。115200 の決定はガイドにしか無い。USB スタックによっては、DTR が下りている間 CDC の口の出力を止め、firmware がそれを変えられるとは限らない。

**案の文。**

core §3.4 の頭に足す:

> - **UART bridge の線**: 8 データビット、パリティなし、1 ストップビット、流れの制御なし。起動時の速さは **115200 bps**（registry `uart_bridge_boot_baud`）。port_speed（§3.5）が変えるのは速さだけ。
> - **USB のシリアルの口**（USB CDC、内蔵の USB シリアル）: probe は host が設定した line coding にかかわらず OEP を受けて送り、line coding を何にも当てない。
> - **制御線**: probe は、DTR、RTS、line state で OEP を受けるか送るかを決めない。host は口を開いている間、DTR と RTS を立てておく（UART bridge はそれを probe のリセットに配線していることがある）。host が DTR を下ろしている間の probe の振る舞いは定めない。

core §3.5 の「起動時の速さ: ボードの profile が決める口の速さ」は「起動時の速さ: 115200 bps（§3.4）」にする。

**変わること:** 参照のコードにはなし（host が DTR を立てているので）。
**今。**
- probe: 例は `Serial.begin(115200)`（8N1）。line coding を読むものは無い。RP2 は `ignoreFlowControl(true)`。ESP32-P4 の例の CDC の stream は、口がつながっていない間（その USB スタックでは DTR による）write が 0 を返す。
- Python: pyserial の既定（115200 8N1、DTR と RTS を立てる、流れの制御なし）。
- JS: 未確認。

**Q8.** どの probe も起動時の速さを 115200 にし、ボードごとの起動時の速さを無くしてよいか。勧め: そうする。host はほかの速さを当てられない。

### C-05 ★ confirm は、どの経路で来たかを言う

**状態: 条件付き合意** — session の op を自分で答える broker についての ch32rv の直しを、下に入れた（2026-10-02）.

**問題。** port_speed の `port` は「この要求の来た口」でなければならないが、host はその index を知る方法が無い。UART bridge が 2 つある probe では、参照の host は最初の 1 つを選ぶので、2 つ目からは速さを上げられない。

**案の文**（core §7.1）:

> answer: "OEP!", revision(u8), flags(u8), max_frame(u16), window(u32), max_inflight(u8), boot_id(u32), [TLV]
> TLV 0x01 transport (u8): この confirm が来た経路の index（§7.5）。probe はいつも付ける。

core §3.5: 「port: この要求の来た経路の index（confirm の応答の TLV transport）」。registry に `[interface.tlv.confirm_answer] transport = 0x01` を足す。応答は 22 byte から 25 byte になり、64 に収まる。

**ch32rv の問い（TCP の broker はどの index を言うか）に答えて足す。** core §3.1、TCP の項の後ろ（「broker は host の実装で、この仕様の外」も差し替える）:

> - **OEP の要求に自分で答える端点は probe である**。何で運ばれていても、後ろに何があっても（たとえば TCP で OEP を出し、別の debugger を動かすプログラム）。probe の規則はすべて当てはまる。要求を OEP の probe へ中継するだけの broker は、その probe に対しては host である。
> - **session の op に自分で答える中継の broker**（confirm、open、end、keepalive、lock_state）で、ほかのどの要求も 1 つの OEP の probe へ中継するものは、自分の describe を持たない: それが中継する fn 0 の describe は probe のもの。その confirm の TLV transport には index 0xFF（「describe に無い」）を入れる。probe に対しては host である。それらの session の op の規則は、どれもその答えに当てはまる。
> - **TCP の経路**: TCP で listen する probe は、listen している socket を 1 つずつ、fn 0 の describe に 1 つの経路として並べる（kind 6、interface 0xFF）。その socket で受けたどの接続も、confirm の TLV transport にその index を入れる。§3.3、§4.4、§7.1、§11.4 が経路ごとに当てる規則（セッションの 0x81 の要求は 1 つの経路、max_frame / window / max_inflight、使っている revision、通知の行き先）は、受けた接続ごとに別々に当てる。

だから TLV transport はいつも、同じ接続で返る fn 0 の describe の中の 1 つを指す。port_speed（UART bridge、§3.5）と bind（シリアルポート、probe-config §1.2）が TCP の index を取ることは無く、その断り方は変わらない。

**変わること。**
- probe、fake: TLV を足す。fake は経路の並びを TLV の順で作り、index の byte を見ていない（endpoint.py:454-455）。これも直す。
- Python（`_speed_port`、link.py:1275）と JS（`speedPort`、speed.js:162）: TLV を使う。

**今:** probe は `port == 今の経路` を確かめる（OepEndpoint.cpp:597）。2 つの client はどちらも `bridges[0]` を使う。

**Q9.** confirm の TLV（勧め）か、「この口」を表す `port = 0xFF` か。TLV なら、probe.config の bind に要る index も host に渡せる（PC-8）。

**答え。** bench と WireSkein: 異議なし。ch32rv は TCP の端点の規則を確かめ、中継の broker（session の op を手元で答え、ほかを中継する broker）の場合を求めた。その 2 つの案、index 0xFF と TLV transport なしのうち、この提案は 0xFF を取る: TLV はいつもあり、host は broker と話していると分かる。

---

## 5. revision の範囲

### C-15 ★ プロトコルの revision が何に効くか

**状態: 合意.**

**問題。** revision 2 の host は、revision 1 の probe に安全に話しかけられない。confirm そのものが変わらないこと、選んだ revision が何に効くか、断りに何を付けるかが書いていない。

**案の文**（core §7.1 に足す）:

> - confirm の要求とその応答の固定部分、magic の `OEP?` / `OEP!`、confirm の前の決まり（64 byte、§3.1 のフレーム、§3.3）は、どのプロトコルの revision でも同じ。
> - probe が選んだ revision は、**その confirm が来た経路で**、両方向のすべての message に、その経路の次の confirm まで効く。経路ごとに違う revision でよい。
> - ある経路で最初の confirm を送った後、host はそこで送る後の confirm（立て直し、もう一度の探り）すべてに `min_rev = max_rev =` 使っている revision を入れる。
> - 範囲の中に扱える revision が無いとき: rejected unsupported、payload の tag は 0x00、続けて TLV 0x01 supported（min(u8), max(u8): probe が扱える範囲）。`min_rev > max_rev` は rejected malformed。

**変わること。**
- probe: supported の TLV を足す。`min > max` は malformed にする（今は unsupported。OepEndpoint.cpp:498）。
- fake: 同じ。
- Python: 口が自分で送る confirm（立て直し、`confirm_raw`、link.py:422、550）は 0..0xFF を送っている。後の probe に対してはセッションの途中で revision が変わってしまうので、使っている revision を送るようにする。
- JS: 未確認。
- Rust: 立て直しの confirm は今 0..0xFF を送る。ch32rv はどこでも使っている revision を送るようにする。

TCP では「経路」は受けた接続の 1 つずつ（C-05）。

**今:** どちらの側も revision 1 しか知らないので、まだ何も壊れない。

**Q10.** 経路ごとの範囲（「その経路の次の confirm まで」）は broker にとって困らないか。勧め: これでよい。

---

## 6. 電気の安全

### P2-★1 ★ scan の count = 0 は、設定が受け持った channel を駆動しない

**状態: 合意.**

**問題。** 利用者が target の電源を切り替えるピンに、出力 high の idle の項目を保存する。後で別の host が、知らない治具で count = 0 の scan をする。そのピンは plan にも connection にも「持たれて」いないので、probe はそれを SWCLK や SWDIO として駆動する。target の電源が入り切りするか、出力どうしがぶつかる。

**案の文**（debug §1、ピンの組の規則に足す）:

> - count = 0 の並びと、pins の無い attach の候補からは、ほかのものが持っている channel と disable の channel に加えて、probe の設定に **idle の項目**（どの mode でも）がある channel を外す。
> - そうした channel を明示した要求（組を並べた scan、attach の pins）は、idle が入力（mode 0〜2）なら受ける。idle が出力（mode 3 / 4）なら rejected unavailable（cause 5、その channel、holder_kind 7 = 設定の idle）。
> - （参考）count = 0 は、空いている候補のピンを順に駆動する。配線の分からない治具には、利用者の同意なしに count = 0 を送らない。

debug §2 に足す（P2-○14、同じ仕組み）:

> - connection が閉じたら、その組の channel は core §8 の空きの状態にする（idle_clock の駆動を止める）。

registry に `holder_kind.settings_idle = 7` を足す。

**変わること。**
- probe: `pairFree`（OepTarget.cpp:169-178）が idle の項目も見る。
- fake: 同じ（endpoint.py:1553-1557）。
- host: idle の項目のある治具では、count = 0 で見つかるピンが減る。
- 保存した設定: debug のピンに idle を置いた治具は、scan でそのピンを明示する必要がある。

**今。** probe と fake は、持たれている channel と disable の channel だけを外す。probe で見つけた関連の穴:
- scan の後、試したピンを空きの状態に戻さず Hi-Z のままにしている。
- connection が閉じた後、idle_clock low の RVSWD は SWCLK を low で駆動し続け、時間の限りが無い（OepRvswdPhy.cpp:207-213）。idle の無い channel は PHY の状態のまま。

**Q11.** idle の項目のある channel をすべて count = 0 から外し、出力の idle の channel を明示されたら断ってよいか。勧め: そうする。点検は label の付いた channel も外す案だったが、外した。利用者は scan したい debug のピンにこそ label を付けるから。

**答え。** そうする（bench: その治具は DUT の RX の線にだけ idle を置く。ch32rv: 賛成。その host は自分で count = 0 を送るので、idle の項目のある治具では見つかるピンが減る）。

### P2-★2 ★ spi-target は CS が有効な間だけ MISO を駆動する

**状態: 合意.**

**問題。** 多くの DUT は 1 本の SPI のバスを複数の target で共有する。「MISO は tx の外では 0」は「MISO をずっと low に駆動する」と読める。選ばれていない target が MISO を駆動すると、選ばれた target とぶつかる。

**案の文**（fixture §4、MISO の文の後ろに足す）:

> - **configure から plan を放すまで、probe は CS が有効な間だけ MISO を駆動する。** CS が無効な間は MISO を駆動しない（pull の無い入力）。「MISO は tx の外では 0」は、CS が有効な間の転送のビットのこと。SCK、MOSI、CS はいつも入力。configure の前は、channel は空きの状態を保つ（P2-○13）。

**変わること:** probe: SPI のペリフェラルによる。CS が high の間も MISO を駆動するペリフェラルなら、firmware が CS に合わせて MISO の出力を切り替える必要がある。ESP32-P4 の build（ESP-IDF の spi_slave、OepP4SpiTarget.cpp:69-87）は規則を満たす。classic の SPI slave の build は満たさない（下の bench の測定）。fake: なし（電気の模型が無い）。

**Q12（bench）.** あなたの spi-target のハードは、CS が high の間 MISO を駆動しないか。1 回測ってほしい。勧め: 選択肢の無い規則にする。それができない probe は、バスにつないで安全な SPI target ではない。

**答え。** 選択肢の無い規則にする（bench の答え。ch32rv と WireSkein は異議なし）。**測定（bench、2026-10-02）:**
- X035 の治具の probe（ESP32-P4、ESP-IDF の spi_slave）: どの状態でも MISO を駆動しない。規則を満たす。
- V003 の治具の probe（classic の SPI slave の build、d4f6293）: configure の前と放した後は MISO を駆動しないが、configure から後は **CS が high の間 MISO を low に駆動する**（configure した、armed、CS を一巡した後、armed し直した）。規則を満たさず、直している。firmware が CS に合わせて MISO の出力を切り替える必要がある。bench は次の build で試験をもう一度まわす。

だから「壊す」の欄は「はい（1 つの probe の build）」になる。

### P2-★3 ★ i2c-target はオープンドレインだけ。内蔵のプルアップは宣言する

**状態: 合意.**

**問題。**
- SDA / SCL を push-pull で駆動する probe は controller と短絡する。
- 黙って内蔵のプルアップを入れる probe は、プルアップの無い DUT の不具合を隠し、プルアップのある DUT では電圧の分け方を変える。

**案の文**（fixture §3 に足す）:

> - SDA と SCL は**オープンドレインだけ**で駆動する。probe は low に引くか離すかで、high には駆動しない。
> - **内蔵のプルアップ**: configure の間、SDA / SCL に自分のプルアップを入れる probe は、features の bit2（内蔵のプルアップ）と describe の tag 0x42 pullup_ohms（u32、おおよその値）で宣言する。宣言しない probe はプルアップを入れない。v1 には、それを切り替える要求は無い。
> - state 0 では、probe はどのアドレスにも ACK せず、両方の線を離しておく。

**変わること:** probe: bit2 と約 45000 Ω を宣言する。fake: 何も宣言しない。host: bit2 が立っていれば注意を出してよい。
**今:** probe: ESP-IDF の slave の driver（オープンドレイン）。`start()` が両方の線にパッドの内蔵プルアップ（約 45 kΩ）を入れる（OepP4I2cTarget.cpp:212-217）。bench の治具に外付けのプルアップが無いため。state 0 ではペリフェラルを作らないので、何にも ACK しない。

**Q13.** プルアップを宣言する（勧め）か、点検の案のとおり内蔵のプルアップを禁じるか。禁じると、外付けのプルアップの無い bench の治具が動かなくなる。宣言なら host が利用者に伝えられる。

**答え。** 宣言する（bench: X035 の治具は内蔵のプルアップに頼り、V003 の治具には 2.2 kΩ の外付けがある）。内蔵のプルアップは禁じない。

### P2-○13 ○ plan を取ってもピンは変わらない。ロジックのキャプチャは聞くだけ

**状態: 合意.**

**問題。** 利用者の出力の idle が target に電源を出している。そのピンを見るためにロジックの plan を取る。probe がそのピンを入力に替えれば、target の電源が切れる。本文にはそれを止める文が無い。

**案の文**（core §8 に足す）:

> - **plan を取っても、ピンの電気の状態は変えない。** ピンは、持っているインターフェースが使い始めるまで空きの状態を保つ。つまり、gpio は最初の set で、uart の TX は plan で（high、fixture §2）、i2c-target と spi-target は configure で、analog は start で（パッドがデジタルの機能から離れる）。ロジックのキャプチャは聞くだけで、いつまでも変えない。出力を止めず、ほかの機能や出力の idle が駆動するピンの pull や向きも変えない。
> - idle が出力（mode 3 / 4）の channel への analog の plan は rejected unavailable（cause 5、holder_kind 7）。

**変わること。** probe: ロジックのキャプチャは `pinMode(INPUT)` をせずに入力の道を開く（OepCapture.cpp:466-475、OepSampler.cpp:193-202）。analog の planCheck は出力の idle の channel を断る。fake: なし。
**今。** probe:
- gpio、i2c、spi、analog は、使うまで idle を保つ。案と同じ。
- ロジックのキャプチャは plan で `INPUT` にするので、出力の idle が止まる。ロジックの plan は gpio / uart / 線のピンと重なってよく（`planShares`）、それらも入力にする。放しても idle に戻さない。

**Q14.** 使っているキャプチャのペリフェラルは、どれも向きを変えずにピンを読めるか。勧め: 規則にする。見ているピンを変えるキャプチャは、見ている回路を壊す。

**答え。** 規則にする（WireSkein: 電源を入れる試験にこれが要る）。

---

## 7. debug の線の一般化

### P2-★5 ★ 宣言が許さない組 → unsupported

**状態: 合意.**

**問題。** debug §1 は、宣言に無いピンの組を unavailable で断る。core §4.3 の順 6、plan_apply、probe.config は、同じ誤りを unsupported で断る。host は 2 つの理由を受けうる。

**案の文**（debug §1。「許していない組は、何も実行せずに rejected unavailable」と差し替える）:

> - 宣言（channel_group / role_channels）が許さない組は、何も実行せずに rejected **unsupported**。attach は payload に受け取ったままの pins の tag を置く。scan は tag 0x00 を置き、続けて TLV 0x40 index（u8、要求の並びの中の位置）を置く。持たれている channel を含む組（plan、connection、設定、disable）は rejected unavailable（cause 1 / 5、その channel つき）。

**変わること。**
- probe: scan に index の TLV を足し、attach は受け取ったままの tag を使う（今はいつも `pins | 0x80`）。
- fake: scan は cause の無い unavailable（endpoint.py:1551）。attach はすでに unsupported。
- 関連: probe の spi-target は、宣言の外の channel を unavailable で断っている（OepP4SpiTarget.cpp:22）。plan_apply と同じく unsupported にする。

**今:** probe はすでに unsupported を返している（OepTarget.cpp:243、290、410）。文が probe に合わせる。

### P2-★7 ★ どの線にも共通のことと、新しい線が定めること

**状態: 合意** — ch32rv が確かめた（2026-10-02）.

**問題。** 第三者が最初に持ち込むのは、たぶん RISC-V の JTAG DTM、cJTAG、ARM の JTAG-DP。「すべての線」の規則は swdio / swclk、DMSTATUS、2 本のピンの固定部分で書かれている。新しい線にどの規則が効くのか、4〜5 本の線がピンをどう書くのかが分からない。

**案の文**（debug、§1 の前に新しい §0）:

> ## 0. どの線にも共通のことと、新しい線が定めること
>
> どの `oep.wire.*` のインターフェースも:
> 1. op 0x01 scan、0x02 attach、0x03 detach、0x05 connections を §1〜§2.1 の意味で使う（線は 0x06 から op を足してよい）。attach、detach、connections はどの線にも要る。scan は、ピンの組を宣言する線（channel_group か role_channels）に要る。
> 2. §1（書く前に読みで速さを確かめる、count = 0 と外すもの、席と max_connections、scan と attach の上限、断り方）と §2（寿命、線切れ、状態機械、閉じても target を変えない）に従う。swdio / swclk は「ピンの role 1 / 2 の channel」と読み替える。
> 3. `oep.target.*` が使う common §2 の connection を作る。
>
> 組が 2 本のピンでない線は、自分の文書で、pins の TLV、scan の entry、connections の entry を、2 つの u16 の欄の代わりに `n(u8), n × (role(u8), channel(u16))` で書く。ほかの欄とその順は変えない。
>
> **ピンを持たない線。** channel_group も role_channels も宣言しない線（そのピンがこの probe の channel でない。たとえば別の debugger を動かす TCP の端点）は、組をちょうど 1 つ、端点が使う組を持つ:
> - attach は pins なしで送る。pins の TLV は、宣言が許さないほかの組と同じく rejected unsupported（受け取ったままの tag。P2-★5）。
> - scan は任意。持たなければ probe は unknown_operation と答える（C-10）。持つなら、count = 0 はその 1 組を試し、組を並べた要求は rejected unsupported。
> - connections の entry と scan の entry は、どの channel にも 0xFFFF を入れる（`n × (role, channel)` の形では n = 0）。
> - P2-★1 と §1 のピンの規則には当てるものが無い。
>
> 新しい線の文書は、ほかに次も定める:
> - ピンの role と、速さの選び方。
> - 「見つかった」の判定と、scan_kind の値。
> - 使う target_id の scheme（1 つの空間から、P2-○5）と、線切れの見つけ方。
> - その connection をどの `oep.target.*` が使うか、コンソールと probe.config の slot が乗るか。

probe.config §1.1 に足す:

> slot が指すのは 2 本のピンの線。組が 2 本のピンでない線は、slot を定めるときに新しい項目の tag を取る。

**変わること:** なし（今の線は 3 つ）。

**Q15.** 2 本でない線のための `n × (role, channel)` の形を、今決めてよいか。勧め: 決める。決めないと、新しい線ごとに形を作り、host はそれぞれを特別に扱うことになる。

**答え。** bench と WireSkein: 異議なし。ch32rv は分からないと答えた: どの線も scan と connections を持たなければならないなら、WCH の broker は両方が要る。答え: 上の「ピンを持たない線」。connections はどこでも要る（host は status line の後にこれで確かめる、P2-★4。端点はいつも自分の connection を知っている）。scan は、探すピンが無いところでだけ任意。ch32rv が確かめた（2026-10-02）。

**置き換え（2026-10-06）。** 「ピンの無い線では scan は任意」は置き換えた: scan はどの線でも必須で、ピンの無い線では count = 0 がその 1 つの組を試す（debug §0、core §1.2: 任意の op は何がそれを宣言するかを書く。これには宣言が無かった）。ch32rv、WireSkein、bench が同意した。

### P2-★8 ★ 速さを確かめる前に probe が書いてよいもの

**状態: 条件付き合意** — ch32rv（形 A。別の debugger を通して attach する probe には下の flag）、bench と WireSkein（反対なし）、2026-10-02。

**問題。** debug §1 は「probe は線の速さを確かめ終えるまで target に書かない（速さは読みだけで選ぶ）」、「scan が target に書くのは dmactive だけ」と言う。起こして設定するまで何も答えない debug module の線を持ち込む第三者は、どちらの文も守れない: 書いたとおりにすると、probe はそういう target を見つけられない。また文は、選んだ速さで書き込みの道をどう確かめるか、その確かめが target に何を残してよいかを言っていない。読みだけでは足りない: 読みがきれいな速さでも書き込みが壊れることがある（参照の probe で測った。OepRvswdPhy.cpp:347-351、[link measurements](link-measurements.ja.md) §3）。だから書き込みの確かめが要る。

**今**（probe）。
- rvswd の attach（OepRvswdPhy.cpp:415-478）: いちばん遅い速さで、何かを確かめる前に、wake の並び、DMSHDWCFGR / DMCFGR（DMI 0x7E / 0x7D）をそれぞれ 2 回、dmactive（module が明らかに動いていれば飛ばす）を書く。速さは DMSTATUS の読みだけで選び、その速さで書き込みの道を確かめる（`writesLand`、:361-379）: ABSTRACTAUTO = 0、続けて PROGBUF0 への書き込みと読み返しを 256 回。PROGBUF0 は前の値でなく 0 のまま残る。
- swio の attach（OepSwioPhy.cpp:148-166、398-416）: 1 つしかない速さで、設定の組を 2 回と dmactive を 2 回書き、DMCFGR を読み返して確かめる。
- scan（OepTarget.cpp:335）は `Ch32Dm::probe`（OepCh32Dm.cpp:41-46）を呼び、これが attach をまるごと走らせる: wake、設定の組、dmactive、ABSTRACTAUTO、PROGBUF0 への 256 回の書き込み。wake は一部の target の debug module をリセットする。`RvswdPhy::probeOnce`（OepRvswdPhy.cpp:316-326: wake、dmactive、DMSTATUS を 1 回読む）は §1 の言うことに近いが、どこからも呼ばれていない。
- swd の scan（OepSwd.cpp:106-122）: JTAG から SWD への切り替え / dormant からの wake、与えられれば TARGETSEL、DPIDR の読み。ほかには何も書かない。

**案の文、形 A**（勧め）。debug §1、最初の項（「probe は線の速さを確かめ終えるまで…」）と差し替える:

> - **速さを確かめる前の書き込み。** probe は線の速さを確かめ終えるまで、target に次だけを書く:
>   1. その線の節が定める wake / 設定の並び（たとえば wake の模様、line reset、target の選択、module が答える前に要る debug module の設定レジスタ）。線のいちばん遅い速さで送る。
>   2. dmactive。connection が RISC-V DM に届く線で、DMCONTROL が dmactive = 1 と読めないときだけ（この書き込みは haltreq を下ろす）。
> - **速さの確かめ。** probe は速さを読みだけで選ぶ。続けて、選んだ速さで書き込みの道を確かめる。書いて読み返してよいのは、その線の節が空きの scratch と名指す debug module のレジスタ（debug の命令が走っていない間、target のどこも使わないレジスタ）と、その線の節がそれを空きにする書き込みと名指すものだけ。確かめの前にそれぞれの scratch のレジスタを読み、確かめの後にその値を書き戻す。書き込みが読み返せない速さは使わない。
> - 速さを確かめる前に、target にほかのものは書かない。

debug §1、「scan が target に書くのは dmactive だけ（DMSTATUS を読むため）」と差し替える:

> - **scan が書くもの**: 上の 1 と 2 の書き込みだけ。「見つかった」の識別子を読むため。scan は書き込みの道を確かめず、scratch のレジスタにも書かない。速さは attach と同じく読みで選んでよい。

debug §3（rvswd / swio）に足す:

> - **wake / 設定の並び**（§1 の 1）: rvswd: wake の模様、続けて DMI 0x7E と DMI 0x7D にそれぞれ 0x5AA50400、この組を 2 回。swio: DMI 0x7E と DMI 0x7D にそれぞれ 0x5AA50400、この組を 2 回。
> - **scratch**（§1）: PROGBUF0（DMI 0x20）。空きにする書き込み: ABSTRACTAUTO（DMI 0x18）= 0。これは戻さない（前のセッションが仕掛けたままの autoexec は、触るたびに走る）。

debug §5（swd）に足す:

> - **wake / 設定の並び**（§1 の 1）: JTAG から SWD への切り替え、dormant からの wake、与えられれば TARGETSEL。swd は scratch のレジスタを名指さない。

P2-★7 の「新しい線の文書が定めるもの」に「wake / 設定の並びと scratch のレジスタ（§1）」を足す。

**形 B。** §1 は「速さを確かめる前に、probe はその線の節が並べるもののほかは書かない」とだけ言い、それぞれの線が自分の書き込みを（上のように）並べる。一般の上限は置かない。簡単だが、新しい線を書く人には従う規則が無く、host は読んでいない線について何も当てにできない。

**勧め: 形 A。** どの線にも効く上限（線が定める並び、dmactive、戻す scratch）を保ち、具体的なレジスタだけをそれぞれの線に任せる。

**変わること。**
- probe: scan は書き込みの確かめの無い立ち上げを使う（wake / 設定の並び、dmactive、DMSTATUS の読み。たとえばいちばん遅い速さの `probeOnce`、または `writesLand` を除いた attach）。`writesLand` は確かめの前に PROGBUF0 を取っておき、後で書き戻す。`Ch32Dm::probe` の注釈（「ほかには何も書かない」）が本当になる。swio と swd: なし。
- fake、host: なし（fake: 未確認）。

**壊す:** いいえ。scan は今より書くものが減る。attach は今と同じものを書き、PROGBUF0 の書き戻しが加わる。

**ch32rv のために足した（別の debugger を通して attach する probe）。** debug §1、形 A の後:

> 上の限りは、自分で線を駆動する probe に当てはまる。attach が、自分では制御できない別の debugger を通る probe（その debugger が書くものを見ることも限ることもできない）は、線の describe の flags の bit `attach_writes_unbounded` を立て、この限りの外になる。host は、そうした線の attach を、効き目の分からないリセットと同じに扱う: target のレジスタや走っているプログラムが残ることを期待しない。

registry は、線の describe にこの flag の bit を足す。文だけでなく flag にするのは、第三者の probe に会った host が見分けられなければならないため。

**Q32.** 形 A（勧め）か形 B か。また、線は、scratch を空きにするために、上の ABSTRACTAUTO = 0 のような戻さない書き込みを名指してよいか。勧め: よい、線ごとに名指す。仕掛けたままの autoexec を次の attach が望むことは無く、この書き込みが無いと、電源を入れ直すまでどの attach でも確かめが落ちる。

### P2-○1 ○ 「見つかった」は DMSTATUS.version ≥ 2 かつ ≠ 15。op も同じ

**状態: 合意.**

**問題。** debug の仕様の後の版（version 4 以降）の RISC-V の DM を「無い」と答える。さらに悪いことに、参照の probe は version 3 の DM（1.0。WCH 以外の RISC-V の多く）を見つけるのに、止まったと見ることが無い。

**案の文**（debug §1）:

> 「見つかった」は、DMSTATUS.version が 2 以上で 15 でないこと（0 = DM が無い、1 = このインターフェースが扱わない版、15 = 準拠しない DM）。swd では DPIDR を読めたこと。

debug §4 に足す:

> riscv-dm の op は、scan が受ける版をすべて同じに扱う。

**変わること:** probe: `Ch32Dm::probe`（OepCh32Dm.cpp:41-46）は 2 か 3 を求める。`checkHalted`（:79）、halt の近道（:145）、`resetHalt`（:451）、コンソール（OepDmConsole.cpp:48）は、ちょうど 2 を求める。fake: 確かめていない（検査が無い）。

### P2-○4 ○ halt / step が失敗したとき target に何を残すか

**状態: 合意.**

**問題。** モーターを動かしている target で、host の step が時間切れになる。dcsr.step は立ったままで、次に何かが resume したとき 1 命令で止まるのか。haltreq は立ったままで、後で止まるのか。不変条件の表は「dcsr.step を下ろす」と書くが、走っている hart ではそれができない。

**案の文**（debug §4 の表と §4.2）:

> - **halt**: 100 ms の間に allhalted が見えなければ、probe は haltreq を下ろして status timeout を返す。
> - **step**: hart が 100 ms の間に debug mode に戻らなければ、probe は haltreq を立て、さらに 100 ms まで待つ。止まれば、dcsr.step を下ろし、DATA1 / DATA0 を戻して、dpc_after を有効にして status state を返す。止まらなければ、haltreq を下ろし、応答の TLV 0x01 step_left（長さ 0）を付けて status state を返す。dcsr.step は立ったままかもしれず、hart は走っている。host が止めて dcsr.step を下ろす。

registry に `[interface.tlv.step_answer] step_left = 0x01` を足す。

**変わること。** probe: 今の halt（OepCh32Dm.cpp:155-172）は haltreq を立てたままにする。step（469-500）は 50 ms 待ってから `halt()` を呼ぶ。それが失敗すると dcsr.step と haltreq は立ったまま。dpc の読みが失敗すると dcsr を戻すのを飛ばす。fake: 未確認。

**Q16.** halt が時間切れのとき haltreq を下ろす（勧め）か、立てたままにする（今）か。残った halt の要求は、どの host も思っていない時に target を止めうる。

### P2-○6 ○ コンソールの規則: どの mechanism にもと、DATA0 の mechanism

**状態: 合意.**

**問題。** ARM のコンソール（MEM-AP で読むメモリのリング、semihosting、SWO）を新しい mechanism として足せない。「1 つの connection に生きているストリームは 1 つ（どれも DATA0 を使う）」「riscv-dm の要求の間は止める」「DMSTATUS は 20 ms ごと」が、インターフェース全体の規則として書かれている。

**案の文。** console §2 には、どの mechanism にも効く規則を残す: 番号、open が既にある (connection, mechanism) のストリームを返すこと、同じ所での開き直し、寿命、close、閉じたストリームを読めること、write の意味、セッションにかかわらず吸い出すこと。足す:

> mechanism はそれぞれ、開ける connection の種類、使う target の資源、ほかの mechanism と合わせて 1 つの connection に生きたストリームをいくつ持てるか、probe が読みを止める時、target の状態を見る間隔を定める。

console §3 の冒頭:

> mechanism 0、1、2 は DATA0 と DATA1 を郵便受けに使う。この 3 つの中では、1 つの connection に生きているストリームは 1 つ（ほかの 1 つでの open は rejected unavailable cause 6）。その connection で riscv-dm の要求が動いている間と hart が止まっている間は、読みを止める（DMSTATUS は少なくとも 20 ms ごとに見る）。arm-adi の connection では開かない（rejected unavailable cause 6）。

**変わること:** なし（意味は変わらない）。**今:** probe は 0〜2 でちょうどこのとおりにしている。

### P2-○5 ○ target_id_scheme は probe で 1 つの空間

**状態: 合意.**

**問題。** registry は scheme を線ごとに持っている。slot の錠は scheme の番号だけで比べるので、新しい線の「scheme 1」が rvswd のものとぶつかりうる。

**案の文**（debug §1）: 「target_id の scheme の番号は probe 全体で 1 つの空間（registry `[common.enum.target_id_scheme]`: 1 その debug module の DMI 0x7F の u32、2 swd の targetsel）。線はどれを使うかを書く」。registry は enum を移す。番号とキーの `wch_dmi_7f` は変わらない。

**変わること:** 線の上ではなし。生成物の識別子の場所が変わる（凍結の前、C-29）。

---

## 8. キャプチャ

### P2-★6 ★ モード、ストリーミングの決めごと、`background` を規範の文へ

**状態: 合意.**

**問題。** describe の mode の `background(u8)` は、意味も値も規範のどこにも無い。ストリーミングの決めごとは日本語の記録にしか無い。英語の読み手はキャプチャを実装できない。

**案の文**（capture に新しい §2.1「モード」。§2 の区画は §2.2 になる）:

> | モード | 動き |
> |---|---|
> | 1 ワンショット | start（とトリガ）の後 samples だけ取って止まる（state 4）。host は自分の速さで読む。次の start でデータは消える |
> | 2 リピート | ワンショットを、区画の境目に隙間を作らず、空いた区画にだけ続けて取る。空きが無くなれば止まり（state 5）、release で再び取る |
> | 3 ストリーミング | リピートと同じく隙間なく取り、ロックの持ち主が購読している間、データを通知で送る |
>
> - トリガは開始の条件だけ。どのモードでも、最初の区画の開始にだけ効く。
> - probe は start の後にだけ取る。先回りして取らない。
>
> **ストリーミングの決めごと**:
> 1. 送る場所が無いとき、probe は**新しい**データを捨てる（すでに並んだデータは送る）。捨てた量は、次のデータのフレームの position の飛びと、status の flags の bit0 に出る。
> 2. stop の後も、probe は stop の前に取ったものを送る。受け取った位置の終わりが stop の後の status の write_pos と等しければ、host はすべて受け取っている。
> 3. ストリーミングでは区画の出来事を送らない（stopped は送る）。
> 4. 通知で送ったデータは、read で読めるとは限らない（読めない位置は gap つきの空の応答）。
> 5. 購読はロックと一緒に終わる（core §11.3）。受け取る host はロックを保つ。

capture §3.5 の mode の行:

> mode(u8), background(u8: 1 = このモードで取っている間も probe は要求に答え、start の blocking_ms は 0。0 = 取っている間は答えず、start の blocking_ms がその長さを言う、§3.2。ほかの値は予約), max_samples(u32), max_segments(u32)

「宣言は目安で、configure の応答が正」はリンクを外して残す。記録へのリンクは「（理由: ……）」の形にする。

**変わること:** probe: なし。fake: データを捨てない（決めごとの 1 は後で模してよい）。
**今。** probe:
- background はいつも 1、blocking_ms は 0。
- 置いてから送る道は新しいデータを捨てて status の dropped を立てる。
- 直接の道は誰も購読していない間は捨てる。
- stop の後はどちらの道も残りを送る。
- 置いてから送る道のデータは区画を使い回すまで読め、直接の道のデータはいつも読めない。

どれも案のとおり。

**Q17.** background の値（0 = 止まる、1 = 答える）でよいか。勧め: これでよい。

### P2-○8 ○ configure のどの TLV を host が critical で送るか

**状態: 条件付き合意** — WireSkein: samples は critical にせず、上限に丸め、答えの値を正とする（反映済み）.

**問題。** host がストリーミングを持たない probe に、critical なしで mode = 3 を送る。probe はそれを無視してワンショットで configure する。host が ignored を見落とすと、違うモードで記録する。

**案の文**（capture §3.3。表に「critical で送る」の列を足す）:

> - mode、rate、trigger、pretrigger、frontend はいつも critical で送る。そのどれかに従えない probe は configure を断る（unsupported、受け取ったままの tag）。
> - rate を critical で送ったときの意味: probe は宣言した範囲の中でいちばん近い作れる値を使う（どれかは actual_rate が言う）。範囲の外の rate は unsupported。
> - samples と segments は critical なしで送ってよい。probe が持てるより大きい samples はその上限に丸め、応答の actual_samples（0x52）を正とする。host は、送った値を当てにせず、actual_samples と actual_segments を読む。

**変わること:** これらを critical なしで送る host は bit を立てる（WireSkein は mode を critical で送る。Python の capture.py: 未確認）。probe: samples を上限に丸めて actual_samples で言う（今そうしているかは未確認）。fake: 未確認。

**Q18（WireSkein）.** この並びは記録の道具に合っているか。勧め: これでよい。

**答え。** WireSkein: mode、trigger、pretrigger、frontend の critical はよい。rate の critical も上の意味ならよい。samples には 2 つの形を出した: critical にして、上限を超える samples を max_samples つきの unsupported で断るか、critical にせず上限に丸めて応答を正とするか。WireSkein は後者を勧め、それを採った（初版は samples を critical にしていた）。

### P2-○9 ○ blocking_ms の間

**状態: 合意.**

**案の文**（capture §3.2。「blocking の間は lease を数えない」と差し替える）:

> - start の応答から blocking_ms の間、probe はどの経路のフレームも処理しないことがあり、失いうる。host はその間、どの経路でもその probe に何も送らない。その後、長さつきのフレームの経路では core §5.1 の立て直しから始める。シリアルの口ではそのまま続ける。lease も host の待ち（core §4.4）も、blocking_ms を数えない。

**変わること:** なし。今は止まる probe が無い（どれも background = 1）。Python は blocking_ms を start の要求の expect_ms に渡しているが、害は無い。

### P2-○10 ○ capture-group の状態の表

**状態: 合意.**

**案の文**（capture §4.1 に足す）:

> - 束ねたトラックが無いとき: start は rejected unavailable cause 6。stop と force は何もせずに成功する。state は 0。
> - 組の state: どれかのトラックが 6 なら 6。そうでなく、start 済みですべてのトラックが 4 なら 4。そうでなく、trigger_track があってまだ発火しておらず、どれかのトラックが 2 か 3 なら 2。そうでなく、どれかのトラックが 2、3、5 なら 3。どれでもなければ 1。
> - start は、どれかを始める前にすべてのトラックを確かめる。ストリーミングで購読の無いトラックがあれば、start は rejected unavailable cause 6。TLV fn（0x05）はそのトラック。

**変わること。**
- probe: 状態はすでに合っている（OepCaptureGroup.cpp:69-81）。購読の無いストリーミングのトラックは始める途中で見つかり、束ねたトラックを止めて completed failed を返している。その検査を start の前に移す。
- fake: error と待ちの状態が無い（fake_capture.py:482-491）。

### P2-○11 ○ 位置つきの read: 書き込み位置より先、量、from 3

**状態: 合意.**

**案の文**（common §1.2 に足す）:

> - 求めた位置（from 0）が書き込み位置より先なら、応答は start = 書き込み位置、len 0、flags 0。
> - len は max 以下で、max_frame の中で応答に入る量以下。残りがあれば more を立てる。
> - from 3 で arg > 0xFF は rejected malformed（印の kind は u8）。

**変わること:** probe: from 3 は今 `arg & 0xFF` を使っており、断るようにする。fake: 未確認。
**今:** probe は start を終わりに寄せ、len を詰めている。案のとおり。

### P2-○15 ○ analog の trigger の enum

**状態: 合意.**

**案の文:** registry の `oep.fixture.analog` の `[interface.enum.trigger]` から level = 1 と edge = 2 を外す。本文はすでに 1〜2 をロジック用と書いている。**変わること:** 生成物の定数が消える。**今:** probe は 0 / 3 / 4 だけを宣言し（OepAnalog.cpp:98）、1 / 2 は断る。

---

## 9. probe-config

### PC-1 ○ 線の名前を firmware の固定の label からも探す

**状態: 合意.**

**問題。** いちばん多い利用者は、リセットのピンが基板で決まった市販の probe を使う。その firmware は、そのピンを describe の 0x46 の label でしか名乗れない。今は、利用者が設定の label を置くまで boot_reset は何もせず、host は規範の手段でリセットの線を見つけられない。

**案の文**（probe-config §1.3。探し方を差し替える）:

> **slot の線を探す**（名前 N、slot の名前 S）。次の順に探し、channel がちょうど 1 つ見つかった段で止める:
> (a) `S.N` と等しい設定の label。
> (b) 設定に slot の項目が多くて 1 つのときだけ、`N` と等しい設定の label。
> (c) 設定に slot の項目が多くて 1 つのときだけ、`N` と等しい firmware の label（fn 0 の describe、0x46）。
> channel が 2 つ以上見つかった段で、線は無しとして探すのを終える。text と名前は ASCII の大文字と小文字を区別せずに比べる。

「探すのは設定の label の項目だけ」の文は消す。

**変わること。**
- probe: `findLine`（OepConfig.cpp:1133-1181）に (c) を足す。
- Python の `find_line`、fake の `line_for`、JS: 同じ。
- 保存した設定: boot_reset 1 で設定の label が無い slot は、firmware が `nrst` の label を持つ probe では、起動時にリセットつきのやり直しを始める。

**Q19.** firmware の label を (c) にする（勧め）か、fn 0 に新しい tag `line(channel, name)` を足すか。新しい tag は label と重なる。

**答え。** (c) にする（bench は歓迎。ch32rv は賛成し、自分の host にもこの段を足す）。

### PC-2 ○ 表に無い名前、標準の名前と独自の名前

**状態: 合意.**

**案の文**（probe-config §1.3 に足す）:

> - 表に無い label の text は役目を表さない（ただの名前）。標準の名前は registry（`oep.probe.config` の `[line_names]`）に並べる。足しても revision は変えない（core §2.7）。標準でない役目の名前は `x-` で始める（例 `x-acme-boot0`）。標準の名前は `x-` で始めず、どの名前も `.` を含まない（`S.N` が使う）。

**変わること:** なし。**今:** 名前を確かめる実装は無い。probe が使うのは `nrst` だけ。

### PC-3 ○ channel に無い pull の idle → unsupported

**状態: 合意.**

**案の文**（probe-config §1 の idle と、断り方の表の unsupported の行）:

> その pull を持たない channel への mode 1 か 2 の idle は rejected unsupported（受け取ったままの項目の tag）。（参考）`oep.fixture.gpio` を持たない probe では、host はどの channel が pull や出力を持つかを前もって知る手段が無い。

点検は mode ≥ 5 を malformed とする案だったが、C-02 により unsupported にする。

**変わること。** probe と fake は今これを黙って受けている。保存した設定: そうした channel に保存した idle 1 / 2 は起動時に断られ、保存の全体が当たらない（理由 3）。

**Q20.** そうした保存した設定が起動時に失敗するようになってよいか。勧め: よい。今は成功と答えて、ピンが浮いている。

**答え。** よい（bench）。

### PC-4 ○ label / idle / disable の channel

**状態: 合意.**

**案の文**（probe-config §1、表の前）:

> - **項目の channel**: label、idle、disable の項目の channel は `channels`（fn 0 の describe 0x43）未満で、`reserved`（0x44）に入らない。そうでなければ set は rejected unsupported（受け取ったままの項目の tag）。

disable の「（idle と同じ）」はここを指すようにする。

**変わること。** probe: 今は label の channel を確かめていない（OepConfig.cpp:250-252）。idle と disable はピンの表の許す組で確かめていて、それは残してよい。fake: label は未確認。保存した設定: 範囲の外の channel に保存した label は起動時に失敗する。

### PC-5 ○ label の text

**状態: 合意.**

**案の文**（probe-config §1 の label）:

> text: 1〜32 byte（registry `limits.label_max_bytes`）の正しい UTF-8 で、C0 の制御文字（0x00〜0x1F）と 0x7F を含まない。そうでなければ rejected malformed。

§1.2 の括弧「（label の項目そのものは制限しない）」は消す。mixed の印の `]` の置き換えは残す。

**変わること。** probe と fake は `len ≥ 3` だけを確かめ、Python は何も確かめない。保存した設定: 長すぎる label や正しくない label は起動時に失敗する。

**Q21.** 32 byte で足りるか（slot の名前と owner に合わせた）。勧め: 足りる。

### PC-6 ○ get の応答（文言）

**状態: 合意.**

**案の文**（probe-config §2、get の行）:

> answer: more(u8), hash(u32), payload の終わりまでの項目。tag 0x7E は応答のメタ情報のための予約で、v1 の probe は置かない。get は TLV を取らない（あれば rejected malformed、core §7.3）。

**変わること:** なし。

### PC-7 △ 正規形（文言）

**状態: 合意.**

**案の文**（probe-config §2 の hash に足す）:

> 正規形の tag は critical の bit を外したもの。キーは数として比べ、欄の複数あるキーは最初の欄から順に比べる。

試験ベクトル（項目、正規形の byte、hash）を `tests/` に置く。**変わること:** probe、fake、Python が一致していればなし（未確認）。

### PC-8 ○ firmware の版を越えた transport の index と、起動時の bind

**状態: 合意.**

**問題。** 利用者は配布元の firmware を更新し、bind を見直さない。USB の構成が変わると、保存した bind は黙って別の口を指す。

**案の文。**

core §7.5 に足す:

> **transport の index の不変**: 同じ model の firmware の版を越えて、transport はその index を保つ。transport を足す firmware は、使ったことの無い index をそれに与え、外した index は使い回さない。

probe-config §1.2: 括弧「（bind を見直す）」を消す。

probe-config §2 に足す:

> 起動時、port がこの firmware のシリアルの口でない保存した bind は、保存を読めないものにする（理由 2）。保存したどれかの項目の適用が断られたら、保存の全体を当てない（理由 3）。

**変わること:** probe と fake は、断られたときすでに保存の全体を飛ばしている（OepConfig.cpp:941-948、endpoint.py:2473-2504）。シリアルでない口は今は理由 3 で、2 にする。

**Q22.** index の不変（勧め）か、bind に transport の kind を一緒に持つか。不変なら、更新の後も bind がそのまま使える。kind の検査は食い違いを見つけるだけ。

**答え。** index の不変（bench: そのファイルは bind の口を番号で持っている）。

---

## 10. 適合

### C-10 ★ 規範の語と、どの probe と host も持つもの（O-14、O-15 を含む）

**状態: 合意.**

**問題。** probe がどの core の op に答えなければならないか（link_source は？ピンの無い probe の plan_apply は？）、最小の host が何をしなければならないかを、1 か所で知れない。英語版は現在形と小文字の may / preferably で書かれ、どれが要求かを言っていない。

**案の文。** core に新しい §1.1「規範の語」:

> 大文字の MUST、MUST NOT、SHOULD、SHOULD NOT、MAY は RFC 2119 と RFC 8174 のとおりに使う。probe や host がすることを現在形で書いた文（「probe は …… を返す」）は要求（MUST）。「preferably」は SHOULD。（参考）と書いた文、例、注は規範ではない。日本語の訳では、「〜する／〜しない」= MUST / MUST NOT、「〜してよい」= MAY、「できれば〜する」= SHOULD。

core に新しい §1.2「適合」:

> probe が必ず持つもの:
> - §3 の経路のどれか 1 つと、そのフレーム。
> - §4〜§6。
> - fn 0 の confirm、list、describe、open、end、keepalive、lock_state、subscribe と unsubscribe、link_source と link_sink。
> - fn 0 の describe の unit_id、transport、max_op_ms。
>
> plan_apply と plan_release は、plan の role を持つインターフェースが 1 つでもあるときに必ず持つ。1 つも無い probe は unknown_operation を返す。任意: port_speed（§3.5）、fn 0 のハートビートのほかの通知、すべてのインターフェース。
>
> probe は、実装していない op には unknown_operation を、実装している op の任意の機能には unsupported を返す。
>
> host が必ずすること: 知らない TLV と tag を飛ばす（§2.3、§2.4）。§3.2 と §3.3 の探りの規則に従う。§4.4 のとおりに待つ。§5.2 のとおりに送り直す。§11.1 のとおりにフレームを振り分ける。

core §12 の表に「必須」の列（はい / plan の role があれば / 任意）を足す。core §0 の規則 4（「project が適合試験を持つ」）は、試験ができるまで「project は registry と適合の材料（試験ベクトル、fake）を保つ」にする（O-8、文書の項目）。

**変わること。**
- probe: plan の role の無いビルドでは、今の plan_apply は unavailable を返す（Oep.h:432-435）。unknown_operation になる。
- probe: 固有の番号の無いプラットフォームでは unit_id を出さず（Oep.h:478）、「必須」に反している（C-24 を見る）。
- fake: これらをすべて実装している。

**Q23.** 現在形の約束をこの規則と一緒に残す（勧め）か、第三者のレビューの前に規範の文をすべて大文字の語で書き直すか。仕様全体の書き直しは大きく、意味を変えてしまうおそれがある。

**Q24.** link_source / link_sink を必須にしてよいか。勧め: する。安く、host のリンクの試験がこれに頼っている。

---

## 11. core のほかの規則

### C-16 ○ rejected の応答も送り直しの表に覚える

**状態: 条件付き合意** — ch32rv が確かめ、中継の broker の接続ごとの corr の対応表を求めた（入れた、2026-10-02）.

**案の文**（core §5.2 に足す）:

> probe は、§4.3 の順 2 を過ぎた最後のセッションのすべての要求の応答を、rejected も含めて覚え、それで最も新しい corr を進める。rejected を受けた要求を直して送る host は、新しい corr を使う。

**ch32rv の問い（§5.2 は broker のような TCP の端点を縛るか）に答えて足す。** core §5.2 に足す:

> §5.2 は、どの probe（C-05: OEP の要求に自分で答えるどの端点も）も、TCP を含むどの経路でも縛る。TCP はフレームを落とさないが、応答が遅れれば host は待ち（§4.4）の後に送り直すので、probe は要求を 2 回実行しないよう表を持つ。表は probe に 1 つで、セッションと同じく、すべての経路と TCP の接続が共有する。OEP の probe へ中継するだけの broker は自分の表を持たない。corr を付け直すなら、client の送り直しを、最初に使ったのと同じ corr で中継する。そのため、受けた client の接続ごとに、client の corr から上流で使った corr への対応を、少なくともその client の最後の max_inflight 個の要求の分だけ持ち、その接続が閉じたら捨てる。

**変わること:** probe はすべての応答を覚えているので、なし（OepEndpoint.cpp:450-463）。fake: 未確認。WCH の broker のような TCP の端点は表を持つ。

**答え。** bench と WireSkein: 異議なし。ch32rv は、§5.2 が TCP の端点を縛るか分からないと答えた。上の段落は「縛る」と答える。ch32rv が確かめるまで未決。

### C-17 ○ lease が数え直される時と、応答の lease_ms

**状態: 合意.**

**案の文。**

core §6.1:

> ロックを持つセッションの要求で §4.3 の順 3 を過ぎたものに答えるたびに、rejected も含めて、lease を数え直す（応答を送った時から lease_ms を数える）。§5.2 の表から返した応答では数え直さない。

core §6.4:

> 応答の lease_ms は lease_min_ms〜lease_max_ms（1000〜60000）の中。

**変わること:** probe はすでに両方をしている（OepEndpoint.cpp:441、714）。fake: 下の止めが無く、上の止めは 600000（endpoint.py:1094-1097）。直す。

### C-18 ○ session_id。open は role 0x01 だけ

**状態: 合意.**

**問題。** どちらも固定の session_id（1 や、プロセスの名前のハッシュ）を使う 2 つの host は、互いのセッションを黙って再開する。

**案の文**（core §6.1、§4.1）:

> host はセッションごとに、session_id を予測できない 32 bit の乱数から選ぶ。固定の値と 0 は使わない。session_id 0 の open は rejected malformed。open は role 0x01 で送り、role 0x81 の open は rejected malformed。

**変わること。** probe と fake は今 0 と 0x81 の open を受けている。検査を 2 つ足す。Python（`SystemRandom`、1〜2^32−1）と JS（crypto、0 でない）は適合していて、open を role 0x01 で送る。

**Q25（ch32rv）.** broker は session_id をどう選んでいるか。0x81 で open を送ることはあるか。

**答え。** ch32rv: 0 でない乱数の session_id で、開き直しは同じ id。open はいつも 0x01 で送り、0x81 では送らない。適合している。

### C-22 ○ 真偽値と text

**状態: 合意.**

**問題。** owner はほかの利用者の端末に出る。host はそこに ANSI のエスケープを入れられる。

**案の文**（core §2.1 に足す）:

> - u8 の真偽値は 0（偽）か 1（真）。要求でほかの値は rejected malformed。応答では、host は 0 でない値を真と読む。
> - 正しい UTF-8 でない text と、C0 の制御文字（0x00〜0x1F）か 0x7F を含む text は、要求なら rejected malformed。host は応答の text を見せる前に、そうした文字と正しくない UTF-8 を置き換える。

**変わること。**
- probe: 今はどこにも text の検査が無く、open の force は 0 でない値をすべて真とする。owner と label のために小さな UTF-8 の検査が要る（slot の名前はすでに制限している）。
- fake: 同じ。
- host: 見せるときに置き換える。

**Q26.** probe の側で確かめる（勧め）か、host の側だけにするか。probe は、どの見る人の text も通るただ 1 つの場所。

### C-23 ○ 名前、model、chip の文法

**状態: 合意.**

**案の文。**

core §13 の 1 に足す:

> 名前の label はそれぞれ 1 文字以上の `a-z 0-9 -` で、`-` で始めも終えもしない。名前は 2 つ以上の label。

core §7.5 の model:

> プロジェクトのものでない model は、作る者の逆 DNS の名前の `.` を `-` に替えたもので始める（例 `com-example-probe1`）。

core §7.5 の chip:

> `<型番> v<リビジョン>`。型番は 1〜24 文字の `a-z 0-9`。リビジョンは数字と、任意の `.数字` の並び。リビジョンが分からなければ型番だけ。

**変わること:** 使われているインターフェースの名前は合っている。参照の firmware の model と chip の文字列は未確認。

**Q27.** model の接頭の規則でよいか。勧め: これでよい。host は model ごとの表（速さ）を持つので、作る者どうしでぶつかると違う表を使ってしまう。

### C-24 ○ 固有の番号も保存も無い probe の unit_id

**状態: 合意.**

**案の文**（core §7.5。ビルドの定数の文と差し替える）:

> 保存を持つが固有の番号を持たない probe は、最初の起動のときに乱数から unit_id を作って保存する。どちらも無い probe は `x-` で始まる unit_id（一意でない）を使う。host は `x-` で始まる unit_id で経路をまとめず、probe を名指すのにも使わず、セッションをまたいで持つもの（たとえば口の link の速さの記録）の鍵にも使わない。同じ口の別の個体が何も引き継がないように。

**変わること:** probe は固有の番号の無いプラットフォームで unit_id を出さず（Oep.h:478）、「必須」に反している。`x-` の値を出すようにする。host: 検査が 1 つ。

**答え。** WireSkein は、client の速さの記録（口 + unit_id が鍵）で、`x-` の unit_id をどの個体も指さないものとして扱うよう求めた。上の文に入れた。

### C-25 ○ 排他で開く、HID の output、WinUSB

**状態: 合意.**

**案の文**（core §3.3 に足す）:

> - host は、OS が許す限り、シリアルの口と HID を排他で開く（Linux では tty に TIOCEXCL）。
> - HID を出す probe は、output の report を interrupt OUT の endpoint からも SET_REPORT（Output）からも受ける。
> - vendor bulk を出す probe は、その interface に Microsoft OS 2.0 の compatible ID `WINUSB` を付けるべきである（SHOULD）。

**変わること:** Python はすでに排他で開いている（flock と TIOCEXCL）。probe の HID と WinUSB は未確認。

**Q28.** WinUSB は SHOULD（勧め）か MUST か。無いと、Windows の利用者は driver を入れる必要がある。

### C-29 ○ registry のキーと hash

**状態: 合意.**

**案の文**（core §0、registry の文の後ろ）:

> 凍結の後、registry のキー（したがって生成物の識別子）は名前を変えず、足すだけにする。REGISTRY_HASH は生成物が registry と合っているかを表すだけで、線の互換については何も言わない。仕様の値でないもの（max_op_ms_reference）は、凍結の外の `[reference]` の表に置く。

**変わること:** 線の上ではなし。

### C-30 ○ instance は (name, revision) ごと

**状態: 合意.**

**案の文**（core §7.2。「同じ名前のものは fn の昇順に 0 から振る」と差し替える）:

> 同じ (name, revision) のインターフェースを、fn の昇順に 0 から振る。

**変わること:** 今はなし。どの probe も、1 つの名前に 1 つの revision しか出していない。

### C-32 ○ port_speed: baud の誤差と verify_ms 0

**状態: 条件付き合意** — ch32rv: verify_ms 0 を malformed にするのは step 0（try）だけ（反映済み）.

**案の文**（core §3.5 の断り方）:

> UART が作れるいちばん近い速さが要求と 2 % を超えて違えば rejected unsupported。応答の baud は実際に掛けた速さ。step 0（try）の verify_ms 0 は rejected malformed。step 1（commit）と step 2（revert）では verify_ms に意味は無く、どの値も受ける。

**変わること:** probe: 作れるかどうかはプラットフォームごとの処理が決める（その誤差は未確認）。try の verify_ms 0 は今は受けて、すぐに戻る。fake: 未確認。

**答え。** ch32rv は commit と revert で verify_ms 0 を送る。その条件「malformed は step 0（try）だけ」を上に入れた。

**Q29.** ±2 % でよいか。勧め: これでよい。両端が ±2 % なら、合わせても 8N1 の読み取りが許す範囲に入る。

### C-33 ○ ハートビートの下限

**状態: 合意.**

**案の文**（core §11.3）: 「probe は、100 ms より短いハートビートの周期を 100 ms に切り上げてよい」。
**変わること:** 要るものはなし（probe に下限は無く、それでも適合する）。

---

## 12. コンソールの dmseq

突き合わせたもの: `docs/target-console-dmseq.md`（cdd26b4）、`experiments/dm-console-seq/DmSeqTest/DmSeq.h`（2026-09-24 の実験）、出荷している target のライブラリ ArduinoCore-CH32RV の `libraries/SerialDMSeq`（このリポジトリの外）、probe の `src/OepDmConsole.cpp`。

### DS-1 ★ DATA0 = 0 は答えではない

**状態: 合意.**

**問題。** target の規則 1 では 0 の語は無効な答え（CRC が合わない）なので、target はすぐに出し直す。debugger の項は、target は 0 を沈黙と読み、時間切れまで待つと言う。2 つの実装も違う:
- 実験は、読むたびにすぐ出し直す。
- 出荷しているライブラリは 0 を「答えが無い」とする。20 ms ごとに出し直すのは時間切れの後だけで、それまでは待ちを使い切る（host が一度答えた後なら 1 s まで）。

**案の文**（target の規則。規則 1 の前に新しい項）:

> **0 の語は答えではない。** DATA0 が 0 を読む間、target は答えを待ち続け（待ち時間は進む）、短い待ちごとに自分のフレームを出し直す。0 を規則 1 では扱わない。

debugger の項は DS-9 に合わせて変える。

**変わること:** 出荷しているライブラリ: 時間切れの前も、短い待ちの時計で出し直す（今は時間切れの後だけ）。実験: 任意。probe: なし（bit 7 = 0 を「まだ何も無い」と読む）。

**Q30（ch32rv）.** 短い待ちごとに出し直す（勧め）か、すぐ（実験）か、出し直さない（時間切れの前のライブラリ）か。すぐ出し直すと、debugger のつながっていない target で読むたびに書き込みが 1 回要る（ライブラリの理由）。出し直さないと、debugger が DATA0 を消した後、コンソールが最大 1 s 止まる。

**答え。** 短い待ちごとに出し直す、を採る。ch32rv もそれを好む: その host は bit 7 = 0（0 を含む）を「まだ何も無い」と読んで 2 ms ごとに読み、その DM の操作で DATA0 = 0 が残りうる。bench と WireSkein: 異議なし。DS-8 はこれに頼る。

### DS-2 ★ 持ち主の規則に target の例外を書く

**状態: 合意.**

**案の文**（郵便受けと持ち主。3 つの項と差し替える）:

> - target が DATA0 / DATA1 に書くのは次のときだけ:
>   (a) begin() のとき（DS-6）。
>   (b) DATA0 の bit 7 が 0 のときにフレームを出す。
>   (c) まだ答えの無い自分のフレームを出し直す: 規則 0（bit 7 が 1 だが自分が出した語ではない）、規則 1、時間切れのとき、フレームを出し続ける間、DS-1。
> - host が書くのは bit 7 が 1 のとき（target のフレームがある）だけ。
> - target 自身のフレームでない bit 7 = 1 の語に (c) で書く場合を除き、どちらの側も相手が書いた語を上書きしない。

**変わること:** なし（文だけ）。

### DS-3 ★ 待ち時間は実時間の下限

**状態: 合意.**

**案の文**（時間切れ。「割り込みを止めていても待ちが終わるよう、時計でなくレジスタを読む回数で数える」と差し替える）:

> 短い待ちは実時間で**少なくとも 20 ms**、長い待ちは**少なくとも 1 s**。target は、割り込みを止めていても終わる方法でそれを測る。「短い待ちごとに」（フレームを出し続けること、DS-1）も同じ測り方を使う。（参考）DATA0 を読む回数で数えるとき、参照の target は、読みの 1 回が少なくとも 8 cycle かかるとして、1 ms あたり F_CPU / 8000 回を使っている。

**変わること:** なし。host が頼るのは「1 秒に 1 回以上読む同期した host は何も失わない」だけ。

### DS-4 ★ byte の順

**状態: 合意.**

**案の文**（target のフレームに足す）:

> DATA0 の byte k（k = 0〜3）はレジスタの bit 8k〜8k+7（byte0 がいちばん下の byte）。DATA1 の byte k は DATA1 の bit 8k〜8k+7 で、payload の byte 3+k を運ぶ。例: S = 0、A = 1 の空の SYN のフレームは byte0 が 0x98、CRC が 0x32 で、DATA0 = 0x00003298。K = 0、H = 0、M = 0 の host の答えは DATA0 = 0x0000F300。

**変わること:** なし。3 つの実装（実験、ライブラリ、probe）とも、この形で語を組んでいる。

### DS-5 ○ 無効な語の数を何が 0 に戻すか

**状態: 合意.**

**案の文**（host の規則 1 に足す）:

> host は、bit 7 = 1 の無効な語（`0xffffffff` を含む）を読んだ読みが続いた数を数える。正しいフレームを読んだとき、この規則で答えた後、セッションを始めたときに 0 に戻す。bit 7 = 0 の語を読んだ読みでは数を変えない。規則 1 の答えは、host が同期している間だけ送る。同期していない間は、数は 3 で止まり（回り込まない）、host は答えない。次の正しいフレームで host は同期し、数は 0 に戻る。

**変わること:** probe: 案のとおり（OepDmConsole.cpp:195-204）。ただし `start()` が `seq_bad_run_` を 0 に戻していないので、足す。同期していない間に数が止まるかも確かめる（未確認）。

**答え。** ch32rv は適合していて、その host の細部を答えた。上に入れた: 数は正しいフレーム、規則 1 の答えの後、セッションの始めに 0 に戻る。規則 1 の答えは同期しているときだけで、同期していない間は数が止まる。同期していない `0xffffffff` は残り物の数に入る。それは DS-8 の保険が使う数で、保険が無くなれば（DS-8）、その語は上の数の無効な語の 1 つになるだけ。

### DS-6 ○ begin() のときの target の状態

**状態: 合意.**

**案の文**（target のフレームに足す）:

> begin() のとき、target は SYN を立て、DATA0 に 0 を書いてよい。S と A はどの値から始めてもよい（host は SYN で同期し直す、host の規則 3）。（参考）参照の target は S = 0、A = 1 で始め、DATA0 = 0 を書く。

**変わること:** なし（実験もライブラリも S = 0、A = 1、DATA0 := 0）。

### DS-7 ○ 「長く読んでも」

**状態: 合意.**

**案の文**（host の最後の項と差し替える）:

> （参考）印字するか入力を見る target は、少なくとも「長い待ち + 短い待ち」ごとに 1 回フレームを出す。同期していない間に 3 s 正しいフレームを読まなかった host は、dmseq のコンソールが答えていないと利用者に伝えてよい。印字も読みもしない target は何も出さないので、これはコンソールが無いことの証にはならない。

**変わること:** なし（probe はこれを知らせていない）。

### DS-8 ★ host の任意の保険を消す

**状態: 条件付き合意** — ch32rv: DS-1 と同時にだけ削る（反映済み）.

**問題。** 「同期していない host は `0xffffffff` を 3 回読んだら bit 7 = 0 の無効な語を書いてよい」の項は、規則 0 を持たない target のためにあり、規則 0 は必須。しかもこれは、bit 7 が 1 の間に、答えるためでない理由で host に書かせるただ 1 つの規則。

**案の文:** 「host（任意）: ……」の項を、**DS-1 と同じ変更で**消す。DS-1 より前には消さない。

**変わること。**
- ch32rv: **その host はこの語を書いている**（初版を正す）。同期していない host が `0xffffffff` を 3 回読むと 0x7f7f7f7f を書く。WCH-Link の attach が、いくつかの target で DATA0 に ESIG の最後の語を残すため。target のライブラリが短い待ちごとに出し直すようになったら（DS-1）、ch32rv はこの書き込みをやめる。
- probe: なし（0x7f7f7f7f の道は無い）。
- target のライブラリ: DS-8 そのものではなし。規則 0 を持ち（SerialDMSeq.cpp:127-141）、DS-1 で短い待ちごとに出し直すようになる。2026-09-24 の実験はどちらも持たないが、それは記録で、誰も出荷していない。

**答え。** ch32rv の条件: target がいつも出し直す（DS-1）ときだけ保険を消す。採った: DS-1 と DS-8 は一緒に入れる。

### DS-9 ○ dmactive を下ろすと DATA0 が 0 に戻る*ことがある*

**状態: 合意.**

**案の文**（debugger の項）:

> **detach のときに debug module をリセットしない**（DMCONTROL.dmactive を下ろさない）。下ろすと DATA0 と DATA1 が 0 に戻ることがあり、そのとき target が出していたフレームは失われる。target は短い待ちのうちに出し直す（DS-1）。

**変わること:** なし。一般の言い方は 1 つの target の系統でしか確かめていない（記録にそう残す）。

### DS-10 ○ CRC-8 の確かめ値

**状態: 合意.**

**案の文**（CRC-8 に足す）:

> 確かめ値: ASCII の 9 byte "123456789" → 0xFB。1 byte の 0x00 → 0xF3。

**確かめた:** 多項式 0x07、初期値 0xFF、反転なし、最後の XOR なしの bit ごとの実装で、どちらの値も計算した。probe の `seqCrc8` やライブラリの 16 項目の表の形と同じ関数。DS-4 の例も同じ計算から出した。

**Q31.** DS-3〜DS-10 はどれも線の上を変えない。ch32rv: host の側（自分で dmseq を読むなら）が DS-4 と DS-5 に合っているか確かめてほしい。

**答え。** ch32rv: DS-4 に合っている。DS-5 も合っていて、細部は DS-5 に入れた。bench と WireSkein: 異議なし。

---

## 外した指摘

| 指摘 | 外した理由 |
|---|---|
| P2-○7「未定義の値: コンソールとキャプチャも fixture のように malformed にする」 | C-02 で逆になった。コンソールとキャプチャの unsupported が正しく、fixture のほうをそれに合わせる |
| P2-○12 凍結の前の io_voltage の describe の tag | 任意の describe の tag は、凍結の後でも revision を変えずに足せる（core §2.7）。今直すことは無く、番号は level shifter を持つ probe と一緒に決めるほうがよい |
| P2-★1 の label の付いた channel を外す部分 | 利用者は scan したい debug のピンにこそ label を付けるので、外すと target が見えなくなる |
| PC-3 の「idle の mode ≥ 5 は malformed」 | C-02（unsupported）に置き換えた |
| C-06 の「前の応答の大きさを足す」 | 1 つ前の応答から待ちを数え始める形に置き換えた。そのほうが簡単で、ちょうど合う |
| C-11 | ユーザーが決めた（変えない） |

## 確かめる途中で見つけた実装の誤り（似た仕組みの確かめ）

どれも**今の**文に対する誤りで、peers の判断は要らない。

| 場所 | 何か |
|---|---|
| probe Oep.h:478 | 固有の番号の無いプラットフォームで unit_id（必須）を出さない（C-24） |
| probe OepCh32Dm.cpp:79、145、451、OepDmConsole.cpp:48 | op とコンソールが DMSTATUS.version == 2 を求める。1.0 の DM は見つかるが、止まったとは扱われない（P2-○1） |
| probe OepRvswdPhy.cpp:207-213、OepTarget.cpp:128-140 | connection が閉じた後、idle_clock low の RVSWD は SWCLK を駆動し続ける。idle の無い channel は PHY の状態のまま。core §8（「放したピンを自分の駆動のまま残さない」）に反する |
| probe の scan | 試したピンを空きの状態に戻さず Hi-Z のままにする（debug §1） |
| probe OepTarget.cpp:335、OepCh32Dm.cpp:41-46 | rvswd / swio の scan が attach をまるごと走らせる（wake、設定、dmactive、ABSTRACTAUTO、PROGBUF0 への 256 回の書き込み）。dmactive だけでない（debug §1、P2-★8） |
| probe OepCapture.cpp:466-475、OepSampler.cpp:193-202 | ロジックのキャプチャがピンを入力に替え、戻さない（P2-○13） |
| probe OepP4SpiTarget.cpp:22 | 宣言の外の channel を unsupported でなく unavailable で断る（core §8 の plan_apply の表） |
| probe OepConfig.cpp:261 | idle の unsupported が、受け取ったままの項目の tag でなく 0x00 を運ぶ（probe-config §1、9ed53e7） |
| probe OepTarget.cpp:243、410 | attach の unsupported がいつも `pins | 0x80` を運び、受け取ったままの tag でない |
| fake endpoint.py:454-455 | 経路の並びを TLV の順で作り、index の byte を見ない |
| Python link.py:422、550 | 立て直しの confirm が範囲 0..0xFF を送る（C-15） |
| JS link.js | 長さつきのフレームの口で、confirm による立て直しが無い（core §5.1） |
| Rust（ch32rv。ch32rv の報告） | single_serial が、kind の byte を読まずに TLV transport の値を平らに読んでいた。ch32rv の手元で直した |
