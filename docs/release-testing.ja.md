# リリース前の結合試験: 誰が何を持つか（案）

状態: **案**（2026-10-01、ユーザーのメモから）。core（ArduinoCore-CH32RV）を中心にしたエコシステムの試験台はできた。OEP の側は、
core を介さずに firmware を転送して試験できるので、**リリース前に「Arduino の firmware」と「Python クライアント」の組で試験するのを必須**
にし、どのリポジトリが環境と手順を持つかをここで決める。

## 1. 責任の分け方

| 何を | 持つリポジトリ | 中身 |
|---|---|---|
| プロトコルの規範、番号、fake の「動く仕様」の根拠 | oep-spec | 文書、registry、生成物。実装は持たない |
| **結合試験の環境と手順** | **oep-client-python** | fake に対する試験（既存の pytest）に加え、**実機の probe に対する試験**（`tests/hw/`）: firmware を用意し、焼き、クライアントで一通り動かす。board-identify の id で口を選ぶ |
| firmware のビルドと単体の試験 | oep-probe-arduino | profile ごとのビルド（CI）、host テスト、release の json。実機の試験は oep-client-python に任せ、自分では持たない |
| JS クライアント | oep-client-js | fake に対する試験。実機の試験は Python の `tests/hw/` の結果を前提にし、ブラウザの手動確認だけ |
| core のベンチ（ジグ、治具の配線） | ArduinoCore-CH32RV | OEP の試験の対象ではなく、OEP を使う側の試験。OEP のリリースの後に追従して回す（今までどおり） |

理由: 実機の試験は「firmware を焼く」「クライアントで動かす」「結果を判定する」の 3 つで、焼くのも判定するのも Python（esptool、
picotool / uf2、oep_client）でできる。firmware のリポジトリは Arduino のビルドの環境しか持たず、probe を「使う側」の知識は
クライアントにある。

## 2. firmware の取り方（oep-client-python の `tests/hw/`）

2 つの取り方を持ち、環境変数で選ぶ:

| 取り方 | 指定 | いつ使うか |
|---|---|---|
| **ローカルのビルド** | `OEP_PROBE_DIR=/path/to/oep-probe-arduino`（arduino-cli で `examples/Firmware/OepProbe` を profile ごとにビルド） | リリース前（main どうしの組で試す。今の開発の形） |
| **リリースの版** | `OEP_PROBE_VERSION=0.0.25`（GitHub の release から `firmware-<ver>.json` と image を取り、sha256 を照合） | クライアントだけを変えたとき、再現、CI |

どちらも、焼く前の firmware の版（describe の firmware）と焼いた後の版を記録し、結果に残す。

## 3. 実機の試験の中身（最小）

対象のボードは `OEP_HW_BOARDS`（board-identify の id の並び、例: `esp32-pico-d4-50029191fe34`）。ボードごとに:

1. 焼く（esp32: esptool の merged.bin、rp2: uf2 を BOOTSEL のドライブへ、P4: DFU の app.bin）。
2. 起動を待ち、confirm / list / describe。boot_id が変わっていること、firmware の文字列が期待の版であること。
3. probe.config: set / get / save / state / unset（disable を含む）。保存して再起動して読めること。
4. 線（接続している target があれば）: scan、attach（reset TLV を含む）、halt → read_block → resume の往復（block op の自己完結）。
5. fixture: gpio の set / read、uart の configure / write / read（ループバックの配線があれば）。
6. port_speed（UART bridge の probe だけ）: `linktest` の matrix を既定の条件（今の速さと候補の速さ、in / out / duplex、同時 1 と max）で
   回し、結果を記録する。壊れ方の閾値（例: 1 つずつで 1 % 以下）を判定にする。
7. セッション: lease の期限切れ、expired、force の往復。

結果は JSON で `tests/hw/results/<board>-<firmware>-<client>.json` に残し、リリースノートから参照する。

## 4. いつ回すか

- oep-probe-arduino のリリースの前: `OEP_PROBE_DIR` でローカルの main をビルドして、手元のボード全部で回す。
- oep-client-python のリリースの前: 最新のリリースの firmware（`OEP_PROBE_VERSION`）で回す。
- どちらも通らなければリリースしない。core のベンチは、そのあとで追従として回す。

## 5. 決めること

1. この分け方（Python が実機の試験を持つ）でよいか。
2. 手元のボード（ATOM、P4 の治具、V003 の治具、Pro Micro RP2350）のうち、OEP のリリース前の試験に常時使えるものはどれか
   （治具は bench と共有なので、使うときの決まり）。
3. 結果の置き場（リポジトリに commit するか、release の添付にするか）。
