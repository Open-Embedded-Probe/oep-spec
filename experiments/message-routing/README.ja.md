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
