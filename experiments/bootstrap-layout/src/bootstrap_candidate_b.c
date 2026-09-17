#include "bootstrap_candidate_b.h"

#include <string.h>

size_t oep_bootstrap_b_handle_report(uint8_t *report, size_t report_length)
{
    uint8_t correlation_low;
    uint8_t correlation_high;
    uint8_t compatible;

    if (report == NULL || report_length != OEP_BOOTSTRAP_B_REPORT_SIZE ||
        report[0] != OEP_BOOTSTRAP_B_REPORT_ID || report[1] != 10u ||
        report[2] != 0x01u || report[3] != 0x01u ||
        report[6] != 0x4fu || report[7] != 0x45u ||
        report[8] != 0x50u || report[9] != 0x3fu) {
        return 0;
    }

    correlation_low = report[4];
    correlation_high = report[5];
    compatible = report[10] <= 1u && report[11] >= 1u;

    memset(report, 0, OEP_BOOTSTRAP_B_REPORT_SIZE);
    report[0] = OEP_BOOTSTRAP_B_REPORT_ID;
    report[1] = 14u;
    report[2] = 0x81u;
    report[3] = 0x01u;
    report[4] = correlation_low;
    report[5] = correlation_high;
    report[6] = 0x4fu;
    report[7] = 0x45u;
    report[8] = 0x50u;
    report[9] = 0x21u;
    report[10] = compatible ? 0u : 1u;
    report[11] = compatible ? 1u : 0u;
    report[12] = 0x00u;
    report[13] = 0x01u;
    report[14] = 0x01u;
    report[15] = 0x01u;
    return OEP_BOOTSTRAP_B_REPORT_SIZE;
}
