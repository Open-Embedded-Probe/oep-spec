#ifndef OEP_EXPERIMENT_REQUEST_CORRELATION_H
#define OEP_EXPERIMENT_REQUEST_CORRELATION_H

#include <stddef.h>
#include <stdint.h>

enum oep_request_resolution {
    OEP_REQUEST_REJECTED = 0,
    OEP_REQUEST_COMPLETED = 1,
    OEP_REQUEST_ACCEPTED = 2,
};

enum oep_correlation_result {
    OEP_CORRELATION_OK = 0,
    OEP_CORRELATION_DUPLICATE = 1,
    OEP_CORRELATION_CONFLICT = 2,
    OEP_CORRELATION_UNKNOWN = 3,
    OEP_CORRELATION_BUSY = 4,
    OEP_CORRELATION_FULL = 5,
    OEP_CORRELATION_INVALID = 6,
    OEP_CORRELATION_EXHAUSTED = 7,
};

enum oep_pending_state {
    OEP_PENDING_FREE = 0,
    OEP_PENDING_WAITING = 1,
    OEP_PENDING_RESOLVED = 2,
};

struct oep_pending_request {
    uint16_t correlation;
    uint16_t target_reference;
    uint16_t activity_reference;
    uint8_t operation;
    uint8_t resolution;
    uint8_t state;
};

struct oep_request_context {
    uint16_t target_reference;
    uint16_t activity_reference;
    uint8_t operation;
    uint8_t resolution;
};

#ifdef __cplusplus
extern "C" {
#endif

void oep_pending_reset(
    struct oep_pending_request *slots,
    size_t slot_count);

enum oep_correlation_result oep_pending_open(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t correlation,
    uint16_t target_reference,
    uint8_t operation);

enum oep_correlation_result oep_pending_allocate(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t *next_candidate,
    uint16_t maximum_value,
    uint16_t target_reference,
    uint8_t operation,
    uint16_t *allocated_correlation);

enum oep_correlation_result oep_pending_resolve(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t correlation,
    uint8_t resolution,
    uint16_t activity_reference,
    struct oep_request_context *context);

enum oep_correlation_result oep_pending_retire(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t correlation);

#ifdef __cplusplus
}
#endif

#endif
