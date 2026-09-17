# Tests

実験実装の自動テスト環境。

- `pytest-embedded` + Arduino CLI backendを使用する
- 既定では`lang-ship:host`上でArduino sketchとしてlogicを実行する
- 各実験を`<name>.ino` / `sketch.yaml` / `test_<name>.py`の組で管理する
- sketchは`TEST done N/N`をSerialへ出力し、pytestが完了と全件成功を確認する

この経路では、host compilerへsourceを直接渡すだけでなく、Arduino libraryの探索、C/C++ compilationおよびlinkも確認できる。peripheral、timing、割込み、memory layoutおよび実UARTの性質はhost testでは保証しない。

`uart_sequence_characterization`は、1 bit sequenceが順序保存されたstreamで重複を抑止できる一方、二つ後まで並べ替えられた古いframeを新規と区別できないことを意図的に再現する。これはその並べ替えを許容する試験ではなく、最小UART bindingが送信順序保存を前提にする根拠を固定するcharacterizationである。

## 現在のtest module

- `uart_binding` — framing、破損回復、stop-and-wait、epoch、partial timeoutおよび双方向queue
- `uart_sequence_characterization` — 1 bit sequenceと順序保存前提の境界

## 実行

```sh
cd tests
uv run pytest
```

初回は、`sketch.yaml`に指定した`lang-ship:host` coreとPython dependencyの取得が必要になる場合がある。

## AVR build確認

UART binding sketchはUno R3 profileも定義している。実機へuploadせずcompileだけ確認する場合:

```sh
cd tests
uv run pytest uart_binding --profile=uno --run-mode=build
```

AVR上の正確なRAM/Flash比較には、実験directoryの測定用targetを補助的に使用する。host testとAVR build確認を通常の検証経路とし、個別compilerを直接呼ぶ測定はfootprintを更新するときだけ行う。
