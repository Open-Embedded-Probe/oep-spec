# v1 のゼロベース再点検（2 回目、2026-10-02）

状態: **記録**（規範ではない。点検）。[ゼロベース再検討（2026-10-01）](v1-zero-base-proposal.ja.md)で採用した 9 つの選択と 8 原則を
前提に、反映後の規範（core、common、debug、console、fixture、capture、probe-config、registry）を全文読み直し、
(a) 部位ごとに「十分に単純か、伸ばせるか、伸ばすならどこか」を判定し、(b) 文書と registry の食い違いを grep で確かめて列挙し、
(c) 凍結前に直すべきもの（★）と、固定のままでよいもの（☆）を提案し、(d) 2026-10-01〜02 の実機の事実
（[リンクの計測](link-measurements.ja.md)、[UART の速さ](uart-speed-negotiation.ja.md) §7〜9、[リリース前の試験](release-testing.ja.md)）が
規範に求める変更をまとめた。採用済みの 9 つの選択は再議論しない。

結論を先に: **骨格に直すものは無い**。直すのは、実機の事実が規範の文言と食い違った 3 か所（リンクの速さの目的、port_speed の壊れの
判定、ブリッジの名前）、断り方の順の取りこぼし 1 か所（block の長さ）、識別子の安定の規則 1 か所（unit_id = serial は版を越えて不変）、
文書どうしの食い違い 6 か所。形（固定部分、番号）を変えるものは無く、すべて文言と registry のコメントで済む。

---

## (a) 部位ごとの判定

「道」の列は、後から足したくなったときにどこに置くか（TLV / 宣言 / op 番号）。「単純」は実装を 1 つ書くのに迷う所が無いか、
「伸びる」は固定部分を変えずに足せるか。

| 部位 | 単純 | 伸びる | 伸ばす道（具体） | 備考 |
|---|---|---|---|---|
| フレームと TLV（core §2〜§3.2） | ○ | ○ | 見出しは confirm の revision。新しい運び方は transport kind を足して自分の詰め方を定める。TLV は長い形（0xFF + u16）で 64 KiB まで。並びは `count × (len, 要素)` | 閉じた末尾は link_source / link_sink だけ（意図） |
| 上限と confirm（§3.3、§4.4、§7.1） | ○ | ○ | 応答の TLV（boot_id の後ろ）に probe 側の情報、要求の TLV（非 critical）に host 側の情報。`flags(u8)` は予約 | host の受けの上限は protocol の外でよい（(d)-1） |
| セッション / ロック / lease（§5〜§6、§9） | ○ | ○ | open の TLV 0x02〜、lock_state の応答 TLV、reject reason 0x0F〜0x3F、`resumed` の enum 3〜 | 状態機械は §6.2 の表 1 つで閉じている |
| describe / 宣言 / 状態（§7.3〜§7.5） | ○ | ○ | fn 0 の tag 0x4F〜0x7F、共通 tag 0x09〜0x3E、インターフェース 0x40〜0x7F。値は閉じた形なので新しい情報は新しい tag。変わるものは各インターフェースの state op | 「宣言だけ」の規則で cache が成り立つ |
| plan / channel / 資源（§8〜§9） | ○ | ○ | plan_apply の TLV 0x91〜、unavailable の TLV 0x06〜（0x05 fn は registry にある）と 0x40〜、cause 7〜、holder_kind 7〜。資源番号は 1 空間 u16 で一周 | — |
| 出来事 / ハートビート（§11） | ○ | ○ | fn 0 の kind 0x02〜0x7F、ハートビートの TLV、subscribe の TLV（ロック無しの購読は予約済み）、データフレームの TLV | 流量のクレジットは持たない（意図）。burst の上限は host が min_bytes で持つ（(d)-1） |
| port_speed（§3.5） | △ | ○ | 要求 / 応答の TLV、step の enum 3〜、describe の port_speed は値を変えず新 tag | 手順 3 / 7 の壊れの判定が絶対数で、実測と合わない（★2） |
| USB の識別（§3.3、§7.5、registry `usb`） | ○ | ○ | 新しい口は transport kind、記述子の定数は registry `[usb]`。VID:PID は規範に入らない | unit_id の「版を越えて不変」が書かれていない（★5） |
| probe.config | ○ | ○ | 項目 tag 0x08〜0x7D、項目の後ろのフィールド（probe はバイト列をそのまま持つ）、state の TLV、describe 0x46〜 | §2 に state op への移行漏れ 1 行（★8） |
| 線 / riscv-dm / arm-adi（debug） | ○ | ○ | wire の op 0x06〜（0x04 予約）、riscv-dm 0x09〜、arm-adi 0x04〜、features のビット、attach の TLV 0x06〜 / 応答 0x12〜、address_hi 予約、status 0x06〜0x3F、target_id_scheme 3〜 | block の長さの断り方が §4.3 の順と違う（★4）。線の速さが上限で、リンクではない（(d)-5） |
| fixture（gpio / uart / i2c / spi） | ○ | ○ | gpio mode 8〜（modes は u32）、uart format の bit5〜7 は新しい値を宣言してから、i2c mode 4〜と features、spi の CS 極性は TLV、read_rx の TLV 0x02〜 | 揃っている |
| capture（logic / analog / group） | ○ | ○ | configure 0x48〜0x5F、応答 0x5B〜、mode / trigger type 0x40〜、layout のビット、describe 0x4A〜、別定義は 0x60〜0x7F、出来事 0x04〜、区画の情報は len 付きで後ろに足せる、group の TLV | 世代で古い read を断る。揃っている |

---

## (b) 文書と registry の食い違い（grep で確認したもの）

| # | 場所 | 何が | 確認 |
|---:|---|---|---|
| 1 | registry `oep-v1.toml` L63 `expired` のコメント | 「lease expiry **or force**」とあるが、core §4.3 0x0E と §9 は force で奪われた側を locked → no_session とし、expired は期限切れだけ | `grep -n expired registry/oep-v1.toml` / core §4.3 |
| 2 | registry L179 / L182 `fn = 0x05`（unavailable / unsupported の payload） | core §4.3 の unavailable の payload の表（0x01〜0x04）に 0x05 fn が無い。capture §4.1 bind の断り方も「どのトラックか」を payload で返すと書いていない | `grep -n "fn = 0x05" registry/oep-v1.toml`、core §4.3 の表 |
| 3 | probe-config §2 L163 | 「その結果は **describe の slot_state と bind_state** で分かる」。state op（0x06、§3.3）に移っていて describe の 0x44 / 0x45 は予約 | `grep -n slot_state docs/oep-if-probe-config.ja.md` |
| 4 | core §7.3「ページングの終わり（describe、**list**、…）: count 0 と more 0」 | list の応答は `total(u16), count(u8), …` で more を持たない（§7.2） | core L470 / L501 |
| 5 | debug §4.1 dmi kind 0x04 の引数名 `us(u32)` | registry は `wait_us`（0x04）。7.3-42 の改名が本文に入っていない | `grep -n "us(u32)" docs/oep-if-debug.ja.md` |
| 6 | core §3.5 手順 3「M5Stack ATOM の **FTDI**」 | ATOM の変換は CH552 の FTDI 互換（uart-speed §3a の注、commit ad89baf）。整数分周だけ・duplex ≥ 500 k で壊れるのは CH552 の性質で FTDI 一般ではない | core L254 |
| 7 | core §3.5 冒頭「デバッグの速さのため」 | 線の block op はリンクではなく線の往復で決まる（link-measurements §1.3: bulk と CDC で 5 % 差、SWIO は 35 ms / 64 語） | core L232 |
| 8 | debug §4.5 / §6 と fixture §3 / §4 | 同じ「describe の max_length 超え」が block では **malformed**、i2c / spi では **unsupported**。core §4.3 の順 6 は「定義にあるが持たない（範囲外）」を unsupported と定める | debug L295 / L354、fixture L96 / L129 |
| 9 | core §7.5 の表 | 0x4E port_speed の行が 0x4D max_op_ms の前（並びだけ） | core L542-543 |
| 10 | usb-identity §2 | `oep_pid = 1` のまま（7.1-12 で `discoverable` に改名） | `grep -rn oep_pid docs/` |
| 11 | probe-development-guide §3.8 | 「PID を取ったら名前での判定は無くなる」のまま（3.4d: iProduct `OEP` 接頭は恒久の規範）（2026-10-02 に置き換え: [core §3.3](oep-core.ja.md)。iProduct と interface の文字列は見分けに使わない。暫定の手がかりは host 開発ガイド §4） | L110-111 |
| 12 | probe-config §4 | 表の見出し行が 2 回（L242-243 の空の表） | 目視 |

registry そのものは `tools/oepgen1.py --check` が exit 0 で、op 番号・ロック要否・tag・enum は全文書と一致。食い違いは**コメントと本文の
文言**だけで、番号の衝突や形の不一致は無い。

---

## (c) 提案

★ = 凍結前に入れる（文言か registry のコメント。形は変えない）。☆ = 固定のままでよい（理由つき）。

### ★1 core §3.5 冒頭: リンクの速さは何のためか

- **今**: 「…同じ速さのリンクでは target の UART の全量を運べない。大きな書き込み、キャプチャ、デバッグの速さのため」。
- **直す**: 「…大きな書き込み、キャプチャ、コンソールのため。**線の block op（read_block / write_block、dmi）の時間は debug の線の
  往復で決まり、リンクを速くしても変わらない**（X035 の RVSWD で 64 語 8 ms、V003 の SWIO で 35 ms。[リンクの計測](link-measurements.ja.md)
  §1.3）。デバッグを速くするのは probe の往復の減らし方（sysbus、abstractauto、まとめ読み）で、リンクではない」。
- **なぜ**: 実測と逆のことを規範が言っている。host の実装者が port_speed を「デバッグが速くなる」と読んで試し、効かずに戸惑う。

### ★2 core §3.5 手順 3 と 7: 壊れの判定を絶対数から「起動時の速さの基準との比」に

- **今**: 手順 3「壊れたフレームが 1 つでもあれば、その速さは使わない」、手順 7「上げた速さで壊れたフレーム（送り直し）が続いたら
  （目安 5 秒に 3 つ）… 戻す」。
- **事実**: V003 の CH340 は **115200 でも 921600 でも** probe → host を 1〜3 % 落とす（間欠、速さに依らない、link-measurements §1.4）。
  ATOM の CH552 はどの速さでも 0.1〜0.3 % 壊す（uart-speed §9）。この線で今の規則は、(i) verify で 32 KiB（≈ 65 フレーム）流せば
  1〜2 個落ちて 921600 を落とし（dogfood では間欠性で偶然通った）、(ii) 通っても 921600 で 140 フレーム/s × 1〜3 % = 毎秒 1〜4 個壊れて
  手順 7 が常に「戻す」になる。どちらも「壊れ方は変わらず 4.5〜5 倍速い」（§1.4 の結論）を捨てる。
- **直す**（手順 3 の末尾と手順 7 を差し替え）:
  > 3. … **host はまず起動時の速さで同じ流し方（向き、同時数、大きさ）を測って基準とし**、候補の速さの壊れ・失われの割合が基準より
  > 明らかに悪くなければ通ったとみなす（目安: 基準の 2 倍以下、かつ 5 % 以下。基準が 0 なら候補も 0）。1 つでも壊れたら落とす、では
  > どの速さでも一定の割合で落とす変換チップ（CH340、CH552）で起動時の速さまで落としてしまう。
  > 7. **使っている間も host は割合で見る**: 上げた速さでの壊れの割合（直近 100 フレーム程度）が基準の 2 倍を超えて続いたら port_speed（戻す）を
  > 送り、そのセッションではその速さを使わない。…（以下は今のまま）
- **なぜ**: 判定の規則は host と probe の両方の約束（probe の自分での戻り 5 も「壊れた候補が続いた（目安 1 秒に 3 つ）」で、CH340 では
  921600 で毎秒 1〜4 個壊れうる → **手順 5 の目安も「1 秒に 3 つ」から「連続して 3 つ、正しいフレームを挟まず」に変える**）。
  port_speed policy（限界を場合ごとに測ってから既定を決める）とも合う。

### ★3 core §3.5 手順 3: ブリッジの名前

- 「M5Stack ATOM の FTDI は 500 kbaud 以上で」→「M5Stack ATOM の変換（CH552 の FTDI 互換。整数分周の速さしか作れず、500 kbaud 以上で
  両方向を同時に流すと応答が壊れた）は」。(b)-6。

### ★4 block の長さ: 断り方を §4.3 の順に揃え、max_length が max_frame に収まることを規範に

- **今**: debug §4.5「count × 4 はこれ（max_length）を超えない（超えれば rejected malformed）」、§6 も同じ。i2c / spi は「max_length 超は
  unsupported（0 は malformed）」。実機では「max_frame に入らない count」が malformed で返り、client は `(max_frame − 18) / 4` を自分で
  計算している（oep-client-python `arm.py` L146、`ch32_flash.py` L98）。
- **直す**:
  1. debug §4.5 と §6: 「count × 4 が max_length を超えれば **rejected unsupported（payload `0x00`）**。count = 0 は success done 0、
     4 の倍数でない address は malformed（今のまま）」。
  2. debug §4.5 に 1 文: 「**probe は max_length を、read_block の応答（見出し 5 + done 2 + status 1 + 語）と write_block の要求
     （見出し 10 + connection 2 + address 4 + count 2 + 語）がどちらも自分の max_frame に TLV の余地を残して収まる値で宣言する**
     （max_frame − 24 以下、4 の倍数が目安）。host は count を max_length から決め、max_frame から計算しない」。
  3. core §7.4 の max_length の説明に「（その op の要求と応答が max_frame に収まる値で宣言する。インターフェースの文書が単位を決める）」。
- **なぜ**: 原則 8（断り方の順は 1 つ）。「定義にはあるが、この probe が持たない」は unsupported で、i2c / spi はすでにそう。別に
  `max_count` を宣言する必要は無い（☆4）。host が max_frame から逆算する今の実装は、probe が TLV を足した瞬間に壊れる。

### ★5 unit_id と USB の serial は firmware の版を越えて変えない

- **事実**: 参照 firmware の serial が `<MAC>-hs` → unit_id に変わり、Windows の usbipd は別の device と見て管理者の再 bind が要った。
  DFU の interface 番号（4 と 7）と転送の大きさ（4096 / 1024）も版で動く。
- **直す**: core §7.5「unit_id の一意性」の後ろに 1 項:
  > **unit_id の不変性**: unit_id は個体の値（チップの固有の番号、保存した乱数）だけから作り、**firmware の版、profile、ビルド、
  > 経路の種類で変えない**。host と OS は unit_id（= USB の serial number、§3.3）で probe を覚えるので、変わると別の probe に見える
  > （USB の口の再 bind、設定のファイルの address `oep://<unit_id>` の失効）。接尾辞（`-hs` など）を足さない。
  core §3.3 の serial の項に「serial number は unit_id **そのもの**で、firmware の更新で変えない」を足す。
- **OEP の外のまま**（☆3）: DFU の interface と転送の大きさは記述子から読む、は実務（usb-identity / probe 開発ガイド）に 1 行。

### ★6 host の受けの上限は host 側の規則のまま、通知の burst も host が min_bytes で持つ

- **今**: core §3.4 の注（2026-10-01）は「未解決の要求の応答の見込み量を 6 KiB 程度に」だけ。通知（データフレーム、出来事）の burst には
  触れていないが、cdc_acm の 8 KiB は向きの性質で、ストリーミングのキャプチャが CDC で大きな burst を出せば同じく失う。
- **直す**: §3.4 の注に 1 文: 「**通知も同じ**: シリアルの口で購読するとき host は subscribe の min_bytes を小さく（目安 2 KiB 以下）保ち、
  probe が一度に送る量を自分の受けに合わせる（§11.3。probe は min_bytes たまるか max_delay_ms で送るので、burst の大きさは host が決める）」。
  §11.4 の 2 に「シリアルの口では host の OS の受けの量（§3.4）も上限になる」を添える。
- **confirm には足さない**（☆1）。

### ★7 unavailable / unsupported の payload の TLV 0x05 fn を core §4.3 の表と capture §4.1 に

- core §4.3 の unavailable の表に `| 0x05 | fn | u16。断りの対象の fn（capture-group の bind のトラックなど） |`、unsupported の payload の
  説明に「channel、index、fn」。capture §4.1 の断り方に「どのトラックかは payload の TLV fn（0x05）」。(b)-2。registry が正、文書を直す。

### ★8 probe-config §2 L163 の「describe の slot_state と bind_state」→「state（§3.3）の slot_state と bind_state」。(b)-3。

### ★9 registry L63 `expired` のコメントから「or force」を外す（「ended by lease expiry; the forced-out side sees locked, then no_session (core §9)」）。(b)-1。
生成コードのコメントに出るので凍結前に。L140 の mark_detail_closed の `expired = 2` は「lease 切れ / force」で正しい（別物）。

### ★10 core §7.3 のページングの終わり: 「list は total で終わりが分かる（more を持たない）。describe、state、connections、streams、segments、get は first が数以上なら count 0 と more 0」。(b)-4。

### ★11 細かい文言（凍結前にまとめて）: debug §4.1 `us(u32)` → `wait_us(u32)`（(b)-5）、core §7.5 の 0x4D / 0x4E の並び（(b)-9）、probe-config §4 の重複した表の見出し（(b)-12）、usb-identity §2 `oep_pid` → `discoverable`（(b)-10）、probe 開発ガイド §3.8「PID を取ったら名前での判定は無くなる」→「iProduct `OEP` 接頭は恒久（core §3.3）」（(b)-11）。（2026-10-02 に置き換え: [core §3.3](oep-core.ja.md)。iProduct と interface の文字列は見分けに使わない。暫定の手がかりは host 開発ガイド §4）

### ★12 release-testing を「案」から「決めた」に（事実 7）

- `tests/hw` は oep-client-python に置いた。§3 の最小の中身に、今回の事実から 3 つ足す: (i) シリアルの口で同時数 × フレーム長を 6 KiB
  まで上げても失われないこと（cdc_acm の 8 KiB を踏まない）、(ii) port_speed は起動時の速さの基準と比べる matrix（★2）、
  (iii) read_block を max_length ちょうどで 1 回（★4 の宣言が max_frame に収まることの確かめ）。規範ではないが、凍結後の「動く仕様」の判定基準。

### ☆ 固定のままでよいもの（理由）

| # | 部位 | 理由 | 必要になったときの道 |
|---:|---|---|---|
| ☆1 | confirm に host の受けの上限（host_window など）を**足さない** | 応答の量は host が同時数で、通知の量は host が min_bytes で決めるので、probe が host の上限を知っても使い道が無い（通知に ack が無く、probe は host が読んだ量を知れない）。OS のドライバの都合は probe に関係なく、host が自分で守るのが筋（§4.4「守るのは host の責任」と同じ向き） | confirm の要求 TLV（非 critical）。purely host → probe の助言として後から足せる |
| ☆2 | max_frame は両方向の上限のまま | cdc_acm の 8 KiB は 1 フレームではなく burst の問題。フレームの上限を下げても解決しない | — |
| ☆3 | DFU / firmware の更新は OEP の外（core §0） | interface 番号も転送の大きさも USB の記述子にあり、焼く側はそれを読めばよい。OEP が写しを持つと版ごとに食い違う。unit_id = serial が不変（★5）なら焼く側は個体を見失わない | 必要なら `oep.probe.firmware` のような名前つきのインターフェース（本体は触らない） |
| ☆4 | read_block に `max_count` の宣言や専用の理由を**足さない** | max_length（byte）で表せる。★4 で断り方と宣言の規則を揃えれば host は計算しなくてよい | address_hi は予約済み（RV64） |
| ☆5 | port_speed で probe は速さの候補を宣言しない | CH552（整数分周だけ）と CH340 で通る速さが全く違い、probe からは見えない（事実 4 が裏付け）。候補は host の変換チップの表 | 要求 TLV に「試した結果の通知」などを後から |
| ☆6 | ブリッジ側の実際の baud（整数分周のずれ）は protocol に出さない | host の変換チップの性質で probe は知れない。応答の baud は probe の UART の実際の値で足りる | — |
| ☆7 | block op の往復の減らし方（sysbus のまとめ読みなど）は v1 の op に足さない | 線の速さの問題で、probe の実装の改善で済む（read_block の意味は「target のバスを通して読む」で、手段は probe が選べる） | riscv-dm の features ビットと op 0x09〜 |
| ☆8 | 提案 §4 の固定の表（見出し、COBS / CRC、u8 の op / tag、要求の並びに len 無し、link_source / link_sink、confirm 前の 64 byte、config のキーの幅） | 今回の点検で、どれも伸ばせないことで困る実例は出ていない。再議論しない | 同表のとおり |

---

## (d) 実機の事実が規範に求めるもの

| # | 事実（2026-10-01〜02） | 規範への影響 | 提案 |
|---:|---|---|---|
| 1 | Linux cdc_acm は probe → host の応答 burst が 8 KiB を超えると黙って失う（7 × 1008 B は通る、libusb 直接は通る）。client は 6 KiB に抑えた（core §3.4 の注、済） | probe の max_inflight / window は probe の受けの上限で、host の受けの上限は誰のものでもない。**host 側の規則で足りる**（☆1）。ただし通知の burst にも同じ上限が効くことを書く | ★6、☆1、☆2 |
| 2 | read_block の count が max_frame に入らないと malformed。host は `(max_frame − 18) / 4` を自分で計算している | max_length の宣言が max_frame に収まることと、host は max_length を使うことを規範に。断りは unsupported に揃える。宣言を増やさない | ★4、☆4 |
| 3 | P4 の DFU interface は版で動く（4 / 7）、転送の大きさも（4096 / 1024）。serial が `<unit>-hs` → unit_id に変わって usbipd の再 bind が要った | unit_id = serial は**版を越えて不変**を規範に。DFU は OEP の外のまま（記述子を読む、は実務の文書） | ★5、☆3 |
| 4 | ATOM の CH552（FTDI 互換）: 整数分周だけ、duplex ≥ 500 k で壊れる、どの速さでも 0.1〜0.3 % 壊れる。V003 の CH340: probe → host が 921600 まで 1〜3 % 落ちる（間欠、速さに依らない）、1.5 M は使えない、host → probe は無傷。RP2350 FS CDC と P4 vendor bulk は 0 | port_speed の壊れの判定は**基準との比**でないと成り立たない。probe は候補を宣言しない（☆5）が正しいと裏付け。ブリッジの名前の誤りを直す | ★2、★3、☆5、☆6 |
| 5 | 線の block op は debug の線の往復で決まる（RVSWD 64 語 8 ms、SWIO 35 ms）。リンクが 10 倍速くても 5 % | core §3.5 の「デバッグの速さのため」を直し、何がデバッグを速くするかを 1 文 | ★1、☆7 |
| 6 | port_speed は実装・dogfood 済み（ブローカー、bench）。上げた後は使いながら数えて下げる | 手順 7 の「数える」の単位を割合に（★2）。それ以外は今の形で動いている | ★2 |
| 7 | リリース前の実機の試験は oep-client-python `tests/hw` に置いた | release-testing を決定に。今回の事実を判定項目に | ★12 |

### 事実 1 の補足: host 側の受けの上限を protocol に入れない判断

protocol に入れるなら「confirm の要求 TLV `host_window(u32)`: host が一度に受けられる未読の量」だが、probe がそれで変えられるのは
(i) 応答を返す速さ（host が同時数で既に決めている）と (ii) 通知の burst（host が min_bytes で既に決めている）だけで、どちらも host の
手にある。probe が守れないもの（OS のドライバの取りこぼし）を probe の約束にしても意味が無い。**host の規則 2 つ**（応答の見込み量
≤ 6 KiB、min_bytes ≤ 2 KiB 程度）を core §3.4 の注に並べて置くのが、原則 6（仕組みより不変条件）に合う。vendor bulk / HID では
両方とも要らない（長さつきのフレームで、OS の tty を通らない）。

### 事実 2 の補足: なぜ「宣言した max count」より max_length の整合か

count の上限は、要求（write_block）と応答（read_block）の両方が max_frame に入ることで決まり、宣言としては既にある max_length（byte）
がそれを表す場所。足りなかったのは「宣言が max_frame と整合していること」と「host は宣言を使う」の 2 文で、新しい tag ではない。
断りは「定義にはあるが持たない（範囲外）」なので unsupported（原則 8）。

---

## 影響と進め方

- **形を変えるものは無い**（固定部分、番号、TLV の tag はそのまま）。★1〜★11 は core / debug / probe-config / registry のコメント /
  usb-identity / probe 開発ガイドの文言。★2 は host の実装（oep-client-python の `speed` / linktest の判定、ch32rv のブローカー）に
  基準の計測を足すことになる（試す時間が 2 倍: 基準 + 候補）。★4 は probe の firmware（断り方を unsupported に、max_length の宣言値の
  確かめ）と client（max_length を使う）。★5 は参照 firmware はすでに満たしている（確かめだけ）。
- **順**: ★3 / ★7〜★11（文言だけ）→ ★1 / ★5 / ★6（規範の 1 文ずつ）→ ★4（spec → fake → probe → client）→ ★2（spec → client /
  ブローカー、V003 と ATOM で実測して目安の数字を決める）→ ★12。
- **凍結後に残してよいもの**: (b)-10〜12 は非規範か見た目なので凍結後でも直せるが、生成コードに出る registry のコメント（★9）は凍結前に。
