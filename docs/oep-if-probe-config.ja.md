# OEP 標準インターフェース: probe の設定 v1

状態: **規範**（2026-09-29 に組み直し。2026-10-01 に[ゼロベースの再検討](v1-zero-base-proposal.ja.md)を反映）。本体は [OEP core](oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。経緯と
実験は [シリアルの口と永続化](probe-cdc-and-persistence.ja.md)。

| 名前 | revision | 役割 |
|---|---:|---|
| `oep.probe.config` | 1 | probe の設定（plan、ラベル、空きのピン、スロット、シリアルの口に流すもの）と、その保存 |

- **既定の値は持たない。** 項目はすべて host が設定し、probe は設定されたとおりに動く。設定されていない項目については何もしない。
- 設定を扱わない probe は、このインターフェースを list に出さない。
- 設定から入れた plan、スロットの接続、bind はセッションの資源ではない（core §9）。lease の期限切れでも外さない。
- **起動の型（モード）は持たない。** 設定はどの経路からでも同じ操作で行い、set したものはすぐ効く。設定のための再起動は要らない。

## 1. 項目

**設定 = 項目（TLV）の並び**。tag はこの文脈の空間。項目ごとに**キー**があり、同じ tag の項目はキーで見分ける。

| tag | 項目 | 値 | キー |
|---:|---|---|---|
| 0x01 | plan | fn(u16)、role(u8)、channel(u16)（1 項目 1 割り当て） | (fn, role, channel)（同じ fn の項目で、その fn の plan になる） |
| 0x02 | label | channel(u16)、text | channel |
| 0x03 | idle | channel(u16)、mode(u8: 0 Hi-Z、1 プルアップの入力、2 プルダウンの入力) | channel |
| 0x04 | slot | §1.1 | slot |
| 0x05 | bind | §1.2 | port |
| 0x06 | uart | fn(u16)、baud(u32)、format(u8)（`oep.fixture.uart` の configure と同じ値） | fn |

- どの項目もすぐ効く。扱う項目は describe の items で宣言し、宣言していない項目の set は rejected unsupported。tag 0x7E は応答の
  メタ情報のために予約。
- **plan**: その fn の plan_apply と同じ（core §8）。設定の plan は設定だけが変える: セッションの plan_release（n = 0 を含む）
  はそれを解かず、plan_apply がその fn を挙げたら rejected unavailable（core §8）。
- **label**: 設定で付けた channel の名前。get で読む（core の describe の label（0x46）は firmware が持つ固定の名前で、設定では
  変わらない。host は両方を合わせて使う。core §7.3: describe は宣言だけ）。
- **uart**: その fn（`oep.fixture.uart`）の plan に RX か TX が付いた時点（設定の plan でも、セッションの plan_apply でも）で、
  configure 相当を掛ける。plan が無くても set は通る（掛かるのは plan が付いたとき）。セッションの configure は、plan を解くか
  probe が再起動するまで、この項目より勝つ。baud は set のときに実現できる値を確かめ、±5% を超えて外れれば rejected unsupported。
  format は configure の TLV format と同じ値（未定義のビットは rejected malformed）。ピンの無い fn の configure は今どおり
  rejected unavailable（項目があっても変わらない）。CDC の口の line coding は fixture UART に写さない（OEP の configure とこの項目
  だけが効く）。
- **idle**: plan にも接続にも使われていないピンの状態。起動時と、そのピンが解放されるたび（core §8）に、この状態にする。
  idle が無いピンは Hi-Z。治具の配線で相手の入力が浮くピン（相手の RX につながる TX など）は、host が idle で明示し、保存する。

### 1.1 slot（スロット）

スロットは、target のつながる**場所**の登録である（チップの登録ではない。チップを付け替えても登録は直さない）。

```text
slot(u8)、wire_fn(u16)、swdio(u16)、swclk(u16)、attach(u8)、retry_ms(u32)、max_speed_hz(u32)、idle_clock(u8)、mechanism(u8)、
name_len(u8)、name、
lock_len(u8)、lock_scheme(u8)、lock_mask(n byte)、lock_value(n byte)
```

lock_len は錠の部分（lock_scheme から lock_value まで）の長さ。0 は錠なし（lock_scheme 以降を置かない）。錠の後ろは、後から
足すフィールドの場所（core §2.3。読む側は知らない後ろを飛ばす）。

| フィールド | 意味 |
|---|---|
| slot | スロットの番号（キー）。0 から、describe の slots_max 未満 |
| wire_fn | 線のインターフェースの fn。**target_id の scheme を持つ線**（`oep.wire.rvswd` / `oep.wire.swio`）だけ。ほか（`oep.wire.swd`）は rejected unsupported |
| swdio、swclk | ピンの組。attach の pins と同じ（1 本の線は swclk = 0xFFFF）。その線が許す組でなければ rejected unsupported |
| attach | attach の方針: 0 host、1 at boot（§3.1） |
| retry_ms | at boot のスロットで、いないときに attach をやり直す間隔（ms）。0 はやり直さない。at boot でなければ 0（ほかは rejected malformed） |
| max_speed_hz | そのスロットの attach に渡す線の速さの上限（Hz、attach の max_speed と同じ）。0 は上限なし。その線が守れない上限（決まった速さがそれより速い、min_clock_hz より遅い）は rejected unsupported |
| idle_clock | そのスロットの attach に渡す線の休ませ方（attach の idle_clock と同じ: 0 = high、1 = low）。`oep.wire.rvswd` だけが 1 を持てる（ほかの線で 1 は rejected unsupported。attach と同じ） |
| mechanism | コンソールの方式（`oep.target.console` の mechanism）、または **0xFF = コンソールなし**（bind に載せない、console を持たない probe）。その probe の console が宣言しない方式は rejected unsupported |
| name | スロットの名前。1〜32 byte で、使える文字は `a-z 0-9 - _` だけ（ほかは rejected malformed）。probe の中で重ならない（重なれば rejected malformed）。host がスロットを名指すのに使い（IDE の address `oep://<unit_id>/<name>` にそのまま入る。unit_id は core §7.5。どちらも URL の中で encode が要らない文字だけ）、mixed の行の印（§1.2）にも使う |
| lock_len | 錠の部分の長さ。0（錠なし）か 1 + 2n（n ≥ 1）。ほかは rejected malformed |
| lock_scheme | 錠があるときだけ。target_id の scheme（[線とデバッグ](oep-if-debug.ja.md) §1）。0 は置かない（錠なしは lock_len 0）。定義にあるがその線が持たない scheme は rejected unsupported、未定義の値は malformed |
| lock_mask、lock_value | 錠があるときだけ。同じ長さ n = (lock_len − 1) / 2。**n はその scheme の値の長さと同じ**（scheme 1 は 4。違えば rejected malformed。長さは registry の `target_id_scheme`）。バイトの並びは attach の応答の target_id の値と同じ（scheme 1 なら u32 の little endian） |

- max_speed と idle_clock は target の性質で（[線とデバッグ](oep-if-debug.ja.md) §3）、probe が自分でスロットを attach するとき
  （at boot、やり直し）に使う。host の attach はそれぞれの TLV で自分の値を渡す（スロットの値は使わない）。
- 同じ wire_fn と同じピンの組のスロットを 2 つ作れない（設定どうしの矛盾: rejected malformed）。
- **スロットの項目を置き換えた・消したとき**: そのスロットが使っていた接続からスロットの分を外し（ほかに使うものが無ければ閉じる。
  target は reset しない、[線とデバッグ](oep-if-debug.ja.md) §2）、bind で開いていたコンソールのスロットの分を外す（mark closed 3）。
  置き換えた項目が at boot なら、新しい組で attach をやり直す。
- **スロットの接続**: 生きている接続のうち、wire_fn が同じでピンの組がスロットと一致するもの（誰が attach したかは問わない）。
- **錠**: スロットの接続の target_id（attach の応答の TLV 0x10）が、scheme が lock_scheme と同じで、値と lock_mask のビットごとの
  AND が lock_value と一致するときだけ、錠が合う。錠の無いスロットは常に合う。比べ方（どのビットを無視するか）は host が mask で
  決める（例: WCH の chip_id でリビジョンのビット [7:4] を無視するなら mask 0xFFFFFF0F）。
- **at boot のスロットの数は、wire_fn ごとに、その線の max_connections まで**（[線とデバッグ](oep-if-debug.ja.md) §1）。超える set
  は rejected unavailable。スロットの並びの順は意味を持たない。
- 登録できる数は probe が describe の slots_max で宣言する。

### 1.2 bind（シリアルの口に何を流すか）

```text
port(u8)、mode(u8)、selected(u8)、n(u8)、n × (len(u8)、kind(u8)、id(u16))
```

| フィールド | 意味 |
|---|---|
| port | シリアルの口の番号（core の describe の transport の index）。シリアルの口でなければ rejected unsupported。firmware の更新で USB の構成が変わると index も変わりうる（bind を見直す） |
| mode | 0 last-reset、1 manual、2 mixed（下）。describe の bind_modes に無い mode は rejected unsupported |
| selected | manual の選択（並びの中の番号、n 未満。外れていれば rejected malformed）。last-reset と mixed では 0 を送り、probe は見ない |
| n、並び | 流すストリーム（n ≥ 1）。各要素の前に要素の長さ len を置く（応答の並びと同じ形、core §2.3）。len は 3 以上（3 未満は rejected malformed）で、probe は 3 byte より後ろを読み飛ばす。host は今は 3 を送る。kind 1 = スロットのコンソール（id = slot）、kind 2 = fixture UART の受信（id = `oep.fixture.uart` の fn）。無いスロットを指せば rejected malformed（設定どうしの矛盾）、fn が無ければ unknown_function、fn が `oep.fixture.uart` でなければ rejected unsupported。mechanism 0xFF のスロットは載せられない（rejected malformed） |

| mode | 口に流すもの | 口から来た生のバイト |
|---|---|---|
| **last-reset** | 選ばれているストリーム。選択は、並びの中のスロットの target を host が reset したときにそのスロットへ替わる（下）。起動時と set の直後は並びの先頭 | 選ばれているストリームへ |
| **manual** | selected のストリーム。替えるのは bind の set だけ | 選ばれているストリームへ |
| **mixed** | 並びのすべて。ストリームごとに行をため、行が閉じたら `[name] ` を前に付けて流す | 捨てる（受信専用） |

- **host の reset として数えるもの**: スロットの接続の上の `oep.target.riscv-dm` の reset と、`oep.wire.*` の attach の reset TLV
  （[線とデバッグ](oep-if-debug.ja.md)）。probe 自身の attach、target の自己リセット、dmi で書いた ndmreset、`oep.fixture.gpio`
  などで動かしたリセットの線は数えない。選ばれた target の接続が切れても、選択は替えない。
- 並びが 1 つなら、どの mode でもそれが流れる（1 つのときと 2 つ以上のときで動きが変わらない）。
- **mixed の行**: LF で閉じる。閉じない出力は、probe が決めた量（目安 128 byte）か静けさ（目安 100 ms）で閉じる。name はスロットの
  name。fixture UART は、その fn の plan の RX の channel に label（§1）があればその label、無ければ `name#instance`（core §7.2、
  例 `oep.fixture.uart#1`）。
  label を印にするとき、probe は `]` と 0x20 未満のバイト（CR、LF など）を `_` に置き換える（label の項目そのものは制限しない）。
  行の前後は、target どうしでは行が閉じた順（機械で読む用途には向かない）。
- **口から来た生のバイト**（core §3.4 の、フレームの外のバイト）は、選ばれているストリームの相手（コンソールなら console の write、
  fixture UART なら TX）に、相手が受け取れる分だけ渡す。受け取れない分は捨ててよい。
- **口の位置**: probe は bind ごとに、流すストリームの中の位置を持つ。口が受け取れる分だけ進め、口が読まれていなくても
  ストリームは捨てない。ストリームが口より丸ごと先に行ったら（あふれ）、口は残っている一番古いバイトまで飛ぶ。
- **セッションの間**（core §3.4 で生の転送を止めた口）: 位置は進めない。セッションが終わったら、流すストリームごとに、
  **そのセッションで host が最後に reset した時点の位置**から再開する（上の「host の reset として数えるもの」のどれか。コンソールの
  ストリームではその reset のマーク（[共通部品](oep-if-common.ja.md) §1.3）の位置、fixture UART ではその時点の受信の位置）。
  そのセッションで reset が無ければ今から。mode に関係なく同じ。
- スロットのストリームは、そのスロットがどれかの bind の並びにあり、スロットの接続があって錠が合う間、probe がその接続で
  コンソールを開いて流す。どの bind にも無いスロットのコンソールを probe は開かない。同じ connection と mechanism のストリームが
  あればそれを使う（[コンソール](oep-if-console.ja.md) §2）。bind はどの接続にも乗る（host が attach した接続にも）。この開いたコンソールは、スロットがその接続を使っているものに数える（[共通部品](oep-if-common.ja.md) §2）。
- fixture UART のストリームは、接続が無くても、その fn の plan に RX がある間は流れる（ストリームは plan が作り、plan を解くと消える。
  位置は起動の中で戻らない、[共通部品](oep-if-common.ja.md) §1.1。口の位置はストリームが消えたら進めない）。baud / format は uart の
  項目（§1）か、セッションの configure。
- DTR / RTS / 1200 baud の touch と CDC の line coding では何もしない（target も probe も reset せず、attach もせず、baud も変えない）。

## 2. 操作

| op | 名前 | 要求 | 応答 | ロック |
|---|---|---|---|---|
| 0x01 | get | first(u16) | more(u8)、hash(u32)、項目の並び（今の設定）、… | 不要 |
| 0x02 | set | 項目の並び | hash(u32)、[TLV] | 必要 |
| 0x03 | save | — | hash(u32)、[TLV] | 必要 |
| 0x04 | erase | — | — | 必要 |
| 0x05 | unset | n(u8)、n × (len(u8)、tag(u8)、key) | hash(u32)、[TLV] | 必要 |
| 0x06 | state | first_slot(u8)、first_bind(u8) | §3.3（今の状態）、ロック不要 | 不要 |

- **set は、要求に含まれる項目のキーごとに置き換える**（含まれないキーはそのまま。何回かの set に分けて積み上げられる）。
  plan の項目は fn ごとにまとめて、その fn の plan を置き換える。項目の順は意味を持たない。
- **unset はキーの項目を消す**（key は tag ごと: plan は fn(u16)（その fn の plan 全部）、label と idle は channel(u16)、slot は slot(u8)、
  bind は port(u8)、uart は fn(u16)。要素に len を置くのはキーの長さが tag ごとに違うため）。検証と原子性は set と同じ。無いキーは
  何もせず成功。消したスロット・bind には §1.1 / §1.2 の後始末を適用する。
- 1 つの set の中で同じキー（plan は (fn, role, channel)）が 2 回出たら、要求全体を rejected malformed。
- set / unset の結果の設定全体が §1 の規則を満たさなければ（bind が消したスロットを指す、など）、何も変えずに rejected malformed。
- **set の原子性は、設定の検証と資源の予約（plan の適用、ピンの取り合いの確かめ）まで**。どれかが受け入れられなければ、何も変え
  ずに rejected。自動の attach とコンソールを開くこと（外の状態を変えること）は、set が済んだ後に行い、その結果は describe の
  slot_state と bind_state で分かる（巻き戻さない）。
- **probe は host が送った項目のバイト列をそのまま持つ**（critical の bit だけ外す。知らない後ろのフィールドも切らずに持つ）。
  probe が自分で後ろにフィールドを足すことはしない。
- **hash** は今の設定の正規形の CRC-32（core §5.2 と同じ IEEE）。正規形 = 項目を tag の昇順に、同じ tag の中はキー（plan は
  (fn, role, channel)）の昇順に並べ、TLV（core §2.2 の一意の符号化）でつないだバイト列。host は自分の欲しい設定から同じ値を計算し、
  get の hash と同じなら何もしない。get はこの正規形の順で first 番目の項目から返し、どのページも同じ hash を返す（変わっていたら
  host は最初から読み直す）。
- **save は host の明示的な操作だけ**で、今の設定をそのまま保存する（同じ内容なら書かない）。書いている間はほかの要求に答えない
  （core の max_op_ms の対象）。**保存は丸ごと置き換え**で、途中で電源が落ちても前の保存か新しい保存のどちらかが読める。describe の
  `max_bytes` は正規形の byte 数で、その長さ以下の設定は必ず保存できる（識別子の表の分は probe が差し引いて宣言する）。超えれば
  rejected unavailable（cause 3）。erase は保存を消す（今の設定は変えない。消した後は状態 0、hash 0）。保存の無い probe
  （max_bytes 0）では save / erase は rejected unsupported。
- **保存は、項目が指す interface を (name、instance、revision) で持つ**（fn の番号は起動ごとに変わりうるため）。指す fn は、plan の
  fn、slot の wire_fn、bind の kind 2 の id、uart の fn。起動時に、その組を今の list で探して fn を読み替えてから適用する（set と get の形は
  fn のまま）。指す interface が無いか、revision が違えば、**保存全体を適用しない**（一部だけ入れると治具が半端に動く。storage の
  状態は「あり・読めない」、理由 2）。指していない interface の追加・削除・並べ替えは、保存に影響しない。
- 保存の形（probe の中の持ち方）は probe が決める。読み替えの規則だけが規範。
- 起動時は、保存を今の設定にして（上の確かめを通ったとき）、idle を掛け、plan を適用し、uart を掛け、at boot のスロットの attach を
  始め、bind を結ぶ。保存を読めないときは適用せず、state で知らせる。

**断り方の表**（core §4.3 の順）:

| 状況 | reason |
|---|---|
| 形の誤り、同じキーが 2 回、name の文字、selected の範囲、retry_ms が host のスロットで 0 でない、lock の長さ、mechanism 0xFF のスロットを bind に載せる、無いスロットを bind が指す、同じ wire_fn と同じピンのスロットが 2 つ、name の重複 | malformed |
| 指す fn が無い（plan、slot の wire_fn、bind の kind 2、uart） | unknown_function |
| 宣言していない項目、その線が許さないピンの組、wire_fn が錠を持てない線、console が宣言しない mechanism、idle_clock 1 を rvswd 以外、守れない max_speed_hz、bind_modes に無い mode、シリアルの口でない port、uart でない fn、実現できない baud / format、保存の無い probe の save / erase | unsupported |
| plan_roles 超え、ピンや資源の取り合い、at boot のスロットが max_connections を超える、保存先が足りない | unavailable（cause 2 / 1 / 2 / 3） |

## 3. スロットの接続と状態

### 3.1 attach の方針

| attach | 接続を作る契機 |
|---:|---|
| 0 host | probe は自分から attach しない。host の attach でスロットの接続ができたら、bind はそれに乗る |
| 1 at boot | 起動時と、そのスロットの項目を set した直後。いなければ retry_ms ごとにやり直す（0 ならやり直さない） |

- **自動の attach（at boot）は止めない attach（method 0）だけ**で、スロットのピンの組で、[線とデバッグ](oep-if-debug.ja.md)
  §1 の規則どおりに行う。錠が合わなければ、コンソールを開かずに自分の分を外す（状態は錠に不一致）。
- 自動の attach は、接続に時間のかかる場合を先に払っておくもの。外れていれば、host は使うときに自分で attach する。
- 席が埋まっていて host の attach がスロットの接続を閉じた（[線とデバッグ](oep-if-debug.ja.md) §1）とき、そのスロットはそのままに
  する（at boot でもやり直さない）。次の接続は、次の起動、そのスロットの set、または host の attach でできる。
- 接続が切れた（線が落ちた）スロットは、at boot なら retry_ms ごとにやり直す。
- **生存の確認**: at boot のスロットの接続は、probe が retry_ms ごとに DMSTATUS を読んで確かめてよい（書かない）。線切れを見たら
  接続を閉じて retry に入る（mechanism 0xFF のスロットでも、コンソールの読みが無くても「いない」が分かる）。retry_ms が 0 なら
  確かめない。
- policy が host のスロットを、probe は確かめない（線を駆動しない）。

### 3.2 状態

state（op 0x06、§3.3）の slot_state はロックなしで読める。host が線を駆動せずに target の有無を知る方法はこれだけである（線を駆動しないと
つながっているかは分からない）。

| state | 意味 |
|---:|---|
| 0 | 接続あり（錠が合う） |
| 1 | いない（接続が無い。last_try_at_ns は最後に自動の attach を試した時刻） |
| 2 | 錠に不一致（接続はあるか、自動の attach で見つけて外した。target_id は見えたもの） |
| 3 | target_id が読めない（錠のあるスロットで、接続の target_id が無い） |

### 3.3 state（今の状態、ロック不要）

```text
要求: first_slot(u8)、first_bind(u8)
応答: more(u8)、storage_state(u8)、storage_hash(u32)、unreadable_reason(u8)、
      n_slots(u8)、n_slots × (len(u8)、slot_state)、n_binds(u8)、n_binds × (len(u8)、bind_state)、[TLV]
slot_state: slot(u8)、state(u8、§3.2)、connection(u16、無ければ 0)、last_try_at_ns(u64: 最後に自動の attach を試した時刻（probe の時計）、全ビット 1 は試していない)、tid_scheme(u8、0 は無し)、tid_len(u8)、tid
bind_state: port(u8)、mode(u8)、selected(u8: 今選ばれている並びの番号。mixed では 0xFF)、flow(u8: 0 流すものが無い / 1 流している / 2 セッションで止めている)
```

- storage_state: 0 保存なし、1 あり・適用済み、2 あり・読めない。storage_hash は、保存を今の fn に読み替えた後の正規形の hash
  （読めなければ 0）。unreadable_reason: 0 なし、1 形が読めない（壊れた、別の版の形）、2 指す interface が無い・revision が違う、
  3 適用が断られた（資源がぶつかる）。
- 登録したスロットを slot の昇順に first_slot 番目から、bind を port の昇順に first_bind 番目から、1 フレームに入る分だけ返す。
  more = 1 なら続きがあり、host は first に受け取った数を足してもう一度聞く。

## 4. describe

| tag | 名前 | 値 |
|---:|---|---|
describe は宣言だけ（core §7.3）。状態は state（§3.3）。

| tag | 名前 | 値 |
|---:|---|---|
| 0x40 | storage | max_bytes(u32、正規形の byte 数。0 = 保存なし) |
| 0x41 | items | 扱う項目の tag の並び（u8） |
| 0x42 | slots_max | u8。登録できるスロットの数（0 はスロットを扱わない） |
| 0x43 | bind_modes | u32 のビット: bit0 last-reset、bit1 manual、bit2 mixed。bind を扱う probe は bit0 と bit1 を必ず立てる |
| 0x44、0x45 | — | 予約（旧 slot_state / bind_state。state op に移った） |
