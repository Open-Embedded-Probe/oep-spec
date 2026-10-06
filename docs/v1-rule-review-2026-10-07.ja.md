# v1 の規則の見直し: 残すか、簡単にするか、外すか（2026-10-07）

Status: **proposal**（非規範）。利用者の判断を待つ。規則を変える項目は、利用者が選んだ後、決まりどおり ch32rv、WireSkein、bench に先に送る。言葉だけの直し（§3）は peers に回さずに入れてよい。

元にしたもの: 規範の文書を 4 つに分けて全部の規則を 1 行ずつ判定した見直し（core と経路、debug と common、console と dmseq と capture、fixture と probe-config と link と plan と restart）と、待っている提案（[v1-pending-proposals-2026-10-07](v1-pending-proposals-2026-10-07.ja.md) の Q1〜Q9、[v1-debug-link-proposal-2026-10-06](v1-debug-link-proposal-2026-10-06.ja.md) の P1〜P4）。前に決めたことは [凍結前の決定](v1-freeze-decisions.ja.md)、[ゼロベース再検討](v1-zero-base-proposal.ja.md)、[案と決めた経緯](v1-open-proposals.ja.md)、[規則の変更の提案 10-02](v1-rule-change-proposal-2026-10-02.ja.md) / [10-06](v1-rule-change-proposal-2026-10-06.ja.md)、[単純化の提案](v1-simplification-proposal-2026-10-06.ja.md)、[構成の見直し](v1-structure-proposal-2026-10-06.ja.md) で調べた。

## 0. 基準

- 規則（MUST）に残すのは、それが無いと、独立に書いた host と probe が通じないか、相手が気づけず防げない形で target やデータを害するものだけ。
- それ以外は、使い方と実装のガイドの注、参照 probe の実装の限界の文書（oep-probe-arduino に置く）のどちらかへ移すか、消す。
- 凍結の前なので、互換の手当ては考えない（番号と形は変えてよい）。

## 1. 判定の数

各見直しの表の行の数（1 行に 2 つの判定があるものは前の方で数えた。概数）。

| 文書 | keep | simplify | guide | impl-limits | delete | 計 |
|---|---:|---:|---:|---:|---:|---:|
| core | 112 | 25 | 15 | 0 | 46 | 198 |
| transports | 38 | 6 | 8 | 2 | 7 | 61 |
| registry（core と経路の分） | 17 | 0 | 0 | 2 | 12 | 31 |
| common | 29 | 2 | 1 | 0 | 7 | 39 |
| debug | 105 | 22 | 9 | 12 | 40 | 188 |
| console | 34 | 6 | 0 | 1 | 12 | 53 |
| dmseq | 20 | 3 | 0 | 0 | 8 | 31 |
| capture（logic、analog、capture-group） | 57 | 14 | 2 | 1 | 20 | 94 |
| registry（console と capture の分） | 6 | 2 | 0 | 0 | 10 | 18 |
| link | 17 | 6 | 1 | 0 | 16 | 40 |
| plan | 11 | 1 | 1 | 0 | 2 | 15 |
| restart | 7 | 1 | 2 | 0 | 3 | 13 |
| fixture（gpio、uart、i2c-target、spi-target） | 36 | 11 | 1 | 1 | 13 | 62 |
| probe-config | 49 | 12 | 3 | 0 | 17 | 81 |
| **計** | **538** | **111** | **43** | **19** | **213** | **924** |

delete の多くは言い直しと理由の文で、規則は変わらない（§3）。規則が変わるものを §2 にまとめた。

## 2. 利用者に決めてもらうこと

前の決定の印:
- 〔利用者〕 前に利用者が決めた（または「案のとおり」で採った）。**変えるには、はっきり決め直してもらう必要がある。**
- 〔peers〕 peers（ch32rv、WireSkein、bench）の合意で入れた。利用者が個別に選んだものではないが、変えるなら peers に戻す。
- 〔なし〕 v1 の最初の設計から続いているだけで、はっきり決めた記録が無い。

簡単になる量が大きいものから並べた。

### 2.1 大きいもの

**1. ignored の TLV を無くす** 〔peers: 上限 16 個と「落とさない」は C-04（2026-10-02）。仕組みは v1 の最初の設計〕
- 今: 知らない非 critical の TLV は無視し、応答の後ろに ignored（0x7F、16 個まで、溢れは 0x00）を付ける。probe は応答に 19 byte を空けておく。要求の 0x7F / 0xFF は malformed。
- 案: 「知らない非 critical の TLV は無視する」だけ。0x7F と 0xFF は特別な tag でなくなる（0x00 を tag にしない、は残す）。
- 得: core の規則 6 つほど、registry の `tag_ignored`、`tag_invalid`、`ignored_max_entries`。link の source の長さの式と debug の block の余白から 19 byte が消える（`link_source_overhead_bytes` 26 → 7、`block_frame_overhead_bytes` 24 → 5）。probe-config の「長い項目は無視して ignored」、gpio の drive の「無視する」の道も要らなくなる。
- 失: host は、非 critical の TLV が効いたかを応答から知れない。効かないと困る項目は今も critical で送るので、困るのは「効いたかを見せたいだけ」の host。
- 壊れる: vectors（headers、ops、refusals）、tools/oepvectors1.py、tests/uart_binding、client、probe、ch32rv のブローカー。

**2. probe の中の時間と回数を規範から外し、待ちは max_op_ms にまとめる** 〔peers: P2-★4（要求ごと 200 ms、線切れ 1000 ms、attach 1000 ms、scan 500 ms、2026-10-02）。〔利用者〕: 規範に残っていた未決の数（DMI busy / SWD WAIT 100 回、reset の待ち 100 ms / 1 回）を数で決めた（open-proposals §9、f50c937）〕
- 今: registry の limits 13 項目（`wire_retry_ms`、`wire_lost_ms`、`attach_budget_ms`、`scan_budget_ms`、`scan_tried_max`、`reset_settle_ms`、`dm_wait_ms`、`dmi_busy_retries`、`reset_wait_ms`、`reset_retries`、`swd_wait_retries`、`block_frame_overhead_bytes`、`tar_rewrite_bytes`）。host はこれらを足して待ちを計算する。
- 案: 「attach、scan、riscv-dm の reset の引数の時間（core §4.4）は max_op_ms」の 1 文。再試行を使い切ったときの status（line、wait、timeout）と、「リセットの線を離した後、DM が答えるまで待つ（max_op_ms まで）、答えなければ status line、connection は保つ」は残す。値は実装の限界の文書へ。
- 得: host の待ちの計算が 1 通りになる。conformance の時間の項と registry の 13 項目が消える。
- 失: 応答が失われたときだけ host の待ちが長くなる（参照 probe の attach で約 2 s が、max_op_ms 10 s + 1 s に）。probe ごとに諦めるまでの時間が違ってよくなる。
- 壊れる: oep-client-python の riscv.py と endpoint.py の待ち、oep-client-js、probe の定数の名前、glossary、security、conformance。

**3. 断り方の順の 4〜8 を「1 つを選ぶ」に** 〔利用者: ゼロベース再検討 3.6（2026-10-01 に採用）。値の扱いは C-02（peers）〕
- 今: core §4.3 が、見出し → 送り直しの表 → セッション → window → malformed → unsupported → unavailable … の順と、「矛盾と定義されていない値」の段落、payload の中の fn に unknown_function を流用することを決める。インターフェースの文書も「ロックの断りの順」を書き直している。
- 案: 順 1〜3（見出し、送り直しの表、セッション）だけ残す。あとは「書式、対応、状態の確かめは何も変える前に行い、当たった理由のどれか 1 つで断る」。
- 得: 本体でいちばん細かい規定と、インターフェースごとの断り方の表（probe-config §2 など）との食い違いの元が消える。
- 失: 理由が 2 つ当たる要求の答えが probe によって違いうる。host はどれでも「直すか諦める」なので動きは同じ。
- 壊れる: vectors の refusals（1 つの答えに決められない組は「どれか」を受ける形に）。

**4. probe.config のスロットの錠を無くす** 〔利用者: 錠の置き場所は凍結前の決定 1（2026-09-30）、長さの規則はゼロベース 3.7e。錠そのものは 2026-09-26 の移植性レビューで入った〕
- 今: slot に lock_len、scheme、mask、value。probe は attach した target の target_id と照らし、合わなければ slot_state 2 / 3。
- 案: 錠を消す。照合は host が connections の target_id でする。slot_state は 0（接続あり）と 1（いない）だけ。
- 得: slot の項目の後半、slot_state 2 / 3、state の tid、registry の `target_id_len`（使うのは錠だけ）が消える。
- 失: 保存した設定の at boot の attach が、違う target にもつながり、コンソールの読みを始める。host が確かめるまで、別の target の出力がストリームに流れる。
- 壊れる: probe-config §1.1 / §3.2 / §3.3、debug の 2 か所の参照、client の設定の dataclass、bench の設定。

**5. boot_reset（リセットでのやり直し）を無くす** 〔利用者: 2026-10-02 に「多くの利用者が要るもの」の基準で、任意の機能として採った（open-proposals §10）〕
- 案: boot_reset、slot_state の reset_at_ns、`slot_retry_reset_hold_ms`、probe が nrst の label を使うこと、§3.1 の条件の一覧を消す。nrst / power_hi / power_lo の名前の決まり（host が使う）は残す。
- 得: probe が自分の判断でリセットの線を動かす唯一の道と、その条件（status line のときだけ、1 起動に 1 回、ロックの前だけ）が消える。
- 失: host の無い治具で、線の応答が無い target を probe が自力で立て直せない。host が reset TLV つきの attach をする。

**6. bind の mode（last-reset / manual / mixed）を無くす** 〔2026-09-29 に ArduinoCore-CH32、ch32rv と決めた形（89879bc）。利用者の個別の選択の記録は見つからない〕
- 案: bind は port、kind、id の 1 本。替えるときは host が set し直す。セッションの間は進めず、終わったら止めた位置から続ける（あふれていれば一番古いバイトから）。
- 得: mode、selected、並び、mixed の書式（行、128 byte / 100 ms、`[name] `、`]` の置き換え）、「host の reset として数えるもの」、describe の bind_modes、bind_state の 2 つのフィールドが消える。
- 失: 1 つのシリアルの口で複数の target の出力を混ぜて見る使い方と、最後にリセットした target へ自動で切り替わる使い方ができなくなる。

**7. port_speed を握手だけにする** 〔利用者: 既定の上限 500000（義務 7、32260e5、ch32rv と合意）、port_speed の形（open-proposals §9）、oep.link に移す（単純化 D3）。idle の上限 3 s は 877cf01〕
- 今: host の義務 1〜8、戻る条件 1〜5、port と idle_ms のフィールド、「壊れ」「候補」「流し方」の定義。
- 案: 残すのは 3 つの状態と切り替えの時刻、戻る条件 1（試しのまま verify_ms）、3（決めた後、正常なフレームが `port_speed_idle_max_ms` 来ない）、5（セッションの終わり）、義務 2（応答の後 `port_speed_switch_wait_ms` 以上待ってから新しい速さで送る。confirm でなくてよい）、義務 6。port と idle_ms のフィールドを消す（別の口で試すは unavailable cause 6）。戻る条件 2 / 4、義務 1 / 3 / 4 / 5 / 8 を消し、**義務 7（500000 の上限と 1 秒の確かめ）は host ガイドへ**。±2 % を registry に `port_speed_tolerance_pct` として足す。
- 得: link の規則が約半分。Q8 の取り違え（上げた速さの待ちのうちに idle が切れる）の元の idle_ms が消える。`port_speed_broken_max`、`port_speed_confirm_extra_ms` が消える。
- 失: 500000 を超えないことが規範の保証でなくなる（host の選び方になる。黙った破壊は CRC が防ぐ）。戻る条件 4 を消すと、壊れが続く間 probe は 3 s の沈黙まで戻らない。
- 壊れる: link の vectors、client の speed、ch32rv のブローカー、bench、host ガイド §17（「義務 7 は規範」の文）。

**8. describe の宣言を減らす** 〔一部〔利用者〕: chip / model の文字列（凍結前の決定 10）、discoverable（ゼロベース 7.1-12）、mode の background（P2-★6、peers）。console の send_queue は peers（f0c68bf）〕
- 消すもの: core の implementation、reserved、profile、resets_on_open、discoverable、chip、model の文字の規則と `model_max_bytes`。console の send_queue と最小 64。capture の rate_list、rate_limit、max_read、segment_ring、frontend_shared、mode の background、channels の layout の候補。capture-group の max_tracks、budget、start_skew。
- 残すもの: host が引数を決めるか断りを避けるのに読むもの（ops、channels、label、transport、max_op_ms、unit_id、firmware、mechanisms、rate_range、trigger、frontend、tracks など）。
- 得: 誰も分岐しない宣言と、その値の規則が 20 ほど消える。
- 失: 表示の手がかり（どの channel が probe 自身のものか、どの速さが選べるか、どのチップか）。host は試して断りで知る。WireSkein は記録に入れる chip を capture 自身の TLV か firmware の文字列から取る。
- 壊れる: registry の tag（予約に）、restart と probe-config の reserved への参照、vectors（discovery）、client の capture.py と console.py、WireSkein。

**9. corr_reused と CRC-32 を無くす** 〔利用者: 重複排除の形（open-proposals 4、2026-09-26 に案のとおり）。corr_reused は v1 の最初の設計〕
- 今: 同じ corr で中身が違う要求は rejected corr_reused。そのため送り直しの表は (corr、fn、op、要求の CRC-32、応答) を持つ。
- 案: 表は (corr、応答)。同じ corr は送り直しとして、覚えた応答を返す。
- 得: reason 1 つ、core の CRC-32 の定義、判定の 1 行。
- 失: host のバグ（corr の使い回し）が、別の要求の応答を受ける形で現れる（今は断りで見える）。正しい host には起きない。
- 壊れる: reason 0x0D は予約に。vectors（sessions、refusals）、client、probe、ch32rv のブローカーの表。

**10. list の prefix と exact を無くす** 〔なし（v1 の最初の設計）〕
- 案: list は first からの全件のページングだけ。host が自分で絞る。
- 得: label の境界で比べる規則、exact、`oep.` の例外が消える。
- 失: 一覧の長い probe では往復が増える（参照 probe は十数件で 1〜2 フレーム）。
- 壊れる: vectors（discovery）、oepvectors1 / oepgen1、client、ch32rv のブローカー、getting-started。

### 2.2 中くらいのもの

**11. i2c-target の mode を無くす** 〔利用者: i2c-target / spi-target を標準にする（凍結前の決定 7 ★）。細目の pullup_ohms は P2-★3（peers）〕
- 案: 「データのある書き込みのトランザクション 1 回 = 1 フレーム（max_length を超えた分は捨てて errors + 1）」「読み出しには先置きの置き場から、空なら 0xFF」の 1 つの形。mode 1 / 2 / 3、arm_rx、reset、stretch と max_stretch_us、pullup_ohms、preload_tx の応答の slots、status の mode / armed を消す。spi-target の reset と、errors の数えすぎ（転送 1 回につき + 1 に）も。
- 得: i2c-target の規則が約半分。
- 失: 長さつきのフレームを probe が区切る使い方は host の解釈になる。clock stretch で target を待たせる試験はできなくなる（後の revision で足す）。プルアップの抵抗の目安が分からない（内蔵プルアップの有無の bit は残る）。

**12. gpio の drive を段の番号だけにする** 〔利用者: 2026-10-02 に任意の機能として採った（open-proposals §11）。kind 1（mA 以下の最も強い段）と read の drive は、そのときの peers の条件〕
- 案: drive は段の番号（u8、0xFF = 既定）。範囲外や drive_levels を宣言しない probe は unsupported（無視しない）。read の drive を消す。probe-config の idle の項目の強さも u8 1 つ（項目 4 byte）。gpio の mode 7（両方のプル）も消す。
- 得: kind の enum、drive_read の enum、無視の道が消える。
- 失: SoC をまたいで同じ治具のファイルを使うための「mA 以下の段」が消え、host が drive_levels から段を選ぶ。効いている強さを probe から読む道（peers の条件だった）が無くなる。

**13. 設定の hash を「変われば変わる u32」にする** 〔利用者: ゼロベース 3.7b（2026-10-01 に採用）〕
- 今: hash は正規形（tag、キーの昇順、critical を外す）の CRC-32。host も計算できる。
- 案: 作り方は probe が決める。host は計算しない。get の順（tag、キーの昇順）は残す。`max_bytes` は「項目の TLV の byte 数の合計」。
- 得: 正規形を両側で作る規則と、probe_config_hash.json のベクタが消える。仕様から CRC-32 が消える（9 と合わせて）。
- 失: 手元の設定ファイルと probe の中身が同じかを hash だけでは判断できない（get で読み比べる）。host ガイド §15 の「hash で比べ、違うときだけ save」が使えない。

**14. holder_fn と holder_kind を無くす** 〔利用者: unavailable の payload（凍結前の決定 4、2026-09-30）〕
- 案: unavailable の payload は cause と channel（と capture-group の fn）だけ。
- 得: enum 1 つと TLV 2 つ、各文書の「cause 5 / holder_kind 7」の書き分けが消える。
- 失: cause 5（設定が持つ）のとき、disable か idle かは host が probe.config の get で調べる。どの plan や接続が持っているかの表示が粗くなる。

**15. restart の host の手順を host ガイドへ** 〔構成の見直し（2026-10-06）で「中継する host は restart をほかのロックの要る op と同じに中継する」を ch32rv の条件として残した〕
- 案: §3（閉じて 100 ms 待つ、confirm を繰り返す、過ぎたら無くなったものとする、中継する host）と `restart_after_answer_ms` を消す。規範は「応答が先、その後どの経路にも答えない、target を reset しない、restart_max_ms のうちに同じ経路で confirm に答える」。
- 得: Q7 が問いごと消える。
- 失: ch32rv が残すよう求めた中継の 1 文が消える（ch32rv の同意が要る）。

**16. ピンの無い wire、attach_writes_unbounded、2 本でない wire の形を消す** 〔peers: P2-★7、P2-★8（2026-10-02）。attach_writes_unbounded は ch32rv が求めた〕
- 得: debug §0 の 2 段落、§1 の 1 項、registry の features 3 節。
- 失: 別のデバッガを通して target を動かす probe を作る人は、その形を自分の文書で決める。ch32rv がその形を使う予定があるなら困る（確かめが要る）。

**17. console の 20 ms を順序の規則にする** 〔peers: console §3 の規則は 10-02 の提案で入った。値の名前 `console_dmstatus_poll_ms` は 5d02a6f〕
- 今: 要求の実行中と hart が止まっている間は読まない。止まっているかは DMSTATUS を 20 ms 以下の間隔で見る。
- 案（文）: 「probe は、その connection の riscv-dm の要求を実行している間と、hart が止まっている間（DMSTATUS の anyhalted が 1）は、コンソールのために DATA0 / DATA1 を読み書きしない。probe は、その connection の riscv-dm の要求に答えた後、次にコンソールのために DATA0 を読む前に DMSTATUS を読む。hart がまた走れば、probe は読みを再開する。」
- 得: 20 ms と registry の値が消える。今の規則に残る窓（host が raw の dmi で止めた直後、20 ms までは読みうる）が閉じる。Q9 も問いごと消える。
- 失: probe は要求の後に DMSTATUS を 1 回多く読む。止まっている間に再開を見つける間隔は実装まかせになる。

**18. riscv-dm の reset の method と、応答の flags bit2 / bit3 / attempts を消す** 〔peers: ○2（2026-10-06、method 0 は ndmreset）〕
- 案: 応答は `status、flags（bit0 / bit1）、pc`（形が変わる）。やり直しの方針は実装まかせ。
- 失: やり直したか、確認の halt / resume が失敗したかを host が見られない（今の host はこれで動きを変えていない）。

**19. dmseq の host の義務を減らす** 〔peers: DS-5、DS-8（2026-10-02）〕
- 案: host 規則 1 の「無効な語が 3 回続き、同期していれば K = last_s、M = 0 で答える」と数え方の段落、host 向けの「切り離しで DM を reset しない」「止めて抽象コマンドを使ったら DATA0 / DATA1 を書き戻す」を消す。target の規則 0 と「0 の語」の規則で target が自分で戻る。空フレームの「暇なときだけ」も外す。
- 失: 規則 0 を持たない target は戻りが遅れる（凍結前なので考えない）。ch32rv の host は 0x7f7f7f7f を書く処理を持っている（消してよいかの確認）。

### 2.3 小さいもの（まとめて可否を）

**20. capture の configure の応答の目安** 〔なし〕: timing は jitter_ns だけ（jitter_kind を消す）。rate_accuracy、frontend_used を消す。reference（電源基準の ADC の電圧）は残す。WireSkein の記録から精度の目安が無くなる。

**21. 「bit 7 によらず critical として扱う TLV」の例外を消す** 〔なし〕: capture §3.3 / §4.1 の例外と、plan の role_assignment（0x90）、uart の format の「critical で送る」を消す。critical の規則は core §2.3 の 1 通り（効かないと意味が無い項目は host が critical で送る）。

**22. search_retries の数え方を消す** 〔peers: Q6（2026-10-02）〕: TLV は残し「数え方は実装が決める。診断用」とだけ書く。

**23. target_id_scheme の値の名前 `wch_dmi_7f`** 〔なし〕: registry の名前にベンダー名が入っている。何を読んだかの名前（例 `dmi_7f`、DMI 0x7F の値）に変える。値（1）は変えない。生成物の定数名を使う client と probe が追う。4 で錠を消しても、connections の tid と attach の target_id で使う。

**24. 予約と未来の話を本文から消す** 〔利用者: 凍結前の決定 §0.3 / 11 で「予約のまま凍結」（長い操作、op 0x04、address_hi、reset の method 2）〕: core §10、ロックを持たない購読の予約、§2.5 の実験用の値、debug の op 0x04、address_hi（riscv-dm と arm-adi の 4 か所）、走ったままの読み、RV64。番号の空きは registry の reserved だけで守る。

**25. 端の場合の断りを消す** 〔一部 peers: C-03（tag の繰り返し）〕: 真偽値の 0 / 1 以外、要求の text の不正、繰り返さない tag の重複、describe の要求の TLV、common の read の from 3 で arg > 0xFF、write の count 0、run の timeout_ms 0、count > 0 の scan の skip を、malformed と決める規則を消す。受け手の読み方（非 0 を真、最初を使う）だけ残す。壊れた host の要求を probe が通しうるが、どれも害の無い値。

**26. ほかの小さな規則** 
- 資源の番号の再利用: 「直近 1024 個を使わない、失敗した作成は番号を消費しない」→「+1 で進め、使用中の番号は飛ばす」〔利用者: 1024 は open-proposals §9〕。
- ops の符号化: 規則 1〜4 と「満たさなければ fn を使わない」→「base(u8)、bitmap。op 0xFF を越えない」〔利用者と peers: 構成の見直し §4（c475dad）。正規形の強制をやめる〕。
- max_op_ms が 0 か上限超えなら probe を使わない、confirm の値が範囲外なら経路を使わない、を消す〔なし〕。
- lease を「表からの返し直しでは数え直さない」例外、owner の「session_id を返さない」を消す〔なし〕。
- uart の status の configured を消す（baud と format だけ）〔なし〕。
- probe-config の断り方の表を消し、起動の順を「ほかのどの項目より先に idle を掛ける」だけに〔利用者: 起動の順は open-proposals §10 / §11〕。長さが定義と違う項目は malformed（無視しない）。
- §7.6 のアドレス `oep://<unit_id>[/<slot>]` と `name#instance` の表記を host ガイドへ〔利用者: アドレスを unit_id にすることは凍結前の決定 3(a) ★。中身は変えず置き場だけ変わるので、確かめだけ。probe-config が label の既定に `name#instance` を使うので、その表記は probe-config に移す〕。

### 2.4 待っている提案（P1〜P4、Q1〜Q9）

どれも前の決定は無い。

| # | 案 | 理由 |
|---|---|---|
| P1 | 規範に 1 文（debug §2）:「connection がある間、probe が自分の判断で行う線の再試行と同期の取り直しは、target の状態を変えない。wake / 設定の手順が target をリセットしうる wire では、connection の上でそれを送るのは attach と reset（TLV と op）の中だけ」。ch32rv の 3 つの条件は新しい規則にしない | 止めた hart が止まり直す害は host から見えない。条件は今の規則で足りる: 諦めたら閉じて link-lost / closed 4 の mark、閉じた後の要求は no_connection、同じ (connection、mechanism) なら同じストリーム。ch32rv の同意が要る |
| P2 + P3 | debug §2 の一般の 1 文（op を問わない）:「probe の線の再試行は、target に届いたかもしれない書き込みを繰り返さない。そういう失敗の要求は failed / partial で答え、done はそれより前の手順か語の数。読み出しは繰り返すことがある」 | 同じ語を 2 回書くと順序が壊れ、success なら host は気づけない。write_block だけでなく dmi の書き込みと arm-adi の transfer にも同じ再試行がかかる |
| P4 | 実装の限界の文書へ（規範にしない） | 線が落ちても古い値を返すのは 1 つの線の PHY の性質で、前後に DMSTATUS / DMCONTROL を読むのは 1 つの対策。規範に要るのは「線の失敗を見つけた要求を success で返さない」だけで、今の status line の規則に含まれる |
| Q1 | 規範に 1 項（debug §4.4）:「走らせる前に失敗したら（レジスタ、dcsr、pc の設定）、probe は走らせずに completed failed で答える。stopped 3（走らせなかった。hart は止まったまま）、status はその失敗、dpc は無効、nvals 0」。registry の run_stopped に not_run = 3 | 今の「止められなかった（2）」では、host は走っていない hart を止めに行くか、ローダーが走ったと誤る |
| Q2 | 規範に書かない。host ガイドの注:「SDI と DMDATA は番号を持たないので、線の書き込みが失われると重複・欠落しうる。完全さが要るなら dmseq」 | 方式の形から読めることで、相手の動きは変わらない |
| Q3 | 実装の限界の文書へ。仕様は §2 を「at boot のスロットは、probe が試せるときに attach する」に緩めるだけ | 試されなかったことは slot_state 1 と last_try_at_ns（全ビット 1）で見える。新しい印は要らない |
| Q4 | 仕様に足さない。参照 probe は firmware の文字列に理由を付けるのをやめ、理由の見方は実装の限界の文書に書く | describe は宣言だけ（core §7.3）。毎回変わる状態は宣言でない |
| Q5 | 規範に 1 文（common §1.3、すべての kind に）:「マークの position は、probe がマークを付けた時の書き込みの位置。position 以降のバイトはすべて、その出来事より後に受けた」 | host は mark で復号の状態や「リセット後の出力」の区切りを決める。見つけるのが遅れた分は position が後ろにずれる側に倒す |
| Q6 | host ガイドと実装の限界の文書へ。規則は足さない。送り直しの上限を 4 にしたいなら、`resend_max` の値の変更だけを別に相談する | すぐ送り直すのは、core §5.2 と送り直しの表の中で host が選べる手順。フロー制御の無い変換器が落とすのは変換器の限界 |
| Q7 | 15 を採れば問いが消える。採らないなら「reopen_s は利用者が前もって頼んだ開き直しに当たる」と答える | |
| Q8 | host ガイドへ（7 を採った後）。probe 側は「正常なフレームが 3000 ms 無ければ戻る」だけになる。「上げた速さのまま早めに送り直す」「下がった後にもう一度上げてよい」は host の手順 | もう一度上げてよいことは状態の表から読める |
| Q9 | 案 A も B も採らない（17 を採った後）。参照 probe の動き（窓の間、コンソールの読みと要求のフレームを後に回す）は実装の限界の文書へ | 20 ms の決まりが無くなれば、窓の間に読みを止めてもどの規則にも反しない。dmseq は同期の後なら長い待ち（1 s 以上）のうちに戻る |

## 3. 言葉だけの直し（peers に回さずに入れてよい）

**適用済み（50bd986、利用者の承認）。** 次は規則が変わるので入れず、残した:
- core §7.5 の「max_op_ms の間もほかの経路を続ける」: 長い要求の間もほかの経路に答えることは、ほかのどこにも書いていない（コンソールの読みは console §3 にある）。
- transports §4 の上げた速さの後の confirm: §4 は「繰り返す」（MUST）、§3 は探りの中で「繰り返してよい」で、重複ではない。§2 の `port_speed_confirm_extra_ms` の判断と一緒に扱う。
- debug §1「書いたものが読み戻らない速さは使わない」: 書く経路の確かめが失敗したときの扱いを決めるのはこの文だけ。
- debug §1 の max_speed の無い scan の速さ: 「probe が安全と考える遅い速さで試す（探索してよい）」は、同じ §1 と TLV の表の「無ければ最も遅い速さ」と食い違う。どちらかを選ぶのは規則の判断。
- debug §4 の端の場合のうち、dmi の n = 0、max_reads / max_us = 0、n_out の重複: ほかの規則から答えが 1 つに決まらない（block の count = 0 と止まっていない hart は §4.5 にあるので §4 から消した）。
- debug §3.1 の速さの選び方は 1 文に縮めて残した（遅い方から進める順はここだけにある）。debug §2 の at boot の生存確認への参照も残した。

規則は変わらない。言い直し、理由、参考、例を消すか、1 か所に寄せる。

- core: 冒頭の project の作業手順、§0 の線引きの規則と言語の段落（設計方針は development-guidelines へ）、§1.2 の host の MUST の一覧（各節の再掲）、§2.4「安全なのは §2.5 があるから」、§2.6a の「ソフトウェアで広げる」「継続時間の単位」、§2.7「名前を変えるのは意味が変わるときだけ」「新 revision の probe は古い revision も出す」、§3 の長い再掲、§4.2 の resolution 0x02 の文、§5.1、§7.1 の「シリアルの口が TCP の index を取らない」と 45 byte の計算、§7.3 の 0x3F、§7.5 の「max_op_ms の間もほかの経路を続ける」、§8.1 の後半、§9 の 1 プロセス 1 コマンドの例と本体の資源の列挙、§11.3 の「送り出さない fn への subscribe」「クレジットを持たない」、§13 の規則 9。§2.3 / §2.5 / §13 の作者向けの方針（伸び方、値の幅、応答に足す値の 3 条件、チェックリスト）は §13 に 1 か所でまとめる。
- transports: §1 の「応答が来ないのは時間切れだけで判断」、cobs の大きさの参考、§3 の「confirm と describe は開いた後にしか」、§4 の上げた速さの後の confirm（§3 と重複）、DTR を落とした間は定めない、再開の位置、§5 の「末尾の TLV が切れていれば壊れている」。
- common: §1.1「応答が失われても同じ位置で読めば同じ」、§1.2 の from ≥ 4 と max = 0、§2「後のセッションの attach が加わるのはスロットが開いている間だけ」、§3 の reset の status の対応、§3 の表の「host の判断の目安」の列（host ガイドへ）。
- debug: 冒頭「target の系統は宣言しない」、§0-2、§1「書いたものが読み戻らない速さは使わない」と max_speed の無い scan の速さ、休み方の理由の注、§2 の「idle は監視しない」と「probe の自動の attach も使っているもの」と逆給電の理由、§3 の線の設定の段落と idle_clock の替え方、§3.1 の速さの選び方と線を失ったときの文、§4「features を宣言しない」「持たない op は unknown_operation」「どの version も同じに扱う」、§4 の端の場合（dmi n = 0、block count = 0、max_reads 0、n_out の重複）、§4.1「1 つの要求は 1 つの hart」、§4.2 の DATA0 / DATA1 の段落（dmseq の参照は §4 の表へ付け替え）、§4.3 の mode ≥ 3、§4.4「run の間ほかに答えない、lease を数えない」（host ガイドの参照は core §4.4 へ）、§4.5 の重複と副作用の説明と cache の範囲外、§4.6 の reset 後の connection、§5 の SWDIO を駆動する側（ADI の言い直し）、§5 の非対称の注は「swd の connection にはコンソールもスロットも乗らない」の 1 文に。
- console: §1 の「方式を変えるときは 3 以降」、rev 1 の通知の話、§1 と §3 の arm-adi の重複、§2 の「各 mechanism が定めるもの」、閉じたストリームの説明の重複と例、列を持つ理由、§3 の「host は抽象コマンドを 1 要求に」（debug §4.1 を指すだけ）と「resume の op を使う必要はない」、§3.1 / §3.2 の「target がどれだけ待つかは target が決める」。
- dmseq: 目的の CRC の理由、参照の target の初期値、init 0xFF の理由、F_CPU/8000、「利用者に伝えてよい」、3 s の参考（ガイドへ）。
- capture: 冒頭の合わせ込みの例とモードの理由、§1.1「規則に入らない取り方」、§1.2 の共有の言い直し、§2.1 のトリガの 3 重の説明、規則 5（core §11.3）、§2.2 の host への助言、§3.1 の u8 の理由と外部クロック、§3.2 の read の max の理由、§3.4 のまとめる条件の再掲と「read で読む」、§3.7 / §4.4 の例（ガイドへ）、§4 の目的とずれの計算は 1 文に。
- link / plan / restart / fixture / probe-config: ロックの断りの順の再掲、core §2.5 の未定義の値の再掲、「通知は無い」、plan §2.4 の holder 7（core §8）、gpio の「解いたら空き」、uart の line coding、probe-config の tag 0x7E の 2 か所目と get の TLV、§3.1 の「at boot の attach は idle の後」「自動の attach は先払い」、§5 の安全（security へ）、片方向の UART の書き方（probe ガイドへ）。

## 4. 実装の限界の文書へ移すもの（oep-probe-arduino）

spec からはこの文書を参照しない（規範の文に 1 つの実装を書かない）。置き場を先に作ってから移す。

**どの platform にも共通（参照 probe の値と手順）**
- debug の時間と回数（2 を採れば）: 要求の中の再試行 200 ms、線切れ 1000 ms、attach 1000 ms、scan 500 ms、DM の待ち 100 ms、DMI busy と SWD WAIT の 100 回、リセットの後の待ち 700 ms、reset の 1 回のやり直し、TAR の 1 KiB、scan の 1 回の組の上限。
- max_op_ms の値 10000 ms（registry の `[reference]` を消してここへ）。
- search_retries の数え方。
- P4: dmi の要求ごとに前後の DMSTATUS / DMCONTROL で線を確かめる（ch32rv の条件: 確かめは要求ごと、失敗の前に終えた手順の数を done に、失敗した要求の中の書き込みは「行われたかもしれない」）。
- Q3: 起動してすぐ落ちることが続いたら at boot の attach を飛ばす条件。
- Q4: 前の起動の終わり方（panic、watchdog、brownout、巻き戻り）をどこで見られるか。
- boot_reset を消すなら、今までの動き（20 ms、条件）の記録。
- 生のバイトが最大 200 ms 遅れうること（transports §4 の参考）。

**線の PHY ごと**
- RVSWD / SWIO: 参照 probe の立て直し（300 µs、DMSTATUS、設定の組の書き直し）、dmactive の後に設定の組をもう 2 回書くこと、wake で target がリセットしうる系列と受け入れの回数（1000 / 256 回）、ほかのデバッガの 85 区切りの長い形。
- SWIO: 勧める low の長さ 262 / 862 ns と、それを測った系列、充電のパルス 30 ns、2 ms のプルアップで target が無いと判断すること。
- SWD: 速さを `min(max_speed, max_clock_hz)` から始めること、休みの level（SWDIO low、SWCLK high）、§2 の再試行で line reset と dormant をやり直すこと。

**classic ESP32**
- Q9: logic の sampler が窓の間（即時で最大 164 ms、トリガの探索は 250 ms ごと）片方の core で GPIO を読み続けるため、コンソールの読みと要求のフレームを窓の後に回す。止める時間は窓の長さ以下。

**周辺のある platform ごと**
- i2c-target のチップの FIFO の癖を probe が吸収していること。

**host と変換器の側**（参照 probe の文書の付録か client の文書に）
- Linux の cdc_acm は probe → host の burst が 8 KiB を超えると黙って失う。client は同時に送る量を 6 KiB、通知の min_bytes を 2 KiB に抑える（`host_serial_inflight_max_bytes`、`host_serial_min_bytes_max` を registry から消してここへ）。
- フロー制御の無い変換器は、続けて流れる probe → host のバイトをどの速さでも落としうる（Q6）。
- 変換器ごとに実測で通った port_speed の速さ。

## 5. 見直しどうしの食い違いと、選んだもの

| 点 | 食い違い | 選んだもの | 理由 |
|---|---|---|---|
| Q5 の文 | 待っている提案は「position から後ろは損失より後（抜けた所の直後の byte の位置か、それより前）」。debug の見直しは、括弧の中が前半と食い違うと指摘した（position が抜けた所より前なら、損失の前のバイトが position の後ろに入る） | debug の見直しの文（§2.4 の Q5）。すべての kind に掛ける | 見つけるのが遅れたときは position を後ろにずらす方が「以降はすべて後」を守れる。参照 probe が抜けた所より前に置いているなら、probe を直す |
| P3 | 待っている提案は「読むと状態が変わるレジスタは host が dmi で読む」。debug の見直しは、dmi も同じ再試行を受けるので正しくないとした | 書かない。P2 と合わせた一般の 1 文の「読み出しは繰り返すことがある」だけ | dmi に逃げても同じことが起きる。その種のレジスタの扱いは host ガイドの注 |
| P2 の範囲 | 待っている提案は write_block だけ。debug の見直しは op を問わない一般の規則 | 一般の規則 | dmi の書き込みと arm-adi の transfer も同じ害がある |
| P4 | 待っている提案は規範。debug の見直しは実装の限界 | 実装の限界 | 確かめ方は 1 つの対策で、要るのは「success で返さない」だけ |
| console の「止まっている間は読まない」 | console の見直しは 20 ms を消して順序で書く。debug の見直しは debug §4.1（抽象コマンドを 1 要求に）を残し、§4 の表の「console の読み」の行を残す | 両方を採る: 規則の本体は console §3 の順序の文（17）、debug §4.1 の host の義務は残し、debug の表の行は console §3 を指すだけにする | §4.1 が防ぐのは要求の中の取り合いだけで、要求と要求の間は console §3 が防ぐ |
| Q9 | 待っている提案は案 A（wire_pause_ms を足し、20 ms から外す）を推奨。console の見直しはどちらも採らない | 採らない | 17 で 20 ms が消えれば、窓の間に止めても規則に反しない |
| Q2 | 待っている提案は console §3 に宣言。console の見直しは実装の限界 | host ガイドの注 | 番号の無い方式の性質で、どの実装でも同じ。1 つの実装の限界ではない |
| holder_kind | core の見直しは消す。debug、capture、probe-config の見直しは「cause 5 / holder_kind 7」を残す前提で文を書いた | 消す（14）。各文書の文は「unavailable cause 5」に | host の動きは cause と channel で決まる |
| 「bit 7 によらず critical」 | core の見直しは例外を消す。capture の見直しは probe 側の扱いを残し host の義務だけ消す | 例外も義務も消す（21） | v1 で定めた TLV は、実装する probe が知っている。知らない probe には、効かないと困る項目を host が critical で送る一般の規則が効く |
| describe の reserved | core の見直しは消す。probe-config の見直しは「項目の channel は reserved に無い」を残す | 消す（8）。probe-config の文は「probe が自分で使う channel を指す項目は unsupported」に | 宣言しなくても断りで分かる |
| `port_speed_confirm_extra_ms` | core の見直しは残す（transports §3 が使う）。fixture の見直しは消す | 消す。transports §3 の confirm を繰り返す時間を `port_speed_idle_max_ms` + `host_wait_add_ms` で書く | 値を 1 つ減らせ、意味は同じ |
| P1 の ch32rv の条件 | 待っている提案は条件つき。debug の見直しは今の規則で足りるとした | 新しい規則にしない | 条件の 3 つは今の規則から出てくる。ch32rv に確かめる |
| Q3、Q4、Q6、Q8 | 待っている提案はどれも規範を足す案。見直しは足さない | 足さない（§2.4） | 基準に当たらない |
| VID:PID | core の見直しは transports §3 と registry の `1209:4F45` を方針違反とした | その指摘は取り下げる。値は取得済みで、spec に書いてよい | |

## 6. 影響

### 6.1 registry から消えるもの（§2 をすべて採ったとき）

- 本体: `constants.tag_ignored`、`tag_invalid`、`reject_reasons.corr_reused`（0x0D は予約に）、`timing.resync_quiet_ms`、`host_resync_wait_ms`、`host_frame_pause_max_ms`、`port_speed_confirm_extra_ms`、`limits.model_max_bytes`、`cobs_frame_max_bytes`、`ignored_max_entries`、`resource_reuse_distance`、`host_serial_inflight_max_bytes`、`host_serial_min_bytes_max`、`[reference]`、`describe_common.implementation`、`core.tlv.unavailable_payload.holder_fn` / `holder_kind`、`core.enum.holder_kind`、`core.tlv.describe` の reserved（0x44）、profile（0x45）、resets_on_open（0x47）、discoverable（0x4A）、chip（0x4C）。
- debug: limits の 13 項目（2）、wire の op 0x04 の予約、3 つの wire の `enum.features`（attach_writes_unbounded）、riscv-dm の `tlv.reset.method`、`enum.reset_method`、`enum.reset_flags` の retried / confirm_failed、riscv-dm と arm-adi の `address_hi`。今でも読まれないもの（swd の attach_answer の target_id / dpc、swd の scan_kind.riscv_dm、使われない attach_flags）も片づける。`target_id_scheme.wch_dmi_7f` は改名。
- console と capture: `console_dmstatus_poll_ms`、`console_send_queue_min_bytes`、console の `tlv.describe.send_queue`、logic / analog の `enum.jitter_kind`、`configure_answer.rate_accuracy`、`enum.rate_accuracy_how`、`enum.background`、`tlv.describe.rate_list` / `rate_limit` / `max_read` / `segment_ring`、analog の `configure_answer.frontend_used`、`tlv.describe.frontend_shared`、capture-group の `max_tracks` / `budget` / `start_skew`。
- link、restart、fixture、probe-config: `port_speed_broken_max`、`link_source_overhead_bytes`、`restart_after_answer_ms`、`slot_retry_reset_hold_ms`、`fixture_count_max`、`common.enum.target_id_len`、gpio の `mode.input_pullup_pulldown`、`read_answer.drive`、`enum.drive_read`、`enum.drive_kind`、uart の `enum.uart_configured`、i2c-target の op arm_rx / reset / stretch、`max_stretch_us`、`pullup_ohms`、`enum.mode`、features の preloaded_tx、spi-target の op reset、probe-config の `enum.slot_boot_reset`、slot_state の lock_mismatch / no_target_id、`enum.bind_mode`、describe の bind_modes、describe 0x44〜0x45 の予約。
- 足すもの: `port_speed_tolerance_pct = 2`、riscv-dm の `run_stopped.not_run = 3`（Q1）。
- 生成物 `generated/oep-v1/` は作り直す。

### 6.2 直すベクタと道具

- tests/vectors: headers.json、ops.json、refusals.json（ignored、corr_reused、断り方の順、端の場合の malformed）、sessions.json（corr_reused）、discovery.json（list の prefix、discoverable、describe の tag）、probe_config_hash.json（13 を採れば消す）、ops_encoding.json（26 の ops の符号）、checks.json と confirm.json は確かめだけ。
- tools/oepvectors1.py、oepgen1.py、tests/registry_v1、tests/uart_binding/uart_binding.ino。

### 6.3 追う実装

- oep-client-python: 応答の組み立てと読み（ignored、corr）、list、describe、riscv.py / endpoint.py の待ち、console.py（send_queue）、capture.py、probe-config の dataclass（錠、boot_reset、bind、drive、hash）、link の speed、fake.py / fake_capture.py と tests（test_console_queue_and_reset_settle.py、test_host_rules_2026_10_02.py、test_fake_rules_2026_10_0{2,6}.py ほか）。
- oep-client-js: registry と README（attach_budget_ms、reset_settle_ms、list）。
- oep-probe-arduino: 送り直しの表、ignored、list、describe、OepWireLoss.h / OepDmiPhy.h / OepSwd.h / OepSwioPhy.h / OepTarget.h / OepCh32Dm.h / OepDmConsole.h の limits の名前、reset の応答の形、run の stopped 3、console の順序の規則、OepConfig（錠、boot_reset、bind、drive、hash）、port_speed、i2c-target、gpio、firmware の文字列（Q4）。実装の限界の文書を新しく作る。
- ch32rv: ブローカーの送り直しの表と list、port_speed、restart の中継、dmseq の host（無効な語の処理）、attach_writes_unbounded を使う予定の有無。
- WireSkein: capture の configure の応答（jitter_kind、rate_accuracy、frontend_used）、describe、chip。
- bench: probe-config（錠、bind の mode、boot_reset、drive の kind）、port_speed。
- 文書: conformance、glossary、security、host / probe 開発ガイド、getting-started、usb-identity、implementation-notes、英語版（凍結のときに作り直すなら後で）。
