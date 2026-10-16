# OEP インターフェース: probe の設定 v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。本体は [OEP core](../docs/oep-core.ja.md)。番号の唯一の定義は `registry/oep-v1.toml`。

| 名前 | revision | 役割 | 対象の系統 |
|---|---:|---|---|
| `oep.probe.config` | 1 | channelのdisable/idle/label、シリアルの口の素通し、ネットワークの経路の設定、任意の保存 | どの系統にも使う |

このインターフェース自体も、各項目の採用も任意である。実行時のplan、接続、UART設定は各操作で明示し、ここには保存しない。
TCPの経路（transports §1）へ届くためのWi-Fiの接続先とIPv4の決め方は§1.3〜§1.5の項目で扱う。probe独自の設定も§1.6のとおり同じ一覧（describeのsetting）に並べて同じ操作で扱う。設定はRAM上でもよく、保存のための不揮発領域を一律に要求しない。

## 1. 項目

設定は**名前のついた項目**の集まりである。項目は名前で見分け、wireでは番号で運ぶ。fnと同じ形で、名前が意味を決め、
番号はprobeが振る（core §7.2のlistとfn番号の関係と同じ）。

- **名前**: 標準の項目は下の表の短い名前（`a-z 0-9 -`、`.`を含まない）。probe独自の項目は定義する者の逆DNSの名前（§1.6）。
  同じ名前は、どのprobeでも同じ意味と同じ値の形を表す。registryは標準の名前だけを持ち、項目に番号を割り当てない。
- **番号**: probeはdescribeのsetting（§4）を扱う項目ごとに1つ並べ、k番目のsettingを項目番号k（1から）とする。番号は同じboot_idの間変わらない。
  hostはdescribeで名前から番号を引き、番号をbootをまたいで覚えない（boot_idが変わったら引き直す）。
- **wireの形**: `number(u8)、len(u16)、key(u16)、data（len − 2 byte）`。lenはkeyとdataのbyte数。
  number 0とlen 2未満はmalformed。settingに無い番号はunsupported（payloadは受け取った番号）。
  **項目は設定データであり、操作の末尾の拡張TLVとは別の容器である。** core §2.3の未知の非critical TLVを無視する規則は外側の[TLV]に適用し、項目には適用しない。
- **キー**: どの項目もkeyで区別し、(番号、key)ごとに1つの値を持つ。keyはsettingのkeys未満（ほかはunsupported、受け取った番号）。
- **保存**: 保存はprobeの形でよいが、項目を名前で読み戻す（firmwareを更新して番号が変わっても、別の項目へ読み替えない）。

| 名前 | key | data | 形 |
|---|---|---|---|
| `label` | channel | text（1〜32byte、coreのtext） | §1 |
| `idle` | channel | mode(u8: 0 Hi-Z、1 pull-up入力、2 pull-down入力、3 出力low、4 出力high) | §1 |
| `disable` | channel | なし | §1 |
| `passthrough` | port | fn(u16)、rx(u16)、baud(u32)、format(u8) | §1.1 |
| `console-passthrough` | port | wire_fn(u16)、swdio(u16)、swclk(u16)、max_speed(u32)、console_fn(u16)、mechanism(u8) | §1.2 |
| `wifi` | entry | ssid_len(u8)、ssid、pass_len(u8)、passphrase | §1.4 |
| `ipv4` | netif（§1.3の番号） | mode(u8)、address(4)、prefix(u8)、gateway(4)、dns(4) | §1.5 |
| `rvswd-rest` | channel（その口の SWCLK） | mode(u8: 0 auto、1 high、2 low) | 下 |

- keyの範囲（settingのkeys）は、channelの項目ではfn 0のchannels、portの項目ではfn 0の経路の数、wifiではentryの数、ipv4ではdescribeのnetifの数 + 1（keyはnetifの番号で、0はunsupported）。
  channelはfirmware自身が使うchannelでもunsupported（受け取った番号）。
- 標準の項目のdataの長さが表の形と違えばmalformed。値を後ろへ伸ばさず、新しい情報は新しい名前の項目で定義する。
- labelは設定の名前で、firmwareのdescribeのlabelを変えない。probeは名前で線を動かさない。
- `rvswd-rest` は、`oep.wire.rvswd` の線の休ませ方を probe が自動で判定するのを、口ごとに止める項目（debug §3.1）。key はその口の SWCLK の
  channel。high / low はその値に固定し（自動の判定をしない）、auto と項目が無いことは自動の判定を表す。attach の idle_clock の TLV がいつも優先する。
  自動の判定をする probe は、この項目を setting に並べる。
  3 以上の mode は unsupported（受け取った番号）。
  線の役目として名前を使うhostの慣行は[hostガイド](../docs/host-development-guide.ja.md) §5.3。
- disableはそのchannelの駆動/設定を行わない指定で、起動時と解放時の空き状態の設定より先に効く。
  firmwareの宣言を広げず、無効なchannelを使う要求はunavailable cause 5。
  使用中のchannelをdisableするsetはunavailable cause 1。変更後の設定で同じchannelにidleとdisableが併存するsetは、設定の使用制限との競合としてunavailable cause 5で断る。
  設定・世代・ピンは変えない。併存を解くには、先に競合する項目をunsetする。重複キーや項目の長さの誤りはmalformedのままである。
  disableをunsetしたchannelは、ただちに空き状態へ戻す。
- idleは空きのchannelの状態（core §8）。空きのchannelへの変更はただちに効き、使用中なら次に空きになったときに効く。
  idleが無いchannelはHi-Z。mode 3/4の出力の強さはprobeが決める。
  対応しないpull/出力/未知のmodeはunsupported（受け取った番号）。出力idleを取得できる機能は各インターフェースに従う。

### 1.1 passthrough（シリアルの口の素通し）

UART bridge しか口の無い probe でも、普通のシリアルモニタで target の出力を見られるようにする任意の項目。
ここでの作用はセッションと独立に適用する設定である（core §9）。

- key の port は fn 0 の describe の経路の index で、シリアルの口（kind 1〜3）。fn はその probe の `oep.fixture.uart`、rx はその fn の role 1（RX）として
  宣言された channel。baud と format は fixture §2 の configure と同じ値と規則（baud 0 は malformed、作れない baud と宣言に無い format は
  unsupported）。違う fn、rx は unsupported（受け取った番号）。port はシリアルの口（kind 1〜3）でなければ unsupported。rx が disable なら、または出力の idle を持てば unavailable cause 5。
- **素通しの条件**: その口からセッションの要求が来ていない、その fn の plan が無い、rx をほかの plan・接続・設定が取っていない、のすべてが成り立つ間、
  probe はその UART を rx だけで受け（TX は使わない。rx を駆動しない）、受けたバイトを [経路](../docs/oep-transports.ja.md) §4 のとおり口へフレームの外で送る。
  どれかが成り立たなくなったら、受けるのをやめて rx を空きの状態に戻す。条件がまた成り立てば再開する。
- 素通しはセッションの資源と取り合わない: セッションの plan、接続、口の使用は、素通しを止めて先に通る（素通しを理由に断らない）。
- 素通しで受けたバイトは OEP のストリーム（fixture UART の read）に入れず、保持しない。口へ送れなかった分は捨てる。
- 口からフレームの外で来たバイトを target へ送ることは定めない（入力は OEP の write を使う）。
- 1 つの口には passthrough と console-passthrough のどちらか 1 つだけを置ける（両方は unavailable cause 5）。

### 1.2 console-passthrough（debug のコンソールの素通し）

UART を空けられない target（debug の郵便受けで出力するもの）の出力を、セッションの無い間も口へ流す任意の項目。§1.1 と同じく、
セッションと独立に適用する設定である。

- wire_fn は `oep.wire.rvswd` か `oep.wire.swio`、(swdio, swclk) はその宣言が許すピンの組、max_speed は debug §1 の attach と同じ値と規則。
  console_fn はその wire の connection を受ける `oep.target.console`、mechanism はその describe の mechanism の並びの位置（core §7.7）。違えば unsupported（受け取った番号）。port は §1.1 と同じ。
  ピンのどれかが disable なら、または出力の idle を持てば unavailable cause 5。
- **素通しの条件**: その口からセッションの要求が来ていない、セッションの接続・plan がそのピンを取っていない、のすべてが成り立つ間、probe はその wire で
  method 0（止めない、reset しない）の attach をして、その方式でコンソールを読み、target の出力を §1.1 と同じに口へフレームの外で送る。
  attach が成らなかったときの試し直しは、wake / 設定の手順が target をリセットしない wire（swio）でだけ、probe が決める間隔で行う。
  wake が target をリセットしうる wire（rvswd、debug §3）では、条件が成り立つたびに 1 回だけ試す（debug §2 の「target の状態を変えない」）。
- 条件が成り立たなくなったら、probe はその接続を target に触れずに閉じ（debug §2）、ピンを空きの状態に戻す。セッションの attach は、
  素通しの接続を理由に断らない（素通しが先に退く）。
- 素通しの接続とコンソールは OEP の資源ではない: connections と streams に現れず、番号を使わず、マークを付けない。target への入力は送らない。
- 線切れ（debug §2）では、probe はその接続を閉じ、上の試し直しの規則で扱う: swio は試し直し、rvswd は条件がいったん崩れて
  また成り立つまで試さない。target の自己リセットは、方式がそのまま読み続けられる間は接続を保つ。
  rvswd でやり直させたい host は、その口でセッションを開いて終えるか、項目を unset して set し直す（どちらも条件の始まりになる）。

### 1.3 ネットワークの経路の設定（共通の規則）

TCPの経路はhostが同じ手順でどのprobeにも設定できなければならない。だから、Wi-Fiの接続先とIPv4の決め方を
OEPで設定させるprobeは、§1.4のwifiと§1.5のipv4を使う。同じ目的の独自の項目や拡張を代わりに出さない
（firmware自身の画面、ボタン、出荷時の値は別にあってよい）。

- **netif**は名前の並び（core §7.7）: probeはネットワークの口ごとに、describeのnetif（§4）に名前を1つ並べ、その位置（1から）を番号とする。
  標準の名前は`wifi`（Wi-Fiのstation、§1.4のwifiが使う）と`ethernet`（有線）。ほかの口（携帯回線など）は逆DNSの名前で、下の共通の既定とipv4はそれにも掛かる。
- **共通の既定**: wifiの項目が1つも無ければ、probeはWi-Fiを使わない。ipv4の項目が無いnetifはDHCPでアドレスを得る。
  有線は、項目が無くても線がつながればDHCPで使う。hostは同じ項目をどのprobeへ送っても同じ意味になると考えてよい。
- **probeが決めるもの**: つなぎ直しの間隔、mDNSのinstanceの名前、TCPで待ち受けるport（§2のnetworkで読める）、NTPを使うかとそのサーバ。
  OEPの時刻はprobeの時計（core）で、壁時計に頼らないため、NTPはOEPの項目にしない。IPv6はv1では定めない。
- **効く時**: set/unsetが使っている経路の設定（使っているwifiのentry、そのnetifのipv4）を変えたら、probeはその応答を送ってから、
  その経路を切り、新しい設定でつなぎ直す。ほかの変更では経路を保ち、次につなぎ直すときに使う。
  保存していない変更は再起動で保存の内容へ戻る。だから、TCPで届かなくなる設定をしても、再起動（電源の入れ直し）で戻せる。
- **（参考）TCPからの変更**: その経路で使っている設定を変えると、その接続も切れる。応答は先に送るので、setの結果は届く。
  hostは新しいアドレスでunit_idを探し直して（hostガイド §4.1）届くことを確かめてから、saveする。
- 今の様子はnetwork（§2）で読む。

### 1.4 wifi（Wi-Fiの接続先）

probeは動く場所によって違うネットワークに会うので、entryを複数持ち、keyのentryの順に試す。entryの数はsettingのkeys。

| フィールド | 意味 |
|---|---|
| ssid_len、ssid | ネットワークの名前。1〜32byte（registryの`wifi_ssid_max_bytes`。ほかはmalformed）。probeが扱えないssidはunsupported（受け取った番号） |
| pass_len、passphrase | 0はpassphraseなし（開いたネットワーク）。8〜63は0x20〜0x7Eのbyteのpassphrase。64は16進の数字64文字の鍵。0xFFは下の「書くだけ」で、後ろに何も付けない。ほかの長さとbyteはmalformed |

- dataの長さは2 + ssid_len + passphraseの長さ（pass_len 0xFFでは0）。違えばmalformed。保存のmax_bytes（§4）はpassphraseを含む形で数える。
- **max_frame**: wifiを扱うprobeは、どの経路でもconfirmのmax_frameを114以上にする（registryの`wifi_min_max_frame`）。
  いちばん長い項目（32byteのssidと64文字の鍵）1つのsetは、要求の見出し10 + count 1 + 項目の見出し3 + key 2 + data 98 = 114byteで、
  これでどの有効な項目も1つのsetで送れる。
- **passphraseは書くだけ**: getはpass_lenを、passphraseがあれば0xFF、無ければ0として、後ろに何も付けずに返す。
  setのpass_len 0xFFは、そのentryの今のpassphrase（無しを含む）を保つ。そのentryの項目が無ければmalformed。
  だからgetの項目をそのままsetで送り返しても何も変わらない。probeはpassphraseをどの応答、出来事、ログにも出さない。
  hostもpassphraseを表示せず、ログに書かない。OEPはpassphraseを暗号化しないので、信頼できる経路（USBなど、transports §1）で送る。
- **つなぎ方**: probeはentryを小さい順に試し、最初につながった（IPv4のアドレスを得た）entryを使う。どれもつながらないとき、
  つながりを失ったときは、初めからまた試す（間隔はprobeが決める）。

### 1.5 ipv4（IPv4のアドレスの決め方）

keyは§1.3のnetifの番号。並びに無い番号はunsupported（受け取った番号）。

| フィールド | 意味 |
|---|---|
| mode | 0 DHCP、1 固定。ほかはmalformed |
| address、prefix、gateway、dns | 固定のときの値。addressは`a.b.c.d`をaから順に。gateway 0、dns 0は「無い」 |

- dataは14byte。違えばmalformed。
- mode 0では、address、prefix、gateway、dnsはすべて0（ほかはmalformed）。DHCPが返すgatewayとdnsを使う。
- mode 1では、addressは0.0.0.0、255.255.255.255、127.0.0.0/8、224.0.0.0/4のどれでもなく、prefixは1〜32。違えばmalformed。
  gatewayが0でなければ、addressと同じprefixの中にある（違えばmalformed）。
- 固定のアドレスが同じネットワークで使われていると分かったときの扱いはprobeが決め、networkのreason 3で示す。

### 1.6 probe独自の項目

標準の項目に無いprobeの設定（NTPのサーバ、ホスト名、画面の明るさなど）は、probe独自の項目として出してよい。
標準の項目と同じくdescribeのsetting（§4）に並び、hostは意味を知らなくても名前と形で表示し、get/set/unset/saveで扱える。

- 名前は定義する者の逆DNSの名前で、core §12規則1のインターフェースの名前と同じ形（1〜48byte、`a-z 0-9 - .`、`.`を含む。例 `com.example.ntp-server`）。
  同じ名前は同じ意味、同じform、同じkeyの使い方を表す。
- dataの形はsettingのform（registryの`setting_form`）で決まる: 1 bytes（0〜max_len byte）、2 text（coreのtext、1〜max_len byte）、
  3 u32、4 ipv4（4byte、`a.b.c.d`をaから）、5 bool（u8の0か1）。形に合わない長さと値はmalformed。form 0（名前が決める形）は標準の項目だけが使う。
  値の意味の範囲（たとえば受けられるサーバ名）はprobeが決め、受けられない値はunsupported（受け取った番号）。
- keyは0からsettingのkeys未満。1つだけの設定ならkeysは1でkeyは0。
- 経路やOEPの動作に関わる設定（§1.3の目的のもの）は独自の項目にしない。複数のfirmwareが同じ名前を使うようになったら、標準の項目にする候補とする。

### 1.7 settingのflags（どの項目にも）

- bit0 secret: dataは書くだけ。getはkeyだけを返し（dataは0byte）、setのdata 0byteはそのkeyの今の値を保つ
  （そのkeyの項目が無ければmalformed）。応答とログに出さない。標準の項目ではwifiだけがpassphraseを§1.4の形で書くだけにし、secretは立てない。
- bit1 restart: 新しい値は再起動の後に効く（getは新しい値を返す）。立っていなければ、各項目の規則のとおりに効く（独自の項目では応答の後）。
- ほかのbitは0。

## 2. 操作と変更の世代

| op | 名前 | 要求 | 応答 | ロック | 要否 |
|---:|---|---|---|---|---|
| 0x10 | get | first(u16) | more(u8)、generation(u32)、count(u8)、count × 項目、[TLV] | 不要 | 必須 |
| 0x11 | set | count(u8)、count × 項目、[TLV] | generation(u32)、[TLV] | 必要 | 必須 |
| 0x12 | save | [TLV] | generation(u32)、[TLV] | 必要 | 任意（erase/stateと組） |
| 0x13 | erase | [TLV] | — | 必要 | saveと組 |
| 0x14 | unset | count(u8)、count × (number(u8)、key(u16))、[TLV] | generation(u32)、[TLV] | 必要 | 必須 |
| 0x15 | state | [TLV] | storage_state(u8)、saved_generation(u32)、reason(u8)、[TLV] | 不要 | saveがあれば必須、ほかでは任意 |
| 0x16 | network | [TLV] | tcp_port(u16)、count(u8)、count × 様子、[TLV] | 不要 | describeにnetifがあれば必須、ほかでは提供しない |

- 設定は最大65535項目。probeはさらに小さい有限量にしてよく、保持できない変更はunavailable（cause 2/3）で断れる。
- setは(番号、key)ごとに置換し、送らないキーは保つ。unsetは指定キーを消し、無いキーはno-op。
  unsetのnumber 0はmalformed、settingに無い番号はunsupported（受け取った番号）。重複キーはmalformed。
- 変更後の設定全体、容量、実行中の資源との競合を先に検証する。拒否時は設定・世代・ピン・実行中の資源を保つ。
  設定を変えないset/unsetは、ピンも再設定しない。
- generationは内容のdigestではなく、同じboot内の変更カウンタ。起動時は1（保存を読み込む場合も初期値1）。
  実際に内容が変わるset/unsetごとに1進める。0は使わない。0xFFFFFFFFでの内容変更はunavailable cause 2で断り、
  再起動まで再利用しない。同じ内容の操作はその値のまま成功する。hostは等値だけを比較する。
- getは番号、keyの順に並べ、firstから1frameに入る項目を返す。
  firstが総数以上ならmore 0/count 0。more 1なら受け取ったcountをfirstへ加えて続ける。
  項目を分割しない。同じ世代のページは同じ内容を表す。途中で世代が変わればhostは最初から読む。
  末尾の拡張TLVを設定項目へ混ぜない。
- count 0のset/unsetはno-op。外側の未知critical TLVはcore §2.3のとおり副作用前に断る。

### network の答え

tcp_portはTCPで待ち受けているport（待ち受けていなければ0）。続いて、describeのnetifの並びの順に、netifごとの様子（19byte）を返す。

| フィールド | 意味 |
|---|---|
| netif(u8) | §1.3のnetifの番号 |
| state(u8) | 0 使わない（wifiの項目が無い、有線の線がつながっていない）、1 つなごうとしている、2 つながっている、3 つながらず、やり直しを待っている |
| entry(u16) | Wi-Fiで、state 1では試している、state 2では使っているwifiのkey。ほかは0xFFFF |
| reason(u8) | 最後の失敗の理由: 0 なし、1 ネットワークが見つからない（APが無い、線のlinkが無い）、2 認証の失敗、3 アドレスが得られない（DHCPの時間切れ、固定のアドレスの重複）、4 そのほか。つながれば0 |
| rssi(i8) | Wi-Fiのstate 2で、受けている電波の強さ（dBm）。ほかは0 |
| address(4)、prefix(u8)、gateway(4)、dns(4) | state 2で使っている値（DHCPで得たものを含む）。ほかは0 |

## 3. 保存と起動

- save/eraseを提供するときだけ不揮発領域を使う。saveは明示操作で、現在の全項目を保存する。
  同じ内容が保存済みなら書き直さない。保存の判定をgenerationの一致だけに頼らない。
- 保存は、書込みの任意の時点で電源が落ちても、更新前の保存か新しい完全な保存のどちらかを保持する。
  更新前に完全な保存があれば、完全な旧保存または完全な新保存を読める。保存がない初回は「保存なし」または新しい完全な保存となる。
  途中の書込みを完全な保存として扱わない。
  保存の内部形式、CRC、bank配置はprobeが選ぶ。保存/消去の全処理はcoreのmax_op_ms内に終える。
- save/eraseは成功・失敗とも現在の設定/世代とピンを変えない。eraseは保存だけを消し、保存なしでも成功する。
  erase中の電源断では、更新前の保存、保存なし、または完全性を確認できない保存が残りうる。
  最後の場合は次の起動で全体を適用せず、storage_state 2/reason 1で示す。消去の原子性は要求しない。
- 保存が読める場合は項目ごとに現firmwareで検証する。未知の項目、非対応channel/mode、無効なlabelがあっても、
  それと独立した有効なdisable/idle/labelと、ほかの項目（素通し、wifi、ipv4、独自の項目）は項目ごとに適用する。保存の名前を今のfirmwareが扱わなければ、その項目は無効な項目とする。disableを先に適用してからidleを掛ける。
  同じchannelにdisableとidleがあればdisableを優先しidleを適用しない。重複キーはそのキーを適用しない。
  不正な項目を黙って別channelや別modeへ読み替えない。
- 保持量が減って保存全体が入らない場合は、disable、idle、label、そのほかの項目の順で、同じ項目内はkey順に適用できる項目を選ぶ。
  独立したdisable/idleをlabelの保持量不足で全部落とさない。容量不足は部分適用とreason 3で示す。
- 容器が壊れて境界/完全性を確かめられない保存は全体を適用しない。
  一部を適用した場合のgetは適用した現在の設定を返し、stateで部分適用を示す。
- 起動では設定済みdisableを先に反映し、ほかのchannelをidle（無ければHi-Z）へ。
  保存全体が有効で、全項目を現在の設定へ適用できた場合にsaved_generation=1とし、そうでなければ0。
- stateのstorage_state: 0 保存なし、1 全体適用済み/保存済み、2 全体を読めない、3 部分適用。
  reason: 0 なし、1 容器の形/完全性、2 無効/非対応の項目、3 保持量不足。保存が無い/全体を読めない/部分適用ならsaved_generation=0。
  save成功後（内容一致で書込みを省いた場合も）はsaved_generationを現在のgenerationへ置く。
  その後set/unsetで内容が変わってもsaved_generationは保つ。次の起動で両者は新しいbootの値になる。

### 保存操作の結果

受理前の拒否は保存状態も変えない。受理したsave/eraseで書込み・消去・検証が完了できなければcompleted failedとし、partialは返さない。
応答の固定部分は成功と失敗で同じ（saveは現在のgeneration、eraseは固定部分なし、いずれも末尾に[TLV]）。
saveの応答のgenerationだけでは保存成功を意味しない。応答喪失時はcoreの再送規則とstateで確認する。

| 結果 | storage_state | saved_generation | reason |
|---|---:|---|---:|
| save成功 | 1 | 現在のgeneration | 0 |
| erase成功 | 0 | 0 | 0 |
| 失敗し、更新前の保存がそのまま残ることを確認できた | 操作前の値 | 操作前の値 | 操作前の値 |
| 失敗し、保存がないことを確認できた | 0 | 0 | 0 |
| 失敗し、保存の完全性を確認できない | 2 | 0 | 1 |

失敗時のstateは操作後に確認できた保存状態を示し、書込みの失敗そのものはcompleted failedで示す。
保存媒体の故障を電源断の原子性保証と混同せず、読めない保存を黙って適用しない。

## 4. describe

| tag | 名前 | 値 | 要否 |
|---:|---|---|---|
| 0x40 | storage | max_bytes(u32、1以上)。項目の見出し込みの合計byte数で、いつでも保存できる上限 | save/eraseを提供するときだけ必須 |
| 0x41 | setting | form(u8)、keys(u16、1以上)、max_len(u8)、flags(u8)、name（text）。扱う項目ごとに1つ、名前の重複なし。k番目が項目番号k | 1つ以上必須 |
| 0x42 | netif | text: ネットワークの口の名前。口ごとに1つ繰り返す。名前の重複なし（§1.3） | wifiかipv4を扱うときだけ必須 |

storageのmax_bytesには保存管理の領域を含めない。これを超えるsaveは副作用前にunavailable cause 3。
保存を提供しないprobeはstorageを宣言しない。

- settingのformは、標準の項目では0（名前が決める形、§1の表）、独自の項目では1〜5（§1.6）。標準の名前にform 0以外、
  独自の名前にform 0を宣言しない。max_lenはform 1/2でだけ意味を持ち、ほかでは0。flagsは§1.7。
- settingの値は5 + 名前の長さで、名前が48byteでも53byteとなり、coreの64byte frameのdescribe（値は55byteまで、core §7.3）に収まる。
- form 1/2のmax_lenは、その項目1つのsetが自分のどの経路のmax_frameにも収まる値（要求の見出し10 + count 1 + 項目の見出し3 + key 2 + max_len以下）にする。
- hostは、知らない名前の項目も、formとflagsのとおりに表示と入力ができる。知っている名前は番号ではなく名前で見分ける。
最大長のlabel項目も、count/見出し込みで48byteのset/getに収まり、coreの64byte frameで使える。
