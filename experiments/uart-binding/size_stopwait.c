#include "uart_stopwait.h"

static struct oep_uart_stopwait link;
static uint8_t captured_wire[OEP_UART_MAX_WIRE];
static uint8_t captured_length;
static volatile uint8_t sink;

static void wire_send(void *context, const uint8_t *wire, size_t length)
{
    (void)context;
    size_t index;

    if (length > sizeof(captured_wire)) {
        return;
    }
    for (index = 0; index < length; ++index) {
        captured_wire[index] = wire[index];
    }
    captured_length = (uint8_t)length;
}

static bool deliver(void *context, const uint8_t *message, uint16_t length)
{
    (void)context;
    if (length != 0) {
        sink ^= message[0];
    }
    return true;
}

int main(void)
{
    static const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x12, 0x34, 0x56, 0x78,
    };
    static const uint8_t message[14] = {
        0x81, 0x01, 0x34, 0x12, 0x4f, 0x45, 0x50,
        0x21, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01,
    };

    oep_uart_stopwait_init(
        &link, OEP_UART_ROLE_HOST, 2, wire_send, deliver, 0);
    (void)oep_uart_stopwait_start_sync(&link, token);
    captured_length = (uint8_t)oep_uart_encode_frame(
        OEP_UART_FRAME_SYNC_ACK,
        0,
        token,
        OEP_UART_EPOCH_TOKEN_SIZE,
        captured_wire,
        sizeof(captured_wire));
    while (captured_length != 0) {
        uint8_t length = captured_length;
        uint8_t index;

        captured_length = 0;
        for (index = 0; index < length; ++index) {
            oep_uart_stopwait_feed(&link, captured_wire[index]);
        }
    }
    (void)oep_uart_stopwait_send(&link, message, sizeof(message));
    (void)oep_uart_stopwait_timeout(&link);
    while (captured_length != 0) {
        uint8_t length = captured_length;
        uint8_t index;

        captured_length = 0;
        for (index = 0; index < length; ++index) {
            oep_uart_stopwait_feed(&link, captured_wire[index]);
        }
    }
    oep_uart_stopwait_reset_epoch(&link);
    for (;;) {
    }
}
