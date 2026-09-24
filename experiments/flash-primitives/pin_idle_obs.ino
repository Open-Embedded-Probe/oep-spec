// Watch this chip's own debug pins while a debugger talks to it: every 500 ms, print on the dmseq console how long the
// two lines sat still in each level combination (runs of 20 us or more = the debugger's idle), and how many changes
// were seen. OBS_BASE = GPIO port base, OBS_A / OBS_B = pin bits (OBS_B < 0: one-wire SWIO), OBS_EN = RCC_APB2PCENR bit.
#include <SerialDMSeq.h>
#ifndef OBS_BASE
#error "build with -DOBS_BASE=... -DOBS_A=... -DOBS_B=... -DOBS_EN=..."
#endif
static inline uint32_t sample() {
  const uint32_t r = *(volatile uint32_t *)(OBS_BASE + 0x08);   // INDR: the pad level, whatever drives it
#if OBS_B >= 0
  return ((r >> OBS_A) & 1) | (((r >> OBS_B) & 1) << 1);
#else
  return (r >> OBS_A) & 1;
#endif
}
void setup() {
  *(volatile uint32_t *)0x40021018 |= 1u << OBS_EN;   // the port's clock, so INDR reads the pads
  SerialDMSeq.begin(115200);
}
void loop() {
  uint32_t idle_us[4] = {0}, idle_n[4] = {0}, longest[4] = {0}, changes = 0;
  uint32_t v = sample(), start = micros();
  const uint32_t t0 = millis();
  while (millis() - t0 < 500) {
    const uint32_t w = sample();
    if (w == v) continue;
    const uint32_t t = micros(), d = t - start;
    if (d >= 20) { idle_us[v] += d; idle_n[v]++; if (d > longest[v]) longest[v] = d; }
    ++changes; v = w; start = t;
  }
  const uint32_t ongoing = micros() - start;
  SerialDMSeq.print("OBS changes="); SerialDMSeq.print(changes);
  for (int s = 0; s < 4; ++s) {
    if (!idle_n[s]) continue;
    SerialDMSeq.print(" a"); SerialDMSeq.print(s & 1); SerialDMSeq.print("b"); SerialDMSeq.print((s >> 1) & 1);
    SerialDMSeq.print("="); SerialDMSeq.print(idle_us[s]); SerialDMSeq.print("us/"); SerialDMSeq.print(idle_n[s]);
    SerialDMSeq.print("/max"); SerialDMSeq.print(longest[s]);
  }
  SerialDMSeq.print(" now=a"); SerialDMSeq.print(v & 1); SerialDMSeq.print("b"); SerialDMSeq.print((v >> 1) & 1);
  SerialDMSeq.print("/"); SerialDMSeq.println(ongoing);
}
