# Open Embedded Probe — 設定のファイル v1

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](versioning.ja.md)を参照。
この文書は、probe の設定（[OEP core](oep-core.ja.md) §13）を host が書き出し、同じ probe や別の probe へ入れ直すためのファイルの形と手順を定める。
probe の中の保存の形式は定めない（core §13.7）。ブラウザと CLI など、違う host が書いたファイルを互いに読めるようにするのが目的である。

## 1. なぜ要るか

- probe は、firmware の版や構成が変わると、保存の中の使えない値を使わず、次の save で消す（core §13.7）。消えてよいのは、host が先に書き出して、
  後で入れ直せるからである。
- firmware の更新の流れ: 書き出し → firmware の書き込み → 入れ直し。保存を持たない probe には、つなぐたびに入れ直す。

## 2. ファイルの形

UTF-8 の JSON（RFC 8259）1 つ。BOM を付けない。拡張子は `.oep-settings.json` を勧める（参考）。

```json
{
  "oep_settings": 1,
  "probe": { "model": "rp2350", "unit_id": "9489dd2ae0953650", "firmware": "0.0.36+cff9253" },
  "settings": {
    "core": {
      "channel.GPIO14.label": "NRST",
      "channel.GPIO14.idle": "pull-up",
      "channel.GPIO2.disable": true,
      "wifi.0.ssid": "lab",
      "wifi.0.passphrase": { "secret": true },
      "ipv4.wifi.mode": "static",
      "ipv4.wifi.address": "192.168.1.23"
    },
    "oep.wire.rvswd/0": { "rest.GPIO5": "low" },
    "oep.fixture.uart/0": { "passthrough.cdc0.rx": "GPIO1", "passthrough.cdc0.baud": 115200 }
  }
}
```

（例の wifi、ipv4、rest、passthrough の項目は、それぞれの文書が定める。）

| メンバー | 値 |
|---|---|
| `oep_settings` | 数。ファイルの形の版。この文書は 1。読む側は知らない版のファイルを使わない |
| `probe` | オブジェクト。書き出した probe: `unit_id`（必須）、`model`、`firmware`（fn 0 の describe にあれば、その text のまま。core §7.5） |
| `settings` | オブジェクト。カテゴリごとのメンバー（§2.1） |

- 読む側は、知らないメンバー（最上位、`probe` の中）を読み飛ばす。書く側は、この文書に無いメンバーを最上位と `probe` に置かない。
- 同じオブジェクトの中に同じ名前のメンバーを 2 回置かない。読む側は、重なりのあるファイルを使わない。

### 2.1 カテゴリ

`settings` のメンバーの名前はカテゴリ（core §13.1）:

- 本体のカテゴリは `core`。
- インターフェースのカテゴリは、その名前と `/` と instance の 10 進（`oep.fixture.uart/0`）。

メンバーの値はオブジェクトで、項目ごとの平らな名前から値への対応である。値の無いカテゴリは書かなくてよい。

### 2.2 平らな名前

平らな名前は、項目の名前（core §13.1）の `{}` を key の書き出しの名前（core §13.3: channel の名前、10 進の数、経路の名前、netif の名前）で
置き換えたもの。key の無い項目は項目の名前のまま。

- 読む側は、平らな名前に当たる項目を、カテゴリの宣言の名前と比べて探す: key の無い項目は名前が同じもの、key のある項目は `{}` の前と後ろが
  平らな名前の先頭と末尾に一致し、その間（key の名前）が空でないもの。key の名前は `.` を含みうる（ほかの者の netif の名前、core §7.7）。
- 当たる項目が 2 つ以上ある平らな名前（`a.{}` と `a.b.{}` の両方に当たる `a.b.c` など）は使わず、利用者に示す。持ち主は、そうなりうる名前の組を
  同じカテゴリに置かない。

### 2.3 値

値は項目の form（core §13.3）の書き出しの形で書く:

| form | JSON | 例 |
|---|---|---|
| bytes | 小文字の 16 進の数字の文字列（2 文字で 1 byte、空でよい） | `"0a1b"` |
| text | 文字列 | `"NRST"` |
| u32 | 0〜4294967295 の整数 | `115200` |
| ipv4 | `"a.b.c.d"`（各 0〜255 の 10 進、先頭の 0 なし） | `"192.168.1.23"` |
| bool | `true`、`false` | `true` |
| enum | 選択肢の name（core §13.2 の setting_choice） | `"pull-up"` |
| channel | channel の名前 | `"GPIO1"` |
| transport | 経路の名前 | `"cdc0"` |
| fn | `"名前/instance"` | `"oep.wire.swio/0"` |

- secret の項目（core §13.5）の値は、値の代わりに `{ "secret": true }` を書く。値は probe から読めないので、ファイルにも入らない。
- 読む側は、form と合わない JSON の値（形の違い、範囲の外、整数でない数）を使わず、利用者に示す。

## 3. 書き出し

1. fn 0 の confirm、list、describe と、各 fn の describe を読み、項目の宣言（setting、setting_choice）、channel の名前、経路、netif の名前を得る。
2. fn 0 の get で全部の値を読む（generation が途中で変われば初めから）。
3. 全部の値を、番号を §2 の名前に引き換えて書く（初期値から来た値も区別せずに書く。core §13.4）。secret の値は §2.3 のとおり
   `{ "secret": true }` と書く（値があることだけ）。

## 4. 入れ直し

入れ直しは、probe の値をファイルの値にすることである。

1. 書き出しの 1 と同じに宣言を読み、今の値を get で読む。
2. ファイルの各値について、カテゴリの fn（`core` は fn 0。インターフェースは list で名前と instance の同じもの）、項目と key（§2.2）、値（§2.3）を
   今の番号へ引く。引けないもの（カテゴリ、項目、key、参照が今の probe に無い）は送らない。
3. 次を利用者に示し、確認を得る:
   - 引けないもの;
   - 書き換わる値、新しく置く値、unset する値（probe の値でファイルに無いもの）;
   - `probe` の unit_id か model が今の probe と違うこと。
4. secret の値:
   - 今の probe にその値があれば、触らない（unset もしない）;
   - 無ければ、利用者に入力を求めるか、置かない。
5. unset を先に、set を後に送る（label を別の channel へ移すときに、一意の規則（core §13.8）にぶつからないため）。値が多ければ要求を分けてよい
   （要求ごとに、まとめて受けるか何もしない。core §13.5）。断られた値は利用者に示す。
6. probe が save を持てば save し、state で確かめる。

- 保存を持たない probe に、host はつないだときに自動で入れ直してよい（利用者が選んだファイルに限る）。
- host は、ファイルを書き出すとき、secret の値をファイルに入れる手段を持たない（probe から読めないため）。利用者が手で入れた secret をファイルに足すことも
  しない（ファイルは秘密を持たない、を保つ）。

## 5. テストベクタ

`tests/vectors/settings_file.json` に、宣言（describe の TLV）、get の値、ファイルの組と、別の番号の probe へ入れ直したときの set、unset、
secret、引けないものの組を置く。ブラウザ（JS）と CLI（Python）の実装は、同じベクタで書き出しと入れ直しの引き換えを確かめる。
