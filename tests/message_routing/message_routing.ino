#include <Arduino.h>
#include <string.h>

#include <message_header_layout.h>
#include <message_routing.h>
#include <request_correlation.h>

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

static bool header_role_is_known(uint8_t role)
{
    return role == OEP_HEADER_ROLE_FUNCTION_REQUEST ||
        role == OEP_HEADER_ROLE_RESULT ||
        role == OEP_HEADER_ROLE_ACTIVITY_UPDATE ||
        role == OEP_HEADER_ROLE_ACTIVITY_OUTCOME ||
        role == OEP_HEADER_ROLE_NOTIFICATION ||
        role == OEP_HEADER_ROLE_DATA;
}

static size_t role_header_size(uint8_t role)
{
    switch (role) {
    case OEP_HEADER_ROLE_FUNCTION_REQUEST:
        return OEP_ROLE_HEADER_REQUEST_SIZE;
    case OEP_HEADER_ROLE_RESULT:
        return OEP_ROLE_HEADER_RESULT_SIZE;
    case OEP_HEADER_ROLE_NOTIFICATION:
        return OEP_ROLE_HEADER_NOTIFICATION_SIZE;
    default:
        return OEP_ROLE_HEADER_ACTIVITY_SIZE;
    }
}

static void test_header_layout_semantics()
{
    const uint8_t uniform_request[OEP_UNIFORM_HEADER_SIZE] = {
        OEP_HEADER_ROLE_FUNCTION_REQUEST, 0x44u,
        OEP_HEADER_SCOPE_OFFERED_FUNCTION, 0x34u, 0x12u, 0x78u, 0x56u,
    };
    const uint8_t role_request[OEP_ROLE_HEADER_REQUEST_SIZE] = {
        OEP_HEADER_ROLE_FUNCTION_REQUEST, 0x44u,
        0x34u, 0x12u, 0x78u, 0x56u,
    };
    const uint8_t role_result[OEP_ROLE_HEADER_RESULT_SIZE] = {
        OEP_HEADER_ROLE_RESULT, 0x02u, 0x34u, 0x12u,
    };
    const uint8_t role_activity[OEP_ROLE_HEADER_ACTIVITY_SIZE] = {
        OEP_HEADER_ROLE_ACTIVITY_OUTCOME, 0x03u, 0x78u, 0x56u,
    };
    const uint8_t role_notification[OEP_ROLE_HEADER_NOTIFICATION_SIZE] = {
        OEP_HEADER_ROLE_NOTIFICATION, 0x04u, 0x09u, 0x78u, 0x56u,
    };
    struct oep_header_view view;

    bool uniform_ok = oep_decode_uniform_header(
        uniform_request, sizeof(uniform_request), &view) &&
        view.role == OEP_HEADER_ROLE_FUNCTION_REQUEST &&
        view.detail == 0x44u &&
        view.scope == OEP_HEADER_SCOPE_OFFERED_FUNCTION &&
        view.correlation == 0x1234u && view.reference == 0x5678u &&
        view.present == (OEP_HEADER_HAS_SCOPE |
            OEP_HEADER_HAS_CORRELATION | OEP_HEADER_HAS_REFERENCE) &&
        view.header_length == OEP_UNIFORM_HEADER_SIZE;
    check(uniform_ok, F("uniform header exposes request semantics"));

    bool request_ok = oep_decode_role_header(
        role_request, sizeof(role_request), &view) &&
        view.scope == OEP_HEADER_SCOPE_OFFERED_FUNCTION &&
        view.correlation == 0x1234u && view.reference == 0x5678u &&
        view.header_length == OEP_ROLE_HEADER_REQUEST_SIZE;
    bool result_ok = oep_decode_role_header(
        role_result, sizeof(role_result), &view) &&
        view.correlation == 0x1234u && view.reference == 0u &&
        view.present == OEP_HEADER_HAS_CORRELATION &&
        view.header_length == OEP_ROLE_HEADER_RESULT_SIZE;
    bool activity_ok = oep_decode_role_header(
        role_activity, sizeof(role_activity), &view) &&
        view.correlation == 0u && view.reference == 0x5678u &&
        view.present == OEP_HEADER_HAS_REFERENCE &&
        view.header_length == OEP_ROLE_HEADER_ACTIVITY_SIZE;
    bool notification_ok = oep_decode_role_header(
        role_notification, sizeof(role_notification), &view) &&
        view.scope == 0x09u && view.reference == 0x5678u &&
        view.present == (OEP_HEADER_HAS_SCOPE | OEP_HEADER_HAS_REFERENCE) &&
        view.header_length == OEP_ROLE_HEADER_NOTIFICATION_SIZE;
    check(
        request_ok && result_ok && activity_ok && notification_ok,
        F("role headers expose only role-required routing"));
}

static void test_all_header_roles_and_lengths()
{
    bool uniform_boundaries_ok = true;
    bool role_boundaries_ok = true;

    for (uint16_t role_value = 0u; role_value <= 0xffu; ++role_value) {
        uint8_t role = static_cast<uint8_t>(role_value);
        for (uint8_t length = 0u; length <= OEP_UNIFORM_HEADER_SIZE; ++length) {
            uint8_t guarded[OEP_UNIFORM_HEADER_SIZE + 2u] = {
                0xa5u, role, 0x44u, 0x09u, 0x34u,
                0x12u, 0x78u, 0x56u, 0x5au,
            };
            struct oep_header_view view;
            struct oep_header_view original;
            memset(&view, 0xa5, sizeof(view));
            original = view;
            bool decoded = oep_decode_uniform_header(
                guarded + 1u, length, &view);
            bool expected = header_role_is_known(role) &&
                length >= OEP_UNIFORM_HEADER_SIZE;
            if (decoded != expected || guarded[0] != 0xa5u ||
                guarded[OEP_UNIFORM_HEADER_SIZE + 1u] != 0x5au ||
                (!decoded && memcmp(&view, &original, sizeof(view)) != 0)) {
                uniform_boundaries_ok = false;
            }

            memset(&view, 0xa5, sizeof(view));
            original = view;
            decoded = oep_decode_role_header(guarded + 1u, length, &view);
            expected = header_role_is_known(role) &&
                length >= role_header_size(role);
            if (decoded != expected || guarded[0] != 0xa5u ||
                guarded[OEP_UNIFORM_HEADER_SIZE + 1u] != 0x5au ||
                (!decoded && memcmp(&view, &original, sizeof(view)) != 0)) {
                role_boundaries_ok = false;
            }
        }
    }

    check(
        uniform_boundaries_ok,
        F("uniform header guards all roles and short lengths"));
    check(
        role_boundaries_ok,
        F("role header guards all roles and short lengths"));
}

static void test_request_correlation_lifecycle()
{
    struct oep_pending_request slots[2];
    struct oep_request_context context;
    struct oep_request_context unchanged;
    memset(&context, 0xa5, sizeof(context));
    unchanged = context;
    oep_pending_reset(slots, 2u);

    bool opened = oep_pending_open(
        slots, 2u, 0x1234u, 0x1001u, 0x44u) == OEP_CORRELATION_OK;
    bool unknown = oep_pending_resolve(
        slots, 2u, 0x9999u, OEP_REQUEST_COMPLETED, 0u, &context) ==
            OEP_CORRELATION_UNKNOWN &&
        memcmp(&context, &unchanged, sizeof(context)) == 0;
    bool resolved = oep_pending_resolve(
        slots, 2u, 0x1234u, OEP_REQUEST_COMPLETED, 0u, &context) ==
            OEP_CORRELATION_OK &&
        context.target_reference == 0x1001u &&
        context.operation == 0x44u &&
        context.resolution == OEP_REQUEST_COMPLETED &&
        context.activity_reference == 0u;
    bool duplicate = oep_pending_resolve(
        slots, 2u, 0x1234u, OEP_REQUEST_COMPLETED, 0u, &context) ==
            OEP_CORRELATION_DUPLICATE;
    bool conflict = oep_pending_resolve(
        slots, 2u, 0x1234u, OEP_REQUEST_REJECTED, 0u, &context) ==
            OEP_CORRELATION_CONFLICT;
    bool reuse_blocked = oep_pending_open(
        slots, 2u, 0x1234u, 0x9001u, 0x55u) == OEP_CORRELATION_BUSY;
    bool retired = oep_pending_retire(slots, 2u, 0x1234u) ==
        OEP_CORRELATION_OK;
    bool reused = oep_pending_open(
        slots, 2u, 0x1234u, 0x9001u, 0x55u) == OEP_CORRELATION_OK;

    check(
        opened && unknown && resolved && duplicate && conflict &&
            reuse_blocked && retired && reused,
        F("correlation lifecycle rejects guessing and early reuse"));

    oep_pending_reset(slots, 2u);
    bool first = oep_pending_open(
        slots, 2u, 0x1111u, 0x1001u, 0x01u) == OEP_CORRELATION_OK;
    bool second = oep_pending_open(
        slots, 2u, 0x2222u, 0x9001u, 0x02u) == OEP_CORRELATION_OK;
    bool full = oep_pending_open(
        slots, 2u, 0x3333u, 0x7777u, 0x03u) == OEP_CORRELATION_FULL;
    bool accepted = oep_pending_resolve(
        slots, 2u, 0x2222u, OEP_REQUEST_ACCEPTED, 0x4567u, &context) ==
            OEP_CORRELATION_OK &&
        context.target_reference == 0x9001u &&
        context.operation == 0x02u &&
        context.activity_reference == 0x4567u;
    bool other_pending = slots[0].state == OEP_PENDING_WAITING &&
        slots[0].correlation == 0x1111u;
    check(
        first && second && full && accepted && other_pending,
        F("accepted result transfers matching request context"));
}

static void test_all_correlation_values()
{
    struct oep_pending_request slot;
    struct oep_request_context context;
    bool all_match = true;

    for (uint32_t correlation = 0u; correlation <= 0xffffu; ++correlation) {
        oep_pending_reset(&slot, 1u);
        if (oep_pending_open(
                &slot, 1u, static_cast<uint16_t>(correlation),
                0x1001u, 0x44u) != OEP_CORRELATION_OK ||
            oep_pending_resolve(
                &slot, 1u, static_cast<uint16_t>(correlation),
                OEP_REQUEST_COMPLETED, 0u, &context) != OEP_CORRELATION_OK ||
            context.target_reference != 0x1001u ||
            context.operation != 0x44u ||
            oep_pending_retire(
                &slot, 1u, static_cast<uint16_t>(correlation)) !=
                    OEP_CORRELATION_OK) {
            all_match = false;
            break;
        }
    }
    check(all_match, F("all correlation values match pending request"));
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
    test_header_layout_semantics();
    test_all_header_roles_and_lengths();
    test_request_correlation_lifecycle();
    test_all_correlation_values();

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
