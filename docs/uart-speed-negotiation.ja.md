# UART の速さの交渉（案）

状態: **案（未決）**（2026-10-01）。V003 ジグ（classic ESP32 + CP2102、115200）で、fixture UART の連続受信が約 2.9 KB/s で
頭打ちになり（115200 の UART が流す 11.5 KB/s に届かない）、1 KB の答えが線の上で 1 byte 落ちるとフレームごと無駄になる件
（bench、2026-10-01）から。**921600 に単純に上げるのは不可**: 921600 を安定して通せない変換チップやボードがあり、Arduino IDE の
シリアルモニターなど、OEP を知らない相手も同じ口を 115200 で開く。

## 1. 方針

- **口の既定は 115200 のまま**。どの probe も起動時と、下の「戻る」契機のたびに 115200 にする。OEP を知らない相手（IDE の
  モニター、ターミナル）はいつも 115200 で読める。
- **上げるのはセッションの間だけ、交渉してから**。host が 115200 で confirm と describe を済ませ、probe が宣言した速さの中から
  選んで頼む。probe は応答を古い速さで送り終えてから切り替え、host も切り替えて、新しい速さで確かめの要求を送る。
- **確かめが来なければ 115200 に戻る**（片方だけ切り替わって話せなくなるのを防ぐ）。
- **黙りが続いたら 115200 に戻る**: セッションが終わったとき（end、lease の期限切れ、force）と、口に正しいフレームが一定時間
  来ないとき。host は keepalive（またはハートビートの購読）で線を生かし続ける。戻った後、host は 115200 で confirm からやり直す。
- 速さは口ごとで、ほかの経路（USB の CDC、vendor bulk、HID）には関係しない。CDC と USB-Serial/JTAG の baud の設定は意味を
  持たないので対象外（transport の kind 1 = UART bridge だけ）。

## 2. 形（案）

describe（fn 0）の transport の宣言の後ろに、その口が使える速さを足す（固定の形の後ろに足す、core §2.3）:

```text
0x49 transport: index(u8)、kind(u8)、interface(u8)、[n(u8)、n × baud(u32)]   kind 1 だけ。115200 は必ず含める
```

fn 0 に op を 1 つ足す（ロックが要る。0x14、セッションの範囲）:

```text
0x14 port_speed  要求: port(u8)、baud(u32)、confirm_ms(u16)、idle_ms(u32)
                 応答: baud(u32: 切り替える速さ)、[TLV]
```

1. probe は、port がその要求の来た口で、baud が宣言の中にあれば受ける（ほかは rejected unsupported。別の口を変えるのは unavailable）。
2. 応答を**今の速さで送り終えてから**切り替える。
3. host も切り替え、confirm_ms 以内に新しい速さで要求（confirm でよい）を送る。probe は confirm_ms の間に正しいフレームを 1 つも
   受けなければ 115200 に戻る（mark は付けない。host はタイムアウトの後 115200 で confirm し直す）。
4. その後、idle_ms の間その口に正しいフレームが来なければ 115200 に戻る。セッションが終われば（end、期限切れ、force）すぐ戻る。
5. 115200 に戻すのは `port_speed(port, 115200, …)` でもできる。

## 3. 決めること

| # | 項目 | 案 |
|---|---|---|
| 1 | 上げてよいのはセッションの間だけか | はい（IDE のモニターと口を共有するため） |
| 2 | confirm_ms と idle_ms を host が決めるか、probe の固定か | host が決める（probe は範囲を宣言してよい。案: confirm_ms 50〜2000、idle_ms 1000〜60000） |
| 3 | 速さの候補の宣言 | 変換チップとボードは probe の firmware しか知らないので probe が宣言する（classic ESP32 の参照 firmware は 115200、230400、460800、921600 を候補に、ボードの profile で絞る） |
| 4 | host の既定 | 上げない（host が明示したときだけ。bench、ch32rv、pytest の plugin、oep-client-python は「宣言があれば最も速い候補を試し、だめなら 115200」を opt-in の設定 1 か所で） |
| 5 | raw のバイト（bind）の扱い | セッションの間は口の raw の転送は止まっている（core §3.4）ので、上げている間に IDE のモニターが読むことは無い。戻った後に再開する |
