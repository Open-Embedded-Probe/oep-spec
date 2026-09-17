#ifndef OEP_EXPERIMENT_BOOTSTRAP_CANDIDATE_C_H
#define OEP_EXPERIMENT_BOOTSTRAP_CANDIDATE_C_H

#include <stddef.h>
#include <stdint.h>

#define OEP_BOOTSTRAP_C_REPORT_SIZE 9u
#define OEP_BOOTSTRAP_C_REPORT_ID 1u

#ifdef __cplusplus
extern "C" {
#endif

size_t oep_bootstrap_c_handle_report(uint8_t *report, size_t report_length);

#ifdef __cplusplus
}
#endif

#endif
