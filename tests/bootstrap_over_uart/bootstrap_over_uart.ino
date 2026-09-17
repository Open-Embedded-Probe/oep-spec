#include <Arduino.h>
#include <string.h>

#include <bootstrap_candidate_b_core.h>
#include <uart_stopwait.h>

static unsigned int test_total;
static unsigned int test_passed;

#define WIRE_CAPACITY (OEP_UART_STOPWAIT_MAX_WIRE * 3u)

struct Endpoint {
    struct oep_uart_stopwait link;
    uint8_t wire[WIRE_CAPACITY];
    uint16_t wire_length;
    uint8_t delivered[OEP_UART_MAX_PAYLOAD];
    uint16_t delivered_length;
    uint8_t delivery_count;
    bool handle_bootstrap;
    bool response_started;
    bool core_rejected;
};

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

static void capture_wire(void *opaque, const uint8_t *wire, size_t length)
{
    struct Endpoint *endpoint = static_cast<struct Endpoint *>(opaque);

    if (length > sizeof(endpoint->wire) - endpoint->wire_length) {
        return;
    }
    memcpy(endpoint->wire + endpoint->wire_length, wire, length);
    endpoint->wire_length =
        static_cast<uint16_t>(endpoint->wire_length + length);
}

static bool deliver_message(
    void *opaque,
    const uint8_t *message,
    uint16_t length)
{
    struct Endpoint *endpoint = static_cast<struct Endpoint *>(opaque);

    if (length > sizeof(endpoint->delivered)) {
        return false;
    }
    memcpy(endpoint->delivered, message, length);
    endpoint->delivered_length = length;
    ++endpoint->delivery_count;

    if (endpoint->handle_bootstrap) {
        uint8_t response[OEP_UART_MAX_PAYLOAD];

        memcpy(response, message, length);
        size_t response_length = oep_bootstrap_b_handle_core_message(
            response, length, sizeof(response));
        if (response_length == 0) {
            endpoint->core_rejected = true;
            return true;
        }
        endpoint->response_started = oep_uart_stopwait_send(
            &endpoint->link, response, response_length);
    }
    return true;
}

static void initialize_endpoint(
    struct Endpoint *endpoint,
    enum oep_uart_role role,
    bool handle_bootstrap)
{
    memset(endpoint, 0, sizeof(*endpoint));
    endpoint->handle_bootstrap = handle_bootstrap;
    oep_uart_stopwait_init(
        &endpoint->link,
        role,
        2,
        capture_wire,
        deliver_message,
        endpoint);
}

static void pump(struct Endpoint *source, struct Endpoint *destination)
{
    uint8_t wire[WIRE_CAPACITY];
    uint16_t length = source->wire_length;

    memcpy(wire, source->wire, length);
    source->wire_length = 0;
    for (uint16_t index = 0; index < length; ++index) {
        oep_uart_stopwait_feed(&destination->link, wire[index]);
    }
}

static void synchronize(struct Endpoint *host, struct Endpoint *probe)
{
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE] = {
        0x42u, 0x53u, 0x54u, 0x50u,
    };

    (void)oep_uart_stopwait_start_sync(&host->link, token);
    pump(host, probe);
    pump(probe, host);
}

static void test_bootstrap_round_trip()
{
    const uint8_t request[OEP_BOOTSTRAP_B_REQUEST_SIZE] = {
        0x01u, 0x01u, 0x34u, 0x12u,
        0x4fu, 0x45u, 0x50u, 0x3fu,
        0x01u, 0x01u,
    };
    struct Endpoint host;
    struct Endpoint probe;

    initialize_endpoint(&host, OEP_UART_ROLE_HOST, false);
    initialize_endpoint(&probe, OEP_UART_ROLE_PROBE, true);

    synchronize(&host, &probe);
    check(
        oep_uart_stopwait_is_active(&host.link) &&
            oep_uart_stopwait_is_active(&probe.link),
        F("UART bootstrap synchronized"));

    check(
        oep_uart_stopwait_send(&host.link, request, sizeof(request)),
        F("UART bootstrap request sent"));
    pump(&host, &probe);
    check(
        probe.delivery_count == 1u && probe.response_started,
        F("UART bootstrap core handled"));
    pump(&probe, &host);
    pump(&host, &probe);

    check(
        host.delivery_count == 1u &&
            host.delivered_length == OEP_BOOTSTRAP_B_RESPONSE_SIZE &&
            host.delivered[0] == 0x81u && host.delivered[1] == 0x01u &&
            host.delivered[2] == 0x34u && host.delivered[3] == 0x12u &&
            host.delivered[4] == 0x4fu && host.delivered[7] == 0x21u &&
            host.delivered[8] == 0u && host.delivered[9] == 1u &&
            host.delivered[10] == 0u && host.delivered[11] == 1u &&
            host.delivered[12] == 1u && host.delivered[13] == 1u,
        F("UART bootstrap response received"));
    check(
        !host.link.waiting_for_ack && !probe.link.waiting_for_ack &&
            host.wire_length == 0u && probe.wire_length == 0u,
        F("UART bootstrap transport complete"));
}

static void test_invalid_core_is_transport_accepted()
{
    uint8_t request[OEP_BOOTSTRAP_B_REQUEST_SIZE] = {
        0x01u, 0x01u, 0x34u, 0x12u,
        0x4fu, 0x45u, 0x50u, 0x3fu,
        0x01u, 0x01u,
    };
    struct Endpoint host;
    struct Endpoint probe;

    request[6] ^= 1u;
    initialize_endpoint(&host, OEP_UART_ROLE_HOST, false);
    initialize_endpoint(&probe, OEP_UART_ROLE_PROBE, true);
    synchronize(&host, &probe);

    check(
        oep_uart_stopwait_send(&host.link, request, sizeof(request)),
        F("invalid core transport sent"));
    pump(&host, &probe);
    pump(&probe, &host);

    check(
        probe.delivery_count == 1u && probe.core_rejected &&
            !probe.response_started,
        F("invalid core rejected above binding"));
    check(
        !host.link.waiting_for_ack &&
            oep_uart_stopwait_timeout(&host.link) == OEP_UART_TIMEOUT_IDLE &&
            host.delivery_count == 0u,
        F("invalid core transport not retried"));
}

static void test_unknown_operation_returns_rejected_response()
{
    uint8_t request[OEP_BOOTSTRAP_B_REQUEST_SIZE] = {
        0x01u, 0x7fu, 0x78u, 0x56u,
        0x4fu, 0x45u, 0x50u, 0x3fu,
        0x01u, 0x01u,
    };
    struct Endpoint host;
    struct Endpoint probe;

    initialize_endpoint(&host, OEP_UART_ROLE_HOST, false);
    initialize_endpoint(&probe, OEP_UART_ROLE_PROBE, true);
    synchronize(&host, &probe);

    check(
        oep_uart_stopwait_send(&host.link, request, sizeof(request)),
        F("unknown operation sent"));
    pump(&host, &probe);
    pump(&probe, &host);
    pump(&host, &probe);

    check(
        probe.delivery_count == 1u && probe.response_started &&
            !probe.core_rejected && host.delivery_count == 1u,
        F("unknown operation answered"));
    check(
        host.delivered_length == OEP_BOOTSTRAP_B_RESPONSE_SIZE &&
            host.delivered[0] == 0x81u && host.delivered[1] == 0x7fu &&
            host.delivered[2] == 0x78u && host.delivered[3] == 0x56u &&
            host.delivered[8] ==
                OEP_BOOTSTRAP_B_STATUS_UNSUPPORTED_OPERATION &&
            host.delivered[9] == 0u &&
            !host.link.waiting_for_ack && !probe.link.waiting_for_ack,
        F("unknown operation correlated rejection"));
}

static void test_malformed_lengths_are_transport_accepted()
{
    const uint8_t unidentified[] = {0u, 7u};

    for (uint8_t case_index = 0;
         case_index < sizeof(unidentified);
         ++case_index) {
        uint8_t message[OEP_UART_MAX_PAYLOAD] = {0};
        struct Endpoint host;
        struct Endpoint probe;

        initialize_endpoint(&host, OEP_UART_ROLE_HOST, false);
        initialize_endpoint(&probe, OEP_UART_ROLE_PROBE, true);
        synchronize(&host, &probe);

        bool sent = oep_uart_stopwait_send(
            &host.link, message, unidentified[case_index]);
        pump(&host, &probe);
        pump(&probe, &host);
        if (!sent || probe.delivery_count != 1u ||
            !probe.core_rejected || probe.response_started ||
            host.link.waiting_for_ack || host.delivery_count != 0u ||
            oep_uart_stopwait_timeout(&host.link) !=
                OEP_UART_TIMEOUT_IDLE) {
            check(false, F("unidentified short message transport accepted"));
            return;
        }
    }
    check(true, F("unidentified short message transport accepted"));

    const uint8_t recognized[] = {
        8u, 9u, 15u, OEP_UART_MAX_PAYLOAD,
    };

    for (uint8_t case_index = 0;
         case_index < sizeof(recognized);
         ++case_index) {
        uint8_t message[OEP_UART_MAX_PAYLOAD] = {
            0x01u, 0x01u, 0x34u, 0x12u,
            0x4fu, 0x45u, 0x50u, 0x3fu,
        };
        struct Endpoint host;
        struct Endpoint probe;

        initialize_endpoint(&host, OEP_UART_ROLE_HOST, false);
        initialize_endpoint(&probe, OEP_UART_ROLE_PROBE, true);
        synchronize(&host, &probe);

        bool sent = oep_uart_stopwait_send(
            &host.link, message, recognized[case_index]);
        pump(&host, &probe);
        pump(&probe, &host);
        pump(&host, &probe);
        if (!sent || probe.delivery_count != 1u ||
            probe.core_rejected || !probe.response_started ||
            host.delivery_count != 1u ||
            host.delivered_length != OEP_BOOTSTRAP_B_RESPONSE_SIZE ||
            host.delivered[1] != 0x01u ||
            host.delivered[2] != 0x34u || host.delivered[3] != 0x12u ||
            host.delivered[8] != OEP_BOOTSTRAP_B_STATUS_MALFORMED ||
            host.link.waiting_for_ack || probe.link.waiting_for_ack) {
            check(false, F("recognized malformed length rejected"));
            return;
        }
    }
    check(true, F("recognized malformed length rejected"));
}

void setup()
{
    Serial.begin(115200);
    delay(500);

    test_bootstrap_round_trip();
    test_invalid_core_is_transport_accepted();
    test_unknown_operation_returns_rejected_response();
    test_malformed_lengths_are_transport_accepted();

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
