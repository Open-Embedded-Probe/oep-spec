#include "request_correlation.h"

#include <string.h>

static struct oep_pending_request *find_correlation(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t correlation)
{
    size_t index;

    for (index = 0u; index < slot_count; ++index) {
        if (slots[index].state != OEP_PENDING_FREE &&
            slots[index].correlation == correlation) {
            return &slots[index];
        }
    }
    return NULL;
}

void oep_pending_reset(
    struct oep_pending_request *slots,
    size_t slot_count)
{
    if (slots != NULL) {
        memset(slots, 0, slot_count * sizeof(slots[0]));
    }
}

enum oep_correlation_result oep_pending_open(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t correlation,
    uint16_t target_reference,
    uint8_t operation)
{
    size_t index;

    if (slots == NULL || slot_count == 0u) {
        return OEP_CORRELATION_INVALID;
    }
    if (find_correlation(slots, slot_count, correlation) != NULL) {
        return OEP_CORRELATION_BUSY;
    }
    for (index = 0u; index < slot_count; ++index) {
        if (slots[index].state == OEP_PENDING_FREE) {
            slots[index].correlation = correlation;
            slots[index].target_reference = target_reference;
            slots[index].activity_reference = 0u;
            slots[index].operation = operation;
            slots[index].resolution = 0u;
            slots[index].state = OEP_PENDING_WAITING;
            return OEP_CORRELATION_OK;
        }
    }
    return OEP_CORRELATION_FULL;
}

enum oep_correlation_result oep_pending_resolve(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t correlation,
    uint8_t resolution,
    uint16_t activity_reference,
    struct oep_request_context *context)
{
    struct oep_pending_request *slot;
    struct oep_request_context resolved;

    if (slots == NULL || slot_count == 0u || context == NULL ||
        resolution > OEP_REQUEST_ACCEPTED ||
        (resolution != OEP_REQUEST_ACCEPTED && activity_reference != 0u)) {
        return OEP_CORRELATION_INVALID;
    }
    slot = find_correlation(slots, slot_count, correlation);
    if (slot == NULL) {
        return OEP_CORRELATION_UNKNOWN;
    }
    if (slot->state == OEP_PENDING_RESOLVED &&
        (slot->resolution != resolution ||
         slot->activity_reference != activity_reference)) {
        return OEP_CORRELATION_CONFLICT;
    }

    resolved.target_reference = slot->target_reference;
    resolved.activity_reference = activity_reference;
    resolved.operation = slot->operation;
    resolved.resolution = resolution;

    if (slot->state == OEP_PENDING_RESOLVED) {
        *context = resolved;
        return OEP_CORRELATION_DUPLICATE;
    }
    slot->resolution = resolution;
    slot->activity_reference = activity_reference;
    slot->state = OEP_PENDING_RESOLVED;
    *context = resolved;
    return OEP_CORRELATION_OK;
}

enum oep_correlation_result oep_pending_retire(
    struct oep_pending_request *slots,
    size_t slot_count,
    uint16_t correlation)
{
    struct oep_pending_request *slot;

    if (slots == NULL || slot_count == 0u) {
        return OEP_CORRELATION_INVALID;
    }
    slot = find_correlation(slots, slot_count, correlation);
    if (slot == NULL) {
        return OEP_CORRELATION_UNKNOWN;
    }
    if (slot->state != OEP_PENDING_RESOLVED) {
        return OEP_CORRELATION_BUSY;
    }
    memset(slot, 0, sizeof(*slot));
    return OEP_CORRELATION_OK;
}
