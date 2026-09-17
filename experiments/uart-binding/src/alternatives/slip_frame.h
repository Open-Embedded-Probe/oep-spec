#ifndef OEP_EXPERIMENT_UART_SLIP_FRAME_H
#define OEP_EXPERIMENT_UART_SLIP_FRAME_H

#include "../uart_frame.h"

#ifdef __cplusplus
extern "C" {
#endif

#define OEP_UART_SLIP_RAW_OVERHEAD 3u
#define OEP_UART_SLIP_MAX_RAW \
    (OEP_UART_MAX_PAYLOAD + OEP_UART_SLIP_RAW_OVERHEAD)
#define OEP_UART_SLIP_MAX_WIRE (OEP_UART_SLIP_MAX_RAW * 2u + 1u)
#define OEP_UART_SLIP_ACK_MAX_WIRE 6u

struct oep_uart_slip_decoder {
    uint8_t raw[OEP_UART_SLIP_MAX_RAW];
    uint8_t raw_length;
    bool escaped;
    bool discard_until_delimiter;
};

void oep_uart_slip_decoder_init(struct oep_uart_slip_decoder *decoder);

size_t oep_uart_slip_encode_frame(
    uint8_t type,
    uint8_t sequence,
    const uint8_t *payload,
    uint16_t payload_length,
    uint8_t *wire,
    size_t wire_capacity);

enum oep_uart_decode_result oep_uart_slip_decoder_feed(
    struct oep_uart_slip_decoder *decoder,
    uint8_t byte,
    struct oep_uart_frame_view *frame);

#ifdef __cplusplus
}
#endif

#endif
