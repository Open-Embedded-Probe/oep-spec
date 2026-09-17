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
