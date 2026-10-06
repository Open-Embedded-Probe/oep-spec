# Open Embedded Probe Specification

[English](README.md)

Open Embedded Probe（OEP）は、組み込み開発用の probe（デバッガ、ロジックアナライザ、治具）が、自分の機能を共通の意味で
公開するためのプロトコルで、異なる probe の実装と異なる host のソフトウェアが一緒に動くようにする。host は probe の機能を
名前で見つけ、それぞれに何ができるかを聞いて使う。target ごとの知識は host が持つ。

## 状態

OEP v1 は**凍結の候補**である。規範の文と registry は揃っていて（決めていない数は残っていない）、参照の実装はそれに従い、
実機で試験している。凍結までは、破壊的な変更を revision を上げずに入れる。凍結で何を止め、何を自由にしておくかは
[版と安定性](docs/versioning.ja.md)、変更の一覧は [CHANGELOG](CHANGELOG.md)。

**言語**: v1 の凍結までは、日本語の文書（`.ja.md`）が作業の文で、規則はそこで決める。英語の文書は凍結のときに日本語から作り直し、
そのときから英語の文が規範として正しくなる。それまでの英語の文書は古いことがあり（各文書の先頭に書いてある）、新しい文書（`oep-transports`
など）は日本語だけである。記録の多くは日本語だけである。

## 文書の地図

`docs/` には本体（core と経路）とガイドと記録、`interfaces/` には名前が `oep.` で始まるインターフェースの文書がある。どの文書も、冒頭の行に状態を書いている: **規範**、**ガイド**、**記録**。

**規範**（仕様）:

- [OEP core](docs/oep-core.ja.md): 層、メッセージ、セッション、発見、channel と資源の寿命、通知、インターフェースの書き方。本体は名前を持たず、fn 0 で話す。
- [OEP の経路](docs/oep-transports.ja.md): フレーム、送り方、複数の経路、USB の見分け方、シリアルの口の共用、区切りの立て直し（本体の層）。
- [インターフェース](interfaces/README.ja.md)（`interfaces/`、名前が `oep.` で始まるもの）: 共通部品、線とデバッグ、コンソール（framing の dmseq）、fixture、キャプチャ、
  probe の設定、plan、再起動、リンク。一覧はその README にある。
- [registry/oep-v1.toml](registry/oep-v1.toml): v1 の wire 上のすべての数の唯一の定義。`tools/oepgen1.py` がそこから
  `generated/oep-v1/`（C++、C、Python、JS）を作る。`python3 tools/oepgen1.py --check` で同期を確かめる。
- [tests/vectors/](tests/vectors/): 機械で読める試験のベクタ（フレーム、ヘッダ、confirm、CRC、発見、セッション、断り方、op）。
  `tools/oepvectors1.py` が文書から計算する。

**ガイド**（規範ではない）:

- [はじめに](docs/getting-started.ja.md): いちばん小さい probe と host を、すべてのバイトと一緒に。次に足すもの。
- [レビューの手引き](docs/review-guide.ja.md): どこに何があるか、最短の読む順番、すべての文書の状態。
- [適合](docs/conformance.ja.md): probe と host が OEP v1 に適合するために何をするか、それをどう確かめるか、適合で何を名乗れるか。
- [host 開発ガイド](docs/host-development-guide.ja.md) と [probe 開発ガイド](docs/probe-development-guide.ja.md): 実務と罠。
- [安全とセキュリティ](docs/security.ja.md): 仕様の安全とセキュリティの考え方を 1 か所に。
- [用語集](docs/glossary.ja.md): 定めた用語とその節、英語と日本語の対応。
- [版と安定性](docs/versioning.ja.md): 何が変わらないか、revision を上げる意味、リリースのタグ。[CHANGELOG](CHANGELOG.md)。
- [プロジェクトの目的と範囲](docs/project-concept.ja.md)、[USB の識別](docs/usb-identity.ja.md)、[リリースの試験](docs/release-testing.ja.md)（プロジェクト自身の手順）。

**記録**（規範ではない）: 決めた理由、実測、レビュー、v1 より前の経緯。一覧は[レビューの手引き](docs/review-guide.ja.md) §5.1
にある。多くは日本語だけである。規範とガイドは記録が無くても完結する。実験は `experiments/` に、その試験の環境は `tests/`（[tests/README.ja.md](tests/README.ja.md)）にある。

## 始め方

1. [はじめに](docs/getting-started.ja.md) のいちばん小さい probe か host を作り、[OEP core](docs/oep-core.ja.md) と要る
   インターフェースの文書を読む。
2. 数は `registry/oep-v1.toml` から取るか、`generated/oep-v1/` の生成物を写して使う。
3. host は oep-client-python の偽の probe（`python -m oep_client.fake_serve`、pty か TCP）に当てて試し、probe は同じ package の
   `oep dump --port <port>`（すべてのインターフェースの list と describe）で見る。
4. 実装を [適合](docs/conformance.ja.md) のチェックリストに照らして確かめる。

参照の実装:

- [oep-probe-arduino](https://github.com/Open-Embedded-Probe/oep-probe-arduino): Arduino のライブラリ `OpenEmbeddedProbe` と
  probe の firmware。そのガイドの[始め方](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/getting-started.ja.md)と
  [probe の書き方](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/docs/guide/writing-a-probe.ja.md)は、動く probe までの短い道である。
- [oep-client-python](https://github.com/Open-Embedded-Probe/oep-client-python): Python の host
  （`pip install oep-client-python`）、`oep` の命令と偽の probe。

USB の識別: host が OEP の probe を自動で見分けるのは、プロジェクトの USB の VID:PID `1209:4F45`（registry の `usb`）だけである。
unit_id で名指した probe は USB の serial number で見つけ、confirm と describe で確かめる。それ以外は利用者が口を選ぶ（transports §3）。
VID:PID を使ってよい範囲: [PID-USE.ja.md](https://github.com/Open-Embedded-Probe/oep-probe-arduino/blob/main/PID-USE.ja.md)。

## 貢献

このリポジトリが唯一の正である。変更は、maintainer がこのリポジトリを直接直すか、このリポジトリへの pull request で入れる。
規則の変更と文言の変更、`oep.` の名前と registry の値の足し方、第三者のインターフェース、errata は
[CONTRIBUTING](CONTRIBUTING.ja.md) にある。

## License

仕様の文と registry は、このリポジトリのほかのものと同じく [MIT License](LICENSE) で公開する。この license は、プロジェクトの
USB の VID:PID を使う許可を与えない。
