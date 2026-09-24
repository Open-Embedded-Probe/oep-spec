// What the debugger leaves on the RVSWD pins while it rests, and what it sends first afterwards. This chip reads its own
// pins (a = SWDIO bit0, b = SWCLK bit1): waits for any level held >= 2 ms, then records the next 512 changes, then prints
// on the dmseq console (the print waits for a reader, which is fine: the observation is already done).
#include <SerialDMSeq.h>
#include <stdio.h>
static uint8_t val[512];
static uint32_t at[512];
volatile uint32_t g_beat, g_now, g_changes, g_phase, g_rest_level, g_n;   // alive / pins now / changes seen while waiting for a rest
char g_line[420];   // latest report (read over the debug port when OBS_PRINT is 0)
#ifndef OBS_PRINT
#define OBS_PRINT 1
#endif
static inline uint32_t sample() {
  const uint32_t r = *(volatile uint32_t *)(OBS_BASE + 0x08);
  return ((r >> OBS_A) & 1) | (((r >> OBS_B) & 1) << 1);
}
void setup() {
  *(volatile uint32_t *)0x40021018 |= 1u << OBS_EN;
  SerialDMSeq.begin(115200);
}
void loop() {
  uint32_t v = sample(), last = micros();
  for (;;) {   // a rest: any level held for 2 ms
    const uint32_t w = sample();
    ++g_beat; g_now = w;
    if (w != v) { v = w; last = micros(); ++g_changes; }
    else if (micros() - last >= 2000) break;
  }
  const uint32_t rest_level = v, rest_from = last;
  g_phase = 1; g_rest_level = v;
  uint32_t iter = 0;
  int n = 0;
  val[n] = v; at[n] = 0; ++n;
  while (n < 512) {   // the burst that ends the rest (waits as long as it takes), until 3000 quiet samples
    ++iter;
    const uint32_t w = sample();
    if (w == v) { if (n > 1 && iter - at[n - 1] > 3000u) break; continue; }
    v = w; val[n] = w; at[n] = iter; ++n; g_n = n;
  }
  g_phase = 2;
  const uint32_t rest_ms = (micros() - rest_from) / 1000;
  int starts = 0, rises = 0, before = -1;
  for (int i = 1; i < n; ++i) {
    const uint8_t p = val[i - 1], c = val[i];
    if (!(p & 2) && (c & 2)) ++rises;
    if ((p & 2) && (c & 2) && (p & 1) && !(c & 1)) { if (before < 0) before = rises; ++starts; }
  }
  int k = snprintf(g_line, sizeof g_line, "REST level a%lub%lu for ~%lu ms; burst: changes %d, clk rises %d, starts %d, rises before first start %d; first:",
                   (unsigned long)(rest_level & 1), (unsigned long)(rest_level >> 1), (unsigned long)rest_ms, n, rises, starts, before);
  for (int i = 1; i < n && i < 48 && k < (int)sizeof g_line - 3; ++i) k += snprintf(g_line + k, sizeof g_line - k, " %u", val[i]);
  if (OBS_PRINT) SerialDMSeq.println(g_line);
}
