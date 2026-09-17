#include <Arduino.h>
#include <string.h>

#include <uart_frame.h>
#include <uart_stopwait.h>

static unsigned int test_total;
static unsigned int test_passed;

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
    uint8_t outgoing[OEP_UART_MAX_WIRE];
    uint8_t outgoing_length;
    uint8_t delivered[OEP_UART_MAX_PAYLOAD];
    uint16_t delivered_length;
    uint8_t delivery_count;
    bool accept_delivery;
    bool drop_next;
    bool drop_all;
    bool corrupt_next;
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
    if (wire_length > sizeof(context->outgoing)) {
        return;
    }

    memcpy(context->outgoing, wire, wire_length);
    context->outgoing_length = static_cast<uint8_t>(wire_length);
    if (context->corrupt_next && wire_length > 2) {
        context->outgoing[1] ^= 0x20;
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
    return true;
}

static void pump(
    struct EndpointContext *source,
    struct oep_uart_stopwait *destination)
{
    uint8_t bytes[OEP_UART_MAX_WIRE];
    uint8_t length = source->outgoing_length;

    memcpy(bytes, source->outgoing, length);
    source->outgoing_length = 0;
    for (uint8_t index = 0; index < length; ++index) {
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

void setup()
{
    Serial.begin(115200);
    delay(500);

    test_codec_round_trip();
    test_codec_payload_boundaries();
    test_corruption_and_resynchronization();
    test_deleted_and_inserted_bytes_resynchronize();
    test_sync_is_required();
    test_lost_sync_ack_is_retried();
    test_same_token_is_idempotent_and_new_token_resets();
    test_one_sided_reset_and_stale_frames();
    test_sync_retry_exhaustion();
    test_normal_stop_and_wait();
    test_lost_ack_does_not_duplicate_delivery();
    test_corrupt_data_is_retried_once();
    test_busy_receiver_withholds_ack();
    test_retry_exhaustion();

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
