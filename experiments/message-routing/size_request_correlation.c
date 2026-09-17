#include "request_correlation.h"

#ifndef OEP_SIZE_SLOT_COUNT
#define OEP_SIZE_SLOT_COUNT 1u
#endif

static struct oep_pending_request slots[OEP_SIZE_SLOT_COUNT];
static struct oep_request_context context;
static volatile uint8_t input_seed;
static volatile uint8_t sink;

int main(void)
{
    uint16_t correlation = (uint16_t)0x1234u ^ input_seed;

    oep_pending_reset(slots, OEP_SIZE_SLOT_COUNT);
    if (oep_pending_open(
            slots, OEP_SIZE_SLOT_COUNT, correlation, 0x1001u, 0x44u) !=
        OEP_CORRELATION_OK) {
        return 1;
    }
    if (oep_pending_resolve(
            slots, OEP_SIZE_SLOT_COUNT, correlation,
            OEP_REQUEST_ACCEPTED, 0x5678u, &context) !=
        OEP_CORRELATION_OK) {
        return 1;
    }
    sink = (uint8_t)(context.target_reference ^ context.activity_reference ^
        context.operation ^ context.resolution);
    return sink == 0u;
}
