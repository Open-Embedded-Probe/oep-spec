#include <Arduino.h>

#include <uart_frame.h>
#include <uart_stopwait.h>

static unsigned int test_total;
static unsigned int test_passed;

struct CharacterizationContext {
    uint8_t delivery_count;
};

static void ignore_wire(void *, const uint8_t *, size_t)
{
}

static bool count_delivery(void *opaque, const uint8_t *, uint16_t)
{
    struct CharacterizationContext *context =
        static_cast<struct CharacterizationContext *>(opaque);
    ++context->delivery_count;
    return true;
}

static void feed_frame(
    struct oep_uart_stopwait *receiver,
    uint8_t type,
    uint8_t sequence,
    const uint8_t *payload,
    uint16_t payload_length)
{
    uint8_t wire[OEP_UART_MAX_WIRE];
    size_t length = oep_uart_encode_frame(
        type,
        sequence,
        payload,
        payload_length,
        wire,
        sizeof(wire));

    for (size_t index = 0; index < length; ++index) {
        oep_uart_stopwait_feed(receiver, wire[index]);
    }
}

static void begin_epoch(
    struct oep_uart_stopwait *receiver,
    struct CharacterizationContext *context,
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE])
{
    context->delivery_count = 0;
    oep_uart_stopwait_init(
        receiver,
        OEP_UART_ROLE_PROBE,
        2,
        ignore_wire,
        count_delivery,
        context);
    feed_frame(
        receiver,
        OEP_UART_FRAME_SYNC,
        0,
        token,
        OEP_UART_EPOCH_TOKEN_SIZE);
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

void setup()
{
    const uint8_t first_token[OEP_UART_EPOCH_TOKEN_SIZE] = {1, 2, 3, 4};
    const uint8_t second_token[OEP_UART_EPOCH_TOKEN_SIZE] = {5, 6, 7, 8};
    const uint8_t first_message[] = {0xa0};
    const uint8_t second_message[] = {0xb1};
    struct oep_uart_stopwait receiver;
    struct CharacterizationContext context;

    Serial.begin(115200);
    delay(500);

    begin_epoch(&receiver, &context, first_token);
    feed_frame(
        &receiver,
        OEP_UART_FRAME_DATA,
        0,
        first_message,
        sizeof(first_message));
    feed_frame(
        &receiver,
        OEP_UART_FRAME_DATA,
        0,
        first_message,
        sizeof(first_message));
    feed_frame(
        &receiver,
        OEP_UART_FRAME_DATA,
        1,
        second_message,
        sizeof(second_message));
    check(context.delivery_count == 2, F("ordered duplicate suppression"));
    Serial.print(F("CHARACTERIZATION ordered delivery="));
    Serial.println(context.delivery_count);

    begin_epoch(&receiver, &context, second_token);
    feed_frame(
        &receiver,
        OEP_UART_FRAME_DATA,
        0,
        first_message,
        sizeof(first_message));
    feed_frame(
        &receiver,
        OEP_UART_FRAME_DATA,
        1,
        second_message,
        sizeof(second_message));
    feed_frame(
        &receiver,
        OEP_UART_FRAME_DATA,
        0,
        first_message,
        sizeof(first_message));
    check(context.delivery_count == 3, F("reordered old frame accepted"));
    Serial.print(F("CHARACTERIZATION reordered delivery="));
    Serial.println(context.delivery_count);

    Serial.print(F("TEST done "));
    Serial.print(test_passed);
    Serial.print('/');
    Serial.println(test_total);
}

void loop()
{
    delay(1);
}
