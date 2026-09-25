# Open Embedded Probe — レビューの手引き（どこに何が書いてあるか）

状態: 2026-09-26 時点の地図。OEP をまだ知らない人がレビューするときに、どこから読めばよいか、どの PATH に何があるかをまとめる。
PATH は各リポジトリの根からの相対。

## 1. OEP とは

組み込み開発用の probe（デバッガ、ロジックアナライザ、治具）が提供する機能を、共通の意味で公開するプロトコルと、その
実装です。異なる probe の実装と、異なる host のソフトウェアが、互いに使えることを目指しています。

- **probe**: USB などで PC につながる装置（今の実装は ESP32-P4、classic ESP32、RP2040 / RP2350 の上で動く Arduino
  スケッチ）。自分のピン（fixture）と、target へのデバッグ線（RVSWD、SWIO、SWD）を持つ。
- **host**: PC 側のソフトウェア（Python の client、書き込みツール ch32rv など）。
- **target**: 開発中のマイコン（WCH の CH32 系、RP2350 など）。

分担の原則: **target の知識は host が持つ**。probe は線と DMI（RISC-V Debug Module Interface）/ DP・AP の転送しか知らず、
flash の書き方やチップ固有の手順は host にある。

## 2. 今の状態

- **v1 を「固める候補」として詰めている段階**です。
  - 合意した規則は `docs/v1-core-wire-delta.ja.md` にあり、実装（probe と client）はそれに合わせてあります。
  - ただし、まだ公開した仕様ではなく、**破壊的な変更を前提**にしています（利用者はまだいない）。
- 決め方は「**先に実験・試作をして、その結果で仕様を固める**」。仕様の文書には、実験の番号（X1、P3 など）や日付がそのまま残っています。
- 文書は**日本語が先**です。英語版は固まってから作ります（既存の英語の文書は古い）。
- v0（最初の草案）は v1 で置き換え済みで、v0 の文書と v0 のコードは経緯として残っています。

## 3. 最短の読む順番（v1 のレビュー）

| 順 | PATH（oep-spec） | 何が分かるか |
|---:|---|---|
| 1 | `docs/project-concept.ja.md` | 目的と範囲（上流の合意）。短い |
| 2 | `docs/v1-core-wire-delta.ja.md` | **v1 の本体**。§0 共通の規則（番号、TLV、失敗の返し方、connection の寿命）、§1 フレームと経路（USB vendor / HID / CDC / UART）、§2〜§4 セッション・reject・長い操作・通知、§5 core とインターフェースごとの op（線、RISC-V DM、ARM、コンソール、fixture、capture、probe の設定） |
| 3 | `docs/session-and-exclusivity.ja.md` | セッション、ロック、lease の考え方 |
| 4 | `docs/capability-identification-comparison.ja.md`、`docs/capability-declaration-model.ja.md`、`docs/capability-name-hierarchy.ja.md` | 機能（interface）を名前で探す方式、describe の語彙、名前の付け方 |
| 5 | `docs/console-stream.ja.md`、`docs/target-console-dmseq.ja.md` | target のコンソールを位置つきのストリームで読む形と、デバッグモジュールのデータレジスタで双方向に運ぶ framing（dmseq） |
| 6 | `docs/target-connection-use-cases.ja.md` | target の発見と接続の使い方 |
| 7 | `docs/logic-capture.ja.md` | キャプチャ（ロジック / アナログ）。長い（約 1000 行）。§3〜§5 が基本の形 |
| 8 | `docs/probe-cdc-and-persistence.ja.md` | USB の複数の経路、シリアル転送（CDC）、設定の保存、起動モード、probe 自身の更新。§7 に試作 P1〜P7 の結果（v1 §5.5 / §5.10 の根拠） |
| 9 | `docs/host-development-guide.ja.md`、`docs/probe-development-guide.ja.md` | host と probe を書く人への実務の約束（フレームの送り方、立て直し、USB-UART の扱いなど） |
| 10 | `docs/v1-open-proposals.ja.md` | まだ合意していない案（スキャンした組への attach、PENDING など） |

## 4. oep-spec（仕様、番号の表、実験）

### 4.1 文書の状態

| 状態 | PATH（`docs/`） |
|---|---|
| **v1 の現行**（上の表の 2〜10） | `v1-core-wire-delta`、`session-and-exclusivity`、`capability-*`（3 つ）、`console-stream`、`target-console-dmseq`、`target-connection-use-cases`、`logic-capture`、`probe-cdc-and-persistence`、`host-development-guide`、`probe-development-guide`、`v1-open-proposals` |
| 上流の合意（目的・要求・モデル） | `project-concept`（英語版 `project-concept.md` もあるが古い）、`use-cases`、`project-requirements`、`conceptual-model`、`responsibility-boundaries`、`development-guidelines`（作業版） |
| v0 以前の設計の比較と候補（経緯。v1 の決定の理由をたどるとき） | `common-protocol-behavior`、`information-model`、`interaction-patterns`、`message-model-candidates`、`message-routing-model`、`message-header-layout-comparison`、`request-correlation-lifecycle`、`implicit-correlation-comparison`、`correlation-width-comparison`、`correlation-retirement-model`、`request-completion-semantics`、`activity-reference-lifecycle`、`connection-binding-design-inputs`、`minimal-connection-channel`、`bootstrap-*`（3 つ）、`uart-*`（5 つ） |
| v0（v1 で置き換え済み） | `v0-core-wire-model`、`v003-destructive-prototype` |
| 調査 | `capture-survey`（sigrok、市販のロジアナ、ESP32 / RP2 の机上調査） |

### 4.2 番号の表と生成

| PATH | 中身 |
|---|---|
| `registry/oep-v1.toml` | **v1 の wire 上の全数値の唯一の定義**（op、TLV の tag、reject reason、status、enum、インターフェースの名前と revision） |
| `tools/oepgen1.py` | registry から C++ ヘッダと Python モジュールを生成し、番号の規則（§0）を検査する。`uv run tools/oepgen1.py --check` で同期を確かめる |
| `generated/oep-v1/oep_v1_registry.h`、`generated/oep-v1/oep_v1_registry.py` | 生成物。probe と client はこれを写して使う（`OepV1Registry.h`、`oep_client/v1/registry.py`） |
| `tests/registry_v1/test_registry_v1.py` | registry と生成物の試験 |
| `registry/oep-v0.yaml`、`tools/oepgen.py`、`generated/oep-v0-*` | v0 の同じもの（経緯） |

### 4.3 そのほか

| PATH | 中身 |
|---|---|
| `experiments/*/README.ja.md` | 非規定の比較実装と実験の記録（flash-primitives: host 主導の書き込みの部品、dm-console-seq: dmseq の実験、v003-reset-flags、session-id-cost、v0 以前の bootstrap-layout / message-routing / uart-binding） |
| `tests/` | 実験実装の検証環境（ハードウェアを使う試験を含む。`tests/README.ja.md`） |
| `memo.ja.md` | 調査・移行のメモ、ユーザーのメモの控え（作業用） |
| `README.ja.md` | 文書の一覧（状態の区別は無いので、この手引きの 4.1 を使う） |

## 5. oep-probe-arduino（probe の実装、Arduino ライブラリ）

注意: **`README.ja.md` は v0 のころのままで、今の実装と合っていない**（「まだ無いもの」に書かれた多くは v1 で実装済み）。
下の表と、各ファイルの冒頭のコメントを見てください。

### 5.1 `src/`

| PATH | 中身 | 世代 |
|---|---|---|
| `src/OepV1.h` | v1 の共通の部品（Interface の基底、TLV、describe、Tail の解析） | v1 |
| `src/OepV1Endpoint.*` | フレームの受け口、名前で探すインターフェース、セッションのロック、通知、plan、複数の経路（`addTransport`） | v1 |
| `src/OepV1Registry.h` | oep-spec の生成物の写し | v1 |
| `src/OepV1Target.*` | `oep.wire.rvswd` / `oep.wire.swio`（attach / detach、connection の利用者）と `oep.target.riscv-dm` | v1 |
| `src/OepV1Swd.*` | `oep.wire.swd` / `oep.target.arm-adi` | v1 |
| `src/OepV1Console.*`、`src/OepV1Stream.h` | `oep.target.console`、位置つきのストリーム、CDC の口への転送（`StreamPort`） | v1 |
| `src/OepV1Fixture.*` | `oep.fixture.gpio` / `oep.fixture.uart`（CDC の口への素通しを含む） | v1 |
| `src/OepV1Capture.*`、`src/OepV1Sampler.*` | `oep.fixture.capture`（P4 の PARLIO、classic ESP32 のソフトウェアのサンプラ） | v1 |
| `src/OepV1Config.*` | `oep.probe.config`（設定、起動モード、NVS への保存）。試作の段階 | v1（試作） |
| `src/OepDirectBulkStream.h` | EspUsbDevice の vendor bulk をゼロコピーで使う transport（キャプチャのストリーミング用） | v1 |
| `src/OepCh32Dm.*`、`src/OepDmiPhy.h` | CH32 のデバッグモジュールの操作（halt / resume / reset、ブロック転送） | 共通 |
| `src/OepRvswdPhy.*`、`src/OepSwioPhy.*`、`src/OepRvswdFrame.h`、`src/OepSwdFrame.h`、`src/OepRp2BitBang.h` | 線の物理層（RVSWD、SWIO、SWD の bit-bang） | 共通 |
| `src/OepDmConsole.*` | コンソールの framing（SerialSDI / SerialDMDATA / dmseq） | 共通 |
| `src/OepFrame.*`、`src/OepPlatform.h`、`src/OepFixtureServices.*`、`src/OepP4I2cTarget.*`、`src/OepP4SpiTarget.*` | フレーム、Arduino の core の差、ピンの表、ESP-IDF の I2C / SPI スレーブ | 共通 |
| `src/OepEndpoint.*`、`src/OepService.h`、`src/OepProbeIdentity.h`、`src/OepFixtureCapture.*`、`src/OepBulkStream.h`、`src/oep_v0.*`、`src/OEP_V0_CODEC_SOURCE.txt` | v0 の endpoint と codec | v0（経緯） |

### 5.2 `examples/`（probe のファームウェア）

| PATH | 中身 |
|---|---|
| `examples/Esp32P4X035Probe/` | ESP32-P4 + CH32X035 の治具（OEP は USB-Serial/JTAG） |
| `examples/Esp32V003Probe/` | classic ESP32 + CH32V003（UIAPduino）の治具（SWIO） |
| `examples/Rp2350L103Probe/`、`examples/Rp2040ZeroProbe/` | RP2350 / RP2040 の probe（RVSWD、SWD） |
| `examples/Esp32P4HsProbe/` | ESP32-P4 の HS USB（vendor bulk）の probe |
| `examples/Esp32P4HsPrototype/` | 試作 P1〜P5 / P7（複数の経路、UART の素通し、設定と起動モード、DFU / Mass Storage での更新、USB 構成ごとの速さ）と、その host 側のスクリプト（`host/`） |
| `examples/Esp32P4X035ConsolePrototype/` | 試作 P6（コンソールを CDC の口に流す、自動 attach、connection の寿命）と host 側のスクリプト |
| `examples/PicoDebugPortSurvey/` | Pico でのデバッグポートの調査用 |

### 5.3 そのほか

| PATH | 中身 |
|---|---|
| `docs/*.ja.md` | 日付入りの作業記録（評価、進め方、ピンの予約、Pico の机、X035 のリリースの作業表）。経緯 |
| `tests/hil/` | v0 の HIL 試験（**古い**。v1 の実機の回帰は ArduinoCore-CH32 の `tests/manual/oep_smoke/` で行っている） |
| `library.properties` | Arduino ライブラリの定義 |

## 6. oep-client-python（host の実装、Python）

| PATH | 中身 |
|---|---|
| `README.ja.md` | モジュールの一覧と使い方（v1 の現行） |
| `src/oep_client/v1/host.py` | セッションの規則、要求と結果、エラーの階層、pipeline |
| `src/oep_client/v1/link.py`、`frames.py`、`cobs.py`、`usb_stream.py`、`hid_stream.py` | transport（シリアル、USB vendor bulk、vendor HID）、フレーム、COBS + CRC、立て直し。`open_usb_host()` は vendor、HID の順に試す |
| `src/oep_client/v1/message.py`、`registry.py` | メッセージの形、oep-spec の番号の表の写し |
| `src/oep_client/v1/core.py`、`catalog.py`、`names.py`、`interfaces.py`、`dump.py` | インターフェースを名前で探す、describe、plan、表示 |
| `src/oep_client/v1/riscv.py`、`arm.py`、`console.py`、`fixture.py`、`capture.py` | インターフェースごとの client |
| `src/oep_client/v1/ch32_flash.py`、`rp2350.py`、`uiapduino.py` | target の知識（CH32 の書き込み、RP2350 の boot ROM、UIAPduino のブートローダ）。host が持つ分担の実例 |
| `src/oep_client/v1/fake.py`、`endpoint.py` | ハードウェアなしの偽の probe（試験用） |
| `src/oep_client/v1/target.py` | 主なものを 1 か所から import する入口 |
| `src/oep_client/v0/` | v0 の client（経緯） |
| `tests/test_v1_*.py` | ハードウェアなしの試験（`uv run pytest`、134 件） |

## 7. 周辺のリポジトリ（参考）

| PATH | 中身 |
|---|---|
| ArduinoCore-CH32 `tests/manual/oep_smoke/` | 実機での回帰（CH32 の Arduino core の試験スケッチを OEP の probe で書き込み、コンソールで判定する）。`README.ja.md` に実績 |
| ArduinoCore-CH32 `libraries/SerialDMSeq/` | target 側の dmseq の実装（`target-console-dmseq.ja.md` の相手） |
| wch-protocols（`experiments/`、`protocols/`、`captures/`） | WCH-Link / LinkE などの既存の probe の線上の観測の記録。OEP の設計の事実の出どころ（実験の番号 E1xx で参照される） |

## 8. 用語

| 用語 | 意味 |
|---|---|
| interface / fn | probe が名前で出す機能（`oep.wire.rvswd` など）と、その番号（fn。list で分かる） |
| describe | interface が自分の能力を TLV で述べるもの |
| session / lock / lease | 要求を送る権利。1 つの host がロックを持ち、lease（期限）を keepalive で延ばす |
| connection | target とのデバッグの接続。host の attach や、設定の bind が「使っているもの」で、誰も使わなくなったら閉じる |
| plan | probe のピンをどのインターフェースのどの役に使うかの割り当て |
| bind | CDC の口に何を流すか（fixture.uart か target.console）の設定 |
| 起動モード | probe が USB に何を出すか（vendor だけ、vendor + HID + CDC など）の組み合わせ |
| TLV | tag(u8)、長さ(u8)、値。要求の TLV は critical だけ。知らない値は失敗として扱う |
| dmseq | target のコンソールを、デバッグモジュールの DATA0 / DATA1 で通番と CRC つきで運ぶ framing |

## 9. 読むときの注意

- 仕様の文書に、実験の番号（X1〜X6、P1〜P7、E1xx）、日付、「ユーザーの方針」がそのまま入っている。決定の根拠を残すため
  で、規範は「〜する」「〜しない」の文。
- 「未確定」「未確認」と書いたものは、まだ確かめていない。
- 同じことを別の文書で古い形で書いていることがある（v0 以前の比較の文書など）。v1 では `v1-core-wire-delta.ja.md`
  が優先で、そこからリンクした文書がその次。
- 実装の振る舞いを確かめたいときは、probe は `src/OepV1*.cpp`、client は `src/oep_client/v1/` を見るのが早い。どちらも
  冒頭のコメントに、対応する仕様の節が書いてある。
