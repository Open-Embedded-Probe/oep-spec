#include <Arduino.h>
#include <string.h>

#include <message_routing.h>

static unsigned int test_total;
static unsigned int test_passed;

static void check(bool condition, const __FlashStringHelper *name)
{
    ++test_total;
    if (condition) {
        ++test_passed;
        return;
    }
    Serial.print(F("FAIL "));
    Serial.println(name);
}

static enum oep_routing_result standard_handler(
    void *context,
    uint8_t operation,
    uint8_t *payload,
    size_t *payload_length,
    size_t payload_capacity)
{
    (void)context;
    if (operation != 1u) {
        return OEP_ROUTING_REJECTED_OPERATION;
    }
    if (*payload_length != 2u || payload_capacity < 2u) {
        return OEP_ROUTING_REJECTED_PAYLOAD;
    }
    uint8_t first = payload[0];
    payload[0] = payload[1];
    payload[1] = first;
    return OEP_ROUTING_COMPLETED;
}

static enum oep_routing_result private_handler(
    void *context,
    uint8_t operation,
    uint8_t *payload,
    size_t *payload_length,
    size_t payload_capacity)
{
    (void)context;
    if (operation != 1u) {
        return OEP_ROUTING_REJECTED_OPERATION;
    }
    if (*payload_length != 2u || payload_capacity < 2u) {
        return OEP_ROUTING_REJECTED_PAYLOAD;
    }
    payload[0] ^= 0xffu;
    payload[1] ^= 0xffu;
    return OEP_ROUTING_COMPLETED;
}

static void prepare_request(
    uint8_t *message,
    uint16_t correlation,
    uint16_t target,
    uint8_t operation)
{
    message[0] = OEP_ROUTING_ROLE_FUNCTION_REQUEST;
    message[1] = operation;
    message[2] = (uint8_t)correlation;
    message[3] = (uint8_t)(correlation >> 8);
    message[4] = (uint8_t)target;
    message[5] = (uint8_t)(target >> 8);
    message[6] = 0x12u;
    message[7] = 0x34u;
}

static void test_definition_scoped_operations()
{
    const struct oep_routing_target targets[] = {
        {0x1001u, standard_handler, NULL},
        {0x9001u, private_handler, NULL},
    };
    uint8_t standard[8];
    uint8_t private_message[8];

    prepare_request(standard, 0x1234u, 0x1001u, 1u);
    prepare_request(private_message, 0x5678u, 0x9001u, 1u);
    size_t standard_length = oep_route_function_request(
        standard, sizeof(standard), sizeof(standard),
        targets, sizeof(targets) / sizeof(targets[0]));
    size_t private_length = oep_route_function_request(
        private_message, sizeof(private_message), sizeof(private_message),
        targets, sizeof(targets) / sizeof(targets[0]));

    check(
        standard_length == sizeof(standard) &&
            standard[0] == OEP_ROUTING_ROLE_RESULT &&
            standard[1] == OEP_ROUTING_COMPLETED &&
            standard[2] == 0x34u && standard[3] == 0x12u &&
            standard[4] == 0x01u && standard[5] == 0x10u &&
            standard[6] == 0x34u && standard[7] == 0x12u,
        F("standard function routed by offered reference"));
    check(
        private_length == sizeof(private_message) &&
            private_message[0] == OEP_ROUTING_ROLE_RESULT &&
            private_message[1] == OEP_ROUTING_COMPLETED &&
            private_message[2] == 0x78u && private_message[3] == 0x56u &&
            private_message[4] == 0x01u && private_message[5] == 0x90u &&
            private_message[6] == 0xedu && private_message[7] == 0xcbu,
        F("private function payload remains handler-specific"));
}

static void test_routing_rejections()
{
    const struct oep_routing_target targets[] = {
        {0x1001u, standard_handler, NULL},
    };
    uint8_t message[8];

    prepare_request(message, 0xabcdu, 0x7777u, 1u);
    size_t length = oep_route_function_request(
        message, sizeof(message), sizeof(message), targets, 1u);
    check(
        length == OEP_ROUTING_HEADER_SIZE &&
            message[1] == OEP_ROUTING_REJECTED_TARGET &&
            message[2] == 0xcdu && message[3] == 0xabu &&
            message[4] == 0x77u && message[5] == 0x77u,
        F("unknown offered function rejected in request scope"));

    prepare_request(message, 0x2468u, 0x1001u, 0x7fu);
    length = oep_route_function_request(
        message, sizeof(message), sizeof(message), targets, 1u);
    check(
        length == OEP_ROUTING_HEADER_SIZE &&
            message[1] == OEP_ROUTING_REJECTED_OPERATION &&
            message[2] == 0x68u && message[3] == 0x24u,
        F("unknown definition-scoped operation rejected"));

    prepare_request(message, 0x1357u, 0x1001u, 1u);
    length = oep_route_function_request(
        message, OEP_ROUTING_HEADER_SIZE + 1u, sizeof(message), targets, 1u);
    check(
        length == OEP_ROUTING_HEADER_SIZE &&
            message[1] == OEP_ROUTING_REJECTED_PAYLOAD,
        F("handler-specific payload rejection preserved"));
}

static void test_invalid_common_routing()
{
    const struct oep_routing_target targets[] = {
        {0x1001u, standard_handler, NULL},
    };
    const struct oep_routing_target duplicate[] = {
        {0x1001u, standard_handler, NULL},
        {0x1001u, private_handler, NULL},
    };
    const struct oep_routing_target missing_handler[] = {
        {0x1001u, NULL, NULL},
    };
    uint8_t message[8];
    uint8_t original[8];

    prepare_request(message, 0x1234u, 0x1001u, 1u);
    message[0] = 0xffu;
    memcpy(original, message, sizeof(message));
    check(
        oep_route_function_request(
            message, sizeof(message), sizeof(message), targets, 1u) == 0u &&
            memcmp(message, original, sizeof(message)) == 0,
        F("unknown role not interpreted as function request"));

    prepare_request(message, 0x1234u, 0x1001u, 1u);
    memcpy(original, message, sizeof(message));
    check(
        oep_route_function_request(
            message, OEP_ROUTING_HEADER_SIZE - 1u,
            sizeof(message), targets, 1u) == 0u &&
            memcmp(message, original, sizeof(message)) == 0,
        F("short routing header not interpreted"));

    check(
        oep_routing_table_is_valid(targets, 1u) &&
            !oep_routing_table_is_valid(duplicate, 2u) &&
            !oep_routing_table_is_valid(missing_handler, 1u) &&
            !oep_routing_table_is_valid(NULL, 1u),
        F("offered function routing table validated"));
}

static void test_all_target_and_correlation_values()
{
    const struct oep_routing_target targets[] = {
        {0x1001u, standard_handler, NULL},
        {0x9001u, private_handler, NULL},
    };
    bool all_targets_match = true;
    bool all_correlations_match = true;

    for (uint32_t target = 0u; target <= 0xffffu; ++target) {
        uint8_t message[8];
        prepare_request(
            message,
            0xa55au,
            static_cast<uint16_t>(target),
            1u);
        size_t length = oep_route_function_request(
            message, sizeof(message), sizeof(message), targets, 2u);
        bool known = target == 0x1001u || target == 0x9001u;
        if (length != (known ? sizeof(message) : OEP_ROUTING_HEADER_SIZE) ||
            message[1] != (known ? OEP_ROUTING_COMPLETED :
                                   OEP_ROUTING_REJECTED_TARGET) ||
            message[2] != 0x5au || message[3] != 0xa5u ||
            message[4] != (uint8_t)target ||
            message[5] != (uint8_t)(target >> 8)) {
            all_targets_match = false;
            break;
        }
    }

    for (uint32_t correlation = 0u;
         correlation <= 0xffffu;
         ++correlation) {
        uint8_t message[8];
        prepare_request(
            message,
            static_cast<uint16_t>(correlation),
            0x7777u,
            1u);
        size_t length = oep_route_function_request(
            message, sizeof(message), sizeof(message), targets, 2u);
        if (length != OEP_ROUTING_HEADER_SIZE ||
            message[2] != (uint8_t)correlation ||
            message[3] != (uint8_t)(correlation >> 8)) {
            all_correlations_match = false;
            break;
        }
    }

    check(all_targets_match, F("all offered function references scoped"));
    check(all_correlations_match, F("all request correlations preserved"));
}

static void test_routing_buffer_boundaries()
{
    const struct oep_routing_target targets[] = {
        {0x1001u, standard_handler, NULL},
    };
    bool all_lengths_guarded = true;

    for (uint8_t length = 0u; length <= 8u; ++length) {
        uint8_t guarded[10];
        memset(guarded, 0, sizeof(guarded));
        guarded[0] = 0xa5u;
        guarded[9] = 0x5au;
        prepare_request(guarded + 1, 0x1234u, 0x1001u, 1u);
        size_t result = oep_route_function_request(
            guarded + 1,
            length,
            8u,
            targets,
            1u);
        bool should_respond = length >= OEP_ROUTING_HEADER_SIZE;
        if ((result != 0u) != should_respond ||
            guarded[0] != 0xa5u || guarded[9] != 0x5au) {
            all_lengths_guarded = false;
        }
    }
    check(all_lengths_guarded, F("routing length boundaries guarded"));
}

void setup()
{
    Serial.begin(115200);
    delay(500);

    test_definition_scoped_operations();
    test_routing_rejections();
    test_invalid_common_routing();
    test_all_target_and_correlation_values();
    test_routing_buffer_boundaries();

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
