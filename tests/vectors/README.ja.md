# 共有 wire ベクタ

このディレクトリには、host / probe の実装が共通に取り込む JSON ベクタと、その自己整合を確認する `test_vectors.py` を置く。

| ファイル | 対象 |
|---|---|
| `checks.json`、`cobs.json` | checksum と COBS encoding |
| `hid_reports.json` | HID の report（transports §1）: フレームを report に詰めたときの count と first、report が欠けたとき・途中から開いたとき・count や first が壊れたときに読めるメッセージ |
| `headers.json`、`confirm.json` | メッセージヘッダと接続確認 |
| `refusals.json` | 要求の拒否とエラー応答 |
| `discovery.json`、`sessions.json` | 機能の発見とセッション |
| `core_extensions.json` | 固定部分（空のものを含む）の後ろの知らない名前つきの拡張 TLV、要求の中の知らない名前（無視、critical なら unsupported）と長さの誤り |
| `core_lifecycle.json` | 未完了再送のcredit、leaseの処理/送信の境界、監視と経路喪失 |
| `core_policy.json` | 任意の方針判定と再送/force/公開発見の順序。認証方式や本番endpointは実装しない |
| `ops.json`、`ops_encoding.json` | 各 op の要求・応答と encoding |
| `logic_layout.json` | logic capture の区画内の layout |
| `capture_formats.json` | キャプチャのデータの形式（capture §1.3 ロジックのブロック、capture §1.4 アナログのブロック、capture §3.8 時刻つきのステート）、トリガの式（capture §4.4）。ロジックは raw と 4 つの縮約（sample、any_high、any_low、change_latch）、区画の最後の部分的なブロックと区間、隙間なく続く区画と隙間の後の区画の change_latch |
| `interface_profiles.json` | 名前付き機能なし、独自拡張、受信専用UART、生のARM転送の小さい宣言例。動作traceではない |
| `settings_file.json` | 設定のファイル（[設定のファイル](../../docs/oep-settings-file.ja.md)）: 宣言と get の値から書き出すファイル、別の番号の probe への入れ直し。`test_settings_file.py` が独立に書き出しと入れ直しを計算する |
| `interface_boundaries.json` | 通知の閾値・停止端数・frame分割、欠落時の受信範囲、serialの飛びを欠落数とする条件、保存失敗の応答/state、group開始の拒否/失敗、I2C/SPIの境界。前提と外部観測を伴う例 |

各 JSON の `about` に読み方を示し、`spec` を持つ case は対応する規範の箇所も示す。前提状態がある case は、その状態を用意して検査する。共有ベクタは列挙した場面を検査するものであり、適合全体を証明しない。各実装に必要な追加試験は [適合要件](../../docs/conformance.ja.md) に従う。

## 更新と検査

JSON は直接編集せず、[tools/oepvectors1.py](../../tools/README.ja.md) の計算を規範に合わせて更新する。リポジトリのルートで実行する。

```sh
python3 tools/oepvectors1.py
python3 tools/oepvectors1.py --check
cd tests
uv run pytest vectors
```

`test_*.py` は、生成ツールとは別に本文から書いた復号、checksum、状態モデルで各 JSON を読み直し、規範で定めた値と比べる。`test_replay_state.py` は再送履歴、open の再送、終了したセッション、16 bit の境界を独立した状態モデルで検査する。境界例の検査は、保存媒体の電源断耐性や SPI の電気的動作を証明するものではない。実装側の unit test と実機試験は、それぞれの実装リポジトリで行う。
