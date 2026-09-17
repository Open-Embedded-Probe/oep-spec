#include "message_header_layout.h"

static uint8_t message[OEP_ROLE_HEADER_REQUEST_SIZE] = {
    OEP_HEADER_ROLE_FUNCTION_REQUEST, 1u, 0x34u, 0x12u, 0x01u, 0x10u,
};
static volatile uint8_t input_seed;
static volatile uint8_t sink;

int main(void)
{
    struct oep_header_view view;

    message[0] ^= input_seed;
    if (!oep_decode_role_header(message, sizeof(message), &view)) {
        return 1;
    }
    sink = (uint8_t)(view.role ^ view.detail ^ view.scope ^ view.present ^
        view.header_length ^ view.correlation ^ view.reference);
    return sink == 0u;
}
