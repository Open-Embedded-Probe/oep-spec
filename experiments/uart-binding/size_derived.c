#include "alternatives/derived_length_frame.h"

static struct oep_uart_derived_decoder decoder;
static uint8_t wire[OEP_UART_DERIVED_MAX_WIRE];
static volatile uint8_t sink;

int main(void)
{
    static const uint8_t message[14] = {
        0x81, 0x01, 0x34, 0x12, 0x4f, 0x45, 0x50,
        0x21, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01,
    };
    struct oep_uart_frame_view frame;
    size_t length = oep_uart_derived_encode_frame(
        OEP_UART_FRAME_DATA,
        0,
        message,
        sizeof(message),
        wire,
        sizeof(wire));
    size_t index;

    oep_uart_derived_decoder_init(&decoder);
    for (index = 0; index < length; ++index) {
        if (oep_uart_derived_decoder_feed(&decoder, wire[index], &frame) ==
            OEP_UART_DECODE_FRAME) {
            sink ^= frame.payload[0];
        }
    }
    for (;;) {
    }
}
