# OEP v1 レビューガイド

状態: **ガイド**（規範ではない）。現行仕様をレビューするための入口であり、過去の検討記録ではない。

## 対象

規範は次の三つで完結する。

1. [OEP core](oep-core.ja.md) と [transport](oep-transports.ja.md)
2. [標準インターフェース](../interfaces/README.ja.md)から参照される各 `.ja.md`
3. [registry](../registry/oep-v1.toml)

ガイド、生成物、テストベクタ、各実装は規範を補助・検証するが、規則を追加しない。リポジトリの責務は [リポジトリ間の責務](repository-boundaries.ja.md) に従う。

コアを先にレビューし、仕様から適合テストを作って確定する。その後、全拡張に適用するインターフェース共通契約、標準 OEP インターフェース固有契約を順にレビューする。3段階の範囲と検査条件は [適合検査](conformance.ja.md) を参照する。

## 確認すること

- 規範だけで probe と host の独立実装を作れるか。必須動作、境界値、失敗時の結果、資源の寿命が一意か。
- 固定部、TLV、op、enum、timing、limit が registry と一致するか。
- 未知の値・未知の TLV・未対応 op に対する動作が core の拡張規則と矛盾しないか。
- 再送、重複実行、順序、timeout、再接続、再起動の各境界で状態が一意か。
- session、plan、connection、stream、capture segment の所有者と解放条件が明確か。
- probe が宣言する能力と、その時点の状態が混同されていないか。
- target 固有の知識や製品固有の制約が共通仕様へ入り込んでいないか。
- 安全性またはセキュリティに影響する操作が、失敗時に部分適用されるか原子的か明記されているか。
- ガイドが規範に無い義務を追加していないか。

## 機械検査

```sh
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest
```

機械検査が通っても意味上の完全性は保証しない。変更したインターフェースについて、正常系だけでなく malformed、unsupported、locked、no_session、no_resource、failed / partial と再送を確認する。

## レビュー結果の反映

採用する指摘は規範、registry、ベクタ、適合要件へ直接反映する。採用理由が将来の互換性判断に必要なら、規則の直後または [版と安定性](versioning.ja.md) に短く残す。レビュー回答表や日付付き提案書は追加しない。
