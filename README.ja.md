# Open Embedded Probe Specification

[English](README.md)

Open Embedded Probe（OEP）は、組み込み開発用probeが提供する機能を共通の意味で公開し、異なるprobe実装とhost softwareの間で相互利用できる状態を目指すprojectです。

現在、project名、相互運用を中心とする目的、OEP外の専用通信へ迂回しない原則、および非互換な派生をOEPとして識別しない原則までを合意しています。その他の目的の文言、範囲、要求、技術方式、運用方針は検討中であり、このrepositoryにはまだ公開済みのprotocol仕様はありません。

まず、解決したい問題、projectの目的、相互運用の意味、対象範囲、成功条件を定義します。機能の分類、protocol構造、接続方法、USBやPIDの扱いなどは、その上流の合意から段階的に検討します。

- [プロジェクトの目的と範囲](docs/project-concept.ja.md)
- [相互運用ユースケース](docs/use-cases.ja.md)
- [Project要求](docs/project-requirements.ja.md)
- [概念モデル](docs/conceptual-model.ja.md)
- [責任境界](docs/responsibility-boundaries.ja.md)
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
