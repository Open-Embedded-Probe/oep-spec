#include <Arduino.h>
#include <string.h>

#include <alternatives/derived_length_frame.h>
#include <alternatives/slip_frame.h>
#include <uart_frame.h>

static unsigned int test_total;
static unsigned int test_passed;
static uint32_t random_state = 0x4f455031u;

static uint8_t next_random_byte()
{
    random_state = random_state * 1664525u + 1013904223u;
    return static_cast<uint8_t>(random_state >> 24);
}

static void check(bool condition, const __FlashStringHelper *name)
{
    ++test_total;
    if (condition) {
        ++test_passed;
        return;
    }
    Serial.print(F("FAIL "));
    Serial.println(name);
}

static void test_all_payload_lengths()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t explicit_wire[OEP_UART_MAX_WIRE];
    uint8_t derived_wire[OEP_UART_DERIVED_MAX_WIRE];
    bool valid = true;

    for (uint16_t length = 0; length <= OEP_UART_MAX_PAYLOAD; ++length) {
        struct oep_uart_derived_decoder decoder;
        struct oep_uart_frame_view frame;
        enum oep_uart_decode_result result = OEP_UART_DECODE_NONE;

        for (uint16_t index = 0; index < length; ++index) {
            payload[index] = static_cast<uint8_t>(
                (index * 41u + length * 17u) & 0xffu);
        }
        size_t explicit_length = oep_uart_encode_frame(
            OEP_UART_FRAME_DATA,
            static_cast<uint8_t>(length & 1u),
            payload,
            length,
            explicit_wire,
            sizeof(explicit_wire));
        size_t derived_length = oep_uart_derived_encode_frame(
            OEP_UART_FRAME_DATA,
            static_cast<uint8_t>(length & 1u),
            payload,
            length,
            derived_wire,
            sizeof(derived_wire));
        if (explicit_length == 0 || derived_length == 0 ||
            explicit_length != derived_length + 2u) {
            valid = false;
            break;
        }

        oep_uart_derived_decoder_init(&decoder);
        for (size_t index = 0; index < derived_length; ++index) {
            result = oep_uart_derived_decoder_feed(
                &decoder, derived_wire[index], &frame);
        }
        if (result != OEP_UART_DECODE_FRAME ||
            frame.type != OEP_UART_FRAME_DATA ||
            frame.sequence != (length & 1u) ||
            frame.payload_length != length ||
            memcmp(frame.payload, payload, length) != 0) {
            valid = false;
            break;
        }
    }
    check(valid, F("all payload lengths"));
}

static void test_derived_mutation_recovery()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t wire[OEP_UART_DERIVED_MAX_WIRE];
    uint8_t stream[OEP_UART_DERIVED_MAX_WIRE * 3u + 1u];
    bool recovered = true;

    for (uint8_t index = 0; index < sizeof(payload); ++index) {
        payload[index] = static_cast<uint8_t>(index * 31u + 3u);
    }
    size_t wire_length = oep_uart_derived_encode_frame(
        OEP_UART_FRAME_DATA,
        0,
        payload,
        sizeof(payload),
        wire,
        sizeof(wire));

    for (uint8_t mode = 0; mode < 3 && recovered; ++mode) {
        for (size_t position = 0;
             position < wire_length && recovered;
             ++position) {
            struct oep_uart_derived_decoder decoder;
            struct oep_uart_frame_view frame;
            size_t stream_length = 0;
            uint8_t delivered = 0;

            for (size_t index = 0; index < wire_length; ++index) {
                if (mode == 1 && index == position) {
                    continue;
                }
                if (mode == 2 && index == position) {
                    stream[stream_length++] =
                        (position & 1u) == 0 ? 0 : 0x7f;
                }
                stream[stream_length++] = wire[index];
            }
            if (mode == 0) {
                stream[position] ^= 0x01;
            }
            memcpy(stream + stream_length, wire, wire_length);
            stream_length += wire_length;
            memcpy(stream + stream_length, wire, wire_length);
            stream_length += wire_length;

            oep_uart_derived_decoder_init(&decoder);
            for (size_t index = 0; index < stream_length; ++index) {
                if (oep_uart_derived_decoder_feed(
                        &decoder,
                        stream[index],
                        &frame) == OEP_UART_DECODE_FRAME) {
                    if (frame.payload_length != sizeof(payload) ||
                        memcmp(frame.payload, payload, sizeof(payload)) != 0) {
                        recovered = false;
                        break;
                    }
                    ++delivered;
                }
            }
            if (delivered == 0) {
                recovered = false;
            }
        }
    }
    check(recovered, F("all single-byte mutations recover"));
}

static void test_slip_payloads_and_bound()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t wire[OEP_UART_SLIP_MAX_WIRE];
    bool valid = true;

    for (uint8_t index = 0; index < sizeof(payload); ++index) {
        payload[index] = (index & 1u) == 0 ? 0xc0u : 0xdbu;
    }
    for (uint16_t length = 0; length <= sizeof(payload); ++length) {
        struct oep_uart_slip_decoder decoder;
        struct oep_uart_frame_view frame;
        enum oep_uart_decode_result result = OEP_UART_DECODE_NONE;
        size_t wire_length = oep_uart_slip_encode_frame(
            OEP_UART_FRAME_DATA,
            static_cast<uint8_t>(length & 1u),
            payload,
            length,
            wire,
            sizeof(wire));

        if (wire_length == 0 || wire_length > OEP_UART_SLIP_MAX_WIRE) {
            valid = false;
            break;
        }
        oep_uart_slip_decoder_init(&decoder);
        for (size_t index = 0; index < wire_length; ++index) {
            result = oep_uart_slip_decoder_feed(
                &decoder, wire[index], &frame);
        }
        if (result != OEP_UART_DECODE_FRAME ||
            frame.payload_length != length ||
            memcmp(frame.payload, payload, length) != 0) {
            valid = false;
            break;
        }
    }
    check(valid, F("SLIP payloads and bound"));
}

static void test_slip_mutation_recovery()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t wire[OEP_UART_SLIP_MAX_WIRE];
    uint8_t stream[OEP_UART_SLIP_MAX_WIRE * 3u + 1u];
    bool recovered = true;

    for (uint8_t index = 0; index < sizeof(payload); ++index) {
        payload[index] = (index & 1u) == 0 ? 0xc0u : 0xdbu;
    }
    size_t wire_length = oep_uart_slip_encode_frame(
        OEP_UART_FRAME_DATA, 0, payload, sizeof(payload), wire, sizeof(wire));

    for (uint8_t mode = 0; mode < 3 && recovered; ++mode) {
        for (size_t position = 0;
             position < wire_length && recovered;
             ++position) {
            struct oep_uart_slip_decoder decoder;
            struct oep_uart_frame_view frame;
            size_t stream_length = 0;
            uint8_t delivered = 0;

            for (size_t index = 0; index < wire_length; ++index) {
                if (mode == 1 && index == position) {
                    continue;
                }
                if (mode == 2 && index == position) {
                    stream[stream_length++] =
                        (position & 1u) == 0 ? 0xc0u : 0x7fu;
                }
                stream[stream_length++] = wire[index];
            }
            if (mode == 0) {
                stream[position] ^= 0x01u;
            }
            memcpy(stream + stream_length, wire, wire_length);
            stream_length += wire_length;
            memcpy(stream + stream_length, wire, wire_length);
            stream_length += wire_length;

            oep_uart_slip_decoder_init(&decoder);
            for (size_t index = 0; index < stream_length; ++index) {
                if (oep_uart_slip_decoder_feed(
                        &decoder,
                        stream[index],
                        &frame) == OEP_UART_DECODE_FRAME) {
                    if (frame.payload_length != sizeof(payload) ||
                        memcmp(frame.payload, payload, sizeof(payload)) != 0) {
                        recovered = false;
                        break;
                    }
                    ++delivered;
                }
            }
            if (delivered == 0) {
                recovered = false;
            }
        }
    }
    check(recovered, F("SLIP mutations recover"));
}

static void test_encoder_capacity_boundaries()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t reference[OEP_UART_SLIP_MAX_WIRE];
    uint8_t guarded[OEP_UART_SLIP_MAX_WIRE + 2u];
    bool valid = true;

    for (uint8_t index = 0; index < sizeof(payload); ++index) {
        payload[index] = (index & 1u) == 0 ? 0xc0u : 0xdbu;
    }

    size_t derived_length = oep_uart_derived_encode_frame(
        OEP_UART_FRAME_DATA,
        0,
        payload,
        sizeof(payload),
        reference,
        sizeof(reference));
    memset(guarded, 0xa5, sizeof(guarded));
    valid = valid && derived_length != 0 &&
        oep_uart_derived_encode_frame(
            OEP_UART_FRAME_DATA,
            0,
            payload,
            sizeof(payload),
            guarded + 1,
            derived_length - 1u) == 0 &&
        guarded[0] == 0xa5 && guarded[derived_length] == 0xa5;
    memset(guarded, 0xa5, sizeof(guarded));
    valid = valid && oep_uart_derived_encode_frame(
        OEP_UART_FRAME_DATA,
        0,
        payload,
        sizeof(payload),
        guarded + 1,
        derived_length) == derived_length &&
        guarded[0] == 0xa5 && guarded[derived_length + 1u] == 0xa5;

    size_t slip_length = oep_uart_slip_encode_frame(
        OEP_UART_FRAME_DATA,
        0,
        payload,
        sizeof(payload),
        reference,
        sizeof(reference));
    memset(guarded, 0xa5, sizeof(guarded));
    valid = valid && slip_length != 0 &&
        oep_uart_slip_encode_frame(
            OEP_UART_FRAME_DATA,
            0,
            payload,
            sizeof(payload),
            guarded + 1,
            slip_length - 1u) == 0 &&
        guarded[0] == 0xa5 && guarded[slip_length] == 0xa5;
    memset(guarded, 0xa5, sizeof(guarded));
    valid = valid && oep_uart_slip_encode_frame(
        OEP_UART_FRAME_DATA,
        0,
        payload,
        sizeof(payload),
        guarded + 1,
        slip_length) == slip_length &&
        guarded[0] == 0xa5 && guarded[slip_length + 1u] == 0xa5;

    check(valid, F("encoder exact capacity and guards"));
}

static void test_noise_then_valid_frame_recovery()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t derived_wire[OEP_UART_DERIVED_MAX_WIRE];
    uint8_t slip_wire[OEP_UART_SLIP_MAX_WIRE];
    bool recovered = true;

    for (uint16_t iteration = 0; iteration < 256u && recovered; ++iteration) {
        struct oep_uart_derived_decoder derived_decoder;
        struct oep_uart_slip_decoder slip_decoder;
        struct oep_uart_frame_view frame;
        uint16_t payload_length = next_random_byte() %
            (OEP_UART_MAX_PAYLOAD + 1u);
        uint16_t noise_length = next_random_byte() % 96u;
        enum oep_uart_decode_result result = OEP_UART_DECODE_NONE;

        for (uint16_t index = 0; index < payload_length; ++index) {
            payload[index] = next_random_byte();
        }
        size_t derived_length = oep_uart_derived_encode_frame(
            OEP_UART_FRAME_DATA,
            static_cast<uint8_t>(iteration & 1u),
            payload,
            payload_length,
            derived_wire,
            sizeof(derived_wire));
        size_t slip_length = oep_uart_slip_encode_frame(
            OEP_UART_FRAME_DATA,
            static_cast<uint8_t>(iteration & 1u),
            payload,
            payload_length,
            slip_wire,
            sizeof(slip_wire));

        oep_uart_derived_decoder_init(&derived_decoder);
        oep_uart_slip_decoder_init(&slip_decoder);
        for (uint16_t index = 0; index < noise_length; ++index) {
            uint8_t noise = next_random_byte();
            if (noise == 0) {
                noise = 1;
            }
            oep_uart_derived_decoder_feed(&derived_decoder, noise, &frame);
            if (noise == 0xc0u) {
                noise = 0xc1u;
            }
            oep_uart_slip_decoder_feed(&slip_decoder, noise, &frame);
        }
        oep_uart_derived_decoder_feed(&derived_decoder, 0, &frame);
        oep_uart_slip_decoder_feed(&slip_decoder, 0xc0u, &frame);

        for (size_t index = 0; index < derived_length; ++index) {
            result = oep_uart_derived_decoder_feed(
                &derived_decoder, derived_wire[index], &frame);
        }
        if (result != OEP_UART_DECODE_FRAME ||
            frame.sequence != (iteration & 1u) ||
            frame.payload_length != payload_length ||
            memcmp(frame.payload, payload, payload_length) != 0) {
            recovered = false;
            break;
        }
        for (size_t index = 0; index < slip_length; ++index) {
            result = oep_uart_slip_decoder_feed(
                &slip_decoder, slip_wire[index], &frame);
        }
        if (result != OEP_UART_DECODE_FRAME ||
            frame.sequence != (iteration & 1u) ||
            frame.payload_length != payload_length ||
            memcmp(frame.payload, payload, payload_length) != 0) {
            recovered = false;
        }
    }
    check(recovered, F("256 noise recovery cases"));
}

void setup()
{
    Serial.begin(115200);
    delay(500);

    test_all_payload_lengths();
    test_derived_mutation_recovery();
    test_slip_payloads_and_bound();
    test_slip_mutation_recovery();
    test_encoder_capacity_boundaries();
    test_noise_then_valid_frame_recovery();
    check(
        OEP_UART_ACK_WIRE_SIZE == 7u &&
            OEP_UART_DERIVED_ACK_WIRE_SIZE == 5u,
        F("ack wire sizes"));
    check(
        sizeof(struct oep_uart_decoder) == 40u &&
            sizeof(struct oep_uart_derived_decoder) == 38u,
        F("decoder state sizes"));

    Serial.print(F("COMPARISON explicit-max="));
    Serial.print(OEP_UART_MAX_WIRE);
    Serial.print(F(" derived-max="));
    Serial.println(OEP_UART_DERIVED_MAX_WIRE);
    Serial.println(F("COMPARISON bootstrap-roundtrip explicit=52 derived=44"));
    Serial.print(F("COMPARISON slip-worst-case="));
    Serial.println(OEP_UART_SLIP_MAX_WIRE);
    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
