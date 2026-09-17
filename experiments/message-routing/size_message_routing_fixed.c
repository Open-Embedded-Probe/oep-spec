#include "message_routing.h"

static uint8_t message[8] = {
    OEP_ROUTING_ROLE_FUNCTION_REQUEST, 1u, 0x34u, 0x12u,
    0x01u, 0x10u, 0x12u, 0x34u,
};
static volatile uint8_t sink;
static volatile uint8_t input_seed;

static enum oep_routing_result first_handler(
    uint8_t operation,
    uint8_t *payload,
    size_t payload_length)
{
    if (operation != 1u || payload_length != 2u) {
        return OEP_ROUTING_REJECTED_OPERATION;
    }
    payload[0] ^= 0x55u;
    return OEP_ROUTING_COMPLETED;
}

static enum oep_routing_result second_handler(
    uint8_t operation,
    uint8_t *payload,
    size_t payload_length)
{
    if (operation != 1u || payload_length != 2u) {
        return OEP_ROUTING_REJECTED_OPERATION;
    }
    payload[1] ^= 0xaau;
    return OEP_ROUTING_COMPLETED;
}

static size_t route_fixed(
    uint8_t *request,
    size_t request_length,
    size_t request_capacity)
{
    uint8_t operation;
    uint8_t correlation_low;
    uint8_t correlation_high;
    uint16_t target;
    size_t payload_length;
    enum oep_routing_result result;

    if (request == NULL || request_length < OEP_ROUTING_HEADER_SIZE ||
        request_length > request_capacity ||
        request[0] != OEP_ROUTING_ROLE_FUNCTION_REQUEST) {
        return 0u;
    }
    operation = request[1];
    correlation_low = request[2];
    correlation_high = request[3];
    target = (uint16_t)request[4] | ((uint16_t)request[5] << 8);
    payload_length = request_length - OEP_ROUTING_HEADER_SIZE;

    switch (target) {
    case 0x1001u:
        result = first_handler(
            operation,
            request + OEP_ROUTING_HEADER_SIZE,
            payload_length);
        break;
    case 0x9001u:
        result = second_handler(
            operation,
            request + OEP_ROUTING_HEADER_SIZE,
            payload_length);
        break;
    default:
        result = OEP_ROUTING_REJECTED_TARGET;
        break;
    }

    if (result != OEP_ROUTING_COMPLETED) {
        payload_length = 0u;
    }
    request[0] = OEP_ROUTING_ROLE_RESULT;
    request[1] = (uint8_t)result;
    request[2] = correlation_low;
    request[3] = correlation_high;
    request[4] = (uint8_t)target;
    request[5] = (uint8_t)(target >> 8);
    return OEP_ROUTING_HEADER_SIZE + payload_length;
}

int main(void)
{
    message[1] ^= input_seed;
    message[4] ^= input_seed;
    sink = (uint8_t)route_fixed(message, sizeof(message), sizeof(message));
    return sink == 0u;
}
