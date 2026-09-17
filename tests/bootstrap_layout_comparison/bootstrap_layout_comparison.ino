#include <Arduino.h>
#include <string.h>

#include <bootstrap_candidate_b.h>
#include <bootstrap_candidate_b_core.h>
#include <bootstrap_candidate_c.h>
#include <hid_feature_lifecycle.h>

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
        !oep_hid_feature_begin_set(&lifecycle, 16u, 16u) &&
            lifecycle.state == OEP_HID_FEATURE_RECEIVING,
        F("lifecycle nested SET rejected"));
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
    test_candidate_b_all_revision_ranges();
    test_candidate_c();
    test_single_buffer_lifecycle();
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
