# 共有 wire ベクタ

このディレクトリには、host / probe の実装が共通に取り込む JSON ベクタと、その自己整合を確認する `test_vectors.py` を置く。

| ファイル | 対象 |
|---|---|
| `checks.json`、`cobs.json` | checksum と COBS encoding |
| `headers.json`、`confirm.json` | メッセージヘッダと接続確認 |
| `refusals.json` | 要求の拒否とエラー応答 |
| `discovery.json`、`sessions.json` | 機能の発見とセッション |
| `core_lifecycle.json` | 未完了再送のcredit、leaseの処理/送信の境界、監視と経路喪失 |
| `ops.json`、`ops_encoding.json` | 各 op の要求・応答と encoding |
| `logic_layout.json` | logic capture の区画内の layout |
| `interface_profiles.json` | 名前付き機能なし、独自拡張、受信専用UART、生のARM転送の小さい宣言例。動作traceではない |
| `interface_boundaries.json` | 通知の閾値・停止端数・frame分割、欠落時の受信範囲、保存失敗の応答/state、group開始の拒否/失敗、I2C/SPIの境界。前提と外部観測を伴う例 |

各 JSON の `about` に読み方を示し、`spec` を持つ case は対応する規範の箇所も示す。前提状態がある case は、その状態を用意して検査する。共有ベクタは列挙した場面を検査するものであり、適合全体を証明しない。各実装に必要な追加試験は [適合要件](../../docs/conformance.ja.md) に従う。

## 更新と検査

JSON は直接編集せず、[tools/oepvectors1.py](../../tools/README.ja.md) の計算を規範に合わせて更新する。リポジトリのルートで実行する。

```sh
python3 tools/oepvectors1.py
python3 tools/oepvectors1.py --check
cd tests
uv run pytest vectors
```

`test_vectors.py` は encoding の復号、独立した checksum 計算、規範で定めた値などで出力を検査する。`test_replay_state.py` は独立した状態モデルで、再送履歴、open の再送、終了したセッション、16 bit の境界を検査する。実装側の unit test と実機試験は、それぞれの実装リポジトリで行う。
`test_interface_boundaries.py`は境界例の独立した復号と状態・区間の計算を行う。保存媒体の電源断耐性やSPIの電気的動作を証明するものではない。

- `core_policy.json`: 任意の方針判定と再送/force/公開発見の順序。認証方式や本番endpointは実装しない。
