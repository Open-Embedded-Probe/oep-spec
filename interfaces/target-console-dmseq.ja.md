# OEP コンソールの mechanism 2: dmseq

[English](target-console-dmseq.md)

状態: **規範**（v1、凍結の前: v1 の凍結までは、規則も数もまだ変わりうる）。凍結までは、この日本語の文（.ja.md）が作業の文である。英語版は凍結のときにこれから作り直し、そのときから英語版が正になる。凍結の前は、revision 1 だけでは形が一つに決まらない: 実装は、自分が実装する仕様のタグを示す（[版と安定性](../docs/versioning.ja.md) §6）。この文書は `oep.target.console` の mechanism 2（dmseq、[コンソール](oep-if-console.ja.md) §3）の framing を規定する。

## 目的

dmseq は両方向に 1 bit の通し番号と CRC-8 を持たせる。
これにより host は、もう一度読んだフレーム（**重複**）と、同じ内容の新しいフレームを区別でき、二重に渡すことも欠落もしない。

名前: framing 名は **dmseq**（`registry/oep-v1.toml`: `oep.target.console` の `[interface.enum.mechanism]`、`dmseq = 2`）。

## 搬送と所有権

debug module の DATA0 と DATA1（[コンソール](oep-if-console.ja.md) §3）。所有権は厳密に交代する。

- target が DATA0 / DATA1 を書くのは次のときだけである:
  (a) begin() のとき（「target のフレーム」）;
  (b) DATA0 の bit 7 が 0 のとき、フレームを出すため;
  (c) 答えを待っているフレームを出し直すため: target の規則 0（bit 7 が 1 だが自分が出した語でない）、target の規則 1、タイムアウトのとき、
  フレームを出したままにしている間（「タイムアウト」）、DATA0 が 0 と読める間（「0 の語は答えではない」、target の規則）。
- host は bit 7 が 1 のとき（target のフレームがある）だけ書く。
- (c) で bit 7 が 1 の、target 自身のフレームでない語の上に書くことを除き、どちらも相手が書いた語を上書きしない。

## target のフレーム（target → host）

    DATA0 byte0  status   bit7 T=1  bit6 TO  bit5 S  bit4 A  bit3 SYN  bits2..0 N
    DATA0 byte1..3        payload 0..2
    DATA1 byte0..3        payload 3..6
    CRC-8 は payload の直後（byte 1+N）。N = 0..6。

- N <= 2 のフレームは DATA0 に収まり、target は DATA1 を書かず、host は読まない。
- target は DATA1 を（使うときは）DATA0 より先に書く。
- **S**: このフレームの通し番号。ack されると反転する。
- **A**: target が最後に受け取った host payload の番号（H）。
- **SYN**: begin() から最初の有効な答えを受けるまでの全フレームで 1。
- **TO**: target が答えを待つのをやめたフレーム（「タイムアウト」参照）。そのフレーム限りで、
  target が次に出すフレームでは 0 に戻る。
- **N = 0** は空フレーム（host に答えを促す）。空でもフレームには番号があり、答えを受ける。
- **byte の順**: DATA0 の byte k（k = 0〜3）はレジスタの bit 8k〜8k+7（byte0 が最下位の byte）。DATA1 の byte k は DATA1 の bit 8k〜8k+7
  で、payload の byte 3+k を運ぶ。例: S = 0、A = 1 の空の SYN フレームは byte0 が 0x98、CRC が 0x32 なので DATA0 = 0x00003298。
  K = 0、H = 0、M = 0 の host の答えは DATA0 = 0x0000F300。
- **begin() のとき** target は SYN を立て、DATA0 に 0 を書いてよい。S と A はどの値から始めてもよい。host は SYN で再同期する（host の規則 3）。

## host の答え（host → target）

    DATA0 byte0  status   bit7 0  bit6 0  bit5 K  bit4 H  bit3 0  bits2..0 M
    DATA0 byte1..3        payload、その直後（byte 1+M）に CRC-8。M = 0..2。

- **K**: 答えるフレームの S。
- **H**: この payload の番号。M = 0 のときは意味を持たない。

## CRC-8

poly 0x07、init 0xFF、反転なし、最終 XOR なし。byte0 と payload（1+N または 1+M byte）にかけ、その直後に置く。

計算方法は問わない（同じ値が出れば適合）。
検査値: ASCII の 9 byte "123456789" → 0xFB。1 byte の 0x00 → 0xF3。

## host の状態

- `synced`: この session でフレームを 1 つ以上受理した。
- `last_s`: 最後に受理したフレームの S。
- `last_syn`: 最後に受理したフレームが SYN 付きだった。
- `h`、`pending`: まだ届いたと分かっていない host payload の番号と中身。

session は未同期で始まる。**target を reset した host は新しい session を始める**（上の状態を全部捨てる）。
OEP の probe については [線とデバッグ](oep-if-debug.ja.md) §4.6。

## host の規則（bit 7 が 1 の word を読んだとき）

1 回の poll の順序: DATA0 を読む。bit 7 が 1 で N >= 3 なら DATA1 を読む。検査する。
答えを書くのはその後（答えた時点で target は次のフレームを出して DATA1 を上書きしてよい）。

1. **無効**なら答えず、次の poll で読み直す。無効とは N > 6、または CRC 不一致。CRC の位置を求める前に N を見る
   （N = 7 では byte 1+N が存在せず、attach が残すことのある全 1 の word `0xffffffff` はちょうど N = 7 になる）。
   無効が 3 回続き、かつ synced なら、K = `last_s`、M = 0 で答える。
   （その word は host 自身の答えが bit 7 = 1 に化けたものかもしれない。K = `last_s` は target が何を出していても安全: その S の
   フレームは受理済みであり、新しいフレームは S が違うので K 検査で落ち、target が出し直す。）
   host は、bit 7 = 1 の無効な word（`0xffffffff` を含む）を読んだ poll が続いた数を数える。有効なフレームを読んだとき、
   この規則で答えた後、session が始まったときに、数を 0 に戻す。bit 7 = 0 の word を読んだ poll は数を変えない。規則 1 の答えは
   host が synced の間だけ送る。synced でない間は数を 3 で止め（一周させない）、答えない。次の有効なフレームで host は同期し、
   数を 0 に戻す。
2. **重複**: synced かつ S == `last_s` かつ（SYN が 0、または `last_syn`）なら payload を捨て、5 のとおり答える。
   （出し直された SYN フレームも、ほかと同じく重複である。）
3. **再同期**: 未同期、または SYN が 1 で 2 の重複でないなら、`last_s` := not S（このフレームを新しいものとして数えるため）、
   `h` := not A、`pending` を捨て、`synced` := true。
   **3 のあとはそのまま 4 へ進む**（別の分岐ではない）。host が SYN フレームを受理した直後に target が再起動し、
   たまたま同じ S を使った場合、その 1 フレームは落ちる。1 bit では区別できないので、target を reset した host は新しい session を始める。
4. **受理**: S != `last_s` なら payload を渡し、`last_s` := S、`last_syn` := SYN。
5. `pending` があり A == `h` なら届いている: `h` := not `h`、`pending` を空にする。
   `pending` が空なら、送るものの次の最大 2 byte を入れる（OEP の probe では送りの列の先頭から、[コンソール](oep-if-console.ja.md) §2）。K = S、H = `h`、M = len(`pending`)、CRC で答える。

## target の規則（フレームを出している間に DATA0 を読んだとき）

0. **bit 7 が 1 で、自分が出した語と違う**（attach が残した `0xffffffff` など）なら、答えを待たずに**すぐ同じフレームを
   出し直す**。タイムアウトの前でも後でも同じ。bit 7 が 1 の語は host の番なので、放っておくと、未同期の host は
   無効な word として答えず、target は「まだ自分のフレーム」と読んで待ち、
   双方が止まる。

bit 7 が 0 を読んだとき:

**0 の語は答えではない.** DATA0 が 0 と読める間、target は答えを待ち続け（待ち時間は進み続ける）、短い待ちごとに 1 回フレームを
出し直す。0 を規則 1 では扱わない。bit 7 が 0 のほかの語については:

1. 無効（M > 2、または CRC 不一致。CRC の位置を求める前に M を見る）、または K != S なら、同じフレームを出し直す
   （host は重複として扱う）。
2. それ以外は ack: S を反転、以後 SYN は 0。M > 0 で H が最後に受け取った H と違い、置き場所があれば
   payload を取り、最後に受け取った H := H。置き場所がなければ取らない（host が送り直す）。
3. 送るものがあれば次のフレームを出す。空フレームは**暇なときだけ**出す（送るものがなく、前の答えのあとアプリケーションが
   書いていない）。書き続けている target は、データフレームへの答えに乗って入力を受け取れる。書込みの合間に空
   フレームを挟むと 1 往復余計にかかる。空フレームを一度も出さない target は、書いたときしか入力を受け取れない（入力は
   答えにしか乗らないため）。

## タイムアウト

**待ち時間.** target は答えを有限時間だけ待つ。begin() 以後（または直前のタイムアウト以後）host が一度も答えていない間は**短い待ち**、
一度答えた後は**長い待ち**。短い待ちは実時間で**少なくとも 20 ms**、長い待ちは**少なくとも 1 s** 続く。
target は、割込み禁止中でも終わるやり方でそれを測る。「短い待ちごと」（フレームを出したままにする間と、DATA0 が 0 と読める間）も
同じ測り方を使う。

**host への含意.** 同期した host が 1 秒に 1 回以上 poll すれば出力は失われない。後から attach した host は、
タイムアウトしたフレームと、自分が答えた後に書かれた分を受け取る。その間の書込みは捨てられている。

**タイムアウトで起きること.** target は出していたフレームを **TO を立てて**出し直し（S と payload は同じ、CRC は計算し
直す）、**出したままにする**。以後の書込みは、有効な答えが来るまで待たずに捨てる。後から attach した host が
そのフレームに答えると、通常どおり渡り、target は元に戻る。

**出したままにする**とは、待っている間 **短い待ちごとにそのフレームを出し直し続ける**ことである。答えを待っている間に DATA0 が
自分の語でなくなったとき（bit 7 が 1 の別の語）は、タイムアウトを待たずにすぐ出し直す
（target の規則 0）。host はこれのために何かを書く必要はない。

- host（debugger）: **切り離すときにデバッグモジュールを reset しない**（DMCONTROL.dmactive を下ろさない）。下ろすと DATA0 と DATA1 が 0 に戻ることがあり、
  そのとき target が出していたフレームは消える。target は短い待ちのうちにそれを出し直す（「0 の語は答えではない」）。
- host（debugger、hart を止める側）: 止めている間に abstract command で DATA0 / DATA1 を使ったら、走らせる前に、止めたときの DATA1、
  DATA0 を書き戻す。書き戻さないと、target の出していたフレーム（または host の答え）が消え、
  target は自分の規則でそれを出し直さなければならない。OEP の probe は、DATA0 / DATA1 を使う op の答えの前にそれらを書き戻す
  （[線とデバッグ](oep-if-debug.ja.md) §4 の表）。
- host: TO フレームは普通のフレームとして扱う（規則 2 と 4 が適用される）。再同期の理由にはしない。
