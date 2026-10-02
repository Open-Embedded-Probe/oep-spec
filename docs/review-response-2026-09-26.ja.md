# OEP — レビューへの対応（2026-09-26）

状態: **記録**（規範ではない。対応表）。2026-09-26 に受けた 2 つの第三者レビューの各項目を、どう決め、規範のどこに入れ、どの
コミットで反映し、実機で確かめたかを並べる。レビューの文書そのものは変えていない。コミットは oep-spec のもの（probe と
client の対応するコミットは、そのコミットの前後にある）。

- レビュー 1: [review-answer-2026-09-26.ja.md](review-answer-2026-09-26.ja.md)（§2〜§3 と、更新後の再レビュー §7）
- レビュー 2: [review-answer-portability-2026-09-26.ja.md](review-answer-portability-2026-09-26.ja.md)（移植性、R1〜R14）

実機の確かめ: x035 / v003 / l103 の oep_smoke（ArduinoCore-CH32 `tests/manual/oep_smoke/`、14 本の sketch）と probe の検査
（`oep_probe_checks.py`）、X035 の治具の試作（コンソールの bind）、43c6 の P4（キャプチャのストリーミング、設定）。

## レビュー 1

| 項目 | 決定 | 規範 | oep-spec | 実機 |
|---|---|---|---|---|
| 2.1 規範を 1 つに | 本体（oep-core）と標準インターフェース（oep-if-*）に分け、ほかは経緯・理由とした | core、oep-if-* | 4270a10、73e1ec9 | — |
| 2.2 / 3.1 寿命の統一 | 1 つの表: end では残し、lease の期限切れと force で外す | core §9 | 55bc092、a35117b | 検査（end で残る、期限切れで外れる） |
| 2.3 revision の規則 | 固定部分の意味か長さを変えるときだけ上げる | core §2.7 | bacdb45 | — |
| 2.4 重複排除 | 同じ corr の送り直しに、probe が覚えた応答を返す | core §5.2 | a35117b | 検査（同じ応答、corr_reused、result_lost） |
| 2.5 スキャンした組への attach | scan は組の並び、attach は pins（critical） | oep-if-debug §1 | fbb95f1 | 検査（scan と pins、許さない組の拒否） |
| 2.6 キャプチャの位置を u64 に | ストリームの位置と start_us を u64 に | oep-if-common §1、oep-if-capture §2 | 0fd55ed | 43c6 でストリーミング 1〜160 MHz |
| 2.7 force と activity | force は期限切れと同じ後始末。activity はその後、長い操作ごと外した（7.4） | core §6.4、§10 | f022095、e5570bf | — |
| 2.8 registry を完全な定義に | registry に全番号、生成物と同期 | registry | a2168c3 | registry の試験 |
| 3.2 subscribe の再設定 | 同じ fn の subscribe は原子的に置き換える | core §11.3 | f022095 | — |
| 3.3 ネットワークの信頼境界 | TCP は信頼できる接続か認証したトンネルの中だけ | core §3.1 | f022095 | — |
| 3.4 設定の正規形 | hash は critical の bit を外した正規形、重複は malformed。その後キーごとの置き換えに（R9） | oep-if-probe-config §2 | f022095、900741b | 43c6 で hash の一致 |
| 7.2 corr の再利用 | corr は要求ごとに 1 ずつ進め、同一性は corr だけ。表から落ちた古い corr は result_lost | core §4.1、§5.2 | e5570bf | 検査（古い corr が result_lost） |
| 7.3 end の送り直し | 重複の判定をセッションの判定より先に。送り直した end でロックは立たない | core §5.2 | e5570bf | 検査（送り直した end でロックが空いたまま） |
| 7.4 / 7.5 activity の所有と lease | 長い操作を v1 から外す（予約） | core §10 | e5570bf | — |
| 7.6 end の後の資源 | 次に成功した open で、そのセッションに移る | core §9 | e5570bf | — |
| 7.7 u8 の番号の一周 | u16 にして同じ boot の間は再利用しない | core §9 | e5570bf | 検査（番号が +1 で進む） |
| 7.8 スキャンの続き | 応答に tried。残りは host が送る | oep-if-debug §1 | e5570bf | — |
| 7.9 critical の規則 | critical は host が選ぶ。インターフェースが必須とした TLV は必ず | core §2.3 | e5570bf | — |
| 7.10 scale の単位 | nV にそろえた | oep-if-capture §1.2 | 0bed87d | — |

## レビュー 2（移植性）

| 項目 | 決定 | 規範 | oep-spec | 実機 |
|---|---|---|---|---|
| R1 chip_id の照合 | attach が任意で target_id（scheme + 値）を返し、設定の target は scheme / mask / value で照合する（WCH のリビジョンのビットは host の mask）。bind に pins と max_speed | oep-if-debug §1、oep-if-probe-config §1.1 | 900741b | X035 の治具（違う target の拒否、正しい target でコンソール、再起動後の自動 attach） |
| R2 全 wire の寿命に RISC-V の記述 | RISC-V の扱いを riscv-dm の節（§4.6）へ移した | oep-if-debug §2、§4.6 | 900741b | — |
| R3 riscv-dm の範囲 | dmi / halt / resume が必須、ほかは features。高水準の op は RV32 の hart 0。ブロック転送の前提と clobbers | oep-if-debug §4 | 900741b | — |
| R4 dpc による出し直し | resume は resumeack で判断、run は出し直さない。CH32 の出し直しは host（`ch32_flash.resume`） | oep-if-debug §4.2、§4.4 | 900741b、3c97446 | L103 で resume 20/20、smoke 14/14 |
| R5 資源の取り合い | 取る前に plan / connection / 設定と確かめ、断るときは何も変えない | core §8.1 | 900741b | — |
| R6 plan が 1 つ | plan は fn ごと。plan_release は fn の並び | core §8 | 900741b | 検査（別の fn を通して残り・解放を確かめる） |
| R7 uart の TX を解放後も駆動 | 解いたピンは idle の状態（既定 Hi-Z）。治具は idle でプルアップを明示 | core §8、oep-if-fixture §2、oep-if-probe-config §1 | 900741b | x035 / v003 / l103 の smoke 14/14 |
| R8 アナログのチャネル別の換算 | scale / skew / frontend をチャネルごとに | oep-if-capture | 900741b | —（アナログは未実装） |
| R9 TLV の長さの上限 | 設定の項目を 1 項目 1 キーに、キーごとの置き換え | oep-if-probe-config §1〜§2 | 900741b | 43c6（plan 2 項目の hash と再起動後） |
| R10 SWD の同一性と reset | connection の同一性に targetsel。reset の線の op は後から足す | oep-if-debug §5 | 900741b | — |
| R11 任意機能と対応値の宣言 | gpio の modes、uart の formats。SDI / DMDATA の framing を定義 | oep-if-fixture、oep-if-console §3 | 900741b | — |
| R12 保存した設定の識別 | 保存に interface 一覧の識別値。違えば適用しない。USB の項目は任意の群。bind_state | oep-if-probe-config §2〜§3 | 900741b | X035 の治具（再起動後に適用、bind_state） |
| R13 target の知識の範囲 | 特化したものは名前で分かるインターフェースに置く（標準でも独自でも）。汎用の名前には入れない | core §13 規則 8 | 64b34ce、3c97446 | — |
| R14 小さい同期実装と接続の条件 | run の上限なしを断る。USB の OEP の口は iInterface で見分ける。max_frame は両方向 | oep-if-debug §4.4、core §3.3 | 900741b | — |

## 2026-09-26 のあとの変更（レビューの項目ではないもの）

| 変更 | 規範 | oep-spec | 実機 |
|---|---|---|---|
| v0 をすべて消した（probe の v0 の部品と codec、client の `oep_client.v0`、spec の v0 の registry と生成器）。ESP32 の I2C / SPI の target は独自インターフェース revision 1 に作り直した | — | f867043（probe af1ab35、client b98e09d） | x035 / v003 の smoke 14/14 |
| ArduinoCore-CH32 の周辺のトレース試験 6 本を v1 に移した（`tests/manual/oep_smoke/trace_kit.py`） | — | — | x035 / v003（各試験の README） |
| 移す途中で見つけた client の不具合: キャプチャの読み出しの見出しの長さ、パイプラインの送り直し、長い読み出しの間の lease | core §5.2、§4.1 | —（client 2a8721a、1a65cc3、7db4bee） | x035 / v003 の i2c、periph |
| gpio の mode 7（プルアップとプルダウンを両方）。表現できないことを理由に試験の確認を外さない | oep-if-fixture §1 | 6aaf618 | x035 の adc の中間電圧 452〜464 |

2026-09-26 版（2ff1d62 / 3160dee / 75ee13e）への 2 回目のレビューと調査（[実機・ソース](hardware-source-review-2026-09-26.ja.md)、
[移植性と復旧性](review-answer-core-standard-portability-2026-09-26.ja.md)、[操作と試験の監査](v1-operation-test-audit-2026-09-26.ja.md)、
[未決事項の事前調査](v1-open-issues-research-2026-09-26.ja.md)）には、**まだ対応していない**。

## 確かめていないこと

- 保存した設定が、firmware の変更（interface の一覧の違い）で適用されない場合。
- SWD の targetsel の違いの拒否、アナログのキャプチャ（実装が無い）。
- L103 で新しく attach(halt) すると、8 回に 1 回ほど status line になる（線の揺れと見ているが、原因は未確認）。
- x035 の gpio_matrix で PB11 のプルダウンの idle が 1 になる（v0 のときは通っていた）。x035 の adc のばらつきが v0 のときより大きい。
  v003 の adc の試験用スケッチが RAM に入らない。
