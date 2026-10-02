# dmseq の記録（理由、経緯、実測）

状態: **記録**（規範ではない）。規範は [target-console-dmseq](target-console-dmseq.md)（英語が原文、[日本語訳](target-console-dmseq.ja.md)）。
ここには、2026-10-02 に規範の文書から移した理由、経緯、実測を置く。実験の元の草案と結果の表は
[experiments/dm-console-seq](../experiments/dm-console-seq/SPEC-draft.md)。

## 1. 経緯

- ch32rv 側のレビュー 2 回を経て合意した（2026-09-24）。
- v0 のときは target.console（owner 0x0000、id 0x0013）の framing 2 と呼んでいた。v1 では `oep.target.console` の mechanism 2。
- 名前: ch32rv では `monitor --source dmseq`、ArduinoCore-CH32 の target ライブラリは `SerialDMSeq`。

## 2. なぜ通し番号を持たせたか

framing 1（ArduinoCore-CH32 の `SerialDMDATA`、minichlink の framing。v1 の mechanism 1 DMDATA）には通し番号がない。
host の答えの DMI 書込みが黙って落ちると target の word がもう一度読まれて**重複**し、
それを読み戻しで救おうとすると、同じ内容の次のフレームと区別できずに**欠落**する。
dmseq は両方向に 1 bit の通し番号と CRC-8 を持たせ、この二つを区別できるようにした。

所有権を厳密に交代させたことで、framing 1 で要った「空フレームを 1 poll 分寝かせる」回避策は不要になった。

## 3. なぜ CRC が必須か

WCH の probe では、attach が DATA0 に `0xffffffff` を、CH32V30x の flash が `0xe339e339`（bit 7 が 0）を残すことが
実測で分かっており、CRC がないと後者を target が有効な答えとして受け取る。

CRC の init を 0xFF にした理由の一つは、debugger 未接続の V4 が DATA0 を 0 と返すこと（値を保持しないレジスタ）。

計算方法の例: ArduinoCore-CH32 は 16 要素の表で 4 bit ずつ計算する。

## 4. 短いフレームを DATA0 だけにした理由

WCH-LinkE では DMI 1 回が USB 1 往復、約 0.4 ms かかるので、N <= 2 のフレームで DATA1 を読まないと、短いフレームの費用の 1/3 が浮く。

## 5. 空フレームの費用

印字の合間に空フレームを挟むと 1 往復余計にかかり、WCH-LinkE では出力の速さが半分になる。

## 6. session と reset

規範の「target を reset した host は新しい session を始める」に従う実装の例: ch32rv の `run` / `monitor`、OEP の probe の reset。

## 7. target の規則 0 ができた経緯

WCH-LinkE の AttachChip は ESIG を読んだ後に DATA0 に `0xffffffff` を残す。V006 / X035 で開き直したコンソールが流れなかった
（2026-09-29）。bit 7 が 1 の語は host の番なので、未同期の host は無効な word として答えず、target は「まだ自分のフレーム」と
読んで待ち、双方が止まっていた。

規範の「host（任意）」の項（`0xffffffff` を 3 回読んだら bit 7 が 0 の無効な語を書いてよい）は、規則 0 を持たない古い target の
ための保険として入れた。

## 8. dmactive を下ろす debugger

- OEP の probe では、断った自動の attach の後にコンソールが戻るまで 1〜10 s かかった。dmactive を残すとすぐ戻った
  （2026-09-26、[probe-cdc-and-persistence](probe-cdc-and-persistence.ja.md) §7.5.1）。
- dmactive を下ろすと DATA0 が 0 に戻るのを確かめたのは CH32X035 だけ（ほかの系統は未確認）。
- WCH-LinkE は DetachChip で dmactive を下ろす（`W dmcontrol 0x40000001` → `R dmstatus` → `W dmcontrol 0x40000000`、
  L103 / V203 / V003 / X035 で同じ。wch-protocols link-to-target §5）が、次の AttachChip が ESIG を読んで DATA0 に 0 でない語を残す。
  bit 7 が 0 の語（V203 の `0xe339e339`）なら target は規則 1 で答えの検査に通らない語と読んですぐ出し直し、bit 7 が 1 の語
  （V006 / X035 の `0xffffffff`）なら規則 0 で出し直す（規則 0 の無い target はここで止まっていた）。
- DATA0 に何も書かない attach（OEP の probe）の後では、0 が残って待たされた。

## 9. hart を止める debugger

halt 中に DATA0 / DATA1 を使って書き戻さないと target が待たされることは [link-measurements](link-measurements.ja.md) §3 にある。
OEP の probe は DATA0 / DATA1 を使う op の答えの前に書き戻す（[線とデバッグ](oep-if-debug.ja.md) §4.2）。移す前の規範の文は
「riscv-dm の halt / resume でこれを行う」と書いていたが、§4.2 は op ごとに書き戻すと定めているので、規範の文はそれに合わせた。
