# Open Embedded Probe Specification

[English](README.md)

Open Embedded Probe（OEP）は、組み込み開発用probeが提供する機能を共通の意味で公開し、異なるprobe実装とhost softwareの間で相互利用できる状態を目指すprojectです。

現在は **v1 を固める候補の仕様**があります（2026-09-26）。規範は、本体の [OEP core](docs/oep-core.ja.md) と、標準インターフェース
の `docs/oep-if-*.ja.md`、番号の唯一の定義の [registry/oep-v1.toml](registry/oep-v1.toml) です。実装（[oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino)、
[oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python)）はこれに合わせてあり、実機で確かめています。まだ公開した
仕様ではなく、破壊的な変更を前提にしています。文書は日本語が先（原文）です。規範の文書には、レビューのための英語訳があります:
[OEP core](docs/oep-core.md)、標準インターフェースの [共通部品](docs/oep-if-common.md)、[線とデバッグ](docs/oep-if-debug.md)、
[コンソール](docs/oep-if-console.md)、[fixture](docs/oep-if-fixture.md)、[キャプチャ](docs/oep-if-capture.md)、[probe の設定](docs/oep-if-probe-config.md)
（コンソールの framing の [dmseq](docs/target-console-dmseq.ja.md) は日本語だけ）、[凍結前の決定と凍結の範囲](docs/v1-freeze-decisions.md)、
[レビューの手引き](docs/review-guide.md)。訳と日本語の原文が食い違えば、日本語の原文が正しい。

2026-09-29 に、シリアルの口で OEP のフレームと target のコンソールを 1 本で運ぶ形（core §3.4）と、スロットと bind の登録
（`oep.probe.config`）を入れました。実装は、Arduino のライブラリ `OpenEmbeddedProbe`（oep-probe-arduino）と、Python の host
（`pip install oep-client-python`、`import oep_client`、`oep` の命令と偽の probe）です。

上流の合意（project名、相互運用を中心とする目的、機能に必要な通信経路を OEP native path または明示的な external binding として
扱う原則、非互換な派生を OEP として識別しない原則）は、下の「プロジェクトの目的と範囲」などにあります。

- [レビューの手引き（どこに何が書いてあるか、読む順番）](docs/review-guide.ja.md)
- **v1 の規範**（固める候補。2026-09-26 に本体と標準インターフェースに分けた）
  - [OEP core（本体）](docs/oep-core.ja.md) — 層と線引きの規則、フレーム、メッセージ、セッション、発見、plan、寿命、通知、インターフェースの書き方
  - 標準インターフェース: [共通部品](docs/oep-if-common.ja.md)、[線とデバッグ](docs/oep-if-debug.ja.md)、[コンソール](docs/oep-if-console.ja.md)（framing: [dmseq](docs/target-console-dmseq.ja.md)）、[fixture](docs/oep-if-fixture.ja.md)、[キャプチャ](docs/oep-if-capture.ja.md)、[probe の設定](docs/oep-if-probe-config.ja.md)
  - [registry/oep-v1.toml](registry/oep-v1.toml) — v1 の wire 上の全数値の唯一の定義（`uv run tools/oepgen1.py --check`）
- v1 の理由・実測・実務（規範ではない）
  - [能力の識別方式の比較](docs/capability-identification-comparison.ja.md)
  - [能力の宣言モデル（describe の語彙）](docs/capability-declaration-model.ja.md)
  - [能力の名前の階層](docs/capability-name-hierarchy.ja.md)
  - [セッションと排他](docs/session-and-exclusivity.ja.md)
  - [コンソールのストリーム](docs/console-stream.ja.md)
  - [target の発見と接続](docs/target-connection-use-cases.ja.md)
  - [キャプチャ（設計と実測）](docs/logic-capture.ja.md)、[キャプチャの机上調査](docs/capture-survey.ja.md)
  - [シリアルの口と永続化](docs/probe-cdc-and-persistence.ja.md)
  - [host 開発ガイド](docs/host-development-guide.ja.md)
  - [target ごとの scan と attach の記録](docs/target-scan-notes.ja.md)（ピンの探し方、つまずき、チップ・治具ごと）
  - [probe 開発ガイド](docs/probe-development-guide.ja.md)
  - [USB の識別](docs/usb-identity.ja.md)（host が probe を iProduct と describe で見分ける方法、参照の firmware の今の VID:PID）
  - [core wire model v1（v0 からの差分、経緯）](docs/v1-core-wire-delta.ja.md)
- v1 の案と決めた経緯: [案と決めた経緯](docs/v1-open-proposals.ja.md)、[凍結前の決定と凍結の範囲（2026-10-02）](docs/v1-freeze-decisions.ja.md)、[凍結前の全面見直し（2026-10-01、対応済み）](docs/v1-freeze-review-2026-10-01.ja.md)、[ゼロベース再検討と仕様案（2026-10-01、採用・反映済み）](docs/v1-zero-base-proposal.ja.md)、[ゼロベース再点検（2026-10-02）](docs/v1-zero-base-review-2026-10-02.ja.md)、第三者レビュー（2026-09-26）の [1](docs/review-answer-2026-09-26.ja.md) と [2（移植性）](docs/review-answer-portability-2026-09-26.ja.md)、[レビューへの対応](docs/review-response-2026-09-26.ja.md)
- 2026-09-26 版（oep-spec 2ff1d62、probe 3160dee、client 75ee13e）へのレビューと調査（未対応）: [実機・ソース・テスト項目レビュー](docs/hardware-source-review-2026-09-26.ja.md)、[コア・標準インターフェースの移植性と復旧性レビュー](docs/review-answer-core-standard-portability-2026-09-26.ja.md)、[操作・状態遷移・テスト監査](docs/v1-operation-test-audit-2026-09-26.ja.md)、[未決事項（IP 経路、設定からの復旧）の事前調査](docs/v1-open-issues-research-2026-09-26.ja.md)
- 上流の合意（目的・要求・モデル）
  - [プロジェクトの目的と範囲](docs/project-concept.ja.md)
  - [相互運用ユースケース](docs/use-cases.ja.md)
  - [Project要求](docs/project-requirements.ja.md)
  - [概念モデル](docs/conceptual-model.ja.md)
  - [責任境界](docs/responsibility-boundaries.ja.md)
  - [開発ガイドライン（作業版）](docs/development-guidelines.ja.md)
- 経緯（v0 以前の検討。規範ではない。各文書の冒頭にそう書いてある）
  - [core wire model v0 draft（作業版）](docs/v0-core-wire-model.ja.md)
  - [共通protocolの抽象的な振る舞い](docs/common-protocol-behavior.ja.md)
  - [共通protocolの情報model](docs/information-model.ja.md)
  - [最小interaction pattern](docs/interaction-patterns.ja.md)
  - [共通message model候補](docs/message-model-candidates.ja.md)
  - [Message routing model候補](docs/message-routing-model.ja.md)
  - [Message header構成比較](docs/message-header-layout-comparison.ja.md)
  - [Request correlationのscopeとlifecycle](docs/request-correlation-lifecycle.ja.md)
  - [明示correlationと暗黙対応の比較](docs/implicit-correlation-comparison.ja.md)
  - [Request correlation幅と再利用の比較](docs/correlation-width-comparison.ja.md)
  - [Request correlationのretire条件](docs/correlation-retirement-model.ja.md)
  - [Requestの受理と完了](docs/request-completion-semantics.ja.md)
  - [Activityの参照とlifecycle](docs/activity-reference-lifecycle.ja.md)
  - [Connection binding設計入力](docs/connection-binding-design-inputs.ja.md)
  - [最小connection channel候補](docs/minimal-connection-channel.ja.md)
  - [Bootstrap layout候補](docs/bootstrap-layout-candidates.ja.md)
  - [Bootstrap具体layout実験案](docs/bootstrap-concrete-layout-experiment.ja.md)
  - [Bootstrap layout比較実装（非規定）](experiments/bootstrap-layout/README.ja.md)
  - [Message routing比較実装（非規定）](experiments/message-routing/README.ja.md)
  - [UART bindingの信頼性model候補](docs/uart-reliability-model.ja.md)
  - [UART connection epoch同期候補](docs/uart-connection-epoch.ja.md)
  - [UART timeoutと回復model候補](docs/uart-timeout-recovery-model.ja.md)
  - [UART duplexとflow control候補](docs/uart-duplex-flow-control.ja.md)
  - [UART frame layout比較](docs/uart-frame-layout-comparison.ja.md)
  - [UART binding比較実装（非規定）](experiments/uart-binding/README.ja.md)
  - [V003開発プローブ破壊的prototype](docs/v003-destructive-prototype.ja.md)
  
- [実験実装の検証環境](tests/README.ja.md)
- [調査・移行メモ](memo.ja.md)

検討中の実装repository構成:

- [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino) — Arduino向けprobe実装
- [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python) — Python client libraryとreference CLI

## 文書と言語に関する現在の進め方

検討中の文書は日本語で作成し、内容が固まった段階で英語版を作成します。既存の英語文書は、それ以降に加えた日本語の検討内容へ常に追随するものではありません。

source code、test vector、機械可読registry、protocol field名の言語規則は未決です。

## License

このrepositoryの内容は[MIT License](LICENSE)で公開します。

このlicenseが将来のUSB VID:PID利用へどのように関係するかを含め、project PIDの有無、取得方法、具体的な利用条件およびgovernanceは未決です。ただし、OEPの必須要求を満たさないprotocolまたは実装には、OEPのproject PIDを利用させない方針です。現時点で一般利用できるproject PIDはありません。
