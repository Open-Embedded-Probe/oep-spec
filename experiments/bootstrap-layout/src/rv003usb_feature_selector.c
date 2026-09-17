#include "rv003usb_feature_selector.h"

bool oep_rv003usb_feature_selector_matches(
    uint32_t value_index,
    uint8_t report_id,
    uint16_t interface_number)
{
    uint32_t expected = (uint32_t)report_id |
        (3u << 8) |
        ((uint32_t)interface_number << 16);
    return value_index == expected;
}
