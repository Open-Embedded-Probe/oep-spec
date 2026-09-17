# OEP message routing比較実装

状態: **非規定の実験実装**。通常のfunction requestを、共通dispatcherが個別payloadを理解せずにoffered function instanceへ配送できるか確認する。field値、幅、byte order、固定headerおよびresult statusは仕様割当ではない。

## 仮layout

Requestとresultは同じ6 byteの外形を使う。

| offset | request | result |
|---:|---|---|
| 0 | function request role | result role |
| 1 | definition固有operation | 仮resolution / rejection |
| 2..3 | request correlation | 同じcorrelation |
| 4..5 | offered function reference | 同じreference |
| 6.. | definition固有payload | definition固有result payload |

offered function referenceは現在のconnection context内だけでinstanceを選ぶ。referenceからfunction definitionと専用handlerを解決するため、operation番号は選択済みdefinitionのscope内で解釈できる。

## 確認する性質

- 同じoperation値を持つ二つのoffered functionを別handlerへ配送する
- 一方を独自機能として扱い、共通dispatcherはpayloadの意味を解釈しない
- 存在しないoffered function referenceだけをcorrelation付きで拒否する
- 既知instance内の未知operationをtarget不明と区別して拒否する
- 未知roleまたはrouting header未満のmessageをfunction requestとして扱わない
- routing table内の重複referenceまたはNULL handlerを拒否する

host testでは16 bitのoffered function reference全65,536値とrequest correlation全65,536値を走査した。二つの既知referenceだけが各handlerへ入り、その他は同じcorrelationとtarget referenceを持つrejectionになった。message length 0から8 byteもguard byte付きで走査し、routing header未満ではbufferを書き換えないことを確認した。

この実験ではrequest/resultだけを扱う。activity、notification、data flow、criticality、referenceの割当と取得、複数connectionおよびprobeからhostへのrequestは実装しない。

`Makefile`は、6 byte routing、8 byte共有message buffer、二つのoffered function tableおよび二つの小さいhandlerを含むbare ELFの補助測定にだけ使用する。通常のlogic検証はhost-arduino-coreを使用する。

```sh
make -C experiments/message-routing sizes
```

2026-09-18時点の測定結果は次のとおり。runtime table版は汎用dispatcher、compile-time固定版は同じ二つのreferenceを`switch`で配送する測定用実装である。

| target | runtime table版 | compile-time固定版 | 差 |
|---|---:|---:|---:|
| ATmega328P Flash | 750 byte | 336 byte | -414 byte |
| ATmega328P static RAM | 22 byte | 10 byte | -12 byte |
| CH32V003 text + rodata | 460 byte | 168 byte | -292 byte |
| CH32V003 static RAM | 10 byte | 10 byte | 0 byte |

ATmega328Pでは二つのentryを持つfunction pointer tableが12 byteのstatic RAMを使う。CH32V003では同じtableが24 byteのread-only dataに置かれる。この差はABIとlinker配置によるもので、routing modelがruntime tableを要求することを意味しない。

提供機能がcompile-timeに固定された小さなprobeは、生成した`switch`等でtableを持たずに実装できる。提供機能をruntimeに構成する実装や共通firmwareではtable版を選べる。測定値にはArduino core、connection binding、bootstrap、および二つの最小handlerを超える実機能は含まない。

## 固定headerとrole別header

[Message header構成比較](../../docs/message-header-layout-comparison.ja.md)の仮幅を使い、6種類のroleを正規化した同じviewへdecodeする二つのparserも比較した。

- 固定header版は全roleを7 byteとし、roleに不要なfieldを出力viewから除外する
- role別header版はrequest 6 byte、result/activity/data 4 byte、notification 5 byteを検証する
- 両方とも未知roleを拒否し、成功前にrole固有fieldを出力しない
- role全256値とmessage length 0から7 byteの組合せをhost testで走査した

2026-09-18時点のbare ELF測定は次のとおり。両方とも6 roleすべてのdecode処理、正規化view、入力message、volatileな測定用sinkを含む。

| target | 7 byte固定header | 4〜6 byte role別header | role別の差 |
|---|---:|---:|---:|
| ATmega328P Flash | 484 byte | 574 byte | +90 byte |
| ATmega328P static RAM | 10 byte | 8 byte | -2 byte |
| CH32V003 text | 346 byte | 392 byte | +46 byte |
| CH32V003 static RAM | 9 byte | 8 byte | -1 byte |

static RAM差は主に測定用入力bufferが7 byteから6 byteになる差であり、どちらのparserも永続状態を要求しない。role別版はroleごとの長さとfield位置を分岐するためcodeが増える一方、messageごとに1から3 byteを削減する。request/resultだけの最小probeは未使用roleのdecode処理をcompileしない実装も可能であり、この全role測定値をすべてのprobeの必須費用とはしない。

## Request correlation matcher

[Request correlationのscopeとlifecycle](../../docs/request-correlation-lifecycle.ja.md)に従う比較用matcherを追加した。一つまたは複数の固定slotへ、correlationとtarget reference、operation、および解決後のresolution/activity referenceを保持する。

host testでは次を確認した。

- 未知correlationのresultで、別のpending requestまたは出力contextを変更しない
- matching resultからtarget referenceとoperationを復元する
- 同じresolutionとactivity referenceの再受信をduplicateとして区別する
- 同じcorrelationに矛盾するresolutionまたはactivity referenceをconflictとする
- resolved slotを明示的にretireするまでcorrelationを再利用しない
- `accepted` resultでrequest contextと新しいactivity referenceを同時に得る
- 複数slotのうち一致したrequestだけを解決する
- 16 bit correlationの全65,536値でopen、resolve、retireが一致する

このmatcherはpayload全体の重複一致、timeout、再送、connectionを越える回復、およびactivity table自体を実装しない。同一envelopeのduplicateを検出しても、機能固有payloadまで同一であることを保証するものではない。
