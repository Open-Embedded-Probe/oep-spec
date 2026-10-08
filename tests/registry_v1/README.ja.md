# OEP v1 registry の検査

`test_registry_v1.py` は、[registry](../../registry/README.ja.md) の番号規則、テーブル構造、予約値などと、[言語別生成物](../../generated/oep-v1/README.ja.md) の一致を検査する。生成ツールが不正な定義を拒否することも確認する。

この検査だけを実行する場合は、リポジトリのルートから次を実行する。

```sh
cd tests
uv run pytest registry_v1
```

仕様の規則を変えた場合は、それに対応する検査も更新する。検査全体の案内は [tests/README.ja.md](../README.ja.md) を参照する。
