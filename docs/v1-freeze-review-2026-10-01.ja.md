# v1 凍結前の全面見直し（2026-10-01）

状態: **対応済み**（2026-10-01。[ゼロベース再検討と仕様案](v1-zero-base-proposal.ja.md)で方針を決め、その §3 / §7 として規範と実装に入れた。項目ごとの扱いは同文書の §7 と、見直しの番号の参照を見る）。元の文:規範の文書（core、common、debug、console、capture、fixture、probe-config、registry、usb-identity）と
開発ガイドを 4 つに分けて全文読み、[凍結前の決定](v1-freeze-decisions.ja.md)の 13 項目（決定済み）と重ならない「凍結の前に決めた
方がよい所」を集めた。各項目は 場所 / 問題 / 案 の順。★ はユーザーに選んでもらう項目、ほかは案のとおりで進めてよいもの。
重要度は **高**（凍結後に形を直せない: 固定の形、番号、意味の規則）、**中**（曖昧で実装が割れる）、**低**（文書と registry の整理）。
場所の § は読んだ時点（962b7ce）のもの。直すときは該当箇所を読み直す。

決めた項目は [凍結前の決定](v1-freeze-decisions.ja.md) に移し、ここは理由と経過の記録に残す。

---

## A. 高: 凍結後に直せない形

### 1. ★ read 系の応答が「閉じた末尾」で、後ろに何も足せない
- 場所: core §2.3 / §12、common §1.2、console §1 read、fixture §2 read、capture §3.2 read、gpio read（`n × level`、数も無い）、
  riscv-dm `dmi` / arm-adi `transfer` の応答（値の個数が無い）、registry `closed_tail`。
- 問題: data の前に長さが無いので TLV を足せない。一方 i2c / spi の read_rx は `count(u16), data` と長さを持つのに closed_tail = true。
  gpio read の応答は数を持たず、要求を見ないと読めない。dmi / transfer の応答は値の数が無く、registry は closed_tail でないので矛盾。
- 案: (a) 推奨: read の応答を `start, flags, len, data`（capture は len u32）にし、gpio read を `n, n × level`、dmi / transfer に
  `nvals(u16)` を置いて、閉じた末尾を link_source（試験用）だけにする。(b) 今のままにするなら i2c / spi の closed_tail を外し、
  dmi / transfer は closed_tail = true にして整合だけ取る。

### 2. ★ halt 中に probe が使う GPR / DATA0-1 の復元責任（raw DMI との境界、connection が閉じる時）
- 場所: debug §2、§4.2、§4.5。
- 問題: 「resume / step の直前に戻す」「host が raw DMI で走らせたら捨てる」だけで、(a) 何をもって host が走らせたと見るか、
  (b) halt → `dmi` で a0 を書く → `resume` で probe が a0 を潰すか、(c) attach(method=1) や dmi の haltreq で止めた hart に
  read_block したとき DATA を覚える契機、(d) halt → read_block → `dmi` でレジスタを読むと probe の作業値が見える、(e) hart を
  止めたまま lease 切れ / force / detach で connection が閉じると覚えた値が消え、target が壊れたまま残る、が未定義。
  2026-10-01 の target 破壊（probe 0.0.20 で直した）はこの境界。
- 案: (a) 推奨: **block op を自己完結にする**。read_block / write_block は自分が使った GPR、DATA1 / DATA0、abstractauto を
  **応答を返す前に**戻す。probe は op の外で hart の状態を持ち越さず、(a)〜(e) が消える。コストは op ごとに DMI 数回。
  (b) 今の方式のまま、「halt 後に host から dmi の書き（kind 0x01）が 1 つでも来たら覚えた値を戻してから捨てる」
  「connection を閉じる前に止まっている hart の値を戻す」「覚える契機は hart が止まっているのを最初に見た op」を明文化。

### 3. ★ lease 切れ後の黙った「再開」で、資源の消失を host が知れない
- 場所: core §6.2（空き + 最後の session_id → 再開）、§9、§6.5。
- 問題: host が止まって lease が切れると、次の 0x81 要求はそのまま処理されるが plan / connection / 購読は消えている。boot_id は
  同じなので検出できず、以後の no_connection / unavailable の理由を host は推測するしかない。
- 案: (a) 推奨: 期限切れ後の最初の 0x81 要求は rejected（新 reason `expired` か no_session）で open を強制し、open の応答に
  「資源を外した」ビット（resumed と別）を足す。(b) 再開を許すなら lock_state / 応答に「期限切れを経た」印を定める。

### 4. ★ probe-config の hash と「後ろに足す」規則の相互作用
- 場所: probe-config §2（hash = 正規形の CRC-32）、§1.2、core §2.3。
- 問題: 新しい host が項目の後ろにフィールドを足して送ったとき、古い probe が保持するか切るか、新しい probe が自分で足した
  後ろを get / hash に出すかが無い。どちらかが切ると host の hash と一致せず「同じなら何もしない」が永久に外れる。
- 案: 推奨: 「probe は host が送った項目のバイト列をそのまま持ち、get と hash はそのまま出す（critical bit を外すだけ）。probe が
  自分で足す後ろは無い」。保存容量もそのバイト数で数える（→ 6）。

### 5. ★ fixture UART の設定（baud / format）の出どころが無い
- 場所: probe-config §1.2 bind kind 2、fixture §2（configure はセッションの操作）、probe-cdc §7.3、旧 v1-core-wire-delta §5.10。
- 問題: plan + bind を保存して再起動しても、host が configure するまで UART は掛からず、口に何も流れない（P4 の試作で踏んだ）。
  CDC の line coding（Monitor の baud）を UART に写すのか無視するのかも規範に無い。ストリームの寿命（plan が作るのか configure が
  作るのか、plan を解いて再び plan すると位置が 0 に戻る）も曖昧。
- 案: (a) 推奨: 設定の項目 `uart`（fn(u16), baud(u32), format(u8)、キー fn）を足し、起動時に configure 相当を掛ける。保存の
  読み替え対象の fn にも入れる。「ストリームは plan が作り、plan を解くと消える」を明記。(b) 口の line coding を写す規則を
  規範にする（「最後に来た方が勝つ」。無視する probe を禁止）。どちらでも「line coding は写す / 無視する」を明記。

### 6. storage の「保存できる最大 byte」の単位と、hash の時点
- 場所: probe-config §4 0x40 storage、§2。
- 問題: 保存の形は probe 固有なので host は自分の設定が入るか判定できず、set は通って save だけ失敗する。保存の hash が「保存時の fn」か
  「起動時に読み替えた後の fn」で計算されるかも無く、firmware 更新で fn が入れ替わると get.hash と食い違い、host が誤って save し直す。
- 案: 「最大 byte は項目の正規形（hash の対象）の byte 数で、その長さ以下なら必ず保存できる（識別子の表の分は probe が差し引く）」
  「storage の hash は読み替え後の今の fn で計算し直した値。読めない保存では 0」。保存なし（最大 0）の probe では save / erase は
  rejected unsupported、erase 後は状態 0、hash 0。

### 7. slot の mechanism に「なし」が無く、swd の線をスロットにできるか不明
- 場所: probe-config §1.1（mechanism u8 必須、wire_fn は rvswd / swio と書く）、debug §2.1 / §5、registry swd の `connection_users.slot`。
- 問題: at-boot attach だけ使うスロット、console を持たない probe はどの値も通らない。swd は target_id scheme を持たないので錠が
  成り立たないが、registry と debug 文書は swd にスロットが乗るように見える。swd 接続への console open の理由も無い。
- 案: mechanism 0xFF = コンソールなし を定義。v1 は「wire_fn は target_id scheme を持つ線に限る。ほかは rejected unsupported」
  と書き、swd の `slot` ビットは常に 0 と注記（DPIDR を scheme 2 にするのは後から enum 追加で足せる）。swd 接続への console open は
  rejected unsupported。arm 側の非対称（halt / run が無い、など）は §5 / §6 に「意図したもの」として一覧にする。

### 8. ★ キャプチャの位置の空間が start ごとに 0 に戻り、host が見分けられない
- 場所: capture §2 segment position、§3.2 read / status、common §1.1（位置が戻るのは起動だけ、と食い違う）。
- 問題: start し直すと position と serial が 0 から。古い read が新しいデータを黙って返す。status に世代が無い。
- 案: (a) 推奨: status と segment の後ろに `generation(u32)`（start ごとに増える）を足す。(b) 「position は boot の中で戻らない
  （start で続きから）」に変える。

### 9. ★ トリガの数の意味（samples、pretrigger、trigger_index、force、value の幅）
- 場所: capture §3.3 TLV 0x43 / 0x45 / 0x46、§2 trigger_index、§3.2 force、§3.4 triggered、§1.2 `b ≤ 32`。
- 問題: samples はプリトリガ込みの総数か。トリガが早く立ちプリトリガ分が足りないときどうするか。force / type 0（即時）で
  trigger_index と triggered はどうなるか。type 3/4 の value は o/b で切り出した後の値か。value(u16) は b > 16 の ADC を表せない。
- 案: samples は総数、足りないときは短い区画（trigger_index がそのまま小さい）、force は trigger_index = その瞬間で triggered を送る、
  即時は triggered を送らない、value は切り出し後の値で **u32 に広げる**。zero(i32) も b = 32 を表せないので b ≤ 31 に縛るか i64。

### 10. ロジックのチャンネル数の上限が自己矛盾（役割 0〜127 vs w ≤ 32）
- 場所: capture §1.1（w は 1〜32、pos[k] < w）、§3.1（役割 0〜127）、§3.5 channels、logic-capture §0.1「128 本まで」。
- 問題: pos が互いに異なり w 以下なので C ≤ 32。役割 0〜127 を plan で受けても基本 layout では表せない。
- 案: w に 64 / 128 を足し（describe channels のビット 6 / 7）、「w ≥ 8 は w/8 byte の LE」の規則で一般化。probe の上限は describe で縛る。

### 11. segments の応答に more が無い
- 場所: capture §3.2 segments、common §1.3 marks（more あり）。
- 問題: 区画情報は 34 byte で min_max_frame 64 なら 1 個しか入らず、count が少ないのが「もう無い」か「入らなかった」か分からない。
- 案: marks と同じく `more(u8), count(u8), …` にする。

### 12. attach_under_reset の応答に flags が無い
- 場所: debug §3 表、§1（既存の connection は flags bit1）。
- 問題: attach は `connection, DMSTATUS, flags, speed_hz`、attach_under_reset は `connection, dpc, speed_hz`。既存接続に乗った印、
  havereset の確認を返せない。
- 案: `flags(u8)` を足して attach と並べる。

### 13. run の「止められなければ payload `status(u8)` だけ」が core §2.3 と矛盾
- 場所: debug §4.4、core §2.3（固定部分より短い応答は壊れた応答）、common §3。
- 案: 常に同じ形で返し、`stopped` に 2 =「止められなかった（dpc と値は無効）」を足す。

### 14. connection 番号の空間（wire ごとか probe 全体か）と、資源番号の使い切り
- 場所: common §2、debug §2.1 / §4、core §9（u16、同じ boot_id の間は再利用しない）。
- 問題: wire ごとに 1 から振ると、riscv-dm の要求（connection だけで wire の fn を持たない）が rvswd の #1 と swd の #1 を区別できない。
  別種の connection を渡したときの理由も無い。また at-boot の retry や抜き差しで 65535 を使い切ると再起動まで新しい資源が作れない。
- 案: 「connection と stream の番号は probe で 1 つの空間」「対応しない種類の connection は rejected unavailable（cause 6）」
  「使い切ったら一周を許し、直近に閉じた番号から十分離れたものを再利用してよい（§2.6 の比べ方）」。失敗した attach は番号を消費しない。

### 15. ★ インターフェース名の最大長と list の entry の len(u8)
- 場所: core §7.2（`count × (len(u8), entry)`、name_len(u8)）、§13.1（逆 DNS の独自名）。
- 問題: entry は 255 byte 以内だが name の上限がどこにも無い（固定部 7 byte を引いて 248 まで）。長い独自名の probe が壊れた応答を出す。
- 案: 名前は 1〜64 byte（`a-z 0-9 - .`）と core §13 に明記。probe-config の保存にも効く。

### 16. ★ USB の口の見分け方が composite device で誤りうる / PID 取得前後で規範が変わる前提
- 場所: core §3.3（class 0xFF の bulk 組 = vendor bulk、vendor usage page の HID）、§7.5 oep_pid、usb-identity §3 / §4。
- 問題: ESP32 の USB-Serial/JTAG も class 0xFF の bulk 組を持つ。WebUSB など別の vendor 機能を持つ firmware もありうる。
  決定 3(b) の「iInterface が `OEP` で始まる」は core に入らず、逆に「interface の文字列は見分けに使わない」になっている。
  PID 取得後に core §3.3 / §7.5 を書き換える計画で、独自実装（自分の VID:PID）が discovery に出る手段が iProduct 以外に無いのに、
  その判定を消すことになっている。USJ の serial は firmware が選べず serial ≠ unit_id になるが例外が書かれていない。
- 案: vendor bulk は class 0xFF かつ bInterfaceSubClass / bInterfaceProtocol を OEP 固有の値に固定（または iInterface `OEP` 接頭を
  規範に）、HID は usage ID まで固定。「iProduct が `OEP` で始まる device は OEP の probe」を恒久の規範にし、プロジェクトの VID:PID は参照
  firmware の値として実務文書に置く。「serial = unit_id は probe が serial を選べる口に限る。unit_id は個体で一意、固有番号の無い
  probe は乱数を保存して使う」。

### 17. アナログの換算の前提（scale はどこの電圧か、vrefint の公称値）
- 場所: capture §1.2 規則 4、§3.3 TLV 0x55 scale / 0x58 frontend_used / 0x59 reference、§3.8 vrefint。
- 問題: scale_nv が前段の減衰を含む「probe の入力ピンの電圧」か ADC 入力の電圧かが無い（attenuation を重ねて掛けると二重）。
  vrefint は raw と時刻だけで公称電圧が無く、電源電圧を逆算できない。
- 案: 「scale と zero はピンの電圧への 1 次式（減衰込み）。attenuation は表示用」。vrefint に `nominal_mv(u32)` を足す。

### 18. マークの時刻 ms(u32) とキャプチャの ns(u64) が揃わない
- 場所: common §1.3 time_ms、core §11.2 uptime_ms、capture（起動からの ns、u64）、probe-config last_try_ms。
- 問題: コンソールのマークとキャプチャの区画を同じ時間軸に並べられず、u32 は 49 日で一周する。
- 案: mark の time を `time_ns(u64)` にして capture と同じ時計にする（len 付きの要素なので後からも足せるが、今なら必須にできる）。

### 19. 「削除はキーだけの項目」が core §2.3 の「短ければ壊れた値」と衝突
- 場所: probe-config §2、core §2.3。
- 問題: slot(u8) 1 byte だけの項目が「削除」か「壊れた項目」か、規則が 2 つある。キー長と全長の間（slot 項目 5 byte）の扱いも無い。
- 案: probe-config に明示の例外「長さがキーの長さにちょうど等しい項目は削除。キーより長く固定部より短ければ malformed」。
  あわせて core §2.3 に「可変の部分を含む固定の形では、知っている最後のフィールドの終わりより後ろを飛ばす」を一言。

### 20. ロック無しで boot_id を知る手段が無い / ストリームの一覧が無い
- 場所: core §6.5（open の応答だけ）、§11.2（heartbeat は購読 = ロック）、console §1 / §2、debug §2.1（connections はある）。
- 問題: 読むだけの host（Monitor、discovery）は probe の再起動を検出できず、覚えた fn 対応・位置・接続番号が無効になったことに
  気付けない。閉じたストリームや bind が開いたストリームの番号を知る op が open（ロック + connection 必要）しか無い。
- 案: lock_state の応答か fn 0 の describe に boot_id を足す（boot_id = 0「不明」は禁止）。connections と同形の `streams` op
  （ロック不要、`count × (len, stream, connection, mechanism, users, state)`）を足す。任意の op なので後からも足せるが、Monitor の
  基本動線なので v1 に入れる価値がある。

### 21. 出来事 kind の番号がトラックと group で揃っていない
- 場所: registry logic / analog（segment 1、stopped 2、triggered 3）、capture-group（triggered 1、stopped 2）。
- 案: group を triggered 3、stopped 2 にする（fn ごとの空間なので違反ではないが、揃えられるのは今だけ）。

### 22. gpio の modes ビット集合（u8）が 0〜7 で満杯
- 場所: fixture §1 describe modes。
- 案: 今 u16 か u32 にしておく（TLV の len で区別できるので後からでも広げられるが、読み手の規則が要る）。

---

## B. 中: 意味が曖昧で実装が割れる（状態機械・責任分担）

### 23. console ストリームの寿命: lease 切れ、bind と共有しているときの close、slot の置き換え
- 場所: console §2、common §2、core §9、probe-config §1.1 / §1.2。
- 問題: lease 切れでストリームを閉じる（吸い出しが止まり dmseq の target が詰まる）か残るかが読めない。bind が開いたストリームに
  host が open して close すると bind の分まで閉じるのか。slot のピンを変えて set した・消した・bind から外したとき、接続と
  コンソールをいつ閉じるかが無い。閉じた理由のマークも無い。
- 案: ストリームにも connection と同じ「使っているもの（セッション / スロット）」の数え方を持たせ、close と lease 切れは自分の分を
  外すだけ、全員が外れたら閉じる。「項目の置き換え・削除で、そのスロットが使っていた接続からスロットの分を外し（ほかに無ければ閉じる、
  target は reset しない）、開いていたコンソールは閉じる」を probe-config に足す。閉じた理由のマーク（detail）を決める。

### 24. 同じ connection に別 mechanism のストリームを開ける
- 場所: console §2 / §3。3 方式とも DATA0 を郵便受けにする。
- 案: 「1 つの connection に生きているストリームは 1 つ。別 mechanism の open は rejected unavailable（cause 6）」。

### 25. console write の「バッファしない」と dmseq / DMDATA の pending の矛盾
- 場所: common §1.4、console §2 / §3.2、target-console-dmseq の `pending`。
- 問題: dmseq と DMDATA は host → target の数 byte を次のフレームまで持つ。write が「次の答えに載るまで待つ」のか「枠に入れたら
  accepted」なのか不明。accepted = 0 のときの outcome（failed か partial か）も共通部品に無い。
- 案: 「accepted は方式の送り枠に入れた分。届いたことは意味しない。枠が空いていなければ accepted 0 = completed failed。
  0 < accepted < count は partial」。common §1.4 の「バッファしない」を「方式が 1 枠だけ持つ」に直す。

### 26. 長く塞ぐ要求（run、dmi の wait、capture の blocking、save）と lease / heartbeat / 他経路
- 場所: debug §4.1 / §4.4、capture §3.2 blocking_ms、probe-config §2 save、core §6.1。
- 問題: run は 49 日、dmi の wait は 71 分まで指定でき、その間 probe は何にも答えず keepalive もできない（lease 最大 60 s）。
  終わった時点でセッションが失効して connection が閉じる。ほかの connection の dmseq も TO で出力が捨てられる。save の最長時間 > lease
  の probe も作れる。引数に時間を持たない op（attach、configure）の待ちの上限も無い。
- 案: core に「probe は 1 つの要求に N ms（例 2000）以上かけない。超えうる op は要求か describe で時間を宣言（`max_wait_ms`）し、
  超える指定は rejected unsupported、その間 lease は切れない」。「save の最長時間は lease の上限より短い」。save は丸ごと置き換え
  （途中で電源が落ちても前か新しい保存のどちらかが読める）を規範に。

### 27. 複数経路で同一セッションの要求が逆転すると §5.2 が誤判定する
- 場所: core §3.3、§5.2（表に無く最新 corr より新しくなければ result_lost）。
- 案: 「1 つのセッションの role 0x81 の要求は 1 つの経路で送る（読むだけの 0x01 は別経路でよい）」を §3.3 に書く。

### 28. §6.2 の判定表の抜け
- 場所: core §6.2 / §6.4。
- 問題: 「自分がロックを持つ + 同じ ID の open（force なし）」の行が無い。「空き + 同じ ID の再開」の lease_ms。open が rejected
  locked のときも §5.2 の表を捨てるのか。
- 案: 2 行を足し、「表の破棄は成功した open だけ」「再開の lease は前の open の値」と明記。

### 29. describe のページングが動的な内容で抜け・重複する
- 場所: core §7.3（first = TLV の番号）、probe-config §4（slot_state、bind_state、storage の hash が describe に入る）。
- 案: 「同じ boot の間、宣言の TLV の順は安定。状態の TLV は宣言の後ろにまとめる」か、状態を別 op に移す。get の並び順と first の
  意味（正規形の順、どのページも同じ hash、hash が変わったら読み直す）も probe-config に書く。

### 30. instance の振り方が未定義なのに保存が (name, instance, revision) で指す
- 場所: core §7.2、probe-config §2。2026-10-01 に firmware と fake を「名前ごとに 0 から」に揃えた。
- 案: 「instance は fn の昇順で 0 から。probe は同名の口の順を firmware の版を越えて保つ」と明記。

### 31. 線切れ判定（1000 ms）の実行主体と、判定後の応答
- 場所: debug §2、common §3。
- 問題: idle な connection を probe が監視するのか（しなければ電源断の target の connection は永遠に生きる。slot_state の「いない」
  判定、retry_s に影響）、再試行の速度が speed_hz を変えるのか、判定した op の応答と connection が消える順。
- 案: 「判定は要求（またはコンソールの読み）の中でだけ行う」「再試行中の速度は一時的」「判定した要求は status line で返し、connection
  はその応答の後に閉じる」。

### 32. scan の未定義: tried = 0 の二義、「見つかった」の判定、試した後のピンと DM の状態
- 場所: debug §1、§3、probe-development-guide §4。
- 問題: 「途中で止めてよい」と「tried = 0 が終わり」が同時にあり、1 組目に時間がかかると host が打ち切る。何を見つかったとするか
  （DMSTATUS.version）、scan が dmactive を書くか、外れた組のピンを空きの状態に戻すか、が無い。
- 案: 「並びに組が残っていれば少なくとも 1 組は試す。tried = 0 は使い切ったときだけ」「見つかった = DMSTATUS.version が 2 か 3」
  「scan で書くのは dmactive だけで、終わったら元に戻す」「外れた組は空きの状態に戻す」。

### 33. reset の線の駆動方式と終了後の状態（安全）
- 場所: debug §3、host-development-guide §4.6。
- 案: 「reset の線はオープンドレインで low に引き、離すときは駆動をやめる（core §8 の空きの状態）。channel は op の間だけ持つ」を規範に。
  失敗時の status の対応（止まらない = timeout、DM が応えない = line、cmderr = fault）も表に。

### 34. SWD の未定義: targetsel の critical 性、multidrop の scan、速度の既定、再同期
- 場所: debug §5、registry `oep.wire.swd`。実装が薄い今が形を直す最後の機会。
- 案: targetsel を critical 必須に、scan の TLV に targetsel（または「multidrop は scan に出ない」の明記）、「speed は
  min(max_speed, max_clock_hz)。max_speed 無しは rejected malformed」、line reset / dormant 起こしのやり直しの手順。

### 35. arm-adi の block op の前提、done の意味、ack の符号化
- 場所: debug §6。
- 案: 「arm-adi の block は hart の状態を問わない」「done は probe が送った語数で target が受けた保証ではない」「ack は線の順で bit0 が
  最初（OK=1, WAIT=2, FAULT=4, 無応答 = status line）」「req の上位 4 bit は 0、ほかは malformed」。

### 36. attach の TLV の必須性（max_speed、idle_clock、pins）
- 場所: debug §1 / §3、core §2.3。
- 案: 「max_speed は必須（無ければ rejected malformed）。idle_clock と pins は任意、送るときは critical」と表に書く。
  idle_clock = 1 を rvswd 以外に送ったときの理由を attach（unsupported）と slot 項目（malformed）で揃える（unsupported を推奨）。

### 37. havereset を見たとき・sysbus の扱い・halt / resume の内部待ち
- 場所: debug §4.2 / §4.5、target-console-dmseq。
- 案: 「havereset を見たら覚えた値を捨て、dmseq の状態を未同期に戻し、mark restart を付ける」「sysbus を使ってよい。SBCS / SBADDRESS は
  戻さない」「halt は allhalted を見たら haltreq を下ろす。resume は haltreq = 0、resumereq = 1 を 1 回書く。待ちは目安 100 ms」。

### 38. リピートの「止まった（state 5）」からの復帰
- 場所: capture §2 表、§3.2 state 5、§3.4 stopped reason 2、§3.7。
- 問題: release で自動再開するのか host が start し直すのか（start し直すと serial と position が 0 に戻る）が無い。
- 案: 「release で空きができたら probe は自動で再開し state は 3 に戻る。再開の区画は flags bit0。stopped reason 2 は送らない」。
  release の `serial 以前` が inclusive かも明記。

### 39. 落としたデータの通知: write_pos に捨てた分を含むか、status flags はいつ消えるか
- 場所: capture §3.2 / §3.4、logic-capture §2.4 / §7.9。
- 案: 「write_pos は position の空間で捨てた分を含む（次に書くバイトの位置）。flags は start で 0 に戻し、その回の累積」。

### 40. capture-group と各トラックの状態・寿命の整合
- 場所: capture §4.1〜4.3、core §4.3 cause 4、§8 / §9。
- 問題: bind はセッションの資源か。束ねた fn の plan 操作を断ることが group の文書に無い。取得中の bind n = 0、start の原子性、
  start 前の start_ns、trigger_track 以外のトラックも triggered を送るか、group の features。
- 案: 「bind はセッションの資源、ロック喪失で解く。束ねた fn の plan 操作は unavailable cause 4。n = 0 は state が 3 以外のときだけ。
  start は全トラックの前提を確かめてから始め、始めた後の失敗は state 6 と stopped reason 3。start 前の start_ns は 0xFFFF…。
  triggered は group と各トラックの両方に出る。features は capture と同じビット」。

### 41. rate と describe の値の形
- 場所: capture §3.3 rate、§3.5 trigger / rate_limit / rate_list。
- 問題: trigger の「type のビット集合」の幅が無い。rate_limit の channels は「以下」か「ちょうど」か。rate_list は 1 TLV か繰り返しか。
  rate は exact = 0 のとき最も近い値か切り下げか、どこまで離れてよいか、範囲外の reason。
- 案: trigger は `types(u32), max_pretrigger(u32)`、rate_limit は「C ≤ channels のときの上限」、rate_list は 1 TLV（足りなければ繰り返し、
  和集合）、rate は「範囲内なら最も近い実現可能な値、範囲外は unsupported」。P4 の 48 kHz 以上の重複は rate_limit で C ごとに上限を下げる。

### 42. i2c-target / spi-target の未定義（ESP32 の挙動が事実上の仕様になる前に）
- 場所: fixture §3 / §4。
- 問題: i2c: mode 2 の長さ byte と本文は同じトランザクションか、mode 3 で置き場が空のとき何を出すか、stretch の位置、reset が何を
  するか、列の深さの宣言、pending / queued (u8) の飽和。spi: CS の極性、未 arm の転送の扱い、length より長い転送、tx の外の MISO。
- 案: 各点を 1 行ずつ決める。reset は「configure 直後と同じ状態（列と累計を消す、mode は保つ）」。列の深さは describe の 0x40 tag。
  「CS は low で有効。未 arm の転送は MOSI を捨て transactions と errors を数える。length を超えた分は捨てる。MISO は tx の外では 0」。
  u8 の数は 255 で止める。

### 43. UART の format の未定義の値、baud の丸め、受信誤りのマーク
- 場所: fixture §2 format / baud、common §1.3 lost。
- 案: 「未定義の値は malformed、format は critical で送る、baud は actual を返し ±5% を超えれば unsupported、lost の detail: 1 あふれ、
  2 framing、3 parity」。

### 44. subscribe の断り方が 2 通り
- 場所: core §11 / §11.3、console / fixture「subscribe は rejected unavailable」。
- 案: 「fn 0 の subscribe / unsubscribe は必ず実装する。送り出さない fn への subscribe は rejected unsupported」に統一。
  「mode 3（ストリーミング）を宣言するなら features bit2 を立てる」も一行。

### 45. lock_mask / lock_value の長さ n と scheme の値の長さ
- 場所: probe-config §1.1。
- 案: 「n はその scheme の値の長さと同じでなければ rejected malformed（scheme 1 は 4）」。長さは registry の `target_id_scheme` に持たせる。

### 46. address `oep://<unit_id>/<name>` の構文がまとまっていない
- 場所: core §7.5 0x42、probe-config §1.1 name、freeze-decisions §3。
- 案: core §7.5 に小節「アドレス」を置く: 文法（scheme、authority = unit_id、path = スロットの名前 1 つだけ、v1 ではそれ以外を定めない）、
  スロット無し `oep://<unit_id>` は probe 自身、大文字は使わない。

---

## C. 中: エラーの選び方・空の結果

### 47. malformed / unsupported / unavailable の使い分けの原則
- 場所: core §4.3、fixture §1 / §3 / §4、capture §3.2〜3.3、probe-config §1.1 / §2。
- 問題: 「値域の外」「定義にあるが probe が持たない」「状態・資源」が混ざり、同じ状況で reason が違う（gpio の扱えない mode は
  unavailable + channel + index、i2c は unsupported、slot name の重複は malformed、ピンの組の重複は unavailable、など）。
- 案: core §4.3 に判定の順を 1 行で書く: 書式と値域の外（mode > 3、address > 0x7F）→ malformed、定義にあるが持たない（mode、format、
  rate の範囲外、trigger type）→ unsupported、plan・状態・資源 → unavailable（cause 付き）。各文書の行をそれに揃える。
  「設定の中の矛盾は malformed、probe の資源との衝突は unavailable」を probe-config に。

### 48. 空の結果・端の値の表
- 場所: debug §2 / §4.1 / §4.5、console §1、probe-config §1、fixture §1。
- 案: 表を 1 つ足す。推奨: 使っていないセッションの detach = ok 何もしない、閉じた stream への close = ok、dmi の n = 0 と read_block の
  count = 0 = success done 0、poll の max_reads / max_us = 0 = 1 回読む、4 の倍数でない address = malformed、swio の scan で swclk ≠ 0xFFFF =
  malformed、label / idle が無い channel や reserved の channel = unavailable（channel 付き）、未割り当て channel の gpio read = unavailable。

---

## D. 低: 文書と registry の整理

### 49. registry に無い線上の番号
- scan の `kind`（1 riscv-dm / 2 arm-adi）、riscv-dm の `features` のビット、attach / reset / read の flags、uart format のビット、
  implementation の enum、fn 0 の op の予約範囲（0x50〜0xEF、0xF0〜0xFF）、swd の `reserved.op = 0x04`、マークの detail（→ 50）。
  共通部品（read_from、mark_kind）が `oep.target.console` の下にしかなく fixture.uart から参照できない → `[common.enum.*]` を作る。

### 50. マークの detail の値
- common §1.3 は「reset = 方法、restart = 検出元、lost = 理由、host = 値」だけ。registry に `mark_detail_reset`（1 ndmreset、2 NRST、
  3 attach_under_reset）、`mark_detail_restart`（1 havereset、2 再同期）、`mark_detail_lost`（1 あふれ、2 受信誤り、3 target の TO）、
  0x40 以降はインターフェース固有。

### 51. registry のコメントの誤りと重複
- logic に analog 専用の tag（configure 0x47 frontend、answer 0x55 scale / 0x57 skew、describe 0x46 / 0x49、cross_up / cross_down）が
  載っている → 外す（「番号は同じ」の方針なら `# analog only` と注記）。capture-group に state / stopped_reason の enum が無く
  コメントが旧名 "capture"。i2c / spi の features のビットの意味が無い。rvswd の pins コメント「on one wire」。storage の
  コメント「last byte = 理由」。`max_speed` に critical の注記が無い。`tests/registry_v1/test_registry_v1.py:41` が
  `oep.fixture.capture` を探す。

### 52. 欠番を予約と書く
- core §7.5 の 0x48、capture configure の 0x41。registry の reserved に入れる。

### 53. 旧名と古い数字
- oep-if-capture の「capture」（第 4 のインターフェースに読める）、§3.7 / §4.4 の例、§4.1 / §4.2 の「capture と同じ」。
  logic-capture §4「区画の情報 29 byte」（今は 33）、§7.8 の reason、§0.1「16 ビットに詰め直す」。core §4.1「revision 1 以上だった
  probe にだけ 0x81」、§5.1「confirm の範囲は 0〜255 でよい」（v0 の残り）。

### 54. core §14 の表に i2c-target / spi-target / capture-group が無い（決定 5・7 の反映漏れ）

### 55. freeze-decisions の参照と反映メモ
- 決定 11 の表「probe-cdc §6 / §7」は open-proposals §6 / §7 の誤り。決定 3(c)（HID の report）は「記述子に任せる形で反映」と追記。
  open-proposals §6（IP）/ §7（回復）を「v1 では扱わない（決定 11）」として閉じ、README の「未対応」を更新。transport kind 6 TCP は
  「経路としては存在するが設定・発見は v1 の外」と一言。

### 56. 非規範の文書に残る「規範」の文言と古い未決
- probe-cdc §4.5 の太字「規範: …」（console §2 と食い違う）、§4.1 の自動 attach、§4.3〜4.4 の起動モード、§7.3 → 「当時の案」と括る。
  session-and-exclusivity L61-62（期限切れで資源を外す、と食い違う）、未決 2 / 4 / 5 に決定先を書く。
  probe-config §1.2 の「CDC は bInterfaceProtocol 0」は USB 記述子の細部なので開発ガイドへ。

### 57. 開発ガイドの古い記述
- host-development-guide §3「USB のシリアル番号は使わない」（決定 3 と矛盾。例が WCH-Link の話）→ 「serial = unit_id なので開かずに取れる。
  serial を持たない口では describe で読む」。発見の手順（VID:PID / iProduct → serial → 開いて unit_id で確かめる）を書く。
  probe-development-guide §3.8 の iProduct「OEP probe (P4 HS)」と serial の記述、§3.6 の「COBS 長 + 2 を超えたら生のバイト」が core §3.4 に無い。
  debug 文書の「§8.1 のとおり」は「core §8.1」。

### 58. 命名と単位の揺れ
- `max_speed`（Hz）→ `max_speed_hz`、dmi の `us` / `max_us` → `wait_us`、group の budget `max_rate` → `max_sps`、`DMSTATUS` / `DPIDR` の
  大文字、dmseq 文書の「host」（OEP の probe を指す）と「framing」（→ mechanism）。registry の名前は生成コードに出るので凍結前に。

### 59. 細かい未定義
- core §4.4 window（role の見出しを含むか）、§7.5 channels（番号は 0〜channels−1 か）、reserved 0x44 の繰り返し、§2.3 ignored
  （閉じた末尾の op では付けられない）、set の中の項目の順序（意味を持たない）と critical bit の扱い、bind の port = transport の index は
  firmware で変わりうる（注記）、mixed の印 `uart<fn>` は `name#instance` の方が安定、plan の表のキー列（(fn, role)）。

---

## E. 問題が無いと確認できた領域（要約）

- registry と文書の op 番号、ロック要否、TLV tag、event kind、enum は全インターフェースで一致。`oepgen1.py --check` は exit 0。
- 凍結の決定 1〜10、12 の反映は確認できた（bind の len は 10-01 に補った）。
- COBS + CRC-16/CCITT-FALSE、CRC-32、little endian、UTF-8 の扱いは統一。
- ビット順・サンプルの詰め方・時刻の基準（capture）、ロック無しで読める op の選び方、analog のピン共有の規則、i2c / spi の名前と役割、
  セッションの資源の寿命（end で残す / 期限切れ・force で外す）の各文書の整合、dmseq の framing、RISC-V DM のレジスタ番号と意味、
  安全の既定（attach の method と reset の mode は明示、run の無限 timeout 拒否、write_block は halt 前提）は問題なし。
- 規範の文書に「暫定 / TBD / 仮」は残っていない。「予約」は決定 11 の表どおり。
