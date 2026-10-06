# 線の落ちと debug の操作の規則の提案（2026-10-06）

Status: **proposal**（非規範）。ch32rv が読んで合意した（条件つき、下）。利用者の判断を待つ。構成の見直し（[v1-structure-proposal-2026-10-06](v1-structure-proposal-2026-10-06.ja.md)）の後に扱う。

## 背景

線によっては、target の hart の状態が変わった後、0.7〜2 ms のあいだ線が落ちる。落ちている間、書き込みは消え、読み出しは前に読んだ値か全部 1 を返す（エラーにならない）。reference probe は次の 3 つを直した（oep-probe-arduino ec57b23、f594f04、2135bb9、bd19b00）。仕様はどれも定めていない。

- 線の立て直しの中で wake を送り、それが target を起動し直していた（止めた hart が止まり直す）。
- write_block が、確かめに失敗した後に書き込みをやり直し、同じ語を 2 回書いて success と答えていた（2 回書くと順序が壊れるレジスタがある）。
- 生の dmi の手順は、落ちを見分けられず、古い値を正しい値として返していた。

## P1（debug §2）: 接続中の立て直しは target を変えない

- connection がある間、probe が要求の中やコンソールの読みの中で行う線の再試行と同期の取り直しは、target の状態（hart の実行状態、haltreq、DM のレジスタ）を変えない。
- wake / 設定の手順が target をリセットしうる wire では、connection の上でその手順を送るのは、host が求めた attach、reset の TLV、reset の op の中だけ。
- 立て直せなければ、probe は status line で答える。

ch32rv の条件（コンソールの読み手が、落ちを読みから知るため）:

- probe が P1 のもとで connection をあきらめたら、その connection のストリームを mark（connection_closed、または「線を失った」の detail）を付けて閉じる。読み手は、ほかの op を問い合わせずに、読みの中でそれを知る。
- スロットの connection では、スロットの retry が attach し直した後、同じ場所のコンソールは同じストリームの番号で開き直す（場所ごとの規則）。そのとき reset または再接続の mark を付ける。
- その connection への dmi / block の要求が何を受けるかを定める（line を返して connection を閉じるのか、次の要求が no_connection になるのか）。

## P2（debug §4.5）: write_block は各語を多くても 1 回書く

- probe は、target に届いたかもしれない書き込みをやり直さない。
- success は、全語を 1 回ずつ書いたと確かめたときだけ。
- 失敗のときの done は、先頭から順に書けたと確かめた語の数。

## P3（debug §4.5）: read_block は読み直すことがある

- read_block は、線を立て直した後に同じ語を読み直すことがある。
- 読むと状態が変わるレジスタは、host が dmi で読む。

## P4（debug §4.1）: dmi は要求ごとに線を確かめる

- probe は、dmi の要求ごとに、手順の前と後で線が保たれていることを確かめる（DMSTATUS と DMCONTROL）。
- 保たれていなければ、古い値を返さずに status line で答える。

ch32rv の条件:

- 確かめは要求ごと（手順ごとではない）。手順の並びは 1 つの要求のまま。
- line の答えは、確かめに失敗する前に終えた手順の数を示す。失敗した要求の中の書き込みの手順は「行われたかもしれない」として扱う。
