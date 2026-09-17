#include "bootstrap_candidate_c.h"

#include <string.h>

size_t oep_bootstrap_c_handle_report(uint8_t *report, size_t report_length)
{
    uint8_t operation;
    uint8_t correlation;
    uint8_t compatible;

    if (report == NULL || report_length != OEP_BOOTSTRAP_C_REPORT_SIZE ||
        report[0] != OEP_BOOTSTRAP_C_REPORT_ID ||
        report[1] != 0x4fu || report[2] != 0x45u || report[3] != 0x01u) {
        return 0;
    }

    operation = report[4];
    correlation = report[5];
    if (operation == 0x01u) {
        compatible = report[6] <= 1u && report[7] >= 1u;
        memset(report, 0, OEP_BOOTSTRAP_C_REPORT_SIZE);
        report[0] = OEP_BOOTSTRAP_C_REPORT_ID;
        report[1] = 0x4fu;
        report[2] = 0x45u;
        report[3] = 0x01u;
        report[4] = compatible ? 0x81u : 0xc1u;
        report[5] = correlation;
        report[6] = compatible ? 1u : 0u;
        report[7] = 0x08u;
        report[8] = 0x01u;
        return OEP_BOOTSTRAP_C_REPORT_SIZE;
    }
    if (operation == 0x02u) {
        memset(report, 0, OEP_BOOTSTRAP_C_REPORT_SIZE);
        report[0] = OEP_BOOTSTRAP_C_REPORT_ID;
        report[1] = 0x4fu;
        report[2] = 0x45u;
        report[3] = 0x01u;
        report[4] = 0x82u;
        report[5] = correlation;
        report[6] = 0x00u;
        report[7] = 0x01u;
        report[8] = 0x01u;
        return OEP_BOOTSTRAP_C_REPORT_SIZE;
    }
    return 0;
}
