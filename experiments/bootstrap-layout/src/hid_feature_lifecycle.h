#ifndef OEP_EXPERIMENT_HID_FEATURE_LIFECYCLE_H
#define OEP_EXPERIMENT_HID_FEATURE_LIFECYCLE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum oep_hid_feature_state {
    OEP_HID_FEATURE_IDLE = 0,
    OEP_HID_FEATURE_RECEIVING = 1,
    OEP_HID_FEATURE_RESPONSE_READY = 2,
    OEP_HID_FEATURE_SENDING = 3,
};

struct oep_hid_feature_lifecycle {
    uint8_t state;
};

void oep_hid_feature_lifecycle_init(
    struct oep_hid_feature_lifecycle *lifecycle);

bool oep_hid_feature_begin_set(
    struct oep_hid_feature_lifecycle *lifecycle,
    uint16_t requested_length,
    uint16_t report_length);

bool oep_hid_feature_finish_set(
    struct oep_hid_feature_lifecycle *lifecycle,
    bool response_valid);

bool oep_hid_feature_begin_get(
    struct oep_hid_feature_lifecycle *lifecycle,
    uint16_t requested_length,
    uint16_t report_length);

#ifdef __cplusplus
}
#endif

#endif
