# OEP v1 外部公開仕様レビュー（2026-10-06）

Status: **record**（非規範）。OEP v1 freeze 前の仕様を、第三者による相互運用実装、曖昧さ、独自拡張、単純性の観点からレビューした記録。

## 1. レビュー範囲

主に次を確認した。

- 規範文書だけから、第三者が互換 host / probe を実装できるか。
- 同じ入力や状態に対して、wire encoding、応答、拒否理由が一意に決まるか。
- 未知の TLV、enum、op、event、interface を安全に扱えるか。
- 第三者が既存実装を変更せず、独自機能を追加できるか。
- core が十分小さく、拡張方法と状態遷移が理解しやすいか。
- registry、生成物、test vector が一致しているか。

対象は主に次の文書とデータである。

- [OEP core](oep-core.md)
- [standard interface common parts](oep-if-common.md)
- [wire and debug](oep-if-debug.md)
- [console](oep-if-console.md) と [dmseq](target-console-dmseq.md)
- [fixture](oep-if-fixture.md)
- [capture](oep-if-capture.md)
- [probe settings](oep-if-probe-config.md)
- [v1 registry](../registry/oep-v1.toml)
- [versioning](versioning.md) と [conformance](conformance.md)

## 2. 結論

OEP の基本構造はよい。特に、interface を名前で発見すること、reverse-DNS 名による第三者 interface、request TLV の critical bit、declaration と state の分離、決定的な拒否順序は、相互運用と拡張の基盤として妥当である。

core の frame、message、discovery、session の大部分は、規範文書から独立実装できる。standard interface も多くは実装可能である。ただし、現在のまま安定版 v1 として freeze することは勧めない。wire encoding の解釈が分かれ得る箇所と、規範性が不明な箇所が残っている。また、仕様は機能ごとには整理されているが、拡張方法と session resource の状態遷移が多く、「小さくて単純な protocol」と呼ぶには複雑である。

freeze 前に最低限解決すべきものは次の4点である。

1. answer sequence の element length 規則と個別 op table の矛盾。
2. console の SDI / DMDATA 定義が規範か参考かの明確化。
3. HID report から length-prefixed stream を再構成する規則の明文化。
4. freeze commit / specification edition / tag の確定。

さらに仕様を小さく単純にするなら、拡張方法の一本化、session resource 継承の廃止、request header と TLV header の単一形式化を、破壊的変更が可能な今の段階で検討する価値が高い。

## 3. 相互運用性に関する指摘

### 3.1 High: answer sequence の encoding 規則が矛盾する

core §2.3 は、answer sequence の各 element を次の形にすると規定している。

```text
count(u8), count x (len(u8), element)
```

一方、個別 interface には element length を持たない固定幅配列がある。例えば GPIO read は次の形である。

```text
n(u8), n x level(u8), [TLV]
```

同様に `nvals x value(u32)`、`done x word(u32)` などがある。意図はおそらく、拡張可能な構造体 element だけに length を付け、固定幅 scalar 配列には付けないという区別である。しかし core の文言はすべての answer sequence element を対象にしている。

第三者が core を優先すると `n x (len, level)` を生成し、個別 op table を優先する実装と非互換になる。

**提案**: core §2.3 を次のように分ける。

- 固定幅 scalar 配列: `count x element`。形式は revision 中で固定し、末尾拡張しない。
- 拡張可能な構造体配列: `count x (len, element)`。既知 field より後を読み飛ばせる。

より単純にするなら、sequence element の末尾拡張自体を廃止し、追加情報を TLV に限定する。

### 3.2 High: SDI / DMDATA の規範性が不明

core §1.1 は `(Informative)`、example、note を非規範と定義している。ところが `oep.target.console` の mechanism 0 SDI と mechanism 1 DMDATA の wire layout は、それぞれ `(Reference)` という未定義の印の後に書かれている。

`(Reference)` が非規範なら mechanism 0 / 1 には互換実装に必要な規範定義がない。規範なら、reference という表記が誤解を招く。

**提案**: 「由来は既存 protocol だが、以下の framing と動作は normative」と明記する。非規範にするなら、mechanism 0 / 1 の完全な規範定義を別に置く。

### 3.3 High: freeze 前の revision 1 同士が非互換になり得る

現在は v1 freeze 前であり、breaking change が protocol revision / interface revision を上げずに入る。仕様 release の tag 運用も proposal である。そのため、異なる commit を参照した2実装が、どちらも revision 1 を名乗りながら非互換になる可能性がある。

**提案**:

- freeze commit に immutable な tag または specification edition を付ける。
- 実装が対応する spec tag / commit を宣言する。
- freeze 前の revision 1 では安定した適合性を主張できないことを明記する。
- normative text または registry の変更を release と結び付ける。

### 3.4 Medium: HID framing の再構成規則が不足する

HID は length-prefixed frame の bytes を report に詰めるとされているが、次が明示されていない。

- 1 frame を複数 report にまたがせてよいか。
- 1 report に複数 frame を入れてよいか。
- `count = 0` の意味。
- padding が非ゼロの場合の扱い。
- 複数 report ID がある descriptor で使用する ID。
- report 境界で frame が未完のまま timeout した場合の回復。

**提案**: 「各 report の count byte 分を順に連結したものを単一の length-prefixed byte stream とみなす」と定義し、空 report、padding、report ID、timeout 後の破棄範囲を定める。

### 3.5 Medium: full probe implementation は外部仕様を必要とする

OEP message codec はこの repository だけから実装できる。一方、SWD / ADI / RISC-V DM / I2C / SPI backend は外部 protocol の知識を前提にする。例えば SWD は ADIv5 / ADIv6 の packet と turnaround を参照しているが、対象文書と版が normative reference として固定されていない。

これは設計上自然だが、「normative text alone で実装できる」という主張は OEP protocol 部分と hardware backend 部分に分けるべきである。

**提案**: standard interface ごとに、外部仕様の文書名、版、利用する subset を列挙する。

### 3.6 Medium: enum の revision なし追加条件が広すぎる

未使用 enum 値や reserved bit は後から定義できる。request の値であれば旧 probe は `unsupported` を返せる。一方、answer の enum 値が後続 field の解釈や意味を変える場合、旧 host は安全に扱えない。

**提案**: revision なしで値を追加できるのは、次をすべて満たす場合に限定する。

- 旧 reader が既知部分の境界を特定できる。
- 未知値を failure または unknown として扱っても危険な動作をしない。
- 未知値によって後続 field の形式や意味が変わらない。
- 必要なら capability によって明示的に opt-in される。

### 3.7 Low: probe.config state paging の文が完結していない

`oep-if-probe-config.md` §3.3 の paging 説明は、次の趣旨と思われる文の述語が欠けている。

> a host that needs the set of slots and binds to stay the same across its pages pages while it holds the lock ...

おそらく「同じ集合が必要なら lock を保持したまま全 page を読む」である。snapshot 保証の範囲に関わるため修正が必要である。

### 3.8 Low: scan の空候補を明示する

wire scan の `count = 0` には「少なくとも1 combinationを試す」と「sequenceを使い切ったら `tried = 0`」がある。disabled、idle、resource contention によって最初から候補が0件の場合を明記するとよい。

## 4. 拡張性の評価

### 4.1 良い点

- interface を name と revision で発見する。
- `oep.` は中央管理し、第三者は reverse-DNS name を登録なしで使える。
- fn は probe 内の動的番号、op / TLV / event は interface context 内の番号であり、名前空間衝突を抑えている。
- request TLV の critical bit により、無視されると意味が変わる追加情報を安全に送れる。
- optional op と describe declaration がある。
- unknown TLV、unknown event、unknown status の基本動作が定義されている。
- chip 固有処理を generic interface に混ぜず、別名の interface にする原則がある。
- declaration と可変 state が分離されている。

このため、独自機能は reverse-DNS interface を別 fn として追加することで実現できる。既存 standard interface に vendor-specific tag を混ぜるより安全である。

### 4.2 改善点

現在の拡張方法は多い。TLV、TLV value末尾、event payload末尾、sequence element末尾、enum、reserved bit、optional op、新interface、revision が併存する。柔軟だが、すべての reader / writer が複数の前方互換規則を実装する必要がある。

また、core §13 の interface 作成規則には、interface-specific status `0x40` から `0x7F` の定義が明示的な checklist に含まれていない。

**提案**: 独自 interface の規範テンプレートを用意し、少なくとも次を必須項目にする。

- name と revision。
- op table、request、answer、lock の要否。
- optional op と、それを宣言する capability。
- request / answer TLV。
- completed success / failed / partial の payload。
- interface-specific status と reject reason。
- resource と lifetime。
- event / data payload と sequence。
- unknown enum / flag の扱い。
- core §4.3 の拒否順序を適用した refusal table。

## 5. 小さく単純にするための破壊的変更案

### 5.1 拡張方法を4つに限定する

次だけを認める。

1. 既存 op への独立した追加情報: 新しい TLV。
2. 新しい操作: optional op。
3. 新しい意味または用途: 新しい interface name。
4. 既存 fixed part の変更: interface revision 更新。

次は廃止する。

- TLV value の暗黙の末尾拡張。
- event fixed payload の暗黙の末尾拡張。
- sequence element の暗黙の末尾拡張。
- 旧 host が受け取り得る answer enum の revision なし追加。

原則を「fixed part は revision 中で完全固定、拡張は TLV」にすると、最も説明しやすく、互換実装も作りやすい。

### 5.2 `end` 後の resource 継承と implicit resume を廃止する

現在は `end` 後も session resource が残り、次の session に渡る。同じ session_id の通常 request は lock を暗黙に再確立できる。これにより probe は、最後の session_id、終了理由、旧 owner、resource、resend table、resume の関係を保持する。

単純化案:

- lock を取得できるのは `open` だけ。
- `end`、expiry、force はすべて session resource を解放する。
- 終了した session は通常 request では復活しない。
- saved settings、slot などだけを probe-owned persistent resource とする。
- 再利用が必要な connection は、新しい `attach` が明示的に既存 connection を返す。

これにより session decision table と resource lifetime tableを大幅に削減できる。

### 5.3 request header を単一固定形式にする

現在は role bit 7 により request header が6 byteまたは10 byteになり、`open` の session_id だけが payload にある。

単純化例:

```text
role = request
corr(u32)
fn(u16)
op(u8)
session_id(u32)  # 0 = sessionなし
payload
```

- parser が1種類になる。
- role 0x01 / 0x81 の区別が不要になる。
- `open` だけ session_id の位置が違う例外を削除できる。
- `corr` を session 中に再利用しない u32 とすれば、u16 wrap の serial-number arithmetic を削除できる。

lock付きrequestでは現在より約2 byte、lockなしrequestでは約6 byte増えるが、仕様と実装の状態数は減る。

### 5.4 TLV header を単一固定形式にする

現在の short / long form をやめ、常に次とする案である。

```text
tag(u8) | len(u16) | value
```

通常の TLV で1 byte増えるが、254 / 255 境界、escape、non-canonical encoding、2種類の parser が不要になる。channel bitmap や calibration raw を考えると、u8 lengthだけに制限するより固定u16が安全である。

### 5.5 optional op の宣言を共通化する

現在は各 interface が独自の features bit や describe tag で optional op を宣言する。core common describe tag として、例えば次を導入する。

```text
supported_ops: base(u8), bitmap
```

optional op は bitmap にある場合だけ提供される。interface-specific features は、op の有無ではなく mode、format、notification 対応などの機能差だけを表す。

### 5.6 core と transport binding を文書上分離する

core には USB descriptor、vendor bulk ZLP、HID packing、serial raw multiplex、UART port speed、link test が含まれる。次の層に分けると、最小実装が読む範囲を小さくできる。

```text
OEP message core
  message envelope, discovery, session, error, TLV, notification model

Transport bindings
  serial/COBS, length-prefixed stream, USB bulk, HID

Optional standard interfaces
  link test, UART bridge speed control
```

binding を分けても framing の種類を増やしすぎず、基本は COBS と length-prefixed stream 程度に保つ。

## 6. 維持すべき設計

次は現在の設計の強みであり、破壊的変更でも維持する価値が高い。

- interface name による discovery。
- reverse-DNS name による第三者拡張。
- `oep.` namespace の中央管理。
- critical request TLV。
- 決定的な拒否順序。
- declaration と state の分離。
- generic interface に chip 固有処理を混ぜない原則。
- fixed part の意味または長さを変えるときの revision 更新。
- standard interface と independent interface を同じ core mechanism で扱うこと。

## 7. 検証結果と不足

次の check は成功した。

```text
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest registry_v1 vectors
```

pytest は19件すべて成功した。

ただし shared test vector が検証するのは、CRC、COBS、header、TLV、confirm、discovery、probe.config hash、拒否の一部である。次は未検証である。

- session state machine。
- resend / deduplication table。
- paging。
- plan と resource contention。
- standard interface の大部分の request / answer encoding。
- interface の状態遷移。
- timing、lease、frame gap、port_speed。
- electrical rule。

各 op について、最小成功例、境界値、malformed、unsupported、unavailable、no_connection、completed failed / partial の byte vector を追加すると、第三者実装の一致を確認しやすくなる。

## 8. 推奨優先順位

### Freeze 前に必須

1. answer sequence の fixed scalar と extensible element を区別する。
2. SDI / DMDATA を明確に normative にする。
3. HID byte stream 再構成規則を完成させる。
4. incomplete sentence と空候補などの曖昧な分岐を修正する。
5. freeze commit と specification release identifier を確定する。

### 単純性を重視するなら freeze 前に行う

1. fixed part の末尾拡張を廃止し、追加 field を TLV に限定する。
2. `end` 後の resource 継承と implicit resume を廃止する。
3. request header を単一形式にし、corr を u32 にする。
4. TLV length を固定u16にする。
5. optional op declaration を共通化する。

### Freeze 後でも追加可能

1. 独自 interface の仕様テンプレート。
2. standard interface の byte vector。
3. state machine の実行可能 test model。
4. 外部 protocol の normative reference 一覧。

最終的な設計目標は、「固定形式は revision で守り、互換追加は TLV、意味が違うものは別 interface」と一文で説明できる状態が望ましい。
