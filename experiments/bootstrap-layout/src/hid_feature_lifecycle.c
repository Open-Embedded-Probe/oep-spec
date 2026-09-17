#include "hid_feature_lifecycle.h"

void oep_hid_feature_lifecycle_init(
    struct oep_hid_feature_lifecycle *lifecycle)
{
    lifecycle->state = OEP_HID_FEATURE_IDLE;
}

static void release_previous_get(
    struct oep_hid_feature_lifecycle *lifecycle)
{
    if (lifecycle->state == OEP_HID_FEATURE_SENDING) {
        lifecycle->state = OEP_HID_FEATURE_IDLE;
    }
}

bool oep_hid_feature_begin_set(
    struct oep_hid_feature_lifecycle *lifecycle,
    uint16_t requested_length,
    uint16_t report_length)
{
    release_previous_get(lifecycle);
    if (lifecycle->state != OEP_HID_FEATURE_IDLE ||
        requested_length != report_length) {
        return false;
    }
    lifecycle->state = OEP_HID_FEATURE_RECEIVING;
    return true;
}

bool oep_hid_feature_finish_set(
    struct oep_hid_feature_lifecycle *lifecycle,
    bool response_valid)
{
    if (lifecycle->state != OEP_HID_FEATURE_RECEIVING) {
        return false;
    }
    lifecycle->state = response_valid ?
        OEP_HID_FEATURE_RESPONSE_READY : OEP_HID_FEATURE_IDLE;
    return response_valid;
}

bool oep_hid_feature_begin_get(
    struct oep_hid_feature_lifecycle *lifecycle,
    uint16_t requested_length,
    uint16_t report_length)
{
    release_previous_get(lifecycle);
    if (lifecycle->state != OEP_HID_FEATURE_RESPONSE_READY ||
        requested_length != report_length) {
        return false;
    }
    lifecycle->state = OEP_HID_FEATURE_SENDING;
    return true;
}
