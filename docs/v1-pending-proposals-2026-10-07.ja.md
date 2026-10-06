# 実機の試験から出た、規則の変更の候補（2026-10-07）

Status: **proposal**（非規範）。利用者の判断を待つ候補の一覧。線の落ちの P1〜P4 は [v1-debug-link-proposal-2026-10-06](v1-debug-link-proposal-2026-10-06.ja.md)。

## Q1. 実行の準備の失敗の答え方（debug §4.4）

run の準備（レジスタの設定、dcsr など）が失敗したとき、hart は止まったままなのに、reference probe は「止められなかった（stopped 2）、status timeout」と答える。仕様は準備の失敗の答えを定めていない。案: 準備の失敗は fault（または line）で答え、hart は止まったままと分かる形にする。

## Q2. コンソールの SDI / DMDATA の限界の宣言（console §3）

SDI と DMDATA は順番の番号を持たないため、線の書き込みが一つ失われると、同じ枠が 2 回届くこと、DMDATA では答えに載せた入力の byte が失われることがある。dmseq は番号で防ぐ。案: この限界を console §3 に宣言する。

## Q3. 安全な起動（probe-config §2）

起動して短い時間で落ちることが続いた probe が、保存した at boot のスロットの attach を飛ばして起動する。今の §2「起動時は at boot のスロットの attach を始める」から外れる。案: 仕様に条件と、host から見える印（専用の状態か、既存の slot_state / last_try_at_ns）を足す。

## Q4. 前の起動の終わり方（fn 0 の describe）

reference probe は、異常なリセット（panic、watchdog、brownout、試しの間の巻き戻り）の後、describe の firmware の文字列の版の後ろに理由を付けている。版を完全一致で比べる道具が合わなくなる。案: firmware の文字列には付けず、fn 0 の describe に専用の tag（last_reset、rolled_back）を足す。

## Q5. lost の印の位置の意味（common §1.3）

lost の印の position が何を指すかの定めが無い。reference probe は「position から後ろの byte は、損失より後に来たもの」（抜けた所の直後の byte の位置か、それより前）として実装した。案: これを規範にする。

## Q6. シリアルの口での壊れたフレーム（transports §4、ch32rv の案）

- host の義務: シリアルの口で、未解決の応答があるときに壊れたフレームが届いたら、それを失われた応答とみなし、未解決の要求をすぐ同じ corr で送り直す（core §5.2）。どの要求のものか分からないので、未解決のものすべて。上限は registry の値（案: broken_resend_max = 4 / 要求）。§4.4 の待ちは何も届かないときのためのもので、そのときは 1 回送り直す。
- probe の送り直しの表があるので、重複には保った応答か result_lost が返り、安全である。
- 注（参考）: フロー制御の無い変換器は、続けて流れる probe→host の byte を、どの速さでも落とすことがある。host は負荷の下で壊れたフレームが来ることを想定し、1 つで線の失敗とみなさない。

## Q7. restart の後の開き直し（restart §3、tests/hw の reopen_s）

restart_max_ms を過ぎたら host は経路を閉じ、利用者が開き直すまで何も送らない。Python client の reopen_s は、利用者が前もって頼んだ開き直しとして、閉じた後に新しく開くのと同じ手順（confirm から）を最大 reopen_s 秒続ける。これを §3 の「利用者が開き直す」に当たるとみなしてよいか（解釈の確認）。

## Q8. 上げた速さでの待ちと probe の idle（link §3 の host の義務 5、ch32rv の案）

上げた速さで要求が失われる（probe が壊れた要求を捨てる、応答がまるごと失われる）と、host が長く待つ間に probe の idle の規則（idle_ms、最長 3000 ms）が働いて起動時の速さに戻り、送り直しが届かず、義務 5 で起動時の速さに落ちたまま残る。案: 義務 5 に「上げた速さでの最初の待ちは idle_ms より十分短く終え（core §4.4 の下限は守る）、上げた速さのまま送り直す。送り直しにも応答が無いときだけ起動時の速さに戻す」を足す。速さが下がった後、host が同じセッションでもう一度上げてよいことも明記する。

## Q9. キャプチャが線を止める間のコンソール（console §3、capture の describe）

classic ESP32 の sampler は、窓（即時で最大 164 ms、トリガの探索で区切り 250 ms）の間、片方の core で GPIO を読み続け、もう片方の core の SWIO のフレームを乱す（パリティの無い SWIO では DMI の書き込みが化けうる）。reference probe は要求のフレームを窓の後に回した（ff847a4、規則は変えない）。残るのはコンソールの読み（DMSTATUS を 20 ms 以内に見る決まり、console §3）。
- 案 A（推奨）: console §3 の「読みを止めてよい場合」に「describe で宣言したキャプチャがサンプルしている間」を足し、その間は 20 ms の決まりから外す。キャプチャの describe に止める最長の時間の TLV（例 wire_pause_ms、u32）を足す。代わりに、即時の窓の間に送ったコンソールの命令は窓の後に届く。
- 案 B（今の仕様の中）: SWIO の接続かコンソールが生きている間、sampler の start を unavailable で断る。キャプチャとコンソールを同時に使えなくなる。
