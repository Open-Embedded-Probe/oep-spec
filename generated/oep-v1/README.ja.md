# OEP v1 の生成定数

[registry/oep-v1.toml](../../registry/oep-v1.toml) から生成した定数を、実装言語ごとに置く。

| ファイル | 用途 |
|---|---|
| `oep_v1_registry.h` | C++ 用ヘッダ |
| `oep_v1_registry_c.h` | C 用ヘッダ |
| `oep_v1_registry.py` | Python 用モジュール |
| `oep_v1_registry.js` | JavaScript 用モジュール |

これらは定数の定義であり、protocol の encoder / decoder や host / probe の実装は含まない。各実装は、対応する仕様の commit または tag と合わせて取り込む。

## 再生成と確認

リポジトリのルートで実行する。

```sh
python3 tools/oepgen1.py
python3 tools/oepgen1.py --check
```

生成コードは直接編集しない。埋め込まれた registry hash は、元の TOML と一致するかを確認する値であり、wire 互換性の保証ではない。互換性は [版と安定性](../../docs/versioning.ja.md) に従って判断する。
