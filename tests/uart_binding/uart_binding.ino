#include <Arduino.h>
#include <string.h>

#include <uart_frame.h>
#include <uart_stopwait.h>

static unsigned int test_total;
static unsigned int test_passed;

#define OEP_TEST_WIRE_QUEUE_CAPACITY (OEP_UART_MAX_WIRE * 4u)

static bool expect_true(bool condition, const __FlashStringHelper *name)
{
    ++test_total;
    if (condition) {
        ++test_passed;
        return true;
    }
    Serial.print(F("FAIL "));
    Serial.println(name);
    return false;
}

#define EXPECT_TRUE(condition, name) \
    expect_true((condition), F(name))

#define REQUIRE_TRUE(condition, name) \
    do { \
        if (!EXPECT_TRUE((condition), (name))) { \
            return; \
        } \
    } while (0)

struct EndpointContext {
    uint8_t outgoing[OEP_TEST_WIRE_QUEUE_CAPACITY];
    uint16_t outgoing_length;
    uint16_t outgoing_peak;
    uint8_t delivered[OEP_UART_MAX_PAYLOAD];
    uint16_t delivered_length;
    uint8_t delivery_count;
    bool accept_delivery;
    bool drop_next;
    bool drop_all;
    bool corrupt_next;
    bool respond_during_delivery;
    bool response_send_succeeded;
    struct oep_uart_stopwait *responding_link;
    const uint8_t *response;
    uint16_t response_length;
};

static void initialize_context(struct EndpointContext *context)
{
    memset(context, 0, sizeof(*context));
    context->accept_delivery = true;
}

static void capture_wire(
    void *opaque,
    const uint8_t *wire,
    size_t wire_length)
{
    struct EndpointContext *context =
        static_cast<struct EndpointContext *>(opaque);

    if (context->drop_all || context->drop_next) {
        context->drop_next = false;
        return;
    }
    if (wire_length >
        sizeof(context->outgoing) - context->outgoing_length) {
        return;
    }

    size_t start = context->outgoing_length;
    memcpy(context->outgoing + start, wire, wire_length);
    context->outgoing_length = static_cast<uint16_t>(
        context->outgoing_length + wire_length);
    if (context->outgoing_length > context->outgoing_peak) {
        context->outgoing_peak = context->outgoing_length;
    }
    if (context->corrupt_next && wire_length > 2) {
        context->outgoing[start + 1] ^= 0x20;
        context->corrupt_next = false;
    }
}

static bool capture_delivery(
    void *opaque,
    const uint8_t *message,
    uint16_t message_length)
{
    struct EndpointContext *context =
        static_cast<struct EndpointContext *>(opaque);

    if (!context->accept_delivery ||
        message_length > sizeof(context->delivered)) {
        return false;
    }
    memcpy(context->delivered, message, message_length);
    context->delivered_length = message_length;
    ++context->delivery_count;
    if (context->respond_during_delivery) {
        context->response_send_succeeded = oep_uart_stopwait_send(
            context->responding_link,
            context->response,
            context->response_length);
    }
    return true;
}

static uint8_t first_queued_frame_type(const struct EndpointContext *context)
{
    struct oep_uart_decoder decoder;
    struct oep_uart_frame_view frame;

    oep_uart_decoder_init(&decoder);
    for (uint16_t index = 0; index < context->outgoing_length; ++index) {
        if (oep_uart_decoder_feed(
                &decoder,
                context->outgoing[index],
                &frame) == OEP_UART_DECODE_FRAME) {
            return frame.type;
        }
    }
    return 0;
}

static void pump(
    struct EndpointContext *source,
    struct oep_uart_stopwait *destination)
{
    uint8_t bytes[OEP_TEST_WIRE_QUEUE_CAPACITY];
    uint16_t length = source->outgoing_length;

    memcpy(bytes, source->outgoing, length);
    source->outgoing_length = 0;
    for (uint16_t index = 0; index < length; ++index) {
        oep_uart_stopwait_feed(destination, bytes[index]);
    }
}

static void initialize_unsynchronized_pair(
    struct oep_uart_stopwait *a,
    struct EndpointContext *a_context,
    struct oep_uart_stopwait *b,
    struct EndpointContext *b_context,
    uint8_t retry_limit = 2)
{
    initialize_context(a_context);
    initialize_context(b_context);
    oep_uart_stopwait_init(
        a,
        OEP_UART_ROLE_HOST,
        retry_limit,
        capture_wire,
        capture_delivery,
        a_context);
    oep_uart_stopwait_init(
        b,
        OEP_UART_ROLE_PROBE,
        retry_limit,
        capture_wire,
        capture_delivery,
        b_context);
}

static bool synchronize_pair(
    struct oep_uart_stopwait *host,
    struct EndpointContext *host_context,
    struct oep_uart_stopwait *probe,
    struct EndpointContext *probe_context,
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE])
{
    if (!oep_uart_stopwait_start_sync(host, token)) {
        return false;
    }
    pump(host_context, probe);
    pump(probe_context, host);
    return oep_uart_stopwait_is_active(host) &&
        oep_uart_stopwait_is_active(probe);
}

static void feed_encoded_frame(
    struct oep_uart_stopwait *destination,
    uint8_t type,
    uint8_t sequence,
    const uint8_t *payload,
    uint16_t payload_length)
{
    uint8_t wire[OEP_UART_MAX_WIRE];
    size_t wire_length = oep_uart_encode_frame(
        type,
        sequence,
        payload,
        payload_length,
        wire,
        sizeof(wire));

    for (size_t index = 0; index < wire_length; ++index) {
        oep_uart_stopwait_feed(destination, wire[index]);
    }
}

static void test_codec_round_trip()
{
    const uint8_t payload[] = {0x00, 0x01, 0x7e, 0x00, 0xff, 0x55};
    uint8_t wire[OEP_UART_MAX_WIRE];
    size_t wire_length = oep_uart_encode_frame(
        OEP_UART_FRAME_DATA, 1, payload, sizeof(payload), wire, sizeof(wire));
    struct oep_uart_decoder decoder;
    struct oep_uart_frame_view frame;
    enum oep_uart_decode_result result = OEP_UART_DECODE_NONE;

    REQUIRE_TRUE(wire_length != 0, "codec/encoded");
    oep_uart_decoder_init(&decoder);
    for (size_t index = 0; index < wire_length; ++index) {
        result = oep_uart_decoder_feed(&decoder, wire[index], &frame);
    }
    EXPECT_TRUE(result == OEP_UART_DECODE_FRAME, "codec/frame");
    EXPECT_TRUE(frame.type == OEP_UART_FRAME_DATA, "codec/type");
    EXPECT_TRUE(frame.sequence == 1, "codec/sequence");
    EXPECT_TRUE(frame.payload_length == sizeof(payload), "codec/length");
    EXPECT_TRUE(
        memcmp(frame.payload, payload, sizeof(payload)) == 0,
        "codec/payload");
}

static void test_codec_payload_boundaries()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t wire[OEP_UART_MAX_WIRE];
    bool valid = true;

    for (uint16_t length = 0; length <= OEP_UART_MAX_PAYLOAD; ++length) {
        struct oep_uart_decoder decoder;
        struct oep_uart_frame_view frame;
        enum oep_uart_decode_result result = OEP_UART_DECODE_NONE;

        for (uint16_t index = 0; index < length; ++index) {
            payload[index] = static_cast<uint8_t>(
                (index * 73u + length * 19u) & 0xffu);
        }
        size_t wire_length = oep_uart_encode_frame(
            OEP_UART_FRAME_DATA,
            static_cast<uint8_t>(length & 1u),
            payload,
            length,
            wire,
            sizeof(wire));
        if (wire_length == 0 || wire_length > sizeof(wire)) {
            valid = false;
            break;
        }

        oep_uart_decoder_init(&decoder);
        for (size_t index = 0; index < wire_length; ++index) {
            result = oep_uart_decoder_feed(&decoder, wire[index], &frame);
        }
        if (result != OEP_UART_DECODE_FRAME ||
            frame.payload_length != length ||
            memcmp(frame.payload, payload, length) != 0) {
            valid = false;
            break;
        }
    }
    EXPECT_TRUE(valid, "codec/all-payload-lengths");
    EXPECT_TRUE(
        oep_uart_encode_frame(
            OEP_UART_FRAME_DATA,
            0,
            payload,
            OEP_UART_MAX_PAYLOAD + 1u,
            wire,
            sizeof(wire)) == 0,
        "codec/reject-oversize");
    EXPECT_TRUE(
        oep_uart_encode_frame(
            OEP_UART_FRAME_DATA,
            0,
            payload,
            1,
            wire,
            1) == 0,
        "codec/reject-small-output");
}

static void test_malformed_frame_recovery()
{
    const uint8_t payload[] = {0x33, 0x44};
    const uint8_t malformed[] = {5, 1, 2, 0};
    uint8_t wire[OEP_UART_MAX_WIRE];
    size_t wire_length = oep_uart_encode_frame(
        OEP_UART_FRAME_DATA, 0, payload, sizeof(payload), wire, sizeof(wire));
    struct oep_uart_decoder decoder;
    struct oep_uart_frame_view frame;
    enum oep_uart_decode_result result = OEP_UART_DECODE_NONE;

    oep_uart_decoder_init(&decoder);
    for (size_t index = 0; index < OEP_UART_MAX_ENCODED_BODY + 3u; ++index) {
        (void)oep_uart_decoder_feed(&decoder, 0x55, &frame);
    }
    result = oep_uart_decoder_feed(&decoder, 0, &frame);
    EXPECT_TRUE(result == OEP_UART_DECODE_DROPPED, "malformed/oversize-dropped");

    for (size_t index = 0; index < sizeof(malformed); ++index) {
        result = oep_uart_decoder_feed(&decoder, malformed[index], &frame);
    }
    EXPECT_TRUE(result == OEP_UART_DECODE_DROPPED, "malformed/cobs-dropped");
    EXPECT_TRUE(
        oep_uart_decoder_feed(&decoder, 0, &frame) == OEP_UART_DECODE_NONE,
        "malformed/empty-delimiter-ignored");

    REQUIRE_TRUE(wire_length != 0, "malformed/valid-encoded");
    for (size_t index = 0; index < wire_length; ++index) {
        result = oep_uart_decoder_feed(&decoder, wire[index], &frame);
    }
    EXPECT_TRUE(result == OEP_UART_DECODE_FRAME, "malformed/recovered");
}

static void test_all_single_byte_mutations_resynchronize()
{
    uint8_t payload[OEP_UART_MAX_PAYLOAD];
    uint8_t wire[OEP_UART_MAX_WIRE];
    uint8_t stream[OEP_UART_MAX_WIRE * 3u + 1u];
    bool all_recovered = true;

    for (uint8_t index = 0; index < OEP_UART_MAX_PAYLOAD; ++index) {
        payload[index] = static_cast<uint8_t>(index * 29u + 7u);
    }
    size_t wire_length = oep_uart_encode_frame(
        OEP_UART_FRAME_DATA,
        0,
        payload,
        sizeof(payload),
        wire,
        sizeof(wire));
    REQUIRE_TRUE(wire_length != 0, "mutation/encoded");

    for (uint8_t mode = 0; mode < 3 && all_recovered; ++mode) {
        for (size_t position = 0;
             position < wire_length && all_recovered;
             ++position) {
            struct oep_uart_decoder decoder;
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

            oep_uart_decoder_init(&decoder);
            for (size_t index = 0; index < stream_length; ++index) {
                if (oep_uart_decoder_feed(
                        &decoder,
                        stream[index],
                        &frame) == OEP_UART_DECODE_FRAME) {
                    if (frame.type != OEP_UART_FRAME_DATA ||
                        frame.sequence != 0 ||
                        frame.payload_length != sizeof(payload) ||
                        memcmp(frame.payload, payload, sizeof(payload)) != 0) {
                        all_recovered = false;
                        break;
                    }
                    ++delivered;
                }
            }
            if (delivered == 0) {
                all_recovered = false;
            }
        }
    }
    EXPECT_TRUE(all_recovered, "mutation/all-positions-resynchronize");
}

static void test_corruption_and_resynchronization()
{
    const uint8_t first[] = {1, 2, 3, 4};
    const uint8_t second[] = {9, 0, 8};
    uint8_t damaged[OEP_UART_MAX_WIRE];
    uint8_t valid[OEP_UART_MAX_WIRE];
    size_t damaged_length = oep_uart_encode_frame(
        OEP_UART_FRAME_DATA, 0, first, sizeof(first), damaged, sizeof(damaged));
    size_t valid_length = oep_uart_encode_frame(
        OEP_UART_FRAME_DATA, 0, second, sizeof(second), valid, sizeof(valid));
    struct oep_uart_decoder decoder;
    struct oep_uart_frame_view frame;
    uint8_t delivered = 0;

    REQUIRE_TRUE(damaged_length > 4 && valid_length != 0, "resync/encoded");
    damaged[2] ^= 0x40;
    oep_uart_decoder_init(&decoder);
    for (size_t index = 0; index < damaged_length; ++index) {
        if (oep_uart_decoder_feed(&decoder, damaged[index], &frame) ==
            OEP_UART_DECODE_FRAME) {
            ++delivered;
        }
    }
    for (size_t index = 0; index < valid_length; ++index) {
        if (oep_uart_decoder_feed(&decoder, valid[index], &frame) ==
            OEP_UART_DECODE_FRAME) {
            ++delivered;
        }
    }
    EXPECT_TRUE(delivered == 1, "resync/corrupt-count");
    EXPECT_TRUE(frame.payload_length == sizeof(second), "resync/next-frame");
}

static void test_deleted_and_inserted_bytes_resynchronize()
{
    const uint8_t payload[] = {3, 1, 4, 1, 5};
    uint8_t wire[OEP_UART_MAX_WIRE];
    size_t length = oep_uart_encode_frame(
        OEP_UART_FRAME_DATA, 0, payload, sizeof(payload), wire, sizeof(wire));
    bool recovered = length != 0;

    for (uint8_t mode = 0; mode < 2 && recovered; ++mode) {
        struct oep_uart_decoder decoder;
        struct oep_uart_frame_view frame;
        uint8_t delivered = 0;

        oep_uart_decoder_init(&decoder);
        for (size_t index = 0; index < length; ++index) {
            if (mode == 0 && index == 2) {
                continue;
            }
            if (mode == 1 && index == 2) {
                (void)oep_uart_decoder_feed(&decoder, 0x33, &frame);
            }
            if (oep_uart_decoder_feed(&decoder, wire[index], &frame) ==
                OEP_UART_DECODE_FRAME) {
                ++delivered;
            }
        }
        for (size_t index = 0; index < length; ++index) {
            if (oep_uart_decoder_feed(&decoder, wire[index], &frame) ==
                OEP_UART_DECODE_FRAME) {
                ++delivered;
            }
        }
        recovered = delivered == 1;
    }
    EXPECT_TRUE(recovered, "resync/delete-insert");
}

static void test_partial_frame_timeout_and_retry()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x61, 0x62, 0x63, 0x64,
    };
    const uint8_t message[] = {0x10, 0x00, 0x20, 0x30};
    uint8_t first_attempt[OEP_UART_MAX_WIRE];
    uint16_t first_attempt_length;
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    REQUIRE_TRUE(
        synchronize_pair(
            &host, &host_context, &probe, &probe_context, token),
        "partial-timeout/synchronized");
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&host, message, sizeof(message)),
        "partial-timeout/send");

    first_attempt_length = host_context.outgoing_length;
    REQUIRE_TRUE(
        first_attempt_length > 4 &&
            first_attempt_length <= sizeof(first_attempt),
        "partial-timeout/captured");
    memcpy(
        first_attempt,
        host_context.outgoing,
        first_attempt_length);
    host_context.outgoing_length = 0;

    for (uint16_t index = 0; index < 3; ++index) {
        oep_uart_stopwait_feed(&probe, first_attempt[index]);
    }
    EXPECT_TRUE(
        oep_uart_stopwait_abort_partial_frame(&probe),
        "partial-timeout/aborted");
    for (uint16_t index = 3; index < first_attempt_length; ++index) {
        oep_uart_stopwait_feed(&probe, first_attempt[index]);
    }
    EXPECT_TRUE(
        probe_context.delivery_count == 0,
        "partial-timeout/not-delivered");
    EXPECT_TRUE(
        probe_context.outgoing_length == 0,
        "partial-timeout/not-acked");

    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&host) == OEP_UART_TIMEOUT_RETRIED,
        "partial-timeout/retry");
    pump(&host_context, &probe);
    EXPECT_TRUE(
        probe_context.delivery_count == 1,
        "partial-timeout/recovered");
    pump(&probe_context, &host);
    EXPECT_TRUE(!host.waiting_for_ack, "partial-timeout/acknowledged");
    EXPECT_TRUE(
        !oep_uart_stopwait_abort_partial_frame(&probe),
        "partial-timeout/no-partial-frame");
}

static void test_sync_is_required()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x10, 0x20, 0x30, 0x40,
    };
    const uint8_t message[] = {0x55};
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    EXPECT_TRUE(
        !oep_uart_stopwait_is_active(&host) &&
            !oep_uart_stopwait_is_active(&probe),
        "sync/initially-inactive");
    EXPECT_TRUE(
        !oep_uart_stopwait_send(&host, message, sizeof(message)),
        "sync/host-data-rejected");
    feed_encoded_frame(
        &probe, OEP_UART_FRAME_DATA, 0, message, sizeof(message));
    EXPECT_TRUE(probe_context.delivery_count == 0, "sync/probe-data-dropped");
    EXPECT_TRUE(
        synchronize_pair(
            &host, &host_context, &probe, &probe_context, token),
        "sync/activated");
}

static void test_control_frame_validation()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x91, 0x92, 0x93, 0x94,
    };
    const uint8_t short_token[] = {0x91, 0x92, 0x93};
    const uint8_t message[] = {0x22};
    const uint8_t invalid_ack_payload[] = {0xff};
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    feed_encoded_frame(
        &probe,
        OEP_UART_FRAME_SYNC,
        0,
        short_token,
        sizeof(short_token));
    EXPECT_TRUE(
        !oep_uart_stopwait_is_active(&probe),
        "control/reject-short-sync-token");

    REQUIRE_TRUE(
        synchronize_pair(
            &host, &host_context, &probe, &probe_context, token),
        "control/synchronized");
    feed_encoded_frame(&probe, 5, 0, message, sizeof(message));
    EXPECT_TRUE(
        probe_context.delivery_count == 0 &&
            probe_context.outgoing_length == 0,
        "control/unknown-type-ignored");

    REQUIRE_TRUE(
        oep_uart_stopwait_send(&host, message, sizeof(message)),
        "control/send");
    feed_encoded_frame(
        &host,
        OEP_UART_FRAME_ACK,
        host.transmit_sequence,
        invalid_ack_payload,
        sizeof(invalid_ack_payload));
    EXPECT_TRUE(host.waiting_for_ack, "control/reject-ack-payload");
    pump(&host_context, &probe);
    pump(&probe_context, &host);
    EXPECT_TRUE(!host.waiting_for_ack, "control/valid-ack");
}

static void test_lost_sync_ack_is_retried()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x21, 0x22, 0x23, 0x24,
    };
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    probe_context.drop_next = true;
    REQUIRE_TRUE(
        oep_uart_stopwait_start_sync(&host, token),
        "sync-lost-ack/start");
    pump(&host_context, &probe);
    EXPECT_TRUE(
        host.state == OEP_UART_LINK_SYNCHRONIZING,
        "sync-lost-ack/host-waits");
    EXPECT_TRUE(
        oep_uart_stopwait_is_active(&probe),
        "sync-lost-ack/probe-active");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&host) == OEP_UART_TIMEOUT_RETRIED,
        "sync-lost-ack/retry");
    pump(&host_context, &probe);
    pump(&probe_context, &host);
    EXPECT_TRUE(
        oep_uart_stopwait_is_active(&host),
        "sync-lost-ack/recovered");
    EXPECT_TRUE(
        probe.expected_receive_sequence == 0,
        "sync-lost-ack/no-sequence-reset-side-effect");
}

static void test_same_token_is_idempotent_and_new_token_resets()
{
    const uint8_t first_token[OEP_UART_EPOCH_TOKEN_SIZE] = {1, 1, 1, 1};
    const uint8_t second_token[OEP_UART_EPOCH_TOKEN_SIZE] = {2, 2, 2, 2};
    const uint8_t message[] = {0xa5};
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    REQUIRE_TRUE(
        synchronize_pair(
            &host,
            &host_context,
            &probe,
            &probe_context,
            first_token),
        "sync-token/first-epoch");
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&host, message, sizeof(message)),
        "sync-token/send");
    pump(&host_context, &probe);
    pump(&probe_context, &host);
    REQUIRE_TRUE(
        probe.expected_receive_sequence == 1,
        "sync-token/sequence-advanced");

    feed_encoded_frame(
        &probe,
        OEP_UART_FRAME_SYNC,
        0,
        first_token,
        OEP_UART_EPOCH_TOKEN_SIZE);
    EXPECT_TRUE(
        probe.expected_receive_sequence == 1,
        "sync-token/same-token-idempotent");

    oep_uart_stopwait_reset_epoch(&host);
    REQUIRE_TRUE(
        oep_uart_stopwait_start_sync(&host, second_token),
        "sync-token/new-epoch-start");
    pump(&host_context, &probe);
    EXPECT_TRUE(
        probe.expected_receive_sequence == 0,
        "sync-token/new-token-resets-sequence");
    pump(&probe_context, &host);
    EXPECT_TRUE(
        oep_uart_stopwait_is_active(&host),
        "sync-token/new-epoch-active");
}

static void test_one_sided_reset_and_stale_frames()
{
    const uint8_t old_token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x31, 0x32, 0x33, 0x34,
    };
    const uint8_t new_token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x41, 0x42, 0x43, 0x44,
    };
    const uint8_t message[] = {0xde, 0xad};
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    REQUIRE_TRUE(
        synchronize_pair(
            &host, &host_context, &probe, &probe_context, old_token),
        "reset/first-epoch");

    oep_uart_stopwait_reset_epoch(&probe);
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&host, message, sizeof(message)),
        "reset/send-to-reset-probe");
    pump(&host_context, &probe);
    EXPECT_TRUE(probe_context.delivery_count == 0, "reset/data-dropped");
    EXPECT_TRUE(probe_context.outgoing_length == 0, "reset/no-ack");

    REQUIRE_TRUE(
        oep_uart_stopwait_start_sync(&host, new_token),
        "reset/new-sync");
    feed_encoded_frame(
        &host,
        OEP_UART_FRAME_SYNC_ACK,
        0,
        old_token,
        OEP_UART_EPOCH_TOKEN_SIZE);
    feed_encoded_frame(
        &host, OEP_UART_FRAME_DATA, 0, message, sizeof(message));
    EXPECT_TRUE(
        host.state == OEP_UART_LINK_SYNCHRONIZING,
        "reset/stale-frames-ignored");
    EXPECT_TRUE(host_context.delivery_count == 0, "reset/stale-data-not-delivered");

    pump(&host_context, &probe);
    pump(&probe_context, &host);
    EXPECT_TRUE(
        oep_uart_stopwait_is_active(&host) &&
            oep_uart_stopwait_is_active(&probe),
        "reset/resynchronized");
}

static void test_sync_retry_exhaustion()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x51, 0x52, 0x53, 0x54,
    };
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context, 1);
    host_context.drop_all = true;
    REQUIRE_TRUE(
        oep_uart_stopwait_start_sync(&host, token),
        "sync-exhaust/start");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&host) == OEP_UART_TIMEOUT_RETRIED,
        "sync-exhaust/retry");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&host) == OEP_UART_TIMEOUT_FAILED,
        "sync-exhaust/failed");
    EXPECT_TRUE(
        host.state == OEP_UART_LINK_FAILED,
        "sync-exhaust/failed-state");
}

static void test_normal_stop_and_wait()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {1, 2, 3, 4};
    struct oep_uart_stopwait a;
    struct oep_uart_stopwait b;
    struct EndpointContext a_context;
    struct EndpointContext b_context;
    const uint8_t request[] = {0x10, 0x20, 0x30};

    initialize_unsynchronized_pair(&a, &a_context, &b, &b_context);
    REQUIRE_TRUE(
        synchronize_pair(&a, &a_context, &b, &b_context, token),
        "stopwait/synchronized");
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&a, request, sizeof(request)),
        "stopwait/send");
    pump(&a_context, &b);
    EXPECT_TRUE(b_context.delivery_count == 1, "stopwait/deliver");
    pump(&b_context, &a);
    EXPECT_TRUE(!a.waiting_for_ack, "stopwait/ack");
    EXPECT_TRUE(a.transmit_sequence == 1, "stopwait/next-sequence");
}

static void test_lost_ack_does_not_duplicate_delivery()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {5, 6, 7, 8};
    struct oep_uart_stopwait a;
    struct oep_uart_stopwait b;
    struct EndpointContext a_context;
    struct EndpointContext b_context;
    const uint8_t request[] = {0xaa, 0xbb};

    initialize_unsynchronized_pair(&a, &a_context, &b, &b_context);
    REQUIRE_TRUE(
        synchronize_pair(&a, &a_context, &b, &b_context, token),
        "lost-ack/synchronized");
    b_context.drop_next = true;
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&a, request, sizeof(request)),
        "lost-ack/send");
    pump(&a_context, &b);
    EXPECT_TRUE(b_context.delivery_count == 1, "lost-ack/first-delivery");
    EXPECT_TRUE(a.waiting_for_ack, "lost-ack/waiting");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&a) == OEP_UART_TIMEOUT_RETRIED,
        "lost-ack/retry");
    pump(&a_context, &b);
    EXPECT_TRUE(b_context.delivery_count == 1, "lost-ack/no-duplicate");
    pump(&b_context, &a);
    EXPECT_TRUE(!a.waiting_for_ack, "lost-ack/recovered");
}

static void test_corrupt_data_is_retried_once()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {9, 10, 11, 12};
    struct oep_uart_stopwait a;
    struct oep_uart_stopwait b;
    struct EndpointContext a_context;
    struct EndpointContext b_context;
    const uint8_t request[] = {1, 2, 3, 4};

    initialize_unsynchronized_pair(&a, &a_context, &b, &b_context);
    REQUIRE_TRUE(
        synchronize_pair(&a, &a_context, &b, &b_context, token),
        "corrupt/synchronized");
    a_context.corrupt_next = true;
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&a, request, sizeof(request)),
        "corrupt/send");
    pump(&a_context, &b);
    EXPECT_TRUE(b_context.delivery_count == 0, "corrupt/not-delivered");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&a) == OEP_UART_TIMEOUT_RETRIED,
        "corrupt/retry");
    pump(&a_context, &b);
    EXPECT_TRUE(b_context.delivery_count == 1, "corrupt/recovered");
    pump(&b_context, &a);
    EXPECT_TRUE(!a.waiting_for_ack, "corrupt/ack");
}

static void test_busy_receiver_withholds_ack()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {13, 14, 15, 16};
    struct oep_uart_stopwait a;
    struct oep_uart_stopwait b;
    struct EndpointContext a_context;
    struct EndpointContext b_context;
    const uint8_t request[] = {0x44};

    initialize_unsynchronized_pair(&a, &a_context, &b, &b_context);
    REQUIRE_TRUE(
        synchronize_pair(&a, &a_context, &b, &b_context, token),
        "busy/synchronized");
    b_context.accept_delivery = false;
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&a, request, sizeof(request)),
        "busy/send");
    pump(&a_context, &b);
    EXPECT_TRUE(b_context.delivery_count == 0, "busy/not-delivered");
    EXPECT_TRUE(b_context.outgoing_length == 0, "busy/no-ack");
    b_context.accept_delivery = true;
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&a) == OEP_UART_TIMEOUT_RETRIED,
        "busy/retry");
    pump(&a_context, &b);
    EXPECT_TRUE(b_context.delivery_count == 1, "busy/recovered");
    pump(&b_context, &a);
    EXPECT_TRUE(!a.waiting_for_ack, "busy/ack");
}

static void test_retry_exhaustion()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {17, 18, 19, 20};
    struct oep_uart_stopwait a;
    struct oep_uart_stopwait b;
    struct EndpointContext a_context;
    struct EndpointContext b_context;
    const uint8_t request[] = {0x99};

    initialize_unsynchronized_pair(&a, &a_context, &b, &b_context, 2);
    REQUIRE_TRUE(
        synchronize_pair(&a, &a_context, &b, &b_context, token),
        "exhaust/synchronized");
    a_context.drop_all = true;
    REQUIRE_TRUE(
        oep_uart_stopwait_send(&a, request, sizeof(request)),
        "exhaust/send");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&a) == OEP_UART_TIMEOUT_RETRIED,
        "exhaust/retry-1");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&a) == OEP_UART_TIMEOUT_RETRIED,
        "exhaust/retry-2");
    EXPECT_TRUE(
        oep_uart_stopwait_timeout(&a) == OEP_UART_TIMEOUT_FAILED,
        "exhaust/failed");
    EXPECT_TRUE(!a.waiting_for_ack, "exhaust/not-waiting");
}

static void test_simultaneous_bidirectional_data()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x71, 0x72, 0x73, 0x74,
    };
    uint8_t host_message[OEP_UART_MAX_PAYLOAD];
    uint8_t probe_message[OEP_UART_MAX_PAYLOAD];
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    for (uint8_t index = 0; index < OEP_UART_MAX_PAYLOAD; ++index) {
        host_message[index] = index;
        probe_message[index] = static_cast<uint8_t>(0x80u + index);
    }
    REQUIRE_TRUE(
        synchronize_pair(
            &host, &host_context, &probe, &probe_context, token),
        "duplex/synchronized");
    REQUIRE_TRUE(
        oep_uart_stopwait_send(
            &host, host_message, sizeof(host_message)),
        "duplex/host-send");
    REQUIRE_TRUE(
        oep_uart_stopwait_send(
            &probe, probe_message, sizeof(probe_message)),
        "duplex/probe-send");

    pump(&host_context, &probe);
    pump(&probe_context, &host);
    pump(&host_context, &probe);

    EXPECT_TRUE(
        host_context.delivery_count == 1 &&
            host_context.delivered_length == sizeof(probe_message) &&
            memcmp(
                host_context.delivered,
                probe_message,
                sizeof(probe_message)) == 0,
        "duplex/host-received");
    EXPECT_TRUE(
        probe_context.delivery_count == 1 &&
            probe_context.delivered_length == sizeof(host_message) &&
            memcmp(
                probe_context.delivered,
                host_message,
                sizeof(host_message)) == 0,
        "duplex/probe-received");
    EXPECT_TRUE(
        !host.waiting_for_ack && !probe.waiting_for_ack,
        "duplex/both-acknowledged");
    EXPECT_TRUE(
        host_context.outgoing_length == 0 &&
            probe_context.outgoing_length == 0,
        "duplex/queues-drained");
    EXPECT_TRUE(
        host_context.outgoing_peak <=
            OEP_UART_MAX_WIRE + OEP_UART_ACK_WIRE_SIZE &&
            probe_context.outgoing_peak <=
                OEP_UART_MAX_WIRE + OEP_UART_ACK_WIRE_SIZE,
        "duplex/max-data-plus-ack-queue");
}

static void test_response_data_before_request_ack()
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x81, 0x82, 0x83, 0x84,
    };
    const uint8_t request[] = {0x11, 0x12};
    const uint8_t response[] = {0x91, 0x92, 0x93};
    struct oep_uart_stopwait host;
    struct oep_uart_stopwait probe;
    struct EndpointContext host_context;
    struct EndpointContext probe_context;

    initialize_unsynchronized_pair(
        &host, &host_context, &probe, &probe_context);
    REQUIRE_TRUE(
        synchronize_pair(
            &host, &host_context, &probe, &probe_context, token),
        "response-order/synchronized");
    probe_context.respond_during_delivery = true;
    probe_context.responding_link = &probe;
    probe_context.response = response;
    probe_context.response_length = sizeof(response);

    REQUIRE_TRUE(
        oep_uart_stopwait_send(&host, request, sizeof(request)),
        "response-order/request");
    pump(&host_context, &probe);
    EXPECT_TRUE(
        probe_context.response_send_succeeded,
        "response-order/response-queued");
    EXPECT_TRUE(
        first_queued_frame_type(&probe_context) == OEP_UART_FRAME_DATA,
        "response-order/data-before-ack-observed");

    pump(&probe_context, &host);
    EXPECT_TRUE(
        host_context.delivery_count == 1 &&
            host_context.delivered_length == sizeof(response) &&
            memcmp(
                host_context.delivered,
                response,
                sizeof(response)) == 0,
        "response-order/host-received-response");
    EXPECT_TRUE(
        !host.waiting_for_ack,
        "response-order/request-acknowledged");
    pump(&host_context, &probe);
    EXPECT_TRUE(
        !probe.waiting_for_ack,
        "response-order/response-acknowledged");
}

void setup()
{
    Serial.begin(115200);
    delay(500);

    test_codec_round_trip();
    test_codec_payload_boundaries();
    test_malformed_frame_recovery();
    test_all_single_byte_mutations_resynchronize();
    test_corruption_and_resynchronization();
    test_deleted_and_inserted_bytes_resynchronize();
    test_partial_frame_timeout_and_retry();
    test_sync_is_required();
    test_control_frame_validation();
    test_lost_sync_ack_is_retried();
    test_same_token_is_idempotent_and_new_token_resets();
    test_one_sided_reset_and_stale_frames();
    test_sync_retry_exhaustion();
    test_normal_stop_and_wait();
    test_lost_ack_does_not_duplicate_delivery();
    test_corrupt_data_is_retried_once();
    test_busy_receiver_withholds_ack();
    test_retry_exhaustion();
    test_simultaneous_bidirectional_data();
    test_response_data_before_request_ack();

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
