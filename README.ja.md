# Open Embedded Probe Specification

[English summary](README.md)

Open Embedded Probe（OEP）は、組み込み開発用の probe（デバッガ、ロジックアナライザ、治具）が機能を共通の意味で公開し、異なる probe と host を組み合わせて使うためのプロトコルである。target 固有の知識は host が持つ。

## 状態と言語

OEP v1 は凍結前である。凍結までは revision を変えずに非互換な変更が入りうるため、実装は対応する仕様の Git commit または tag を明記する。

凍結までは日本語の文書（`.ja.md`）だけを保守し、これを正とする。英訳は凍結時に作成し、それ以後は英語を規範、日本語を対訳として同時に保守する。古い英訳は誤って現行仕様として読まれるため、このリポジトリには置かない。

## 仕様の正

- [OEP core](docs/oep-core.ja.md) と [transport](docs/oep-transports.ja.md)
- [標準インターフェース](interfaces/README.ja.md)
- wire 上の数値を定める [registry/oep-v1.toml](registry/oep-v1.toml)

wire 上の数値は registry が唯一の定義である。文書と registry が食い違う場合は仕様の欠陥として文書を正し、両方を同じ変更で一致させる。生成物 `generated/oep-v1/` は registry から作るため編集しない。

## 読む順番

1. [目的と範囲](docs/project-concept.ja.md)
2. [はじめに](docs/getting-started.ja.md)
3. [OEP core](docs/oep-core.ja.md)、[transport](docs/oep-transports.ja.md)、必要な[インターフェース](interfaces/README.ja.md)
4. [適合要件](docs/conformance.ja.md)

実装時は [host 開発ガイド](docs/host-development-guide.ja.md) または [probe 開発ガイド](docs/probe-development-guide.ja.md) も参照する。用語、セキュリティ、互換性の方針はそれぞれ [用語集](docs/glossary.ja.md)、[安全とセキュリティ](docs/security.ja.md)、[版と安定性](docs/versioning.ja.md) にまとめた。レビューの入口は [レビューガイド](docs/review-guide.ja.md) である。

## リポジトリの境界

[リポジトリ間の責務](docs/repository-boundaries.ja.md)を正とする。要点は次のとおり。

- `oep-spec`: プロトコル、registry、生成物、共有テストベクタ、適合要件
- `oep-probe-arduino`: probe 実装、platform 固有の制約、firmware のビルドと試験
- `oep-client-python` / `oep-client-js`: host 実装、API、CLI、実装試験
- `wireskein` / `wireskein-web` / `pytest-embedded-wireskein`: OEP を利用するアプリケーションと、それぞれのデータ形式・運用

実装固有の手順、実機測定、製品の制約、調査ログ、適用済み提案、レビュー回答はこのリポジトリに複製しない。最終的な規則と、将来変更しにくい判断に必要な理由だけを現行文書へ残す。過去の経緯は Git 履歴で確認できる。

## 検証

```sh
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest
```

共有ベクタは `tests/vectors/` にある。各実装はこれを取り込み、自身のリポジトリで unit test と結合試験を持つ。

## 貢献

仕様変更、registry の追加、第三者インターフェース、errata の扱いは [CONTRIBUTING.ja.md](CONTRIBUTING.ja.md) を参照する。

仕様、registry、生成物は [MIT License](LICENSE) で公開する。このライセンスはプロジェクトの USB VID:PID の使用許可を含まない。VID:PID の利用条件は、それを管理する probe 実装リポジトリで定める。
