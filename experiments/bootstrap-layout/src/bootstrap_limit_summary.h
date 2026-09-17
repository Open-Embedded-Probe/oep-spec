#ifndef OEP_EXPERIMENT_BOOTSTRAP_LIMIT_SUMMARY_H
#define OEP_EXPERIMENT_BOOTSTRAP_LIMIT_SUMMARY_H

#include <stdbool.h>
#include <stdint.h>

#define OEP_BOOTSTRAP_LIMIT_DETAIL_REQUIRED UINT16_MAX

#ifdef __cplusplus
extern "C" {
#endif

uint16_t oep_bootstrap_summarize_message_limit(uint32_t exact_limit);

bool oep_bootstrap_message_limit_needs_detail(uint16_t summary);

bool oep_bootstrap_message_limit_allows_without_detail(
    uint16_t summary,
    uint32_t message_length);

#ifdef __cplusplus
}
#endif

#endif
