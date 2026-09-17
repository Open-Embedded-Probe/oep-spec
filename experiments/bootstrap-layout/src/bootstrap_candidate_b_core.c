#include "bootstrap_candidate_b_core.h"

#include <string.h>

size_t oep_bootstrap_b_handle_core_message(
    uint8_t *message,
    size_t message_length,
    size_t message_capacity)
{
    uint8_t correlation_low;
    uint8_t correlation_high;
    uint8_t operation;
    uint8_t compatible;

    if (message == NULL || message_length != OEP_BOOTSTRAP_B_REQUEST_SIZE ||
        message_capacity < OEP_BOOTSTRAP_B_RESPONSE_SIZE ||
        message[0] != 0x01u ||
        message[4] != 0x4fu || message[5] != 0x45u ||
        message[6] != 0x50u || message[7] != 0x3fu) {
        return 0;
    }

    correlation_low = message[2];
    correlation_high = message[3];
    operation = message[1];
    compatible = operation == 0x01u &&
        message[8] <= 1u && message[9] >= 1u;

    memset(message, 0, OEP_BOOTSTRAP_B_RESPONSE_SIZE);
    message[0] = 0x81u;
    message[1] = operation;
    message[2] = correlation_low;
    message[3] = correlation_high;
    message[4] = 0x4fu;
    message[5] = 0x45u;
    message[6] = 0x50u;
    message[7] = 0x21u;
    message[8] = compatible ? OEP_BOOTSTRAP_B_STATUS_COMPATIBLE :
        (operation == 0x01u ? OEP_BOOTSTRAP_B_STATUS_INCOMPATIBLE :
            OEP_BOOTSTRAP_B_STATUS_UNSUPPORTED_OPERATION);
    message[9] = compatible ? 1u : 0u;
    message[10] = 0x00u;
    message[11] = 0x01u;
    message[12] = 0x01u;
    message[13] = 0x01u;
    return OEP_BOOTSTRAP_B_RESPONSE_SIZE;
}
