#include "bootstrap_limit_summary.h"

uint16_t oep_bootstrap_summarize_message_limit(uint32_t exact_limit)
{
    return exact_limit < OEP_BOOTSTRAP_LIMIT_DETAIL_REQUIRED ?
        (uint16_t)exact_limit : OEP_BOOTSTRAP_LIMIT_DETAIL_REQUIRED;
}

bool oep_bootstrap_message_limit_needs_detail(uint16_t summary)
{
    return summary == OEP_BOOTSTRAP_LIMIT_DETAIL_REQUIRED;
}

bool oep_bootstrap_message_limit_allows_without_detail(
    uint16_t summary,
    uint32_t message_length)
{
    return message_length <= (uint32_t)summary;
}
