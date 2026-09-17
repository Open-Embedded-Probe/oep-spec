#ifndef OEP_EXPERIMENT_BOOTSTRAP_CANDIDATE_B_CORE_H
#define OEP_EXPERIMENT_BOOTSTRAP_CANDIDATE_B_CORE_H

#include <stddef.h>
#include <stdint.h>

#define OEP_BOOTSTRAP_B_REQUEST_SIZE 10u
#define OEP_BOOTSTRAP_B_RESPONSE_SIZE 14u
#define OEP_BOOTSTRAP_B_STATUS_COMPATIBLE 0u
#define OEP_BOOTSTRAP_B_STATUS_INCOMPATIBLE 1u
#define OEP_BOOTSTRAP_B_STATUS_UNSUPPORTED_OPERATION 2u

#ifdef __cplusplus
extern "C" {
#endif

size_t oep_bootstrap_b_handle_core_message(
    uint8_t *message,
    size_t message_length,
    size_t message_capacity);

#ifdef __cplusplus
}
#endif

#endif
