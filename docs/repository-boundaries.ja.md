# OEP リポジトリ間の責務

状態: **ガイド**（規範ではない）。仕様と実装の正を混ぜないための保管規則である。

## 責務

| リポジトリ | 正として持つもの | 持たないもの |
|---|---|---|
| `oep-spec` | プロトコルの規範、標準インターフェース、wire 番号の registry、生成物、共有テストベクタ、適合要件、互換性方針 | 実装コード、platform 固有値、製品の使い方、実機試験結果、調査ログ、適用済み提案 |
| `oep-probe-arduino` | Arduino probe の実装、対応 board と profile、pin・memory・timing の制約、firmware の build・unit test・release、プロジェクト VID:PID の利用条件 | OEP の規範そのもの、host や利用アプリケーションの仕様 |
| `oep-client-python` | Python host library と CLI、仮想ベンチ、target 固有処理、実機を使う結合試験と結果、Python API の互換性 | OEP の規範そのもの、probe firmware の実装条件 |
| `oep-client-js` | JavaScript host library、browser / Node の接続処理、JS API とその試験 | OEP の規範そのもの、他言語 client の設計 |
| `wireskein` | 取得・解析・記録のアプリケーション、WireSkein ファイル形式、OEP を利用する capture workflow | OEP capture interface の規範 |
| `wireskein-web` | WireSkein の browser UI と web library | OEP および WireSkein ファイル形式の正 |
| `pytest-embedded-wireskein` | pytest との統合、test run の保存・照合方法 | OEP、probe、WireSkein の各仕様 |

ほかの consumer も同じ原則に従い、OEP の利用方法は自身のリポジトリに、共通契約だけを `oep-spec` に置く。

## 変更の流れ

1. 相互運用契約を変える必要があれば、`oep-spec` の規範、registry、ベクタを先に変更する。
2. 各実装は、対応する仕様の commit または tag を明記して追随する。
3. 実装で見つかった制約が共通契約を変えないなら、その実装の文書にだけ記録する。
4. 複数実装に共通する必須動作になったときだけ、製品名や測定履歴を除いた規則として `oep-spec` へ戻す。

## 理由を残す基準

理由を残すのは、規則だけでは選択の境界が分からず、将来の変更で同じ問題を再発させる場合に限る。理由は現在採用している選択を直接説明し、比較した案、日時、担当者、commit の列挙はしない。

未決事項は規範文書へ混ぜない。issue で管理し、決定後に最終形だけを文書へ反映する。適用前の提案書と適用後のレビュー回答を現行ツリーへ残さない。Git 履歴は監査のために残る。
