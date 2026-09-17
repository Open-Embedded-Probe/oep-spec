#include "ch32fun.h"

#include <string.h>

#include "rv003usb.h"

#if defined(OEP_BOOTSTRAP_LAYOUT_B)
#include "bootstrap_candidate_b.h"
#define REPORT_SIZE OEP_BOOTSTRAP_B_REPORT_SIZE
#define HANDLE_REPORT oep_bootstrap_b_handle_report
#elif defined(OEP_BOOTSTRAP_LAYOUT_C)
#include "bootstrap_candidate_c.h"
#define REPORT_SIZE OEP_BOOTSTRAP_C_REPORT_SIZE
#define HANDLE_REPORT oep_bootstrap_c_handle_report
#else
#error Select a bootstrap layout
#endif

static uint8_t report[REPORT_SIZE];
static volatile uint8_t response_ready;

int main(void)
{
    SystemInit();
    Delay_Ms(1);
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
        response_ready =
            HANDLE_REPORT(report, sizeof(report)) == sizeof(report);
    }
}

void usb_handle_hid_get_report_start(
    struct usb_endpoint *endpoint,
    int requested_length,
    uint32_t value_index)
{
    (void)value_index;
    if (!response_ready || requested_length > (int)sizeof(report)) {
        requested_length = 0;
    }
    endpoint->opaque = report;
    endpoint->max_len = requested_length;
    response_ready = 0;
}

void usb_handle_hid_set_report_start(
    struct usb_endpoint *endpoint,
    int requested_length,
    uint32_t value_index)
{
    (void)value_index;
    response_ready = 0;
    if (requested_length != (int)sizeof(report)) {
        requested_length = 0;
    }
    endpoint->max_len = requested_length;
}
