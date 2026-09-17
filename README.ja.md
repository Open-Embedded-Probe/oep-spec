# Open Embedded Probe Specification

[English](README.md)

Open Embedded Probe（OEP）は、組み込み開発用probeが提供する機能を共通の意味で公開し、異なるprobe実装とhost softwareの間で相互利用できる状態を目指すprojectです。

現在確定しているのはproject名だけです。目的、範囲、要求、技術方式、運用方針を含め、このrepositoryの文書はすべて検討中のたたき台であり、公開済みのprotocol仕様ではありません。

まず、解決したい問題、projectの目的、相互運用の意味、対象範囲、成功条件を定義します。機能の分類、protocol構造、接続方法、USBやPIDの扱いなどは、その上流の合意から段階的に検討します。

- [プロジェクトの目的と範囲](docs/project-concept.ja.md)
- [調査・移行メモ](memo.ja.md)

検討中の実装repository構成:

- [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino) — Arduino向けprobe実装
- [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python) — Python client libraryとreference CLI

## 文書と言語に関する現在の案

現在の文書は英語と日本語の二言語で作成しています。英語版は`.md`、対応する日本語版は`.ja.md`とし、各翻訳pairから相互にリンクしています。この運用を正式な規則とするかは未決です。

source code、test vector、機械可読registry、protocol field名の言語規則は未決です。

## License

このrepositoryの内容は[MIT License](LICENSE)で公開します。

このlicenseが将来のUSB VID:PID利用へどのように関係するかを含め、project PIDの有無、取得方法、利用条件およびgovernanceは未決です。現時点で一般利用できるproject PIDはありません。
