# Open Embedded Probe Specification

[English](README.md)

Open Embedded Probe（OEP）は、組み込み開発用の probe（デバッガ、ロジックアナライザ、治具）が、自分の機能を共通の意味で
公開するためのプロトコルで、異なる probe の実装と異なる host のソフトウェアが一緒に動くようにする。host は probe の機能を
名前で見つけ、それぞれに何ができるかを聞いて使う。target ごとの知識は host が持つ。

## 状態

OEP v1 は**凍結の候補**である。規範の文と registry は揃っていて（決めていない数は残っていない）、参照の実装はそれに従い、
実機で試験している。凍結までは、破壊的な変更を revision を上げずに入れる。凍結で何を止め、何を自由にしておくかは
[凍結の範囲](docs/v1-freeze-decisions.ja.md) §0。

**言語**: 規範は英語の文である。日本語の文書（`.ja.md`）は訳で、両者が食い違えば英語の文が正しい。ガイドと記録の一部は
日本語だけである。

## 文書の地図

`docs/` のどの文書も、冒頭の行に状態を書いている: **規範**、**ガイド**、**記録**。

**規範**（仕様）:

- [OEP core](docs/oep-core.ja.md): 層、フレーム、メッセージ、セッション、発見、plan、資源の寿命、通知、インターフェースの書き方。
- 標準インターフェース: [共通部品](docs/oep-if-common.ja.md)、[線とデバッグ](docs/oep-if-debug.ja.md)、
  [コンソール](docs/oep-if-console.ja.md)（framing: [dmseq](docs/target-console-dmseq.ja.md)）、[fixture](docs/oep-if-fixture.ja.md)、
  [キャプチャ](docs/oep-if-capture.ja.md)、[probe の設定](docs/oep-if-probe-config.ja.md)。
- [registry/oep-v1.toml](registry/oep-v1.toml): v1 の wire 上のすべての数の唯一の定義。`tools/oepgen1.py` がそこから
  `generated/oep-v1/`（C++、Python、JS）を作る。`python3 tools/oepgen1.py --check` で同期を確かめる。

**ガイド**（規範ではない）:

- [レビューの手引き](docs/review-guide.ja.md): どこに何があるか、最短の読む順番、すべての文書の状態。
- [プロジェクトの目的と範囲](docs/project-concept.ja.md)。
- host と probe の開発ガイド、リリースの試験、USB の識別（日本語だけ:
  [host](docs/host-development-guide.ja.md)、[probe](docs/probe-development-guide.ja.md)、
  [リリースの試験](docs/release-testing.ja.md)、[USB の識別](docs/usb-identity.ja.md)）。

**記録**（規範ではない）: 決めた理由、実測、レビュー、v1 より前の経緯。一覧は[レビューの手引き](docs/review-guide.ja.md) §5.1
にある。多くは日本語だけである。実験は `experiments/` に、その試験の環境は `tests/`（[tests/README.ja.md](tests/README.ja.md)）にある。

## 始め方

1. [OEP core](docs/oep-core.ja.md) を読み、次に要る標準インターフェースを読む。
2. 数は `registry/oep-v1.toml` から取るか、`generated/oep-v1/` の生成物を写して使う。
3. host は oep-client-python の偽の probe（`python -m oep_client.fake_serve`、pty か TCP）に当てて試し、probe は同じ package の
   `oep dump --port <port>`（すべてのインターフェースの list と describe）で見る。

参照の実装:

- [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino): Arduino のライブラリ `OpenEmbeddedProbe` と
  probe の firmware。
- [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python): Python の host
  （`pip install oep-client-python`）、`oep` の命令と偽の probe。

USB の識別: host が OEP の probe を自動で見分けるのは、プロジェクトの USB の VID:PID が registry に載ったときの、その VID:PID
だけである（今は載っていない）。unit_id で名指した probe は USB の serial number で見つけ、confirm と describe で確かめる。
それ以外は利用者が口を選ぶ（core §3.3）。

## 貢献

このリポジトリが唯一の正である。変更は、maintainer がこのリポジトリを直接直すか、このリポジトリへの pull request で入れる。
規則の変更と文言の変更、`oep.` の名前と registry の値の足し方、第三者のインターフェース、errata は
[CONTRIBUTING](CONTRIBUTING.ja.md) にある。

## License

仕様の文と registry は、このリポジトリのほかのものと同じく [MIT License](LICENSE) で公開する。この license は、プロジェクトの
USB の VID:PID を使う許可を与えない。
