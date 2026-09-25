# target.console framing 2: dmseq

状態: `target.console`（owner 0x0000, id 0x0013）の framing 2 として規定する。
根拠と実測は [experiments/dm-console-seq](../experiments/dm-console-seq/SPEC-draft.md)。
ch32rv 側のレビュー 2 回を経て合意済み（2026-09-24）。

## なぜ

framing 1（ArduinoCore-CH32 の `SerialDMDATA`、minichlink の framing）には通し番号がない。
host の答えの DMI 書込みが黙って落ちると target の word がもう一度読まれて**重複**し、
それを読み戻しで救おうとすると、同じ内容の次のフレームと区別できずに**欠落**する。
dmseq は両方向に 1 bit の通し番号と CRC-8 を持たせ、この二つを区別できるようにする。

CRC は必須である。WCH の probe では、attach が DATA0 に `0xffffffff` を、CH32V30x の
flash が `0xe339e339`（bit 7 が 0）を残すことが実測で分かっており、CRC がないと後者を
target が有効な答えとして受け取る。

名前: framing 名 **dmseq**。ch32rv では `monitor --source dmseq`、ArduinoCore-CH32 の
target ライブラリは `SerialDMSeq`。

## 搬送と所有権

debug module の DATA0/DATA1（framing 0/1 と同じ）。所有権は厳密に交代する。

- target は DATA0 の bit 7 が 0 のとき（答えがある、またはまだ何もない）だけ書く。
- host は bit 7 が 1 のとき（target のフレームがある）だけ書く。
- どちらも相手の word を上書きしない。framing 1 で要った「空フレームを 1 poll 分寝かせる」
  回避策はこれで不要になる。

## target のフレーム（target → host）

    DATA0 byte0  status   bit7 T=1  bit6 TO  bit5 S  bit4 A  bit3 SYN  bits2..0 N
    DATA0 byte1..3        payload 0..2
    DATA1 byte0..3        payload 3..6
    CRC-8 は payload の直後（byte 1+N）。N = 0..6。

- N <= 2 のフレームは DATA0 に収まり、target は DATA1 を書かず、host は読まない。
  （WCH-LinkE では DMI 1 回が USB 1 往復、約 0.4 ms かかるので、短いフレームの費用の 1/3 が浮く。）
- target は DATA1 を（使うときは）DATA0 より先に書く。
- **S**: このフレームの通し番号。ack されると反転する。
- **A**: target が最後に受け取った host payload の番号（H）。
- **SYN**: begin() から最初の有効な答えを受けるまでの全フレームで 1。
- **TO**: target が答えを待つのをやめたフレーム（「タイムアウト」参照）。そのフレーム限りで、
  次に出すフレームでは 0 に戻る。
- **N = 0** は空フレーム（host に答えを促す）。空でもフレームには番号があり、答えを受ける。

## host の答え（host → target）

    DATA0 byte0  status   bit7 0  bit6 0  bit5 K  bit4 H  bit3 0  bits2..0 M
    DATA0 byte1..3        payload、その直後（byte 1+M）に CRC-8。M = 0..2。

- **K**: 答えるフレームの S。
- **H**: この payload の番号。M = 0 のときは意味を持たない。

## CRC-8

poly 0x07、init 0xFF、反転なし、最終 XOR なし。byte0 と payload（1+N または 1+M byte）に
かけ、その直後に置く。init 0xFF により全 0 の word は常に無効になるので、値を保持しない
レジスタ（debugger 未接続の V4 は 0 を返す）や host が mailbox を 0 で消した状態を、フレーム
や答えと取り違えない。CRC は DATA1 の byte も覆うので、target の書き直しをまたいで読んだ
DATA0/DATA1 の組は通らない。

計算方法は問わない（同じ値が出れば適合）。ArduinoCore-CH32 は 16 要素の表で 4 bit ずつ計算する。

## host の状態

- `synced`: この session でフレームを 1 つ以上受理した。
- `last_s`: 最後に受理したフレームの S。
- `last_syn`: 最後に受理したフレームが SYN 付きだった。
- `h`、`pending`: まだ届いたと分かっていない host payload の番号と中身。

session は未同期で始まる。**target を reset した host は新しい session を始める**（上の
状態を全部捨てる）。ch32rv の `run`/`monitor` と OEP probe の reset はそうする。

## host の規則（bit 7 が 1 の word を読んだとき）

1 回の poll の順序: DATA0 を読む。bit 7 が 1 で N >= 3 なら DATA1 を読む。検査する。
答えを書くのはその後（答えた時点で target は次のフレームを出して DATA1 を上書きしてよい）。

1. **無効**なら答えず、次の poll で読み直す。無効とは N > 6、または CRC 不一致。CRC の位置を
   求める前に N を見る（N = 7 では byte 1+N が存在せず、attach が残す `0xffffffff` はちょうど
   N = 7 になる）。無効が 3 回続き、かつ synced なら、K = `last_s`、M = 0 で答える。
   （その word は host 自身の答えが bit 7 = 1 に化けたものかもしれない。K = `last_s` は
   target が何を出していても安全: その S のフレームは受理済みであり、新しいフレームは
   S が違うので K 検査で落ち、target が出し直す。）
2. **重複**: synced かつ S == `last_s` かつ（SYN が 0、または `last_syn`）なら payload を捨て、
   5 のとおり答える。（出し直された SYN フレームも、ほかと同じく重複である。）
3. **再同期**: 未同期、または SYN が 1 で 2 の重複でないなら、`last_s` := not S（このフレームを
   新しいものとして数えるため）、`h` := not A、`pending` を捨て、`synced` := true。
   **3 のあとはそのまま 4 へ進む**（別の分岐ではない）。host が SYN フレームを受理した直後に
   target が再起動し、たまたま同じ S を使った場合、その 1 フレームは落ちる。1 bit では
   区別できないので、target を reset した host は新しい session を始める。
4. **受理**: S != `last_s` なら payload を渡し、`last_s` := S、`last_syn` := SYN。
5. `pending` があり A == `h` なら届いている: `h` := not `h`、`pending` を空にする。
   `pending` が空なら次の最大 2 byte を入れる。K = S、H = `h`、M = len(`pending`)、CRC で答える。

## target の規則（フレームを出している間に bit 7 が 0 を読んだとき）

1. 無効（M > 2、または CRC 不一致。CRC の位置を求める前に M を見る）、または K != S なら、
   同じフレームを出し直す（host は重複として扱う）。
2. それ以外は ack: S を反転、以後 SYN は 0。M > 0 で H が最後に受け取った H と違い、
   置き場所があれば payload を取り、最後に受け取った H := H。置き場所がなければ取らない
   （host が送り直す）。
3. 送るものがあれば次のフレームを出す。空フレームは**暇なときだけ**出す（送るものがなく、
   前の答えのあと sketch が書いていない）。書き続けている target は、データフレームへの
   答えに乗って入力を受け取れる。印字の合間に空フレームを挟むと 1 往復余計にかかる
   （LinkE では出力の速さが半分になる）。空フレームを一度も出さない target は、印字した
   ときしか入力を受け取れない（入力は答えにしか乗らないため）。

## タイムアウト

**待ち時間.** target は答えを有限時間だけ待つ。begin() 以後（または直前のタイムアウト以後）
host が一度も答えていない間は **20 ms**、一度答えた後は **1 s**。割込み禁止中でも終わるよう、
時計ではなくレジスタを読んだ回数で数える。

**host への含意.** 同期した host が 1 秒に 1 回以上 poll すれば出力は失われない。後から
attach した host は、タイムアウトしたフレームと、自分が答えた後に書かれた分を受け取る。
その間の書込みは捨てられている。

**タイムアウトで起きること.** target は出していたフレームを **TO を立てて**出し直し（S と
payload は同じ、CRC は計算し直す）、**出したままにする**。以後の書込みは、有効な答えが来るまで
待たずに捨てる。後から attach した host がそのフレームに答えると、通常どおり渡り、target は
元に戻る。

**出したままにする**とは、待っている間 **短い方の待ち時間（20 ms）ごとにそのフレームを出し直し
続ける**ことである。probe の attach は DATA0 を書き換えることがあり、bit 7 が 1 の値
（`0xffffffff` など）が残ると、target は「まだ自分のフレーム」と読んで待ち、未同期の host は
無効な word として答えないので、双方が止まる。target が自分から出し直していれば、host は
次の poll でそのフレームを読める。host がこれのために何かを書く必要はない。

- host（debugger）: **切り離すときにデバッグモジュールを reset しない**（DMCONTROL.dmactive を下ろさない）。下ろすと DATA0
  が 0 に戻り、target が出していたフレームが消える。target は 0 を沈黙と読んでタイムアウトまで待つ。その待ちは target が
  DATA0 を読んだ回数で数えるので、debugger が DMI を速く読んでいると延びる。OEP の probe では、断った自動の attach の後に
  コンソールが戻るまで 1〜10 s かかった。dmactive を残すとすぐ戻った（2026-09-26、oep-spec probe-cdc-and-persistence
  §7.5.1）。DATA0 が消えるのを確かめたのは CH32X035 だけ。WCH-LinkE の attach の後の L103 / V203 では、DATA0 に最後に
  読んだ ESIG の語が残っていた（ch32rv wch-link.ja.md §7a）。LinkE は AttachChip の最後に dmactive を下ろすと線上で見えて
  いる（wch-protocols link-to-target §5）ので、系統によってはデバッグモジュールの reset で DATA0 が消えないのかもしれない
  （未確認）。
- host: TO フレームは普通のフレームとして扱う（規則 2/4 が適用される）。再同期の理由にはしない。
  host は「誰も答えていない間の出力が捨てられた」と利用者に伝えてよい。
- host: 未同期のまま、フレームでない word（CRC 不一致、または bit 7 が 0）だけを長く読み続けた
  場合、その target には dmseq のコンソールがない。host は黙っているより、そう報告してよい。
