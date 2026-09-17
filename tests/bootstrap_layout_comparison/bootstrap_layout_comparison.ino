#include <Arduino.h>
#include <string.h>

#include <bootstrap_candidate_b.h>
#include <bootstrap_candidate_b_core.h>
#include <bootstrap_candidate_c.h>
#include <hid_feature_lifecycle.h>
#include <rv003usb_feature_selector.h>

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

static void prepare_b(uint8_t *report, uint8_t minimum, uint8_t maximum)
{
    memset(report, 0, OEP_BOOTSTRAP_B_REPORT_SIZE);
    report[0] = OEP_BOOTSTRAP_B_REPORT_ID;
    report[1] = 10u;
    report[2] = 0x01u;
    report[3] = 0x01u;
    report[4] = 0x34u;
    report[5] = 0x12u;
    report[6] = 0x4fu;
    report[7] = 0x45u;
    report[8] = 0x50u;
    report[9] = 0x3fu;
    report[10] = minimum;
    report[11] = maximum;
}

static void test_candidate_b()
{
    uint8_t report[OEP_BOOTSTRAP_B_REPORT_SIZE];

    prepare_b(report, 1u, 1u);
    check(
        oep_bootstrap_b_handle_report(report, sizeof(report)) ==
            sizeof(report) &&
            report[1] == 14u && report[2] == 0x81u &&
            report[4] == 0x34u && report[5] == 0x12u &&
            report[6] == 0x4fu && report[9] == 0x21u &&
            report[10] == 0u && report[11] == 1u &&
            report[12] == 0u && report[13] == 1u &&
            report[14] == 1u && report[15] == 1u,
        F("candidate B compatible"));

    prepare_b(report, 2u, 3u);
    check(
        oep_bootstrap_b_handle_report(report, sizeof(report)) ==
            sizeof(report) &&
            report[10] == 1u && report[11] == 0u,
        F("candidate B incompatible"));

    prepare_b(report, 1u, 1u);
    report[8] ^= 1u;
    check(
        oep_bootstrap_b_handle_report(report, sizeof(report)) == 0,
        F("candidate B marker rejection"));
    prepare_b(report, 1u, 1u);
    check(
        oep_bootstrap_b_handle_report(report, sizeof(report) - 1u) == 0,
        F("candidate B length rejection"));

    prepare_b(report, 1u, 1u);
    report[12] = 0xa5u;
    report[13] = 0x5au;
    report[14] = 0xffu;
    report[15] = 0x01u;
    check(
        oep_bootstrap_b_handle_report(report, sizeof(report)) ==
            sizeof(report),
        F("candidate B default ignores request padding"));
}

static void test_candidate_b_core_without_hid_wrapper()
{
    uint8_t message[OEP_BOOTSTRAP_B_RESPONSE_SIZE] = {
        0x01u, 0x01u, 0x78u, 0x56u,
        0x4fu, 0x45u, 0x50u, 0x3fu,
        0x01u, 0x01u,
    };

    check(
        oep_bootstrap_b_handle_core_message(
            message,
            OEP_BOOTSTRAP_B_REQUEST_SIZE,
            sizeof(message)) == OEP_BOOTSTRAP_B_RESPONSE_SIZE &&
            message[0] == 0x81u && message[1] == 0x01u &&
            message[2] == 0x78u && message[3] == 0x56u &&
            message[4] == 0x4fu && message[7] == 0x21u &&
            message[8] == 0u && message[9] == 1u &&
            message[10] == 0u && message[11] == 1u &&
            message[12] == 1u && message[13] == 1u,
        F("candidate B binding-independent core"));
}

static void test_candidate_b_unknown_operation_response()
{
    uint8_t message[OEP_BOOTSTRAP_B_RESPONSE_SIZE] = {
        0x01u, 0x7fu, 0xabu, 0xcdu,
        0x4fu, 0x45u, 0x50u, 0x3fu,
        0x01u, 0x01u,
    };

    check(
        oep_bootstrap_b_handle_core_message(
            message,
            OEP_BOOTSTRAP_B_REQUEST_SIZE,
            sizeof(message)) == OEP_BOOTSTRAP_B_RESPONSE_SIZE &&
            message[0] == 0x81u && message[1] == 0x7fu &&
            message[2] == 0xabu && message[3] == 0xcdu &&
            message[8] == OEP_BOOTSTRAP_B_STATUS_UNSUPPORTED_OPERATION &&
            message[9] == 0u,
        F("candidate B unknown operation response"));
}

static void test_candidate_b_role_and_operation_namespaces()
{
    bool all_roles_match = true;
    bool all_operations_match = true;

    for (uint16_t role = 0u; role <= 0xffu; ++role) {
        uint8_t message[OEP_BOOTSTRAP_B_RESPONSE_SIZE] = {
            static_cast<uint8_t>(role), 0x01u, 0xabu, 0xcdu,
            0x4fu, 0x45u, 0x50u, 0x3fu,
            0x01u, 0x01u,
        };
        uint8_t original[OEP_BOOTSTRAP_B_RESPONSE_SIZE];
        memcpy(original, message, sizeof(message));
        size_t result = oep_bootstrap_b_handle_core_message(
            message,
            OEP_BOOTSTRAP_B_REQUEST_SIZE,
            sizeof(message));

        if (role == 0x01u) {
            if (result != OEP_BOOTSTRAP_B_RESPONSE_SIZE ||
                message[0] != 0x81u) {
                all_roles_match = false;
            }
        } else if (result != 0u ||
                   memcmp(message, original, sizeof(message)) != 0) {
            all_roles_match = false;
        }
    }

    for (uint16_t operation = 0u; operation <= 0xffu; ++operation) {
        uint8_t message[OEP_BOOTSTRAP_B_RESPONSE_SIZE] = {
            0x01u, static_cast<uint8_t>(operation), 0xabu, 0xcdu,
            0x4fu, 0x45u, 0x50u, 0x3fu,
            0x01u, 0x01u,
        };
        size_t result = oep_bootstrap_b_handle_core_message(
            message,
            OEP_BOOTSTRAP_B_REQUEST_SIZE,
            sizeof(message));
        uint8_t expected_status = operation == 0x01u ?
            OEP_BOOTSTRAP_B_STATUS_COMPATIBLE :
            OEP_BOOTSTRAP_B_STATUS_UNSUPPORTED_OPERATION;

        if (result != OEP_BOOTSTRAP_B_RESPONSE_SIZE ||
            message[0] != 0x81u || message[1] != operation ||
            message[2] != 0xabu || message[3] != 0xcdu ||
            message[8] != expected_status) {
            all_operations_match = false;
        }
    }

    check(all_roles_match, F("candidate B all role values scoped"));
    check(
        all_operations_match,
        F("candidate B all operation values scoped by role"));
}

static void test_candidate_b_all_revision_ranges()
{
    bool valid = true;

    for (uint16_t minimum = 0; minimum <= 0xffu && valid; ++minimum) {
        for (uint16_t maximum = 0; maximum <= 0xffu; ++maximum) {
            uint8_t message[OEP_BOOTSTRAP_B_RESPONSE_SIZE] = {
                0x01u, 0x01u, 0xa5u, 0x5au,
                0x4fu, 0x45u, 0x50u, 0x3fu,
                static_cast<uint8_t>(minimum),
                static_cast<uint8_t>(maximum),
            };
            bool compatible = minimum <= 1u && maximum >= 1u;
            size_t response_length = oep_bootstrap_b_handle_core_message(
                message,
                OEP_BOOTSTRAP_B_REQUEST_SIZE,
                sizeof(message));

            if (response_length != OEP_BOOTSTRAP_B_RESPONSE_SIZE ||
                message[2] != 0xa5u || message[3] != 0x5au ||
                message[8] != (compatible ?
                    OEP_BOOTSTRAP_B_STATUS_COMPATIBLE :
                    OEP_BOOTSTRAP_B_STATUS_INCOMPATIBLE) ||
                message[9] != (compatible ? 1u : 0u)) {
                valid = false;
                break;
            }
        }
    }
    check(valid, F("candidate B all revision ranges"));
}

static void prepare_c(
    uint8_t *report,
    uint8_t operation,
    uint8_t minimum,
    uint8_t maximum)
{
    memset(report, 0, OEP_BOOTSTRAP_C_REPORT_SIZE);
    report[0] = OEP_BOOTSTRAP_C_REPORT_ID;
    report[1] = 0x4fu;
    report[2] = 0x45u;
    report[3] = 0x01u;
    report[4] = operation;
    report[5] = 0x5au;
    report[6] = minimum;
    report[7] = maximum;
}

static void test_candidate_c()
{
    uint8_t report[OEP_BOOTSTRAP_C_REPORT_SIZE];

    prepare_c(report, 0x01u, 1u, 1u);
    check(
        oep_bootstrap_c_handle_report(report, sizeof(report)) ==
            sizeof(report) &&
            report[1] == 0x4fu && report[2] == 0x45u &&
            report[4] == 0x81u && report[5] == 0x5au &&
            report[6] == 1u && report[7] == 0x08u && report[8] == 1u,
        F("candidate C compatible"));

    prepare_c(report, 0x01u, 2u, 3u);
    check(
        oep_bootstrap_c_handle_report(report, sizeof(report)) ==
            sizeof(report) &&
            report[4] == 0xc1u && report[6] == 0u,
        F("candidate C incompatible"));

    prepare_c(report, 0x02u, 0u, 0u);
    check(
        oep_bootstrap_c_handle_report(report, sizeof(report)) ==
            sizeof(report) &&
            report[4] == 0x82u && report[5] == 0x5au &&
            report[6] == 0u && report[7] == 1u && report[8] == 1u,
        F("candidate C exact limits"));

    prepare_c(report, 0x7fu, 0u, 0u);
    check(
        oep_bootstrap_c_handle_report(report, sizeof(report)) == 0,
        F("candidate C operation rejection"));
    prepare_c(report, 0x01u, 1u, 1u);
    report[1] ^= 1u;
    check(
        oep_bootstrap_c_handle_report(report, sizeof(report)) == 0,
        F("candidate C marker rejection"));
}

static void test_single_buffer_lifecycle()
{
    struct oep_hid_feature_lifecycle lifecycle;

    oep_hid_feature_lifecycle_init(&lifecycle);
    check(
        lifecycle.state == OEP_HID_FEATURE_IDLE &&
            !oep_hid_feature_begin_get(&lifecycle, 16u, 16u),
        F("lifecycle GET requires response"));
    check(
        oep_hid_feature_begin_set(&lifecycle, 16u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_RECEIVING,
        F("lifecycle SET starts receive"));
    check(
        oep_hid_feature_begin_set(&lifecycle, 16u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_RECEIVING,
        F("lifecycle new SET replaces interrupted receive"));
    check(
        oep_hid_feature_finish_set(&lifecycle, true) &&
            lifecycle.state == OEP_HID_FEATURE_RESPONSE_READY,
        F("lifecycle response ready"));
    check(
        !oep_hid_feature_begin_set(&lifecycle, 16u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_RESPONSE_READY,
        F("lifecycle pending response preserved"));
    check(
        !oep_hid_feature_begin_get(&lifecycle, 15u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_RESPONSE_READY,
        F("lifecycle wrong GET length preserved"));
    check(
        oep_hid_feature_begin_get(&lifecycle, 16u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_SENDING,
        F("lifecycle GET starts send"));
    check(
        oep_hid_feature_begin_set(&lifecycle, 16u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_RECEIVING,
        F("lifecycle next SET releases send"));
    check(
        !oep_hid_feature_finish_set(&lifecycle, false) &&
            lifecycle.state == OEP_HID_FEATURE_IDLE,
        F("lifecycle invalid request returns idle"));
    check(
        !oep_hid_feature_begin_set(&lifecycle, 9u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_IDLE,
        F("lifecycle wrong SET length rejected"));
}

enum lifecycle_operation {
    LIFECYCLE_BEGIN_SET_VALID,
    LIFECYCLE_BEGIN_SET_WRONG_LENGTH,
    LIFECYCLE_FINISH_SET_VALID,
    LIFECYCLE_FINISH_SET_INVALID,
    LIFECYCLE_BEGIN_GET_VALID,
    LIFECYCLE_BEGIN_GET_WRONG_LENGTH,
};

struct lifecycle_expectation {
    bool result;
    uint8_t state;
};

static bool apply_lifecycle_operation(
    struct oep_hid_feature_lifecycle *lifecycle,
    uint8_t operation)
{
    switch (operation) {
    case LIFECYCLE_BEGIN_SET_VALID:
        return oep_hid_feature_begin_set(lifecycle, 16u, 16u);
    case LIFECYCLE_BEGIN_SET_WRONG_LENGTH:
        return oep_hid_feature_begin_set(lifecycle, 15u, 16u);
    case LIFECYCLE_FINISH_SET_VALID:
        return oep_hid_feature_finish_set(lifecycle, true);
    case LIFECYCLE_FINISH_SET_INVALID:
        return oep_hid_feature_finish_set(lifecycle, false);
    case LIFECYCLE_BEGIN_GET_VALID:
        return oep_hid_feature_begin_get(lifecycle, 16u, 16u);
    case LIFECYCLE_BEGIN_GET_WRONG_LENGTH:
        return oep_hid_feature_begin_get(lifecycle, 15u, 16u);
    }
    return false;
}

static void test_lifecycle_transition_matrix()
{
    static const struct lifecycle_expectation expected[4][6] = {
        {
            {true, OEP_HID_FEATURE_RECEIVING},
            {false, OEP_HID_FEATURE_IDLE},
            {false, OEP_HID_FEATURE_IDLE},
            {false, OEP_HID_FEATURE_IDLE},
            {false, OEP_HID_FEATURE_IDLE},
            {false, OEP_HID_FEATURE_IDLE},
        },
        {
            {true, OEP_HID_FEATURE_RECEIVING},
            {false, OEP_HID_FEATURE_IDLE},
            {true, OEP_HID_FEATURE_RESPONSE_READY},
            {false, OEP_HID_FEATURE_IDLE},
            {false, OEP_HID_FEATURE_IDLE},
            {false, OEP_HID_FEATURE_IDLE},
        },
        {
            {false, OEP_HID_FEATURE_RESPONSE_READY},
            {false, OEP_HID_FEATURE_RESPONSE_READY},
            {false, OEP_HID_FEATURE_RESPONSE_READY},
            {false, OEP_HID_FEATURE_RESPONSE_READY},
            {true, OEP_HID_FEATURE_SENDING},
            {false, OEP_HID_FEATURE_RESPONSE_READY},
        },
        {
            {true, OEP_HID_FEATURE_RECEIVING},
            {false, OEP_HID_FEATURE_SENDING},
            {false, OEP_HID_FEATURE_SENDING},
            {false, OEP_HID_FEATURE_SENDING},
            {true, OEP_HID_FEATURE_SENDING},
            {false, OEP_HID_FEATURE_SENDING},
        },
    };
    bool all_transitions_match = true;

    for (uint8_t state = OEP_HID_FEATURE_IDLE;
         state <= OEP_HID_FEATURE_SENDING;
         ++state) {
        for (uint8_t operation = LIFECYCLE_BEGIN_SET_VALID;
             operation <= LIFECYCLE_BEGIN_GET_WRONG_LENGTH;
             ++operation) {
            struct oep_hid_feature_lifecycle lifecycle;
            lifecycle.state = state;
            bool result = apply_lifecycle_operation(
                &lifecycle,
                operation);
            const struct lifecycle_expectation *want =
                &expected[state][operation];

            if (result != want->result || lifecycle.state != want->state) {
                all_transitions_match = false;
            }
        }
    }
    check(
        all_transitions_match,
        F("lifecycle all state and operation combinations"));
}

static void test_lifecycle_reset_from_every_state()
{
    bool all_states_reset = true;

    for (uint8_t state = OEP_HID_FEATURE_IDLE;
         state <= OEP_HID_FEATURE_SENDING;
         ++state) {
        struct oep_hid_feature_lifecycle lifecycle;
        lifecycle.state = state;
        oep_hid_feature_lifecycle_reset(&lifecycle);
        if (lifecycle.state != OEP_HID_FEATURE_IDLE ||
            oep_hid_feature_begin_get(&lifecycle, 16u, 16u)) {
            all_states_reset = false;
        }
    }
    check(
        all_states_reset,
        F("lifecycle reset clears every state and pending response"));
}

static bool simulated_hid_set(
    struct oep_hid_feature_lifecycle *lifecycle,
    uint8_t *device_report,
    const uint8_t *request)
{
    if (!oep_hid_feature_begin_set(
            lifecycle,
            OEP_BOOTSTRAP_B_REPORT_SIZE,
            OEP_BOOTSTRAP_B_REPORT_SIZE)) {
        return false;
    }
    memcpy(device_report, request, OEP_BOOTSTRAP_B_REPORT_SIZE);
    bool response_valid = oep_bootstrap_b_handle_report(
        device_report,
        OEP_BOOTSTRAP_B_REPORT_SIZE) == OEP_BOOTSTRAP_B_REPORT_SIZE;
    return oep_hid_feature_finish_set(lifecycle, response_valid);
}

static bool simulated_hid_get(
    struct oep_hid_feature_lifecycle *lifecycle,
    uint8_t *response,
    const uint8_t *device_report)
{
    if (!oep_hid_feature_begin_get(
            lifecycle,
            OEP_BOOTSTRAP_B_REPORT_SIZE,
            OEP_BOOTSTRAP_B_REPORT_SIZE)) {
        return false;
    }
    memcpy(response, device_report, OEP_BOOTSTRAP_B_REPORT_SIZE);
    return true;
}

static void test_silent_busy_recovery_by_correlation()
{
    struct oep_hid_feature_lifecycle lifecycle;
    uint8_t device_report[OEP_BOOTSTRAP_B_REPORT_SIZE];
    uint8_t first_request[OEP_BOOTSTRAP_B_REPORT_SIZE];
    uint8_t second_request[OEP_BOOTSTRAP_B_REPORT_SIZE];
    uint8_t response[OEP_BOOTSTRAP_B_REPORT_SIZE];

    oep_hid_feature_lifecycle_init(&lifecycle);
    prepare_b(first_request, 1u, 1u);
    first_request[4] = 0x11u;
    first_request[5] = 0x11u;
    prepare_b(second_request, 1u, 1u);
    second_request[4] = 0x22u;
    second_request[5] = 0x22u;

    bool first_accepted = simulated_hid_set(
        &lifecycle,
        device_report,
        first_request);
    bool second_busy = !simulated_hid_set(
        &lifecycle,
        device_report,
        second_request);
    bool first_received = simulated_hid_get(
        &lifecycle,
        response,
        device_report) &&
        response[4] == 0x11u && response[5] == 0x11u;
    bool second_retried = simulated_hid_set(
        &lifecycle,
        device_report,
        second_request) &&
        simulated_hid_get(&lifecycle, response, device_report) &&
        response[4] == 0x22u && response[5] == 0x22u;

    check(
        first_accepted && second_busy && first_received && second_retried,
        F("silent busy recovered by correlation and retry"));
}

static void test_get_report_retry_keeps_response()
{
    struct oep_hid_feature_lifecycle lifecycle;
    uint8_t device_report[OEP_BOOTSTRAP_B_REPORT_SIZE];
    uint8_t request[OEP_BOOTSTRAP_B_REPORT_SIZE];
    uint8_t first_response[OEP_BOOTSTRAP_B_REPORT_SIZE];
    uint8_t retried_response[OEP_BOOTSTRAP_B_REPORT_SIZE];

    oep_hid_feature_lifecycle_init(&lifecycle);
    prepare_b(request, 1u, 1u);
    request[4] = 0x5au;
    request[5] = 0xa5u;

    bool request_accepted = simulated_hid_set(
        &lifecycle,
        device_report,
        request);
    bool first_get = simulated_hid_get(
        &lifecycle,
        first_response,
        device_report);
    bool wrong_length_preserved =
        !oep_hid_feature_begin_get(
            &lifecycle,
            OEP_BOOTSTRAP_B_REPORT_SIZE - 1u,
            OEP_BOOTSTRAP_B_REPORT_SIZE) &&
        lifecycle.state == OEP_HID_FEATURE_SENDING;
    bool retry_get = simulated_hid_get(
        &lifecycle,
        retried_response,
        device_report);

    check(
        request_accepted && first_get && wrong_length_preserved &&
            retry_get &&
            memcmp(
                first_response,
                retried_response,
                OEP_BOOTSTRAP_B_REPORT_SIZE) == 0 &&
            retried_response[4] == 0x5au &&
            retried_response[5] == 0xa5u,
        F("GET retry returns cached correlated response"));
}

static void test_rv003usb_feature_selector()
{
    check(
        oep_rv003usb_feature_selector_matches(0x00000301u, 1u, 0u),
        F("rv003usb feature selector accepted"));
    check(
        !oep_rv003usb_feature_selector_matches(0x00000101u, 1u, 0u) &&
            !oep_rv003usb_feature_selector_matches(
                0x00000201u,
                1u,
                0u),
        F("rv003usb non-feature report types rejected"));
    check(
        !oep_rv003usb_feature_selector_matches(0x00000302u, 1u, 0u),
        F("rv003usb other report ID rejected"));
    check(
        !oep_rv003usb_feature_selector_matches(0x00010301u, 1u, 0u) &&
            !oep_rv003usb_feature_selector_matches(
                0x01000301u,
                1u,
                0u),
        F("rv003usb other interface rejected"));
}

static uint8_t rv003usb_forwarded_out_bytes(uint8_t report_length)
{
    uint8_t forwarded = 0;

    while (report_length != 0) {
        uint8_t packet = report_length > 8u ? 8u : report_length;
        if (packet > 3u) {
            forwarded = static_cast<uint8_t>(forwarded + packet);
        }
        report_length = static_cast<uint8_t>(report_length - packet);
    }
    return forwarded;
}

static void test_rv003usb_short_final_packet_characterization()
{
    bool all_lengths_match = true;

    check(
        rv003usb_forwarded_out_bytes(16u) == 16u,
        F("rv003usb 16-byte report fully forwarded"));
    check(
        rv003usb_forwarded_out_bytes(9u) == 8u,
        F("rv003usb 9-byte report loses final byte"));
    check(
        rv003usb_forwarded_out_bytes(12u) == 12u,
        F("rv003usb padded 12-byte report fully forwarded"));

    for (uint8_t length = 1u; length <= 64u; ++length) {
        uint8_t remainder = length & 7u;
        bool expected_complete = remainder == 0u || remainder >= 4u;
        bool complete = rv003usb_forwarded_out_bytes(length) == length;

        if (complete != expected_complete) {
            all_lengths_match = false;
            break;
        }
    }
    check(
        all_lengths_match,
        F("rv003usb report lengths 1 through 64 characterized"));
}

void setup()
{
    Serial.begin(115200);
    delay(500);

    test_candidate_b();
    test_candidate_b_core_without_hid_wrapper();
    test_candidate_b_unknown_operation_response();
    test_candidate_b_role_and_operation_namespaces();
    test_candidate_b_all_revision_ranges();
    test_candidate_c();
    test_single_buffer_lifecycle();
    test_lifecycle_transition_matrix();
    test_lifecycle_reset_from_every_state();
    test_silent_busy_recovery_by_correlation();
    test_get_report_retry_keeps_response();
    test_rv003usb_feature_selector();
    test_rv003usb_short_final_packet_characterization();

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
