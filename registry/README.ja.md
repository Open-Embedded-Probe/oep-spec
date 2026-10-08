# Wire 番号の registry

[oep-v1.toml](oep-v1.toml) は OEP v1 の wire 上の番号と定数の唯一の定義である。op、TLV tag、enum、共通 status、USB の識別用定数などを持つ。各値の意味と payload の構造は [core](../docs/oep-core.ja.md)、[transport](../docs/oep-transports.ja.md)、[標準インターフェース](../interfaces/README.ja.md) に定める。registry のテーブル構造は TOML 冒頭のコメントで説明している。

## 更新方法

規範文書と registry を同じ変更で更新し、リポジトリのルートで実行する。

```sh
python3 tools/oepgen1.py
python3 tools/oepgen1.py --check
```

生成した定数は [generated/oep-v1/](../generated/oep-v1/README.ja.md) に置く。wire ベクタに影響する変更では [ベクタ](../tests/vectors/README.ja.md) も更新し、[自動検査](../tests/README.ja.md) を実行する。番号の割り当てと互換性の判断は [貢献手順](../CONTRIBUTING.ja.md) と [版と安定性](../docs/versioning.ja.md) に従う。
