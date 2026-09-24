// What does the debugger send first after the bus has rested? This chip watches its own RVSWD pins (a = SWDIO,
// b = SWCLK): after >= 2 ms with both high, it records the next 512 changes with SysTick timestamps, then reports on the
// dmseq console: SWCLK pulses before the first start condition (a wake burst would be ~100), frames (starts) in the
// burst, and the median SWCLK period. OBS_BASE / OBS_A / OBS_B / OBS_EN as in pin_idle_obs;
#include <SerialDMSeq.h>
#include <stdio.h>
#ifndef OBS_PRINT
#define OBS_PRINT 1   // 0: keep the report in g_report only (no console reader: a print would wait for one)
#endif
char g_report[400];   // latest report, readable over the debug port without the console
static uint32_t g_count = 0;
static uint8_t val[512];
static uint32_t tick[512];
static inline uint32_t sample() {
  const uint32_t r = *(volatile uint32_t *)(OBS_BASE + 0x08);
  return ((r >> OBS_A) & 1) | (((r >> OBS_B) & 1) << 1);
}
static uint32_t iter = 0;   // loop iterations: a steady clock inside the recording loop
void setup() {
  *(volatile uint32_t *)0x40021018 |= 1u << OBS_EN;
  SerialDMSeq.begin(115200);
}
void loop() {
  // wait for a rest: both high for 2 ms
  uint32_t v = sample(), last = micros();
  const uint32_t give_up = millis();
  for (;;) {
    const uint32_t w = sample();
    if (w != v) { v = w; last = micros(); }
    else if (v == 3 && micros() - last >= 2000) break;
    if (millis() - give_up > 2000) {
      snprintf(g_report, sizeof g_report, "#%lu none: no 2 ms rest with both high in 2 s, pins now %lu", (unsigned long)++g_count, (unsigned long)v);
      if (OBS_PRINT) SerialDMSeq.println("BURST none (no 2 ms rest in 2 s)");
      return;
    }
  }
  // record the burst
  int n = 0;
  iter = 0;
  val[n] = v; tick[n] = 0; ++n;
  const uint32_t rest_start = micros();
  uint32_t burst_start_us = 0, burst_start_iter = 0;
  while (n < 512) {
    ++iter;
    const uint32_t w = sample();
    if (w == v) {
      if (n > 1 && iter - tick[n - 1] > 3000u) break;   // quiet for a while: the burst is over
      if (n == 1 && micros() - rest_start > 1000000u) break;
      continue;
    }
    if (n == 1) { burst_start_us = micros(); burst_start_iter = iter; }
    v = w; val[n] = w; tick[n] = iter; ++n;
  }
  const uint32_t burst_us = micros() - burst_start_us, burst_iter = iter - burst_start_iter;
  const uint32_t ns_per_iter = burst_iter ? burst_us * 1000u / burst_iter : 0;
  const uint32_t rest_us = 2000 + (burst_start_us - rest_start);
  // analyse: a = bit0 (SWDIO), b = bit1 (SWCLK)
  int clk_before_start = -1, starts = 0, stops = 0, rises = 0;
  uint32_t periods[64]; int np = 0; uint32_t last_rise = 0;
  for (int i = 1; i < n; ++i) {
    const uint8_t p = val[i - 1], c = val[i];
    if (!(p & 2) && (c & 2)) {   // SWCLK rising
      if (last_rise && np < 64) periods[np++] = tick[i] - last_rise;
      last_rise = tick[i]; ++rises;
    }
    if ((p & 2) && (c & 2) && (p & 1) && !(c & 1)) { if (clk_before_start < 0) clk_before_start = rises; ++starts; }
    if ((p & 2) && (c & 2) && !(p & 1) && (c & 1)) ++stops;
  }
  for (int i = 0; i < np; ++i) for (int j = i + 1; j < np; ++j) if (periods[j] < periods[i]) { uint32_t t = periods[i]; periods[i] = periods[j]; periods[j] = t; }
  int k = snprintf(g_report, sizeof g_report, "#%lu rest %lu us: changes %d clk_before_first_start %d starts %d stops %d rises %d clk_period_ns %lu ns_per_sample %lu first:",
                   (unsigned long)++g_count, (unsigned long)rest_us, n, clk_before_start, starts, stops, rises,
                   (unsigned long)(np ? periods[np / 2] * ns_per_iter : 0), (unsigned long)ns_per_iter);
  for (int i = 1; i < n && i < 40 && k < (int)sizeof g_report - 3; ++i) k += snprintf(g_report + k, sizeof g_report - k, " %u", val[i]);
  if (OBS_PRINT) { SerialDMSeq.print("BURST "); SerialDMSeq.print(g_report); SerialDMSeq.println(); }
  delay(100);
}
