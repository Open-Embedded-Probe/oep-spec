# OEP 仕様への貢献

## 変更する場所

OEP の仕様の正は、規範文書（`docs/oep-core.ja.md`、`docs/oep-transports.ja.md`、`interfaces/*.ja.md`）と `registry/oep-v1.toml` である。凍結までは日本語だけを変更する。実装の挙動を仕様として採用する場合も、先にこのリポジトリの規範文書へ書く。

このリポジトリに置く情報と実装側に置く情報は [リポジトリ間の責務](docs/repository-boundaries.ja.md) に従う。日付付きの提案、会議録、レビュー回答、旧仕様の写しは追加しない。採用した結論は規範またはガイドへ直接反映し、必要な理由だけをその近くに残す。不採用案と検討の順序は Git 履歴または issue で扱う。

## 文言の変更と規則の変更

- **文言の変更**は、probe と host の必須動作を変えない修正である。曖昧さ、誤字、リンク、例、ガイドを直してよい。
- **規則の変更**は、実装の必須動作、wire 上の形、registry の値、名前、revision を変える修正である。変更理由、互換性への影響、追随が必要な実装を pull request に書き、実装者のレビューを受ける。

規範文書は、それだけで相互運用実装を作れる必要がある。必須の分岐、境界値、エラー、寿命を明記し、「通常」「など」「実装による」で必須動作を曖昧にしない。hardware 名、製品名、性能測定、実装上の回避策は、それを所有する実装リポジトリへ置く。

## registry と生成物

`oep.` の名前および wire 上の番号は、定義する規範文書と `registry/oep-v1.toml` を同じ変更で更新したときだけ割り当てる。生成物は直接編集せず、次を実行して commit する。

```sh
python3 tools/oepgen1.py
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest
```

ベクタが扱う規則を変えた場合は、check の前に `python3 tools/oepvectors1.py` で更新する。

第三者のインターフェースは逆 DNS 名（例 `io.github.owner.name`）を使い、この registry への登録を必要としない。`oep.` 名前空間を使うものだけが、このリポジトリのレビュー対象である。

## 凍結後

凍結後の互換性と revision の規則は [版と安定性](docs/versioning.ja.md) に従う。英語を規範、日本語を対訳として同じ変更で更新する。

貢献は [MIT License](LICENSE) のもとで行う。
