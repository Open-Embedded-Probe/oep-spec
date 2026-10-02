# Open Embedded Probe — レビューの手引き（どこに何が書いてあるか）

[English](review-guide.md)

状態: 2026-10-02 時点の地図（v1 の凍結前。凍結前の決定とゼロベースの再検討を規範に入れ、残っていた数を埋めた後）。OEP をまだ知らない人が
v1 の凍結のレビューをするときに、どこから読めばよいか、どの PATH に何があるか、何を見てほしいかをまとめる。PATH は各リポジトリの根からの相対。

## 1. OEP とは

組み込み開発用の probe（デバッガ、ロジックアナライザ、治具）が提供する機能を、共通の意味で公開するプロトコルと、その
実装です。異なる probe の実装と、異なる host のソフトウェアが、互いに使えることを目指しています。

- **probe**: USB などで PC につながる装置（参照の実装は Arduino のライブラリとスケッチ）。自分のピン（fixture）と、target へのデバッグ線
  （RVSWD、SWIO、SWD）を持つ。
- **host**: PC 側のソフトウェア（Python の client、書き込みツール ch32rv など）。
- **target**: 開発中のマイコン。

分担の原則: **target の知識は host が持つ**。probe は線と DMI（RISC-V Debug Module Interface）/ DP・AP の転送しか知らず、
flash の書き方やチップ固有の手順は host にある。

## 2. 今の状態

- **v1 の凍結の候補**です。規範は `docs/oep-core.ja.md`、`docs/oep-if-*.ja.md`（6 つ）、`docs/target-console-dmseq.ja.md`、番号は `registry/oep-v1.toml`。
  規範の中に未決の数（「決める」の印）は残っていません。凍結で何を止め、何を止めないかは [凍結の範囲](v1-freeze-decisions.ja.md) §0。
- 凍結までは破壊的な変更を revision を上げずに入れます（利用者はまだいない）。凍結後は revision を上げます。
- **リリース**: oep-spec は GitHub の main に push 済み（タグは無い。commit で指す）。参照の実装は oep-probe-arduino **0.0.27**（Arduino ライブラリ
  `OpenEmbeddedProbe`、GitHub release に profile ごとの firmware）、oep-client-python **0.0.27**（PyPI `oep-client-python`）。oep-client-js は
  未公開（npm に出していない。fake に対する試験だけ）。firmware と client は同じ minor 版で組にします。
- **実機の試験**（[release-testing](release-testing.ja.md)、oep-client-python `tests/hw/`）が覆うもの: 焼く、confirm / list / describe、`oep.probe.config` の
  set / get / save / 再起動 / unset（disable を含む）、線（scan、attach、halt → dmi → read_block → resume の往復。target をつないだボードだけ）、
  gpio、fixture uart、port_speed（UART bridge のボードだけ）、lease の期限切れ / expired / force。結果は `tests/hw/results/` の JSON。
  **覆わないもの**: console（dmseq）、キャプチャ（logic / analog / capture-group）、i2c-target / spi-target、通知、HID の経路、複数の経路の
  同時使用、TCP。これらは fake に対する試験（`uv run pytest`、247 件）と手動の確認だけです。
- 決め方は「先に実験・試作をして、その結果で仕様を固める」。実験の番号や日付は**記録の文書**に残し、規範の文には置きません
  （規範はチップ名・ボード名・日付を持たず、数は目安ではなく値）。
- 文書は**日本語が先**です。英語版は固まってから作ります（既存の英語の文書は古い）。

## 3. 最短の読む順番（v1 の凍結のレビュー）

| 順 | PATH（oep-spec） | 何が分かるか |
|---:|---|---|
| 1 | `docs/project-concept.ja.md` | 目的と範囲（上流の合意）。短い |
| 2 | `docs/v1-freeze-decisions.ja.md` §0 | **凍結の範囲**: 止めるもの、自由なもの、意図して固定するものと理由、伸ばす道 |
| 3 | `docs/oep-core.ja.md` | **本体（規範）**。§0 層と線引きの規則、§2 共通の規則（TLV、知らない値、番号の空間、revision）、§3 経路とフレーム、§4 メッセージと reject reason（§4.3 に**断り方の順**）、§5 立て直しと送り直し、§6 セッション、§7 発見（confirm / list / describe）、§8 plan、§9 資源の寿命、§10 長い操作（予約）、§11 通知、§12 core の op、§13 インターフェースの書き方。**§3.5（シリアルの口の速さ）は握手だけ**: 候補の選び方、確かめ、使用中の判定は `host-development-guide` §7 の参考の手順 |
| 4 | `docs/oep-if-common.ja.md` | 標準インターフェースの共通部品（位置つきのストリーム、debug の connection、線と target の status） |
| 5 | `docs/oep-if-debug.ja.md`、`docs/oep-if-console.ja.md`、`docs/oep-if-fixture.ja.md`、`docs/oep-if-capture.ja.md`、`docs/oep-if-probe-config.ja.md` | 標準インターフェース（規範）: 線と RISC-V DM / ARM ADI、target のコンソール、GPIO / UART / I2C・SPI の target、ロジック / アナログのキャプチャと組、probe の設定（スロット、bind、disable） |
| 6 | `docs/target-console-dmseq.ja.md` | コンソールの framing（dmseq）: デバッグモジュールのデータレジスタで、通番と CRC つきで双方向に運ぶ（target と host の規範） |
| 7 | `registry/oep-v1.toml` | 番号と数の唯一の定義。`timing` / `limits` は規範の文の数（凍結の対象） |
| 8 | `docs/v1-zero-base-proposal.ja.md` §1、§4、`docs/v1-zero-base-review-2026-10-02.ja.md` | 判定に使った **8 つの原則**、意図して伸ばさない所、2 回目の点検（★ 直した、☆ 固定のまま） |
| 9 | `docs/host-development-guide.ja.md`、`docs/probe-development-guide.ja.md` | 実務（規範ではない）: フレームの送り方、立て直し、USB-UART の扱い、**§7 シリアルの口の速さの選び方**（7.1 釣り合い、7.2 最小の形、7.3 用途別に確かめを足す形、7.4 記録、7.5 実測の要約） |
| 10 | `docs/link-measurements.ja.md`、`docs/uart-speed-negotiation.ja.md`、`docs/logic-capture.ja.md` | **記録**（規範ではない）: USB とシリアルの経路の実測、UART の速さの実験と経緯、キャプチャの設計と実測。参考の数字の出どころ |
| 11 | `docs/release-testing.ja.md` | リリース前の実機の試験: 誰が持つか、何を確かめるか |
| 12 | `docs/session-and-exclusivity.ja.md`、`docs/capability-*.ja.md`（3 つ）、`docs/console-stream.ja.md`、`docs/target-connection-use-cases.ja.md`、`docs/probe-cdc-and-persistence.ja.md` | 決めた理由（セッションとロック、名前で探す方式、describe の語彙、ストリーム、target の発見、シリアルの口の共用と設定の保存） |
| — | `docs/usb-identity.ja.md`、`docs/pid-codes-application/` | USB の識別と、pid.codes への申請の資料 |
| 13 | `docs/v1-open-proposals.ja.md`、`docs/v1-freeze-review-2026-10-01.ja.md`、`docs/review-response-2026-09-26.ja.md`、`docs/review-answer-*.ja.md` | 案と決めた経緯、凍結前の全面見直し（59 項目、対応済み）、前回の第三者レビューへの対応表 |
| — | `docs/hardware-source-review-2026-09-26.ja.md`、`docs/v1-operation-test-audit-2026-09-26.ja.md`、`docs/v1-open-issues-research-2026-09-26.ja.md` | 2026-09-26 版への 2 回目のレビューと、未決事項（IP、復旧）の事前調査。項目ごとの対応表は無い（凍結前の見直しと重なるものはそちらで扱った。IP と復旧は v1 の外） |
| — | `docs/v1-core-wire-delta.ja.md` | 分ける前の v0 からの差分（経緯） |

## 4. レビューで見てほしい観点

1. **規範の文だけで作れるか。** core と `oep-if-*` と registry だけを読んで、host（または probe）を書けるか。足りない所、ガイドや記録を読まないと
   決まらない所、「目安」や「など」で逃げている所を指摘してほしい。数が規範の文と registry で食い違っていれば registry が誤り。
2. **断りの理由は 1 つに決まるか。** core §4.3 の「断り方の順」（見出し → 送り直し → セッション → window → malformed → unsupported →
   unavailable → no_connection）を、各インターフェースの op に当てたとき、同じ状況に 2 つの理由が作れる所が残っていないか。
3. **意図して固定した所の理由は成り立つか。** [凍結の範囲](v1-freeze-decisions.ja.md) §0.3 の表（フレームの見出し、u8 の op / tag、要求の並びに len 無し、
   confirm に host の上限を足さない、probe は速さの候補を宣言しない、など）。理由が崩れる使い方があれば、それが凍結前に直す候補。
4. **8 つの原則に反する所は無いか。** [ゼロベース再検討](v1-zero-base-proposal.ja.md) §1: 容器は自分の長さを知る、伸ばし方は 1 つ、要求は probe に
   応答は host に合わせる、ハードウェアの性質の値は u32、宣言と状態を混ぜない、仕組みより不変条件、識別子と時計は 1 つずつ、断り方の順は 1 つ。
5. **参考の数字の出どころが狭い所。** `host-development-guide` §7 の数字（5 %、10 %、16 フレーム、3 秒、60 フレーム）と `link-measurements` の結論は、
   UART bridge としては **2 種類の変換チップ（CH340 と、FTDI 互換を名乗る CH552）**、USB としては 2 系統の MCU の実測から来ている。ほかのブリッジ
   （FTDI 純正、CP210x、CDC の MCU）や native の OS での計測を歓迎する。規範はこれらの数字に依らない（握手だけ）ので、凍結は止めない。

## 5. oep-spec（仕様、番号の表、実験）

### 5.1 文書の状態

| 状態 | PATH（`docs/`） |
|---|---|
| **v1 の規範** | `oep-core`、`oep-if-*`（6 つ）、`target-console-dmseq` |
| 凍結の範囲と決定 | `v1-freeze-decisions`（§0 範囲、§A / §B の 13 項目）、`v1-zero-base-proposal`、`v1-zero-base-review-2026-10-02`、`v1-freeze-review-2026-10-01`（対応済み） |
| 実務（規範ではない） | `host-development-guide`、`probe-development-guide`、`release-testing` |
| 記録（実測。追記は自由） | `link-measurements`、`uart-speed-negotiation`、`logic-capture`（§7 以降）、`probe-cdc-and-persistence` §7 |
| v1 の理由 | `session-and-exclusivity`、`capability-*`（3 つ）、`console-stream`、`target-connection-use-cases`、`probe-cdc-and-persistence`、`usb-identity` |
| 案と経緯、レビューの対応 | `v1-open-proposals`、`review-response-2026-09-26`、`review-answer-*`（3 つ）、`hardware-source-review-2026-09-26`、`v1-operation-test-audit-2026-09-26`、`v1-open-issues-research-2026-09-26`、`v1-core-wire-delta` |
| 上流の合意（目的・要求・モデル） | `project-concept`（英語版 `project-concept.md` は古い）、`use-cases`、`project-requirements`、`conceptual-model`、`responsibility-boundaries`、`development-guidelines` |
| v0 以前の設計の比較と候補（経緯） | `common-protocol-behavior`、`information-model`、`interaction-patterns`、`message-model-candidates`、`message-routing-model`、`message-header-layout-comparison`、`request-correlation-lifecycle`、`implicit-correlation-comparison`、`correlation-width-comparison`、`correlation-retirement-model`、`request-completion-semantics`、`activity-reference-lifecycle`、`connection-binding-design-inputs`、`minimal-connection-channel`、`bootstrap-*`（3 つ）、`uart-*`（`uart-speed-negotiation` を除く 5 つ） |
| v0（v1 で置き換え済み） | `v0-core-wire-model`、`v003-destructive-prototype` |
| 調査 | `capture-survey`（sigrok、市販のロジアナの机上調査） |

### 5.2 番号の表と生成

| PATH | 中身 |
|---|---|
| `registry/oep-v1.toml` | **v1 の wire 上の全数値の唯一の定義**（op、TLV の tag、reject reason、status、enum、timing、limits、USB の識別、インターフェースの名前と revision） |
| `tools/oepgen1.py` | registry から C++ ヘッダ、Python、JS のモジュールを生成し、番号の規則（core §2）を検査する。`python3 tools/oepgen1.py --check` で同期を確かめる |
| `generated/oep-v1/oep_v1_registry.{h,py,js}` | 生成物。probe と client はこれを写して使う（`OepRegistry.h`、`oep_client/registry.py`） |
| `tests/registry_v1/` | registry と生成物の試験（`cd tests && uv run pytest registry_v1`） |

### 5.3 そのほか

| PATH | 中身 |
|---|---|
| `experiments/*/README.ja.md` | 非規定の比較実装と実験の記録（flash-primitives、dm-console-seq、v003-reset-flags、session-id-cost、v0 以前の bootstrap-layout / message-routing / uart-binding） |
| `tests/` | 実験実装の検証環境（`tests/README.ja.md`） |
| `memo.ja.md` | 調査・移行のメモ、ユーザーのメモの控え（作業用） |
| `README.ja.md` | 文書の一覧（状態の区別は無いので、この手引きの 5.1 を使う） |

## 6. oep-probe-arduino（probe の実装、Arduino ライブラリ、0.0.27）

`README.ja.md` に構成と使い方、`CHANGELOG.md` に版ごとの変更がある。各ファイルの冒頭のコメントに、対応する仕様の節が書いてある。

| PATH | 中身 |
|---|---|
| `src/Oep.h`、`src/OepResult.h` | 本体の部品（Interface の基底、TLV、describe、Tail の解析、結果） |
| `src/OepEndpoint.*` | フレームの受け口、シリアルの口の共用（core §3.4）と port_speed（§3.5）、名前で探すインターフェース、セッションのロック、通知、plan、複数の経路 |
| `src/OepBind.*`、`src/OepStream.h` | シリアルの口に流すもの（bind）、位置つきのストリーム |
| `src/OepRegistry.h` | oep-spec の生成物の写し |
| `src/OepTarget.*`、`src/OepSwd.*`、`src/OepDebug.h` | `oep.wire.rvswd` / `oep.wire.swio` / `oep.wire.swd`、`oep.target.riscv-dm` / `oep.target.arm-adi`、共通部品 |
| `src/OepConsole.*`、`src/OepDmConsole.*` | `oep.target.console` と framing（dmseq ほか） |
| `src/OepFixture.*`、`src/OepP4I2cTarget.*`、`src/OepP4SpiTarget.*` | `oep.fixture.gpio` / `uart` / `i2c-target` / `spi-target` |
| `src/OepCapture.*`、`src/OepAnalog.*`、`src/OepCaptureGroup.*`、`src/OepSampler.*`、`src/OepDirectBulkStream.h` | `oep.fixture.logic` / `analog` / `capture-group`、サンプラ、ゼロコピーの bulk 転送 |
| `src/OepConfig.*` | `oep.probe.config`（スロット、bind、disable、保存） |
| `src/OepCh32Dm.*`、`src/OepDmiPhy.h`、`src/Oep*Phy.*`、`src/Oep*Frame.h`、`src/OepRp2BitBang.h` | DM の操作と線の物理層（bit-bang） |
| `src/OepFrame.*`、`src/OepPlatform.h`、`src/OepPinTable.h` | フレーム、Arduino の core の差、ピンの表と空き・無効の状態 |
| `examples/Firmware/OepProbe/` | チップごとに 1 本の firmware（profile ごと）。ピンはすべて host が選び、治具は設定で表す。release の image はこれ |
| `examples/01.Basics/`〜`06.Settings/`、`examples/Tools/` | 学ぶための example（Minimal / Fixture / CustomInterface / MultipleTransports / Rvswd・Swio・Swd / LogicCapture / ProbeConfig）と立ち上げの道具 |

## 7. oep-client-python（host の実装、Python、0.0.27）

| PATH | 中身 |
|---|---|
| `README.ja.md` | 公開するモジュールの一覧と使い方 |
| `src/oep_client/host.py` | セッションの規則、要求と結果、エラーの階層、pipeline、待ち時間 |
| `src/oep_client/link.py`、`frames.py`、`cobs.py`、`usb_stream.py`、`hid_stream.py` | transport（シリアル、USB vendor bulk、vendor HID）、フレーム、COBS + CRC、立て直し |
| `src/oep_client/message.py`、`registry.py` | メッセージの形、oep-spec の番号の表の写し |
| `src/oep_client/core.py`、`catalog.py`、`names.py`、`interfaces.py`、`dump.py` | 名前で探す、describe、plan、表示 |
| `src/oep_client/riscv.py`、`arm.py`、`console.py`、`fixture.py`、`capture.py`、`config.py` | インターフェースごとの client |
| `src/oep_client/linktest.py`、`speed_record.py` | 線の試験（link_source / link_sink の matrix）と速さの記録（host ガイド §7.4 の形） |
| `src/oep_client/ch32_flash.py`、`rp2350.py`、`uiapduino.py` | target の知識（host が持つ分担の実例） |
| `src/oep_client/fake.py`、`fake_capture.py`、`endpoint.py`、`fake_serial.py`、`fake_serve.py` | ハードウェアなしの偽の probe（動く spec。`python -m oep_client.fake_serve` で pty / TCP に出す） |
| `tests/test_*.py` | ハードウェアなしの試験（`uv run pytest`、247 件） |
| `tests/hw/` | 実機の試験（§2）。`README.ja.md` に各試験が確かめることと、ボードごとの焼き方 |

## 8. 周辺のリポジトリ（参考）

| PATH | 中身 |
|---|---|
| oep-client-js | JS の client（未公開）。fake に対する試験と、ブラウザの手動確認 |
| ArduinoCore-CH32RV `tests/manual/oep_smoke/`、`libraries/SerialDMSeq/` | 実機での回帰（OEP の probe で書き込み、コンソールで判定）、target 側の dmseq |
| wch-protocols（`experiments/`、`protocols/`、`captures/`） | 既存の probe の線上の観測の記録。OEP の設計の事実の出どころ（実験の番号 E1xx で参照される） |

## 9. 用語

| 用語 | 意味 |
|---|---|
| interface / fn | probe が名前で出す機能（`oep.wire.rvswd` など）と、その番号（fn。list で分かる） |
| describe | interface が自分の能力を TLV で述べるもの（宣言だけ。状態は別の op） |
| session / lock / lease | 要求を送る権利。1 つの host がロックを持ち、lease（期限）を keepalive で延ばす |
| connection | target とのデバッグの接続。誰も使わなくなったら閉じる。番号は probe で 1 つの空間（core §9） |
| plan | probe のピンをどのインターフェースのどの役に使うかの割り当て |
| slot / bind / disable | `oep.probe.config` の項目: 保存した plan、シリアルの口に流すもの、probe が触らない channel |
| port_speed | セッションの間だけ UART bridge の速さを上げる握手（core §3.5） |
| TLV | tag(u8)、長さ(u8)、値。要求の TLV は critical だけ。知らない値は失敗として扱う |
| dmseq | target のコンソールを、デバッグモジュールの DATA0 / DATA1 で通番と CRC つきで運ぶ framing |

## 10. 読むときの注意

- 規範は「〜する」「〜しない」の文で、数は値（目安ではない）。実験の番号（X1〜X6、P1〜P7、E1xx）、日付、チップやボードの名前は記録の文書にある。
- 「未確定」「未確認」と書いたものは、まだ確かめていない。
- 同じことを別の文書で古い形で書いていることがある（v0 以前の比較の文書、`v1-core-wire-delta.ja.md` など）。v1 では
  `oep-core.ja.md` と `oep-if-*.ja.md` が正しく、番号は `registry/oep-v1.toml` が正しい。
- 実装の振る舞いを確かめたいときは、probe は `src/Oep*.cpp`、client は `src/oep_client/` を見るのが早い。どちらも
  冒頭のコメントに、対応する仕様の節が書いてある。
