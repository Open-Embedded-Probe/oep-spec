# OEP の仕様への貢献

[English](CONTRIBUTING.md)

この文書と [CONTRIBUTING.md](CONTRIBUTING.md) は同じことを書く。

## 仕様の置き場

このリポジトリが OEP の唯一の正である。仕様は規範の文（`docs/` の `oep-core.ja.md`、`oep-transports.ja.md` と、`interfaces/` の、名前が `oep.` で始まるインターフェースの `oep-if-*.ja.md`、`target-console-dmseq.ja.md`。凍結までは日本語が作業の文）と、
番号の registry `registry/oep-v1.toml` である。実装は仕様に従うもので、仕様を決めるものではない。実装が適合するために何をするか、それをどう確かめるかは [適合](docs/conformance.ja.md) に並べてある。

仕様を変えるやり方は 2 つ: maintainer がこのリポジトリを直接直すか、誰でもこのリポジトリに pull request を出す。誤りは issue で
知らせるか、pull request で直してよい。

v1 の凍結までは、日本語の文（`.ja.md`）が作業の文で、変更は日本語の文に入れる。英語の文書は保たず、凍結のときに日本語から作り直す。そのときから英語の文が規範として正しく、変更は両方の言語を同じ commit で直し、両者が食い違えば英語が正しい。

## 変更の 2 つの種類

- **文言の変更**: probe や host のすることは変わらない。分かりやすい文、誤字、訳の直し、コメント、例、リンク、状態の行。
  文言の変更はそのまま入れてよい。
- **規則の変更**: 実装がしなければならないことが変わる。または registry の値（op、tag、enum、timing、limit、名前、revision）が
  変わる。pull request には、規則、理由、どの実装が追随するかを書き、merge の前に実装者のレビューを受ける。実装は仕様の後で
  直す。

規範の文は、文だけで実装できなければならない: 数は目安ではなく値で、手順のすべての分かれ道を書く。チップ、ボード、製品の名前、
実測、日付、逸話は記録の文書に置く。規範とガイドは記録が無くても完結する: 読む人が必要とするもの（事実、数、短い理由）は
文そのものに書き、どちらも記録へはリンクしない。ガイドは例としてチップの名前を挙げてよい。記録を並べるのは、レビューの手引きの §5.1 と README だけ。

## `oep.` の名前や registry の値を足す

`oep.` の名前と registry のすべての番号は、`registry/oep-v1.toml` と、新しい名前や値を定める文を一緒に変える pull request を
merge したときにだけ割り当てる。その pull request では:

1. `registry/oep-v1.toml` と規範の文（両方の言語）を直す。
2. `python3 tools/oepgen1.py`、続いて `python3 tools/oepgen1.py --check` を走らせ、`generated/` を commit する。
3. `python3 tools/oepvectors1.py --check` を走らせる（ベクタが扱う規則が変わったら `python3 tools/oepvectors1.py` を走らせ、`tests/vectors/` を commit する）。
4. `cd tests && uv run pytest registry_v1 vectors` を走らせる。

merge されるまでは、自分の逆 DNS の名前か、出荷する probe が使わない実験用の op の範囲 0xF0〜0xFF（core §2.5）で試す。

## 第三者のインターフェース

project のものでないインターフェースは逆 DNS の名前（例 `io.github.<owner>.<name>`、core §13）を使う。プロトコルの上では、`oep.` の名前のインターフェースと同じに扱われる。登録も、ここへの pull request も
要らない。op、tag、値は、そのインターフェース自身の定義が割り当てる。

## 凍結の後の errata

v1 の凍結の後も、errata は同じ pull request の手順で入れる。文言だけを直す erratum は文言の変更、振る舞いを変えるものは
規則の変更で、core §2.7 の revision の規則に従う。

## License

貢献は、このリポジトリの [MIT License](LICENSE) のもとで行う。
