#include "message_routing.h"

bool oep_routing_table_is_valid(
    const struct oep_routing_target *targets,
    size_t target_count)
{
    size_t outer;
    size_t inner;

    if (target_count != 0u && targets == NULL) {
        return false;
    }
    for (outer = 0u; outer < target_count; ++outer) {
        if (targets[outer].handler == NULL) {
            return false;
        }
        for (inner = outer + 1u; inner < target_count; ++inner) {
            if (targets[outer].offered_function_reference ==
                targets[inner].offered_function_reference) {
                return false;
            }
        }
    }
    return true;
}

size_t oep_route_function_request(
    uint8_t *message,
    size_t message_length,
    size_t message_capacity,
    const struct oep_routing_target *targets,
    size_t target_count)
{
    uint8_t operation;
    uint8_t correlation_low;
    uint8_t correlation_high;
    uint16_t target_reference;
    enum oep_routing_result result = OEP_ROUTING_REJECTED_TARGET;
    size_t payload_length;
    size_t index;

    if (message == NULL || message_length < OEP_ROUTING_HEADER_SIZE ||
        message_length > message_capacity ||
        message_capacity < OEP_ROUTING_HEADER_SIZE ||
        message[0] != OEP_ROUTING_ROLE_FUNCTION_REQUEST ||
        !oep_routing_table_is_valid(targets, target_count)) {
        return 0u;
    }

    operation = message[1];
    correlation_low = message[2];
    correlation_high = message[3];
    target_reference = (uint16_t)message[4] |
        ((uint16_t)message[5] << 8);
    payload_length = message_length - OEP_ROUTING_HEADER_SIZE;

    for (index = 0u; index < target_count; ++index) {
        if (targets[index].offered_function_reference == target_reference) {
            result = targets[index].handler(
                targets[index].context,
                operation,
                message + OEP_ROUTING_HEADER_SIZE,
                &payload_length,
                message_capacity - OEP_ROUTING_HEADER_SIZE);
            break;
        }
    }

    if (result != OEP_ROUTING_COMPLETED) {
        payload_length = 0u;
    }
    if (payload_length > message_capacity - OEP_ROUTING_HEADER_SIZE) {
        return 0u;
    }

    message[0] = OEP_ROUTING_ROLE_RESULT;
    message[1] = (uint8_t)result;
    message[2] = correlation_low;
    message[3] = correlation_high;
    message[4] = (uint8_t)target_reference;
    message[5] = (uint8_t)(target_reference >> 8);
    return OEP_ROUTING_HEADER_SIZE + payload_length;
}
