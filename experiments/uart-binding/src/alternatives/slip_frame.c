#include "slip_frame.h"

#define SLIP_END 0xc0u
#define SLIP_ESC 0xdbu
#define SLIP_ESC_END 0xdcu
#define SLIP_ESC_ESC 0xddu

struct slip_writer {
    uint8_t *wire;
    size_t capacity;
    size_t length;
    bool failed;
};

static uint16_t crc_update(uint16_t crc, uint8_t byte)
{
    uint8_t bit;

    crc ^= (uint16_t)byte << 8;
    for (bit = 0; bit < 8; ++bit) {
        if ((crc & 0x8000u) != 0) {
            crc = (uint16_t)((crc << 1) ^ 0x1021u);
        } else {
            crc <<= 1;
        }
    }
    return crc;
}

static uint16_t frame_crc16(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xffffu;

    while (length-- != 0) {
        crc = crc_update(crc, *data++);
    }
    return crc;
}

static void writer_put_raw(struct slip_writer *writer, uint8_t byte)
{
    if (writer->failed) {
        return;
    }
    if (byte == SLIP_END || byte == SLIP_ESC) {
        if (writer->length + 2u > writer->capacity) {
            writer->failed = true;
            return;
        }
        writer->wire[writer->length++] = SLIP_ESC;
        writer->wire[writer->length++] =
            byte == SLIP_END ? SLIP_ESC_END : SLIP_ESC_ESC;
        return;
    }
    if (writer->length >= writer->capacity) {
        writer->failed = true;
        return;
    }
    writer->wire[writer->length++] = byte;
}

void oep_uart_slip_decoder_init(struct oep_uart_slip_decoder *decoder)
{
    decoder->raw_length = 0;
    decoder->escaped = false;
    decoder->discard_until_delimiter = false;
}

size_t oep_uart_slip_encode_frame(
    uint8_t type,
    uint8_t sequence,
    const uint8_t *payload,
    uint16_t payload_length,
    uint8_t *wire,
    size_t wire_capacity)
{
    struct slip_writer writer = {wire, wire_capacity, 0, false};
    uint8_t type_sequence;
    uint16_t crc = 0xffffu;
    uint16_t index;

    if (type == 0 || type > 0x0fu || sequence > 1u ||
        payload_length > OEP_UART_MAX_PAYLOAD ||
        (payload_length != 0 && payload == NULL)) {
        return 0;
    }
    type_sequence = (uint8_t)((type << 4) | sequence);
    crc = crc_update(crc, type_sequence);
    writer_put_raw(&writer, type_sequence);
    for (index = 0; index < payload_length; ++index) {
        crc = crc_update(crc, payload[index]);
        writer_put_raw(&writer, payload[index]);
    }
    writer_put_raw(&writer, (uint8_t)crc);
    writer_put_raw(&writer, (uint8_t)(crc >> 8));
    if (writer.failed || writer.length >= writer.capacity) {
        return 0;
    }
    writer.wire[writer.length++] = SLIP_END;
    return writer.length;
}

static enum oep_uart_decode_result finish_frame(
    struct oep_uart_slip_decoder *decoder,
    struct oep_uart_frame_view *frame)
{
    uint16_t payload_length;
    uint16_t expected_crc;
    uint16_t actual_crc;
    uint8_t type_sequence;

    if (decoder->raw_length < OEP_UART_SLIP_RAW_OVERHEAD) {
        decoder->raw_length = 0;
        return OEP_UART_DECODE_DROPPED;
    }
    type_sequence = decoder->raw[0];
    if ((type_sequence & 0x0eu) != 0 || (type_sequence >> 4) == 0) {
        decoder->raw_length = 0;
        return OEP_UART_DECODE_DROPPED;
    }
    payload_length =
        (uint16_t)(decoder->raw_length - OEP_UART_SLIP_RAW_OVERHEAD);
    expected_crc = (uint16_t)decoder->raw[decoder->raw_length - 2] |
        ((uint16_t)decoder->raw[decoder->raw_length - 1] << 8);
    actual_crc = frame_crc16(decoder->raw, decoder->raw_length - 2);
    if (expected_crc != actual_crc) {
        decoder->raw_length = 0;
        return OEP_UART_DECODE_DROPPED;
    }
    frame->type = (uint8_t)(type_sequence >> 4);
    frame->sequence = (uint8_t)(type_sequence & 1u);
    frame->payload = decoder->raw + 1;
    frame->payload_length = payload_length;
    decoder->raw_length = 0;
    return OEP_UART_DECODE_FRAME;
}

enum oep_uart_decode_result oep_uart_slip_decoder_feed(
    struct oep_uart_slip_decoder *decoder,
    uint8_t byte,
    struct oep_uart_frame_view *frame)
{
    if (byte == SLIP_END) {
        if (decoder->discard_until_delimiter || decoder->escaped) {
            oep_uart_slip_decoder_init(decoder);
            return OEP_UART_DECODE_DROPPED;
        }
        if (decoder->raw_length == 0) {
            return OEP_UART_DECODE_NONE;
        }
        return finish_frame(decoder, frame);
    }
    if (decoder->discard_until_delimiter) {
        return OEP_UART_DECODE_NONE;
    }
    if (decoder->escaped) {
        decoder->escaped = false;
        if (byte == SLIP_ESC_END) {
            byte = SLIP_END;
        } else if (byte == SLIP_ESC_ESC) {
            byte = SLIP_ESC;
        } else {
            decoder->raw_length = 0;
            decoder->discard_until_delimiter = true;
            return OEP_UART_DECODE_NONE;
        }
    } else if (byte == SLIP_ESC) {
        decoder->escaped = true;
        return OEP_UART_DECODE_NONE;
    }
    if (decoder->raw_length >= sizeof(decoder->raw)) {
        decoder->raw_length = 0;
        decoder->escaped = false;
        decoder->discard_until_delimiter = true;
        return OEP_UART_DECODE_NONE;
    }
    decoder->raw[decoder->raw_length++] = byte;
    return OEP_UART_DECODE_NONE;
}
