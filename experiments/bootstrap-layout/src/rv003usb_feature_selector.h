#ifndef OEP_EXPERIMENT_RV003USB_FEATURE_SELECTOR_H
#define OEP_EXPERIMENT_RV003USB_FEATURE_SELECTOR_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

bool oep_rv003usb_feature_selector_matches(
    uint32_t value_index,
    uint8_t report_id,
    uint16_t interface_number);

#ifdef __cplusplus
}
#endif

#endif
