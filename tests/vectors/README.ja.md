# 共有 wire ベクタ

このディレクトリには、host / probe の実装が共通に取り込む JSON ベクタと、その自己整合を確認する `test_vectors.py` を置く。

| ファイル | 対象 |
|---|---|
| `checks.json`、`cobs.json` | checksum と COBS encoding |
| `headers.json`、`confirm.json` | メッセージヘッダと接続確認 |
| `refusals.json` | 要求の拒否とエラー応答 |
| `discovery.json`、`sessions.json` | 機能の発見とセッション |
| `ops.json`、`ops_encoding.json` | 各 op の要求・応答と encoding |
| `logic_layout.json`、`multirate.json` | logic capture の layout と multirate stream |

各 JSON の `about` に読み方を示し、`spec` を持つ case は対応する規範の箇所も示す。前提状態がある case は、その状態を用意して検査する。共有ベクタは列挙した場面を検査するものであり、適合全体を証明しない。各実装に必要な追加試験は [適合要件](../../docs/conformance.ja.md) に従う。

## 更新と検査

JSON は直接編集せず、[tools/oepvectors1.py](../../tools/README.ja.md) の計算を規範に合わせて更新する。リポジトリのルートで実行する。

```sh
python3 tools/oepvectors1.py
python3 tools/oepvectors1.py --check
cd tests
uv run pytest vectors
```

`test_vectors.py` は encoding の復号、独立した checksum 計算、規範で定めた値などで出力を検査する。実装側の unit test と実機試験は、それぞれの実装リポジトリで行う。
