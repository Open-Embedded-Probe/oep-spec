# Open Embedded Probe — target の発見と接続のユースケース

状態: **検討中の要求入力**（2026-09-24）。probe は何がつながっているかを知らない、という前提から、host が target を
見つけ、識別し、接続し、使い、手放すまでの作業の流れを具体化する。wire format は決めない。
[能力の宣言モデル](capability-declaration-model.ja.md) の命名（静的な名前と、接続ごとに現れる名前）の入力になる。

## 前提

- **probe は target を知らない。** 起動時に分かるのは probe 自身と、どのピンでどの線（RVSWD、SWIO、SWD、JTAG）を
  出せるか、治具側の I/O だけである。
- **target の知識は host が持つ。** 返ってきた ID から「CH32X035 だ」と判断するのも、flash の形や制御方法を知って
  いるのも host（ch32rv の DB など）である。
- **probe は自発的に target に触らない。** スキャン、接続、識別、切断はすべて host の指示で行う。probe が勝手に
  attach すると、host が知らないうちに target の状態が変わる（次節の副作用）。

## attach と detach の副作用（実測）

接続の寿命の決め方は、attach / detach に副作用があることで決まる。このベンチで実際に起きたこと:

| 事象 | 内容 |
|---|---|
| attach が target を書き換える | WCH-LinkE は attach のたびに、動いている target の RCC_CFGR0 と FLASH ACTLR を書き換えた（CH32V307 / V203 / L103）。attach を繰り返すほど target が乱れる |
| 接続中は target の動きが変わる | debug module が有効な間は低消費電力のスリープが効かないことがあり、停止中は DBGMCU の設定次第でタイマ等が止まる。dmseq のコンソールは接続中しか使えない |
| 放置すると線が落ちる | CH32L103 の RVSWD は 1 ms 程度の無通信で落ちる。probe が次の転送の前に立て直している |
| タイムアウトが自分を切る | 「一定時間要求がなければセッションを捨てる」処理が、長い verify の最中に自分のセッションを捨てた（idle を要求の完了から数えるよう直した） |
| host を見失ったときの後始末が副作用になる | 現行の probe は host を見失うと target をリセットする |

## 接続の寿命（推奨）

1. **attach / detach は host が明示的に指示する。** host のセッションの間は、操作をまたいで接続を持ち越す
   （attach の回数を減らす）。
2. **host が接続している間は、タイムアウトで detach しない。** 線の維持（RVSWD の立て直しなど）は probe の中で行い、
   host に見せない。
3. **host のセッションが終わる・host を見失ったときだけ、probe が安全な状態に戻す。** 止めていたなら再開して離れ、
   ピンは入力に戻す。**リセットはしない**（現行の実装は直す対象）。
4. **host のセッションをまたいで接続は持ち越さない。** 次回は host が記録から attach し直す（スキャンは省略）。
5. **attach の副作用は describe で宣言する。** 停止するか、リセットするか、target のレジスタを書くか、接続中に
   target の動きが変わるか。host はそれを見て、attach したまま進めるか、用が済んだら detach するかを決める。
6. **2 回目以降の attach は、最初に ID を読んで記録と照合する。** 機材は入れ替わる（このベンチでは日常的に）。
   違えばはっきり失敗させ、host がスキャンからやり直せるようにする。

## ユースケース

### UC-T1: 初めてのベンチで、何がつながっているかを調べる

1. host がつながっている probe を列挙する（USB など。OEP の外）。
2. 各 probe について list で静的な能力を読む（`oep.probe.*`、`oep.wire.*`、`oep.fixture.*`）。
3. 各線（`oep.wire.<線>`）について、host がピンを指定してスキャンを指示する。ピン配線が分からなければ、候補の
   ピン組を順に試す（RP2350 から CH32L103 の RVSWD の対を 420 通り探したように）。
4. probe は応答を生で返す（RISC-V の DMSTATUS / hartinfo、ARM の DPIDR / AP、JTAG の IDCODE の並び）。
5. host が ID を DB と照合し、target を特定する。
6. host が attach を指示し、target の識別レジスタ（CH32 なら ESIG の chip ID と UID）を読んで確定する。
7. host が「probe の個体、線、ピン、target の ID」を記録する。
8. host が detach を指示する。

### UC-T2: 2 回目以降に、書き込んで走らせる

1. host が記録を読み、スキャンを省略する。
2. host が attach を指示し、最初に ID を照合する（違えば UC-T5）。
3. 書き込み、verify、リセットして走らせる。
4. 用途に応じて detach するか、接続を持ち越して UC-T3 に進む。

### UC-T3: 走らせながらコンソールを読む（テストの実行）

1. 接続を持ち越したまま、コンソール（CH32 なら debug module のデータレジスタ）を読み書きする。
2. テストが終わったら detach する。
3. target のリセットで線が切れた場合は UC-T6。

### UC-T4: host が落ちた・ケーブルが抜けた

1. probe が host を見失う（transport の切断、または心拍の途絶）。
2. probe が target を安全な状態に戻す（止めていたなら再開、ピンは入力に）。リセットはしない。
3. 次に host がつながったら、UC-T2 と同じく attach からやり直す。

### UC-T5: 機材が入れ替わっていた

1. UC-T2 の ID の照合で、記録と違う target が見える（または何も見えない）。
2. host は操作を中止し、その線について UC-T1 のスキャンからやり直す。

### UC-T6: target のリセットや電源断で接続が切れた

1. target のリセット（ndmreset、NRST、電源の入れ直し）で、debug module の状態や線の同期が失われる。
2. probe は接続が失われたことを host に伝える（次の操作の失敗、または通知）。
3. host が方針に従って attach し直すか、止める。probe が黙って attach し直すことはしない。

### UC-T7: debug の影響なしに target を観測する

1. 書き込みのあと detach し、debug module の影響（スリープ、停止中のタイマ）を外す。
2. 治具側の I/O（`oep.fixture.*`）だけで target の振る舞いを観測する（消費電流、低消費電力モード、ピンの動き）。

## 未決

1. **スキャンが返すものの形**: 線ごとに生の ID の形が違う（RISC-V / ARM / JTAG）。共通の形にするか、線ごとにするか。
2. **ピンの探索**: 総当たりを probe の中でやるか、host が 1 組ずつ指示するか（速さと、probe の実装の重さ）。
3. **attach の引数**: 停止してから attach するか、止めずに attach するか、リセットしながら attach するか
   （connect-under-reset）。どこまでを標準にするか。
4. **attach の副作用の宣言の語彙**: 停止、リセット、レジスタの書き込み、接続中の振る舞いの変化を、どう表すか。
5. **接続の喪失の伝え方**: 次の操作の失敗で分かればよいか、通知（notification）を使うか。
6. **host のセッションの終わりの判定**: transport の切断だけでよいか、心拍（heartbeat）を必須にするか。
7. **flash の書き込み手順の受け渡し**: host が flash の形と制御方法を与えるか、target の RAM で動く小さな書き込み
   プログラムを渡すか（probe-rs / CMSIS の flash algorithm の考え方）。
8. **治具専用の probe**: target が決まっている probe が、最初から接続済みの状態を宣言してよいか。
