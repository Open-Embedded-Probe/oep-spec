# OEP コンソールの方式 dmseq

状態: **規範**（v1）。凍結状態と言語・互換性の方針は[版と安定性](../docs/versioning.ja.md)を参照。この文書は `oep.target.console` の方式 `dmseq`（[コンソール](oep-if-console.ja.md) §3）の framing を規定する。

dmseqは両方向に1bitの通し番号とCRC-8を持たせ、同期中の再読フレームと新しいフレームを区別する。
この文書のtarget側の規則（20ms/1sの待ちを含む）は、dmseqを採用するtarget firmwareへの要件である。
全OEP probe/hostへtarget firmwareや常時pollを要求するものではない。targetの再起動や同期状態喪失の制限は下記のとおり。

## 搬送と所有権

debug moduleのDATA0とDATA1を使う（[コンソール](oep-if-console.ja.md) §3）。

- targetはbit7が0のときに新しいフレームを書き、答え待ちの間は同じフレームの出し直しだけを行う。
  bit7が1でも自分の語と違う場合は、無効な語との待ち合いを防ぐため、すぐ出し直す（targetの規則0）。
- begin()は同期の初期化であり、上の交代にかかわらずDATA0を0にしてよい。その後SYN付きのフレームを出す。
- hostはbit7が1の有効なtargetフレームにだけ答える。DATA1を読んでからDATA0を書き、相手の新しいDATA1を先に上書きさせない。

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

poly 0x07、init 0xFF、反転なし、最終 XOR なし。byte0からpayloadの末尾までの合計1+N byte（target→host）または1+M byte（host→target）にかけ、payloadの直後にCRCを置く。

計算方法は問わない（同じ値が出れば適合）。
検査値: ASCII の 9 byte "123456789" → 0xFB。1 byte の 0x00 → 0xF3。

## host の状態

- `synced`: この同期状態でフレームを1つ以上受理した。
- `last_s`: 最後に受理したフレームの S。
- `last_syn`: 最後に受理したフレームが SYN 付きだった。
- `h`、`pending`: まだ届いたと分かっていない host payload の番号と中身。

同期状態は未同期で始まる。**targetをresetしたhostは同期状態を初期化する**（上の状態を全部捨てる）。
これはOEP coreのsession_id/ロックとは別の状態である。
OEP の probe については [線とデバッグ](oep-if-debug.ja.md) §4.6。

## host の規則（bit 7 が 1 の word を読んだとき）

1回のpollの順序: DATA0を読み、bit7とNを確かめる。bit7が1で3 ≤ N ≤ 6ならDATA1を読み、CRCを検査する。
答えを書くのはその後（答えた時点で target は次のフレームを出して DATA1 を上書きしてよい）。

1. **無効**なら答えず、次の poll で読み直す。無効とは N > 6、または CRC 不一致。CRC の位置を求める前に N を見る
   （N = 7 では byte 1+N が存在せず、attach が残すことのある全 1 の word `0xffffffff` はちょうど N = 7 になる）。
   target は規則 0 でフレームを出し直す。
2. **重複**: synced かつ S == `last_s` かつ（SYN が 0、または `last_syn`）なら payload を捨て、5 のとおり答える。
   （出し直された SYN フレームも、ほかと同じく重複である。）
3. **再同期**: 未同期、または SYN が 1 で 2 の重複でないなら、`last_s` := not S（このフレームを新しいものとして数えるため）、
   `h` := not A、`pending` を捨て、`synced` := true。
   **3 のあとはそのまま 4 へ進む**（別の分岐ではない）。host が SYN フレームを受理した直後に target が再起動し、
   たまたま同じSを使った場合、その1フレームは落ちる。1bitでは区別できないため、targetをresetしたhostは同期状態を初期化する。
4. **受理**: S != `last_s` なら payload を渡し、`last_s` := S、`last_syn` := SYN。
5. `pending` があり A == `h` なら届いている: `h` := not `h`、`pending` を空にする。
   `pending` が空なら、送るものの次の最大 2 byte を入れる（OEP の probe では送りの列の先頭から、[コンソール](oep-if-console.ja.md) §2）。K = S、H = `h`、M = len(`pending`)、CRC で答える。

OEP probe がこれらの観測をストリームの mark として通知する条件は、[コンソール §2](oep-if-console.ja.md#2-ストリームの規則)で定める。
TO付きも普通のフレームとして重複/受理を判定し、TOを再同期の理由にしない。

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
   bit3とbit6は受信側では無視する。ただしCRCの計算は、そのbitも含め受信したbyte0全体にかける。
2. それ以外は ack: S を反転、以後 SYN は 0。M > 0 で H が最後に受け取った H と違い、置き場所があれば
   payload を取り、最後に受け取った H := H。置き場所がなければ取らない（host が送り直す）。
3. 送るものがあれば次のフレームを出す。送るものが無ければ空フレームを出してよい（入力は答えにしか乗らないので、空フレームを出さない target は、
   書いたときしか入力を受け取れない）。

## タイムアウト

**待ち時間.** target は答えを有限時間だけ待つ。begin() 以後（または直前のタイムアウト以後）host が一度も答えていない間は**短い待ち**、
一度答えた後は**長い待ち**。短い待ちは実時間で**少なくとも 20 ms**、長い待ちは**少なくとも 1 s** 続く。
target は、割込み禁止中でも終わるやり方でそれを測る。「短い待ちごと」（フレームを出したままにする間と、DATA0 が 0 と読める間）も
同じ測り方を使う。

**pollの間隔.** 有効なフレームに答える間隔がtargetの長い待ちより短い間は、タイムアウトによる出力の損失は起きない。
ちょうど1sの境界でのpoll、CRC不一致、長いdebug操作中の非pollに無損失を保証しない。後からattachしたhostは、
タイムアウトしたフレームと、自分が答えた後に書かれた分を受け取る。その間の書込みは捨てられている。

**タイムアウトで起きること.** target は出していたフレームを **TO を立てて**出し直し（S と payload は同じ、CRC は計算し
直す）、**出したままにする**。以後の書込みは、有効な答えが来るまで待たずに捨てる。後から attach した host が
そのフレームに答えると、通常どおり渡り、target は元に戻る。

**出したままにする**とは、待っている間 **短い待ちごとにそのフレームを出し直し続ける**ことである。答えを待っている間に DATA0 が
自分の語でなくなったとき（bit 7 が 1 の別の語）は、タイムアウトを待たずにすぐ出し直す
（target の規則 0）。host はこれのために何かを書く必要はない。

- DATA0 / DATA1 を使う抽象コマンドの後の書き戻しは [線とデバッグ](oep-if-debug.ja.md) §4。
