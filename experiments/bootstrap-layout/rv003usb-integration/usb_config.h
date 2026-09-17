#ifndef OEP_BOOTSTRAP_RV003USB_CONFIG_H
#define OEP_BOOTSTRAP_RV003USB_CONFIG_H

#define ENDPOINTS 2
#define USB_PORT D
#define USB_PIN_DP 3
#define USB_PIN_DM 4
#define USB_PIN_DPU 5

#define RV003USB_DEBUG_TIMING 0
#define RV003USB_OPTIMIZE_FLASH 1
#define RV003USB_EVENT_DEBUGGING 0
#define RV003USB_HANDLE_IN_REQUEST 1
#define RV003USB_OTHER_CONTROL 0
#define RV003USB_HANDLE_USER_DATA 1
#define RV003USB_HID_FEATURES 1

#ifndef __ASSEMBLER__

#include <tinyusb_hid.h>

#ifdef INSTANCE_DESCRIPTORS

#if defined(OEP_BOOTSTRAP_LAYOUT_B)
#define OEP_HID_REPORT_COUNT 15
#elif defined(OEP_BOOTSTRAP_LAYOUT_C)
#define OEP_HID_REPORT_COUNT 8
#else
#error Select OEP_BOOTSTRAP_LAYOUT_B or OEP_BOOTSTRAP_LAYOUT_C
#endif

static const uint8_t device_descriptor[] = {
    18, 1, 0x10, 0x01,
    0, 0, 0, 8,
    0x09, 0x12, 0x03, 0xd0,
    0x00, 0x00,
    0, 0, 0,
    1,
};

static const uint8_t special_hid_desc[] = {
    HID_USAGE_PAGE(0xff),
    HID_USAGE(0x00),
    HID_REPORT_SIZE(8),
    HID_COLLECTION(HID_COLLECTION_LOGICAL),
        HID_REPORT_COUNT(OEP_HID_REPORT_COUNT),
        HID_REPORT_ID(0x01)
        HID_USAGE(0x01),
        HID_FEATURE(HID_DATA | HID_VARIABLE | HID_ABSOLUTE),
    HID_COLLECTION_END,
};

static const uint8_t config_descriptor[] = {
    9, 2, 0x22, 0x00,
    1, 1, 0, 0x80, 0x32,
    9, 4, 0, 0, 1, 0x03, 0x00, 0x00, 0,
    9, 0x21, 0x10, 0x01, 0, 1, 0x22,
    sizeof(special_hid_desc), 0,
    7, 5, 0x81, 0x03, 1, 0, 100,
};

const static struct descriptor_list_struct {
    uint32_t lIndexValue;
    const uint8_t *addr;
    uint8_t length;
} descriptor_list[] = {
    {0x00000100, device_descriptor, sizeof(device_descriptor)},
    {0x00000200, config_descriptor, sizeof(config_descriptor)},
    {0x00002200, special_hid_desc, sizeof(special_hid_desc)},
    {0x00002100, config_descriptor + 18, 9},
};

#define DESCRIPTOR_LIST_ENTRIES \
    (sizeof(descriptor_list) / sizeof(descriptor_list[0]))

#endif
#endif
#endif
