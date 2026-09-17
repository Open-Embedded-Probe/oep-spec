#include "derived_length_frame.h"

#include <string.h>

struct derived_cobs_writer {
    uint8_t *output;
    size_t capacity;
    size_t code_index;
    size_t write_index;
    uint8_t code;
    bool failed;
};

static void writer_init(
    struct derived_cobs_writer *writer,
    uint8_t *output,
    size_t capacity)
{
    writer->output = output;
    writer->capacity = capacity;
    writer->code_index = 0;
    writer->write_index = 1;
    writer->code = 1;
    writer->failed = capacity == 0;
}

static void writer_put(struct derived_cobs_writer *writer, uint8_t byte)
{
    if (writer->failed) {
        return;
    }
    if (byte == 0) {
        if (writer->code_index >= writer->capacity ||
            writer->write_index >= writer->capacity) {
            writer->failed = true;
            return;
        }
        writer->output[writer->code_index] = writer->code;
        writer->code_index = writer->write_index++;
        writer->code = 1;
        return;
    }
    if (writer->write_index >= writer->capacity) {
        writer->failed = true;
        return;
    }
    writer->output[writer->write_index++] = byte;
    ++writer->code;
}

static size_t writer_finish(struct derived_cobs_writer *writer)
{
    if (writer->failed || writer->code_index >= writer->capacity ||
        writer->write_index >= writer->capacity) {
        return 0;
    }
    writer->output[writer->code_index] = writer->code;
    writer->output[writer->write_index++] = 0;
    return writer->write_index;
}

static size_t decode_in_place(uint8_t *data, size_t encoded_length)
{
    size_t read_index = 0;
    size_t write_index = 0;

    while (read_index < encoded_length) {
        uint8_t code = data[read_index++];
        size_t copy_length;

        if (code == 0) {
            return 0;
        }
        copy_length = (size_t)code - 1u;
        if (read_index + copy_length > encoded_length) {
            return 0;
        }
        if (copy_length != 0) {
            memmove(data + write_index, data + read_index, copy_length);
            write_index += copy_length;
            read_index += copy_length;
        }
        if (code != 0xff && read_index < encoded_length) {
            data[write_index++] = 0;
        }
    }
    return write_index;
}

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

static uint16_t derived_crc16(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xffffu;

    while (length-- != 0) {
        crc = crc_update(crc, *data++);
    }
    return crc;
}

void oep_uart_derived_decoder_init(struct oep_uart_derived_decoder *decoder)
{
    decoder->encoded_length = 0;
    decoder->discard_until_delimiter = false;
}

bool oep_uart_derived_decoder_abort_partial_frame(
    struct oep_uart_derived_decoder *decoder)
{
    bool had_partial_frame =
        decoder->encoded_length != 0 || decoder->discard_until_delimiter;

    if (decoder->encoded_length != 0) {
        decoder->encoded_length = 0;
        decoder->discard_until_delimiter = true;
    }
    return had_partial_frame;
}

size_t oep_uart_derived_encode_frame(
    uint8_t type,
    uint8_t sequence,
    const uint8_t *payload,
    uint16_t payload_length,
    uint8_t *wire,
    size_t wire_capacity)
{
    struct derived_cobs_writer writer;
    uint16_t crc = 0xffffu;
    uint8_t type_sequence;
    uint16_t index;

    if (type == 0 || type > 0x0fu || sequence > 1u ||
        payload_length > OEP_UART_MAX_PAYLOAD ||
        (payload_length != 0 && payload == NULL)) {
        return 0;
    }

    type_sequence = (uint8_t)((type << 4) | sequence);
    writer_init(&writer, wire, wire_capacity);
    crc = crc_update(crc, type_sequence);
    writer_put(&writer, type_sequence);
    for (index = 0; index < payload_length; ++index) {
        crc = crc_update(crc, payload[index]);
        writer_put(&writer, payload[index]);
    }
    writer_put(&writer, (uint8_t)crc);
    writer_put(&writer, (uint8_t)(crc >> 8));
    return writer_finish(&writer);
}

enum oep_uart_decode_result oep_uart_derived_decoder_feed(
    struct oep_uart_derived_decoder *decoder,
    uint8_t byte,
    struct oep_uart_frame_view *frame)
{
    size_t raw_length;
    uint16_t payload_length;
    uint16_t expected_crc;
    uint16_t actual_crc;
    uint8_t type_sequence;

    if (byte != 0) {
        if (decoder->discard_until_delimiter) {
            return OEP_UART_DECODE_NONE;
        }
        if (decoder->encoded_length >= sizeof(decoder->encoded)) {
            decoder->discard_until_delimiter = true;
            decoder->encoded_length = 0;
            return OEP_UART_DECODE_NONE;
        }
        decoder->encoded[decoder->encoded_length++] = byte;
        return OEP_UART_DECODE_NONE;
    }

    if (decoder->discard_until_delimiter) {
        decoder->discard_until_delimiter = false;
        decoder->encoded_length = 0;
        return OEP_UART_DECODE_DROPPED;
    }
    if (decoder->encoded_length == 0) {
        return OEP_UART_DECODE_NONE;
    }

    raw_length = decode_in_place(decoder->encoded, decoder->encoded_length);
    decoder->encoded_length = 0;
    if (raw_length < OEP_UART_DERIVED_RAW_OVERHEAD) {
        return OEP_UART_DECODE_DROPPED;
    }

    type_sequence = decoder->encoded[0];
    if ((type_sequence & 0x0eu) != 0 || (type_sequence >> 4) == 0) {
        return OEP_UART_DECODE_DROPPED;
    }
    payload_length = (uint16_t)(raw_length - OEP_UART_DERIVED_RAW_OVERHEAD);
    if (payload_length > OEP_UART_MAX_PAYLOAD) {
        return OEP_UART_DECODE_DROPPED;
    }

    expected_crc = (uint16_t)decoder->encoded[raw_length - 2] |
        ((uint16_t)decoder->encoded[raw_length - 1] << 8);
    actual_crc = derived_crc16(decoder->encoded, raw_length - 2);
    if (expected_crc != actual_crc) {
        return OEP_UART_DECODE_DROPPED;
    }

    frame->type = (uint8_t)(type_sequence >> 4);
    frame->sequence = (uint8_t)(type_sequence & 1u);
    frame->payload = decoder->encoded + 1;
    frame->payload_length = payload_length;
    return OEP_UART_DECODE_FRAME;
}
