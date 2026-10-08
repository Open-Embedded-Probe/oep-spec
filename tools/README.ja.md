# 仕様の生成・検査ツール

このディレクトリには、仕様リポジトリ内の定数と共有ベクタを生成し、commit された出力との一致を検査するツールを置く。Python 3.11 以降の標準ライブラリで実行できる。

| ツール | 入力と出力 |
|---|---|
| `oepgen1.py` | [registry](../registry/README.ja.md) の番号規則を検査し、[言語別定数](../generated/oep-v1/README.ja.md) を生成する |
| `oepvectors1.py` | 規範の規則をコード化した計算と registry の数値から、[共有 wire ベクタ](../tests/vectors/README.ja.md) を生成する |

`oepvectors1.py` は Markdown を自動解析しない。ベクタが扱う規則を変更した場合は、規範文書とこのツールの計算を同じ変更で更新する。

## 実行方法

リポジトリのルートで実行する。引数なしでは生成物を書き出し、`--check` では書き換えずに検査する。不整合がある場合は非ゼロで終了する。

```sh
python3 tools/oepgen1.py
python3 tools/oepvectors1.py
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
```

生成物は元の変更と一緒に commit する。検査全体の実行方法は [tests/](../tests/README.ja.md)、変更の判断基準は [貢献手順](../CONTRIBUTING.ja.md) を参照する。
