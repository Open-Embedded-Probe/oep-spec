#include <Arduino.h>
#include <string.h>

#include <bootstrap_candidate_b.h>
#include <bootstrap_candidate_c.h>

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

void setup()
{
    Serial.begin(115200);
    delay(500);

    test_candidate_b();
    test_candidate_c();

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
