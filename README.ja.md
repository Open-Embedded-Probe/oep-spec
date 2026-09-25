# Open Embedded Probe Specification

[English](README.md)

Open Embedded Probe（OEP）は、組み込み開発用probeが提供する機能を共通の意味で公開し、異なるprobe実装とhost softwareの間で相互利用できる状態を目指すprojectです。

現在、project名、相互運用を中心とする目的、機能に必要な通信経路をOEP native pathまたは明示的なexternal bindingとして扱う原則、および非互換な派生をOEPとして識別しない原則までを合意しています。その他の目的の文言、範囲、要求、技術方式、運用方針は検討中であり、このrepositoryにはまだ公開済みのprotocol仕様はありません。

まず、解決したい問題、projectの目的、相互運用の意味、対象範囲、成功条件を定義します。機能の分類、protocol構造、接続方法、USBやPIDの扱いなどは、その上流の合意から段階的に検討します。

- [レビューの手引き（どこに何が書いてあるか、読む順番）](docs/review-guide.ja.md)
- [開発ガイドライン（作業版）](docs/development-guidelines.ja.md)
- [core wire model v0 draft（作業版）](docs/v0-core-wire-model.ja.md)
- v1 の仮置き（議論の合意。実験してから調整する）
  - [能力の識別方式の比較](docs/capability-identification-comparison.ja.md)
  - [能力の宣言モデル（describe の語彙）](docs/capability-declaration-model.ja.md)
  - [能力の名前の階層](docs/capability-name-hierarchy.ja.md)
  - [core wire model v1（v0 からの差分）](docs/v1-core-wire-delta.ja.md)
  - [セッションと排他](docs/session-and-exclusivity.ja.md)
  - [コンソールのストリーム](docs/console-stream.ja.md)
  - [target の発見と接続](docs/target-connection-use-cases.ja.md)
  - [target のコンソール: dmseq](docs/target-console-dmseq.ja.md)
  - [host 開発ガイド](docs/host-development-guide.ja.md)
  - [probe 開発ガイド](docs/probe-development-guide.ja.md)
- v1 の未合意の案（決めてから上へ移す）: [スキャンで見つけた組への attach と PENDING、fixture の payload](docs/v1-open-proposals.ja.md)
- [registry/oep-v0.yaml](registry/oep-v0.yaml) — v0 の wire 上の全数値の唯一の定義。`uv run tools/oepgen.py` が `generated/` に C library、Python module、test vector を生成する（`--check` で同期確認）
- [プロジェクトの目的と範囲](docs/project-concept.ja.md)
- [相互運用ユースケース](docs/use-cases.ja.md)
- [Project要求](docs/project-requirements.ja.md)
- [概念モデル](docs/conceptual-model.ja.md)
- [責任境界](docs/responsibility-boundaries.ja.md)
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
- [実験実装の検証環境](tests/README.ja.md)
- [V003開発プローブ破壊的prototype](docs/v003-destructive-prototype.ja.md)
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
