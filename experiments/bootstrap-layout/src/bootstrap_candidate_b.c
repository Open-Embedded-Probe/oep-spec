#include "bootstrap_candidate_b.h"

#include "bootstrap_candidate_b_core.h"

size_t oep_bootstrap_b_handle_report(uint8_t *report, size_t report_length)
{
    size_t response_length;

    if (report == NULL || report_length != OEP_BOOTSTRAP_B_REPORT_SIZE ||
        report[0] != OEP_BOOTSTRAP_B_REPORT_ID ||
        report[1] != OEP_BOOTSTRAP_B_REQUEST_SIZE) {
        return 0;
    }
#if defined(OEP_BOOTSTRAP_B_STRICT_PADDING)
    if (report[12] != 0 || report[13] != 0 ||
        report[14] != 0 || report[15] != 0) {
        return 0;
    }
#endif
    response_length = oep_bootstrap_b_handle_core_message(
        report + 2,
        report[1],
        OEP_BOOTSTRAP_B_REPORT_SIZE - 2u);
    if (response_length == 0) {
        return 0;
    }
    report[1] = (uint8_t)response_length;
    return OEP_BOOTSTRAP_B_REPORT_SIZE;
}
