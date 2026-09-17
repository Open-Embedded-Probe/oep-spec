#include "message_routing.h"

static uint8_t message[8] = {
    OEP_ROUTING_ROLE_FUNCTION_REQUEST, 1u, 0x34u, 0x12u,
    0x01u, 0x10u, 0x12u, 0x34u,
};
static volatile uint8_t sink;
static volatile uint8_t input_seed;

static enum oep_routing_result first_handler(
    void *context,
    uint8_t operation,
    uint8_t *payload,
    size_t *payload_length,
    size_t payload_capacity)
{
    (void)context;
    if (operation != 1u || *payload_length != 2u || payload_capacity < 2u) {
        return OEP_ROUTING_REJECTED_OPERATION;
    }
    payload[0] ^= 0x55u;
    return OEP_ROUTING_COMPLETED;
}

static enum oep_routing_result second_handler(
    void *context,
    uint8_t operation,
    uint8_t *payload,
    size_t *payload_length,
    size_t payload_capacity)
{
    (void)context;
    if (operation != 1u || *payload_length != 2u || payload_capacity < 2u) {
        return OEP_ROUTING_REJECTED_OPERATION;
    }
    payload[1] ^= 0xaau;
    return OEP_ROUTING_COMPLETED;
}

int main(void)
{
    static const struct oep_routing_target targets[] = {
        {0x1001u, first_handler, NULL},
        {0x9001u, second_handler, NULL},
    };

    message[1] ^= input_seed;
    message[4] ^= input_seed;
    sink = (uint8_t)oep_route_function_request(
        message,
        sizeof(message),
        sizeof(message),
        targets,
        sizeof(targets) / sizeof(targets[0]));
    return sink == 0u;
}
