# OEP の仕様とガイド

このディレクトリには、プロトコル全体の規範、実装の共通ガイド、仕様の保守方針を置く。標準インターフェースの規範は [interfaces/](../interfaces/README.ja.md)、wire 上の数値の正は [registry/](../registry/README.ja.md) にある。

## 読む順番

1. [目的と範囲](project-concept.ja.md): OEP が扱う範囲と host / probe の役割。
2. [はじめに](getting-started.ja.md): 接続から機能の利用までの流れ。
3. [OEP core](oep-core.ja.md) と [transport](oep-transports.ja.md): メッセージ、セッション、機能の発見、通信経路の規範。
4. [適合要件](conformance.ja.md): 実装が満たす要件と確認方法。

## 目的別の案内

| 目的 | 文書 |
|---|---|
| host を実装する | [host 開発ガイド](host-development-guide.ja.md) |
| probe を実装する | [probe 開発ガイド](probe-development-guide.ja.md) |
| 用語を確認する | [用語集](glossary.ja.md) |
| 安全性と接続先の信頼を扱う | [安全とセキュリティ](security.ja.md) |
| USB デバイスを識別する | [USB の識別](usb-identity.ja.md) |
| revision と互換性を確認する | [版と安定性](versioning.ja.md) |
| 情報を置くリポジトリを決める | [リポジトリ間の責務](repository-boundaries.ja.md) |
| 仕様をレビューする | [レビューガイド](review-guide.ja.md) |

規範とガイドの区分は各文書の冒頭で示す。変更は [貢献手順](../CONTRIBUTING.ja.md) に従い、凍結までは日本語版を正として保守する。
