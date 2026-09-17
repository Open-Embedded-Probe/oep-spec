#include "bootstrap_candidate_c.h"

static uint8_t report[OEP_BOOTSTRAP_C_REPORT_SIZE];
static volatile uint8_t sink;

static void prepare(uint8_t operation)
{
    report[0] = OEP_BOOTSTRAP_C_REPORT_ID;
    report[1] = 0x4fu;
    report[2] = 0x45u;
    report[3] = 0x01u;
    report[4] = operation;
    report[5] = 0x5au;
    report[6] = 0x01u;
    report[7] = 0x01u;
    report[8] = 0x00u;
}

int main(void)
{
    prepare(0x01u);
    sink ^= (uint8_t)oep_bootstrap_c_handle_report(report, sizeof(report));
    prepare(0x02u);
    sink ^= (uint8_t)oep_bootstrap_c_handle_report(report, sizeof(report));
    sink ^= report[8];
    for (;;) {
    }
}
