#include "request_correlation.h"

#ifndef OEP_SIZE_CORRELATION_MAXIMUM
#define OEP_SIZE_CORRELATION_MAXIMUM 0xffffu
#endif

static struct oep_pending_request slot;
static struct oep_request_context context;
static uint16_t next_candidate;
static uint16_t allocated;
static volatile uint8_t input_seed;
static volatile uint8_t sink;

int main(void)
{
    next_candidate = input_seed;
    oep_pending_reset(&slot, 1u);
    if (oep_pending_allocate(
            &slot, 1u, &next_candidate, OEP_SIZE_CORRELATION_MAXIMUM,
            0x1001u, 0x44u, &allocated) != OEP_CORRELATION_OK) {
        return 1;
    }
    if (oep_pending_resolve(
            &slot, 1u, allocated, OEP_REQUEST_COMPLETED, 0u, &context) !=
        OEP_CORRELATION_OK) {
        return 1;
    }
    sink = (uint8_t)(allocated ^ context.target_reference ^
        context.operation ^ context.resolution);
    return sink == 0u;
}
