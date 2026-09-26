# Open Embedded Probe v1 仕様レビューへの回答

状態: **レビュー結果**（2026-09-26）。この文書は仕様そのものではなく、
[レビューの手引き](review-guide.ja.md)に沿って現在の OEP v1 候補を確認した結果と、v1 を固める前に推奨する変更をまとめたもの。

## 1. 結論

OEP の基本方針は妥当であり、実用性につながる設計上の強みも多い。

- target 固有の知識を host に置き、probe は線と debug transport の癖に集中する責任分担
- interface を名前で発見し、セッション中は短い `fn` で操作する方式
- critical TLV、未知の応答 TLV、未知の status を安全側に扱う拡張規則
- request の不受理と、実行を開始した後の失敗を分ける結果モデル
- 読んでも消費しない位置付きの console / UART stream
- attach、capture、USB 構成などを実測してから仕様へ反映する進め方
- registry と code generation を wire 上の番号の中心に置く方針

一方、現在の文書群は、独立した host と probe の実装者が同じ挙動を一意に実装できる状態にはまだ達していない。
主な理由は、規範となる文書が分散して相互に食い違っていること、revision と再送の規則が将来の相互運用を損なうこと、
connection、stream、session、activity の寿命が一つの状態機械として定義されていないことである。

したがって、現段階では v1 の freeze は推奨しない。ただし利用者がまだおらず破壊的変更が可能なので、以下の点を直すには
適切な時期である。

## 2. freeze 前に解決する問題

### 2.1 P0: v1 の規範文書を一つに定める

レビューの手引きは、v0 は v1 で置き換え済みであり、`v1-core-wire-delta.ja.md` が v1 の本体であるとしている。
しかし v1 本体は、記載していない request / result header、resolution、TLV の形を v0 に委ねている。

また、現行として案内されている文書間にも次の食い違いがある。

- `session-and-exclusivity.ja.md` は OEP の制御口を一つに限定する。
- `v1-core-wire-delta.ja.md` は複数の制御 transport を同時に開ける。
- `capability-declaration-model.ja.md` の `describe.first` は `u8` である。
- `v1-core-wire-delta.ja.md` の同じフィールドは `u16` である。

差分文書を規範にすると、変更のたびに「v0 のどの規則が残っているか」を判断する必要があり、独立実装間で解釈が分かれる。

推奨する変更:

1. wire format、状態機械、全 core operation、標準 interface を含む単独の `oep-v1-spec.ja.md` を作る。
2. 比較、実験、採用理由、過去の案は非規定文書として分離する。
3. 規範文書内では「別文書を優先する」という上書き関係を作らない。
4. `review-guide.ja.md` は、規範文書と設計資料を明確に分けて案内する。

### 2.2 P0: connection、stream、session の寿命を統一する

現行文書には、次の規則が同時に存在する。

- lease 切れや transport 切断では attach を解かない。
- lease が切れたら、その session が connection を使用していた分を外す。
- console stream は session や lease の終了では終わらない。

bind のない通常の console stream で lease が切れた場合、connection が閉じて stream も閉じるのか、stream 自身が
connection を保持するのかが一意に決まらない。

connection は参照を持つ資源として定義し、少なくとも次を参照元として列挙する必要がある。

- session が行った attach
- 開いている console stream
- 永続設定の bind
- 将来 connection を利用する interface

各 operation と事象について、参照を追加・削除するかを表にする。console stream を lease 終了後も残すなら、stream 自身を
connection の利用者として数えるのが自然である。最後の参照がなくなったときだけ connection を閉じる形にすれば、bind と
one-shot CLI の両方を同じ規則で扱える。

`connection(u8)` と `stream(u8)` の再利用規則も必要である。古い handle が別の target や stream を指さないよう、少なくとも
同じ `boot_id` の間に古い handle をいつ再利用できるかを規定する。長期的には generation を含む `u16` 以上の handle の方が
安全である。

### 2.3 P0: revision の互換性規則を一本化する

能力識別の文書では、後方互換な optional TLV や末尾フィールドの追加でも revision を上げ、非互換変更では名前を変えるとしている。
一方、v1 wire は payload の形を `(name, revision)` で決め、host は未知の revision を使用しないとしている。

この組み合わせでは、optional TLV を一つ追加しただけで古い host が interface 全体を使用しなくなる。これは、末尾 TLV によって
既存機能の相互運用を維持する目的と矛盾する。

v1 では、次の単純な規則を推奨する。

- 固定部分を変えず、optional request TLV、response TLV、任意 operation、任意 event を追加する場合は revision を変えない。
- 固定部分の意味や長さを変える場合だけ revision を上げる。
- breaking revision を導入する probe は、可能なら旧 revision も別の `fn` として同時に公開する。
- interface 名は意味が変わった場合だけ変更し、単なる版番号の代用にはしない。

これにより、revision は互換性境界、TLV と feature bit は互換な機能追加という役割に分かれる。

### 2.4 P0: 状態変更 request の重複排除を全 transport 共通にする

UART は COBS と CRC により破損を検出できるが、request の重複を識別する sequence がまだない。現行規則では、応答が来なかった
状態変更 request は二重実行を避けるため再送できない。

この場合、応答だけが失われると、host は request が実行済みか未実行かを判断できない。`reset`、`write_block`、config の
`set` / `save` などで実害がある。CRC は破損の検出には有効だが、request を実行した後の応答喪失を解決しない。

UART binding だけの特殊な sequence にせず、全 transport 共通で `(session_id, request_seq)` による短期的な重複排除を入れる
ことを推奨する。

- host は状態変更 request に単調増加する `request_seq` を付ける。
- probe は session ごとに、直近の sequence と結果を小さな範囲だけ保持する。
- 同じ sequence を再受信したら再実行せず、以前の result を返す。
- session が変わった場合の exactly-once は保証しない。

これなら USB、UART、HID、将来の network transport で同じ host 実装を使える。

### 2.5 P1: scan で見つけたピンの組へ attach できるようにする

現行 wire の `scan` request には候補の指定がなく、`attach` request にも SWDIO / SWCLK などのピンの組がない。一方、target の
発見ユースケースでは、host が候補の部分集合を指定し、scan で見つけた組へ attach することを前提としている。

このままでは、任意のピンを使える汎用 probe が scan の結果を実際の接続に利用できない。

`v1-open-proposals.ja.md` の案を採用することを推奨する。

- `scan`: `count` とピン組の並びを request に持つ。`count = 0` は許可された全候補。
- `attach`: ピン組を固定部分または critical TLV で指定する。
- 指定した組が describe の許可リストにない場合は、実行前に reject する。
- scan result には、attach へそのまま渡せる形でピン組を返す。

PENDING を使用するかは実測時間で決めてよいが、ピン組の指定は v1 の基本用途に必要である。

### 2.6 P1: capture の position を u64 にする

共通規則と capture は byte position に `u32` を使い、serial number arithmetic で比較する。40 MB/s の capture では約107秒で
一周し、符号付き比較で安全に扱える半周は約54秒である。host がそれ以上遅れた場合、欠損量を一意に判断できない。

また、capture は `samples(u32)` と最大32 bit/sampleを許しており、理論上の区画サイズは4 GiBを超える。設定可能な長さと
`position(u32)` で参照できる長さが一致していない。

次の形を推奨する。

- console と低速 UART stream は現在の `u32 position`を維持してよい。
- `oep.fixture.capture` の `position`、`write_pos`、通知の position は `u64` にする。
- 長時間の区画比較が必要なら `start_us` も `u64` にする。
- もし `u32` を残すなら、1回のcapture全体を2 GiB未満に制限し、describeとconfigureで明示的に拒否する。

高速転送では4 byteの追加は小さく、曖昧な欠損検出を避ける方が重要である。

### 2.7 P1: force takeover と activity の所有権を決める

長い操作は host がいなくなっても続き、最後の結果は同じ session だけが取得できる。一方、新しい session が force で lock を
奪った場合の実行中 activity の扱いが定義されていない。

無期限の `run` などの途中で takeover されると、新しい host は activity ID を知らず、probe は busy のままになる可能性がある。

単純な規則として、次を推奨する。

1. `open(force)` は、以前の session の購読を終了する。
2. cancel 可能な activity があれば cancel する。
3. cancel できない activity が実行中なら、`open(force)` を busy で拒否し、残りの状態を返す。
4. activity の最終結果は、所有 session が同じ間だけ取得できる。

別案として新しい session に activity ID を公開することもできるが、操作の結果に旧 session の情報が含まれ得るため、所有権が
複雑になる。

### 2.8 P1: registry を wire 上の番号の完全な定義にする

`review-guide.ja.md` は `registry/oep-v1.toml` を wire 上の全数値の唯一の定義としているが、文書にあり registry にない値がある。

- describe の `exclusive_group = 0x04`
- describe の `min_clock_hz = 0x05`
- plan の `start_together = 0x91`
- 文書で revision 1 として扱われる `oep.fixture.analog`

仕様から外す値は文書から削除し、採用する値は registry に追加する必要がある。特に `start_together` は mixed-signal capture の
説明でも前提になっており、単なる未使用値ではない。

また、registry は現在主に番号だけを定義している。独立実装の一致を検証するため、次の段階では payload layout と golden test
vector も生成対象にすることを推奨する。

## 3. 実用性のために再検討する点

### 3.1 plan と GPIO 状態を無期限に残すか

現在は one-shot CLI のため、session や lease が終わっても plan とピン状態を戻さない方針である。しかし host が異常終了した
場合に、reset を low に保持し続けたり、GPIO を出力にしたまま残したりする危険がある。

「保存された構成」と「一時的な操作」を分ける方が安全である。

- 通常の `plan_apply` は session または専用 lease に属し、期限切れで安全状態へ戻す。
- `oep.probe.config` で保存した plan / bind は永続状態として残す。
- 一時 plan を意図的に残したい場合だけ critical な `persistent` 指定を使う。
- 各 channel の安全状態を describe で宣言できるようにする。

これなら既定は安全で、治具や常設 console の用途だけを明示的に永続化できる。

### 3.2 subscribe の再設定規則

同じ session が同じ `fn` を再度 subscribe した場合に、既存購読を置き換えるのか、追加するのか、reject するのかが明記されて
いない。複数 transport を同時に開けるため、通知先の経路も変わり得る。

「同じ session / fn の subscribe は一つだけで、再度の subscribe は条件と送信経路を原子的に置き換え、`seq` を0へ戻す」と
定義するのが単純である。

### 3.3 network transport の信頼境界

TCP が transport の候補に含まれる一方、session lock の `force` は誰でも使用でき、認証を目的としていない。USB直結では妥当でも、
networkへそのまま公開するとtargetの書き換えやprobeの再起動を第三者が行える。

暗号や認証をOEP coreへ入れない場合でも、TCP transportは「信頼されたローカル接続または認証済みトンネルの内側でのみ使う」
ことを規範として明示すべきである。

### 3.4 config の正規形

config hash の正規形について、requestで受け取ったcritical bitを保存・hashへ含めるか、同じkeyのlabel / bindが重複した場合に
どうするかが明確でない。

設定値として保存するtagからcritical bitを除き、keyの重複はrequest全体をmalformedとして拒否するのがよい。同じ意味の設定が
hostの送信方法によって異なるhashにならないようにする必要がある。

## 4. 維持したい設計判断

今回の指摘を直す際にも、次の性質は維持する価値が高い。

1. **target の知識は host が持つ。** flash algorithmやchip固有registerをprobeへ戻さない。
2. **probeは低レベルのタイミングと回復を持つ。** attach under reset、DMI / SWDの再試行、線速度の選択はprobeに置く。
3. **固定部分は小さく保つ。** optionalな追加はTLVに置く。
4. **失敗を安全側に解釈する。** 未知のstatusを成功扱いしない。
5. **低スペックprobeも同じprotocolを使う。** 小さい`max_frame`、window、少ないinterfaceで表現する。
6. **実測を仕様の根拠にする。** ただし、測定結果そのものは規範文から分離する。
7. **通知を購読制にする。** 購読していないhostへ非同期frameを送らない。
8. **consoleを非消費型streamにする。** monitorの再接続とクラッシュ直前のlog回収に有効である。

## 5. 推奨する作業順序

v1 freeze に向けて、次の順で進めることを推奨する。

1. 単独の規範的なv1仕様書を作る。
2. revisionと互換な拡張の規則を確定する。
3. session、connection、stream、subscription、activityの状態遷移表を作る。
4. request sequenceと重複排除を全transportへ入れる。
5. scan / attachのピン指定を確定する。
6. captureのposition幅を確定する。
7. registryを規範文書と一致させる。
8. 各operationについて、成功、reject、partial、timeout、再送、lease切れのgolden vectorを作る。
9. reference実装とは別の最小hostと最小probeで相互接続試験を行う。

freeze の最低条件は、少なくとも次の通りと考える。

- 規範文書だけを読んで、第三者がcodecと状態機械を実装できる。
- 同じ入力に対するprobeの応答が、文書上で一意に決まる。
- 応答喪失後に、状態変更requestの結果を安全に確定できる。
- 古いhostと新しいprobeが、共有する既知機能を引き続き利用できる。
- lease切れ、force、再起動、target切断時の資源の寿命が試験できる。
- registry、生成物、仕様中の番号が自動検査で一致する。

## 6. 総評

OEPは、単なるdebug probeの共通コマンドではなく、debug、console、fixture、capture、外部bindingを同じ発見・排他・拡張の
仕組みで扱おうとしている。この方向には十分な実用性がある。一方、現在の複雑さの多くは機能数そのものではなく、同じ決定が
複数文書に異なる世代の形で残っていることから生じている。

機能を大きく削るより先に、規範を一つにし、寿命と再送の状態機械を小さく明示する方が、単純さと拡張性の両方に効く。
破壊的変更が可能な現在は、field幅、handle、revision、request sequenceを修正する最後の良い機会である。

## 7. 更新後の仕様の再レビュー（2026-09-26）

`oep-core.ja.md` と `oep-if-*.ja.md` へ規範を分けた更新後に、前回の指摘を再確認した。

### 7.1 解消した指摘

次の点は、更新後の規範で解消されている。

- `oep-core.ja.md` が単独の規範的な本体となり、古い差分文書と設計資料は非規範になった。
- 複数の制御経路は一つのlockを共有する規則に統一された。
- `describe.first` は `u16` に統一された。
- revisionは固定部分を壊すときだけ上げ、optional TLV / op / eventの追加では上げない規則になった。
- 状態変更requestを同じcorrで再送し、probeが重複を除く仕組みが追加された。
- force takeover時の、cancelできるactivityとcancelできないactivityの扱いが追加された。
- scanの候補とattachのpins指定が規範へ入った。
- streamとcaptureのposition、captureの時刻が`u64`になった。
- subscribeの再設定、通知先の経路、seqの再開始が定義された。
- TCPは信頼済み接続または認証済みトンネル内でだけ使うと明記された。
- config hashからcritical bitを外すことと、同じkeyの重複をmalformedにすることが定義された。
- registryに`min_clock_hz`、pins、`oep.fixture.analog`、新しいreject reasonが追加され、生成物との同期も取れている。

規範と理由を分けた構成は、前版より大幅に読みやすく、第三者実装にも適した形になっている。

### 7.2 P0: corrの再利用規則と重複排除表が矛盾する

core §4.1 は、corrの重複を禁止する範囲を「未解決の要求の間」だけとしている。この規則なら、応答を受け取ったhostは同じcorrを
次のrequestへ再利用できる。一方、core §5.2 は、解決済みrequestを重複排除表に残し、同じcorrで内容が違うrequestを
`corr_reused`で拒否する。

probeが表をいつ捨てたかをhostは知ることができないため、現在の規則では、仕様に従ってcorrを再利用したhostが正当なrequestを
拒否され得る。

さらに、重複判定にpayloadのCRC-32を使うため、CRCが衝突した異なるrequestを同じrequestとして扱う可能性がある。CRCは伝送誤りの
検出には適するが、状態変更requestのidentityを決める値にはしない方がよい。

最も単純な修正は、corrを`request_id(u32)`へ広げ、同じsession内では再利用しないことである。requestとresponseの対応付けと
重複排除を一つの番号で行え、payload hashとretire windowが不要になる。u16を維持する場合は、少なくともhostが再利用してよい
条件と、probeの表から消えたことを知る方法が必要である。

### 7.3 P0: endの再送でlockが復活し得る

`end`の応答が失われた場合を考える。

1. 最初の`end`がlockを解く。
2. hostが同じcorrで`end`を再送する。
3. core §6.2により、空きlockへ最後と同じsession_idが来たためsessionが再開する。
4. core §5.2により、`end`は再実行されず、覚えていた応答だけが返る。

この順で実装すると、hostはendが成功した応答を受け取るが、probeではlockが再び立ったままになる。重複判定とsession再開の判定の
順序が規定されていないため、実装によって結果が変わる。

重複した`end`は、lockを再開せずに以前の応答を返す、と明記する必要がある。一般には、session状態を変える前にduplicate requestを
判定するか、`end`を特別な冪等操作として定義する。

### 7.4 P0: status(activity)のsession識別ができない

core §10 は、activityの最後の結果を同じsession_idだけが取得できるとしている。しかしcore §12の`status`はロック不要で、通常の
role 0x01にはsession_idが無い。probeは、問い合わせたhostがactivityを作ったsessionかどうか判定できない。

`status(activity)`は、少なくともsession_id付きのrole 0x81を必須にする必要がある。lockを現在持っていることまで要求するか、lease
切れ後に同じsession_idで結果だけを回収できるかは別に決められるが、所有sessionを識別する情報は必要である。

activity番号の再利用条件も定義する。古いstatusが新しいactivityへ当たらないよう、同じsession内では単調な番号を使い、結果を
捨てるまで再利用しない形がよい。

### 7.5 P1: lease期限切れ中のactivityの扱いが残っている

forceは実行中activityをcancelする規則になったが、自然なlease期限切れで同じ後始末をするかは明記されていない。cancelできない
無期限activityが旧sessionに属したまま動くと、新しいhostはactivity番号を知らず、probe全体がbusyのままになる可能性がある。

lease期限切れでもforceと同じ順序を使うことを推奨する。

- cancel可能ならcancelして資源を外す。
- cancel不能なら、完了まで「終了処理中」のlockを残し、新しいopenをbusyで断る。
- activityが終わったらlockと旧sessionの資源を外す。

### 7.6 P1: end後に残した資源の所有権移転を明記する

core §9 は、end後の資源を「次のセッションに渡す」としているが、どの時点で新sessionの資源になるかが明記されていない。
特に、session Aがconnectionとstreamを残してendし、session Bがopenしただけでattachせず、その後Bのleaseが切れた場合に、Aが作った
資源を外すかが一意に決まらない。

「end後に残った資源は、次に成功したopenでそのsessionへ原子的に移り、そのsessionのlease切れまたはforceで外れる」と定義すると
明確になる。引き継ぎを望まないhostは、end前にdetach / close / plan_releaseを行う。

### 7.7 P1: u8の資源番号は一周後に古いhandleへ別資源を割り当てる

core §9 は資源番号を1〜255で順に再利用する。再利用前は閉じた番号を`no_connection`にできるが、一周後には古いhandleが新しい
connectionまたはstreamを指す。probeを再起動していなくても、古い非同期処理や保存された状態が別targetへ作用し得る。

connectionとstreamはgenerationを含む`u16`以上にすることを引き続き推奨する。u8を維持するなら、同じboot_idの間は番号を再利用
しないため、256個目の作成を`unavailable`で断る方が安全である。

### 7.8 P1: scan結果が1フレームに収まらない場合の継続方法がない

scanはcount=0で許可された全組を試せるが、応答は`count(u8)`と見つかった組の並びを1フレームで返す形である。低スペックprobeの
64 byte frameでは、数件の結果しか返せない。複数targetや誤応答があると、結果をすべて返す方法がない。

単純さを優先するなら、scan requestを一度に1組へ制限し、全組の走査はhostが行う方法が最も小さい。probe内で全組を高速に走査
する利点を残すなら、結果に`more`と`first`を入れるか、activityの最終結果をページで読む操作が必要である。

### 7.9 P1: request TLVのcritical規則を修正する

core §2.3 は「hostはcriticalのbitを付けて送る」と読めるが、同じ節はnon-critical TLVを無視して`ignored`へ載せる規則を持つ。
captureのconfigureも、hostが項目ごとにcriticalかnon-criticalかを選ぶことを前提としている。

ここは「hostは、その項目が満たされなければ操作に意味がない場合にcriticalを付ける。non-criticalで送ってもよい」と直す必要が
ある。速度上限やpinsなど、安全条件として仕様がcriticalを要求するTLVだけは必須とする。

### 7.10 P2: アナログscaleの単位が一致していない

`oep-if-capture.ja.md` §1.2 はscaleをµV / 1値としているが、configure応答のTLV 0x55は`scale_nv`（nV / 1値）としている。
1000倍の差になるため、どちらかに統一する必要がある。整数精度を保てるnVを採用し、換算式側をnVへ直すのが扱いやすい。

### 7.11 更新後の判定

前回の構造上の大きな問題は解消され、仕様はfreeze候補にかなり近づいた。残る主なblockerは、重複排除とsession再開の状態遷移、
activityの所有者確認、resource handleの再利用である。この3点は正常系の実装試験だけでは見つかりにくいため、次のtest vectorを
freeze条件へ追加することを推奨する。

- 状態変更requestの応答だけを落とし、同じrequestを再送する。
- `end`の応答を落として`end`を再送する。
- request完了後、同じcorrを別requestへ再利用する。
- activity実行中にlease切れ、force、同じsessionの再開を行う。
- end後に別sessionが資源を引き継ぎ、そのleaseを切らす。
- connection / stream番号を一周させ、古いhandleを送る。
- scan結果をmax_frameより多く発生させる。
