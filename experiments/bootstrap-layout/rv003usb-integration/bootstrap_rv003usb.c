#include "ch32fun.h"

#include <string.h>

#include "rv003usb.h"
#include "hid_feature_lifecycle.h"

#if defined(OEP_BOOTSTRAP_LAYOUT_B)
#include "bootstrap_candidate_b.h"
#define TRANSFER_SIZE OEP_BOOTSTRAP_B_REPORT_SIZE
#define PARSER_SIZE OEP_BOOTSTRAP_B_REPORT_SIZE
#define HANDLE_REPORT oep_bootstrap_b_handle_report
#elif defined(OEP_BOOTSTRAP_LAYOUT_C)
#include "bootstrap_candidate_c.h"
#if defined(OEP_RV003USB_SHORT_OUT_PATCHED)
#define TRANSFER_SIZE OEP_BOOTSTRAP_C_REPORT_SIZE
#else
/* Pad 9 bytes to 12 so rv003usb forwards the final 4-byte OUT packet. */
#define TRANSFER_SIZE 12u
#endif
#define PARSER_SIZE OEP_BOOTSTRAP_C_REPORT_SIZE
#define HANDLE_REPORT oep_bootstrap_c_handle_report
#else
#error Select a bootstrap layout
#endif

static uint8_t report[TRANSFER_SIZE];
static struct oep_hid_feature_lifecycle lifecycle;

int main(void)
{
    SystemInit();
    Delay_Ms(1);
    oep_hid_feature_lifecycle_init(&lifecycle);
    usb_setup();
    for (;;) {
        __asm__ volatile("nop");
    }
}

void usb_handle_user_in_request(
    struct usb_endpoint *endpoint,
    uint8_t *scratchpad,
    int endpoint_number,
    uint32_t send_token,
    struct rv003usb_internal *internal)
{
    (void)endpoint;
    (void)scratchpad;
    (void)internal;
    if (endpoint_number != 0) {
        usb_send_empty(send_token);
    }
}

void usb_handle_user_data(
    struct usb_endpoint *endpoint,
    int current_endpoint,
    uint8_t *data,
    int length,
    struct rv003usb_internal *internal)
{
    int offset = endpoint->count << 3;
    int remaining = endpoint->max_len - offset;

    (void)current_endpoint;
    (void)internal;
    if (remaining > length) {
        remaining = length;
    }
    if (remaining <= 0 || offset < 0 ||
        (size_t)offset >= sizeof(report)) {
        return;
    }
    if ((size_t)(offset + remaining) > sizeof(report)) {
        remaining = (int)sizeof(report) - offset;
    }
    memcpy(report + offset, data, (size_t)remaining);
    ++endpoint->count;
    if ((endpoint->count << 3) >= endpoint->max_len) {
        bool response_valid =
            HANDLE_REPORT(report, PARSER_SIZE) == PARSER_SIZE;
#if defined(OEP_BOOTSTRAP_LAYOUT_C)
#if !defined(OEP_RV003USB_SHORT_OUT_PATCHED)
        memset(report + PARSER_SIZE, 0, TRANSFER_SIZE - PARSER_SIZE);
#endif
#endif
        (void)oep_hid_feature_finish_set(&lifecycle, response_valid);
    }
}

void usb_handle_hid_get_report_start(
    struct usb_endpoint *endpoint,
    int requested_length,
    uint32_t value_index)
{
    (void)value_index;
    if (!oep_hid_feature_begin_get(
            &lifecycle,
            (uint16_t)requested_length,
            TRANSFER_SIZE)) {
        requested_length = 0;
    }
    endpoint->opaque = requested_length != 0 ? report : 0;
    endpoint->max_len = requested_length;
}

void usb_handle_hid_set_report_start(
    struct usb_endpoint *endpoint,
    int requested_length,
    uint32_t value_index)
{
    (void)value_index;
    if (!oep_hid_feature_begin_set(
            &lifecycle,
            (uint16_t)requested_length,
            TRANSFER_SIZE)) {
        requested_length = 0;
    }
    endpoint->max_len = requested_length;
}
