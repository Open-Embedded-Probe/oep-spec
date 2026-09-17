#ifndef OEP_EXPERIMENT_UART_DERIVED_LENGTH_FRAME_H
#define OEP_EXPERIMENT_UART_DERIVED_LENGTH_FRAME_H

#include "../uart_frame.h"

#ifdef __cplusplus
extern "C" {
#endif

#define OEP_UART_DERIVED_RAW_OVERHEAD 3u
#define OEP_UART_DERIVED_MAX_RAW \
    (OEP_UART_MAX_PAYLOAD + OEP_UART_DERIVED_RAW_OVERHEAD)
#define OEP_UART_DERIVED_MAX_ENCODED_BODY \
    (OEP_UART_DERIVED_MAX_RAW + 1u)
#define OEP_UART_DERIVED_MAX_WIRE \
    (OEP_UART_DERIVED_MAX_ENCODED_BODY + 1u)
#define OEP_UART_DERIVED_ACK_WIRE_SIZE 5u

struct oep_uart_derived_decoder {
    uint8_t encoded[OEP_UART_DERIVED_MAX_ENCODED_BODY];
    uint8_t encoded_length;
    bool discard_until_delimiter;
};

void oep_uart_derived_decoder_init(
    struct oep_uart_derived_decoder *decoder);

bool oep_uart_derived_decoder_abort_partial_frame(
    struct oep_uart_derived_decoder *decoder);

size_t oep_uart_derived_encode_frame(
    uint8_t type,
    uint8_t sequence,
    const uint8_t *payload,
    uint16_t payload_length,
    uint8_t *wire,
    size_t wire_capacity);

enum oep_uart_decode_result oep_uart_derived_decoder_feed(
    struct oep_uart_derived_decoder *decoder,
    uint8_t byte,
    struct oep_uart_frame_view *frame);

#ifdef __cplusplus
}
#endif

#endif
