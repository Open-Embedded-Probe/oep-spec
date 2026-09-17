#include "message_header_layout.h"

static uint16_t read_u16(const uint8_t *input)
{
    return (uint16_t)input[0] | ((uint16_t)input[1] << 8);
}

static bool role_is_known(uint8_t role)
{
    return role == OEP_HEADER_ROLE_FUNCTION_REQUEST ||
        role == OEP_HEADER_ROLE_RESULT ||
        role == OEP_HEADER_ROLE_ACTIVITY_UPDATE ||
        role == OEP_HEADER_ROLE_ACTIVITY_OUTCOME ||
        role == OEP_HEADER_ROLE_NOTIFICATION ||
        role == OEP_HEADER_ROLE_DATA;
}

bool oep_decode_uniform_header(
    const uint8_t *message,
    size_t message_length,
    struct oep_header_view *view)
{
    struct oep_header_view decoded = {0};

    if (message == NULL || view == NULL ||
        message_length < OEP_UNIFORM_HEADER_SIZE ||
        !role_is_known(message[0])) {
        return false;
    }

    decoded.role = message[0];
    decoded.detail = message[1];
    decoded.header_length = OEP_UNIFORM_HEADER_SIZE;

    switch (decoded.role) {
    case OEP_HEADER_ROLE_FUNCTION_REQUEST:
        decoded.scope = message[2];
        decoded.correlation = read_u16(message + 3u);
        decoded.reference = read_u16(message + 5u);
        decoded.present = OEP_HEADER_HAS_SCOPE |
            OEP_HEADER_HAS_CORRELATION | OEP_HEADER_HAS_REFERENCE;
        break;
    case OEP_HEADER_ROLE_RESULT:
        decoded.correlation = read_u16(message + 3u);
        decoded.present = OEP_HEADER_HAS_CORRELATION;
        break;
    case OEP_HEADER_ROLE_NOTIFICATION:
        decoded.scope = message[2];
        decoded.reference = read_u16(message + 5u);
        decoded.present = OEP_HEADER_HAS_SCOPE | OEP_HEADER_HAS_REFERENCE;
        break;
    default:
        decoded.reference = read_u16(message + 5u);
        decoded.present = OEP_HEADER_HAS_REFERENCE;
        break;
    }

    *view = decoded;
    return true;
}

bool oep_decode_role_header(
    const uint8_t *message,
    size_t message_length,
    struct oep_header_view *view)
{
    struct oep_header_view decoded = {0};

    if (message == NULL || view == NULL || message_length < 1u ||
        !role_is_known(message[0])) {
        return false;
    }

    decoded.role = message[0];
    switch (decoded.role) {
    case OEP_HEADER_ROLE_FUNCTION_REQUEST:
        if (message_length < OEP_ROLE_HEADER_REQUEST_SIZE) {
            return false;
        }
        decoded.detail = message[1];
        decoded.scope = OEP_HEADER_SCOPE_OFFERED_FUNCTION;
        decoded.correlation = read_u16(message + 2u);
        decoded.reference = read_u16(message + 4u);
        decoded.present = OEP_HEADER_HAS_SCOPE |
            OEP_HEADER_HAS_CORRELATION | OEP_HEADER_HAS_REFERENCE;
        decoded.header_length = OEP_ROLE_HEADER_REQUEST_SIZE;
        break;
    case OEP_HEADER_ROLE_RESULT:
        if (message_length < OEP_ROLE_HEADER_RESULT_SIZE) {
            return false;
        }
        decoded.detail = message[1];
        decoded.correlation = read_u16(message + 2u);
        decoded.present = OEP_HEADER_HAS_CORRELATION;
        decoded.header_length = OEP_ROLE_HEADER_RESULT_SIZE;
        break;
    case OEP_HEADER_ROLE_NOTIFICATION:
        if (message_length < OEP_ROLE_HEADER_NOTIFICATION_SIZE) {
            return false;
        }
        decoded.detail = message[1];
        decoded.scope = message[2];
        decoded.reference = read_u16(message + 3u);
        decoded.present = OEP_HEADER_HAS_SCOPE | OEP_HEADER_HAS_REFERENCE;
        decoded.header_length = OEP_ROLE_HEADER_NOTIFICATION_SIZE;
        break;
    default:
        if (message_length < OEP_ROLE_HEADER_ACTIVITY_SIZE) {
            return false;
        }
        decoded.detail = message[1];
        decoded.reference = read_u16(message + 2u);
        decoded.present = OEP_HEADER_HAS_REFERENCE;
        decoded.header_length = OEP_ROLE_HEADER_ACTIVITY_SIZE;
        break;
    }

    *view = decoded;
    return true;
}
