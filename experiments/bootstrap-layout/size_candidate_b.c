#include "bootstrap_candidate_b.h"

static uint8_t report[OEP_BOOTSTRAP_B_REPORT_SIZE];
static volatile uint8_t sink;

int main(void)
{
    report[0] = OEP_BOOTSTRAP_B_REPORT_ID;
    report[1] = 10u;
    report[2] = 0x01u;
    report[3] = 0x01u;
    report[4] = 0x34u;
    report[5] = 0x12u;
    report[6] = 0x4fu;
    report[7] = 0x45u;
    report[8] = 0x50u;
    report[9] = 0x3fu;
    report[10] = 0x01u;
    report[11] = 0x01u;
    sink ^= (uint8_t)oep_bootstrap_b_handle_report(report, sizeof(report));
    sink ^= report[10];
    for (;;) {
    }
}
