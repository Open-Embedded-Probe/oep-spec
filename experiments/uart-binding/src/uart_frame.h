#ifndef OEP_EXPERIMENT_UART_FRAME_H
#define OEP_EXPERIMENT_UART_FRAME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef OEP_UART_MAX_PAYLOAD
#define OEP_UART_MAX_PAYLOAD 32u
#endif

#define OEP_UART_RAW_OVERHEAD 5u
#define OEP_UART_MAX_RAW (OEP_UART_MAX_PAYLOAD + OEP_UART_RAW_OVERHEAD)
#define OEP_UART_MAX_ENCODED_BODY (OEP_UART_MAX_RAW + 1u)
#define OEP_UART_MAX_WIRE (OEP_UART_MAX_ENCODED_BODY + 1u)
#define OEP_UART_ACK_WIRE_SIZE 7u

enum oep_uart_frame_type {
    OEP_UART_FRAME_DATA = 1,
    OEP_UART_FRAME_ACK = 2,
    OEP_UART_FRAME_SYNC = 3,
    OEP_UART_FRAME_SYNC_ACK = 4,
};

enum oep_uart_decode_result {
    OEP_UART_DECODE_NONE = 0,
    OEP_UART_DECODE_FRAME = 1,
    OEP_UART_DECODE_DROPPED = 2,
};

struct oep_uart_frame_view {
    uint8_t type;
    uint8_t sequence;
    const uint8_t *payload;
    uint16_t payload_length;
};

struct oep_uart_decoder {
    uint8_t encoded[OEP_UART_MAX_ENCODED_BODY];
    uint8_t encoded_length;
    bool discard_until_delimiter;
};

void oep_uart_decoder_init(struct oep_uart_decoder *decoder);

bool oep_uart_decoder_abort_partial_frame(
    struct oep_uart_decoder *decoder);

size_t oep_uart_encode_frame(
    uint8_t type,
    uint8_t sequence,
    const uint8_t *payload,
    uint16_t payload_length,
    uint8_t *wire,
    size_t wire_capacity);

enum oep_uart_decode_result oep_uart_decoder_feed(
    struct oep_uart_decoder *decoder,
    uint8_t byte,
    struct oep_uart_frame_view *frame);

uint16_t oep_uart_crc16(const uint8_t *data, size_t length);

#ifdef __cplusplus
}
#endif

#endif
