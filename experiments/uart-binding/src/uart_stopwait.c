#include "uart_stopwait.h"

static void reset_transport_state(struct oep_uart_stopwait *link)
{
    oep_uart_derived_decoder_init(&link->decoder);
    link->transmit_length = 0;
    link->transmit_sequence = 0;
    link->expected_receive_sequence = 0;
    link->retries = 0;
    link->waiting_for_ack = false;
}

static void copy_token(
    uint8_t destination[OEP_UART_EPOCH_TOKEN_SIZE],
    const uint8_t source[OEP_UART_EPOCH_TOKEN_SIZE])
{
    uint8_t index;

    for (index = 0; index < OEP_UART_EPOCH_TOKEN_SIZE; ++index) {
        destination[index] = source[index];
    }
}

static bool token_matches(
    const uint8_t left[OEP_UART_EPOCH_TOKEN_SIZE],
    const uint8_t right[OEP_UART_EPOCH_TOKEN_SIZE])
{
    uint8_t index;

    for (index = 0; index < OEP_UART_EPOCH_TOKEN_SIZE; ++index) {
        if (left[index] != right[index]) {
            return false;
        }
    }
    return true;
}

static void activate_epoch(
    struct oep_uart_stopwait *link,
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE])
{
    reset_transport_state(link);
    copy_token(link->epoch_token, token);
    link->state = OEP_UART_LINK_ACTIVE;
}

static void send_ack(struct oep_uart_stopwait *link, uint8_t sequence)
{
    uint8_t ack[OEP_UART_STOPWAIT_ACK_WIRE_SIZE];
    size_t ack_length = oep_uart_derived_encode_frame(
        OEP_UART_FRAME_ACK,
        sequence,
        NULL,
        0,
        ack,
        sizeof(ack));

    if (ack_length != 0) {
        link->wire_send(link->callback_context, ack, ack_length);
    }
}

static void send_sync_ack(
    struct oep_uart_stopwait *link,
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE])
{
    uint8_t response[
        OEP_UART_EPOCH_TOKEN_SIZE + OEP_UART_DERIVED_RAW_OVERHEAD + 2u];
    size_t response_length = oep_uart_derived_encode_frame(
        OEP_UART_FRAME_SYNC_ACK,
        0,
        token,
        OEP_UART_EPOCH_TOKEN_SIZE,
        response,
        sizeof(response));

    if (response_length != 0 && link->wire_send != NULL) {
        link->wire_send(
            link->callback_context,
            response,
            response_length);
    }
}

void oep_uart_stopwait_init(
    struct oep_uart_stopwait *link,
    enum oep_uart_role role,
    uint8_t retry_limit,
    oep_uart_wire_send_fn wire_send,
    oep_uart_deliver_fn deliver,
    void *callback_context)
{
    reset_transport_state(link);
    link->retry_limit = retry_limit;
    link->role = (uint8_t)role;
    link->state = OEP_UART_LINK_UNSYNCHRONIZED;
    link->wire_send = wire_send;
    link->deliver = deliver;
    link->callback_context = callback_context;
}

bool oep_uart_stopwait_start_sync(
    struct oep_uart_stopwait *link,
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE])
{
    size_t wire_length;

    if (link->role != OEP_UART_ROLE_HOST || token == NULL ||
        link->wire_send == NULL) {
        return false;
    }

    reset_transport_state(link);
    copy_token(link->epoch_token, token);
    wire_length = oep_uart_derived_encode_frame(
        OEP_UART_FRAME_SYNC,
        0,
        token,
        OEP_UART_EPOCH_TOKEN_SIZE,
        link->transmit_wire,
        sizeof(link->transmit_wire));
    if (wire_length == 0) {
        return false;
    }

    link->transmit_length = (uint8_t)wire_length;
    link->state = OEP_UART_LINK_SYNCHRONIZING;
    link->wire_send(
        link->callback_context,
        link->transmit_wire,
        link->transmit_length);
    return true;
}

bool oep_uart_stopwait_is_active(const struct oep_uart_stopwait *link)
{
    return link->state == OEP_UART_LINK_ACTIVE;
}

bool oep_uart_stopwait_send(
    struct oep_uart_stopwait *link,
    const uint8_t *message,
    uint16_t message_length)
{
    size_t wire_length;

    if (link->state != OEP_UART_LINK_ACTIVE ||
        link->waiting_for_ack || link->wire_send == NULL) {
        return false;
    }
    wire_length = oep_uart_derived_encode_frame(
        OEP_UART_FRAME_DATA,
        link->transmit_sequence,
        message,
        message_length,
        link->transmit_wire,
        sizeof(link->transmit_wire));
    if (wire_length == 0) {
        return false;
    }

    link->transmit_length = (uint8_t)wire_length;
    link->retries = 0;
    link->waiting_for_ack = true;
    link->wire_send(
        link->callback_context,
        link->transmit_wire,
        link->transmit_length);
    return true;
}

void oep_uart_stopwait_feed(
    struct oep_uart_stopwait *link,
    uint8_t byte)
{
    struct oep_uart_frame_view frame;
    enum oep_uart_decode_result result = oep_uart_derived_decoder_feed(
        &link->decoder,
        byte,
        &frame);

    if (result != OEP_UART_DECODE_FRAME) {
        return;
    }

    if (frame.type == OEP_UART_FRAME_SYNC) {
        uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE];

        if (link->role != OEP_UART_ROLE_PROBE || frame.sequence != 0 ||
            frame.payload_length != OEP_UART_EPOCH_TOKEN_SIZE) {
            return;
        }
        copy_token(token, frame.payload);
        if (link->state != OEP_UART_LINK_ACTIVE ||
            !token_matches(link->epoch_token, token)) {
            activate_epoch(link, token);
        }
        send_sync_ack(link, token);
        return;
    }

    if (frame.type == OEP_UART_FRAME_SYNC_ACK) {
        uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE];

        if (link->role != OEP_UART_ROLE_HOST ||
            link->state != OEP_UART_LINK_SYNCHRONIZING ||
            frame.sequence != 0 ||
            frame.payload_length != OEP_UART_EPOCH_TOKEN_SIZE) {
            return;
        }
        copy_token(token, frame.payload);
        if (token_matches(link->epoch_token, token)) {
            activate_epoch(link, token);
        }
        return;
    }

    if (link->state != OEP_UART_LINK_ACTIVE) {
        return;
    }

    if (frame.type == OEP_UART_FRAME_ACK) {
        if (frame.payload_length == 0 && link->waiting_for_ack &&
            frame.sequence == link->transmit_sequence) {
            link->waiting_for_ack = false;
            link->transmit_length = 0;
            link->transmit_sequence ^= 1u;
        }
        return;
    }

    if (frame.type != OEP_UART_FRAME_DATA) {
        return;
    }

    if (frame.sequence == link->expected_receive_sequence) {
        if (link->deliver != NULL && link->deliver(
                link->callback_context,
                frame.payload,
                frame.payload_length)) {
            link->expected_receive_sequence ^= 1u;
            send_ack(link, frame.sequence);
        }
        return;
    }

    if (frame.sequence == (uint8_t)(link->expected_receive_sequence ^ 1u)) {
        send_ack(link, frame.sequence);
    }
}

bool oep_uart_stopwait_abort_partial_frame(struct oep_uart_stopwait *link)
{
    return oep_uart_derived_decoder_abort_partial_frame(&link->decoder);
}

enum oep_uart_timeout_result oep_uart_stopwait_timeout(
    struct oep_uart_stopwait *link)
{
    bool awaiting_sync =
        link->state == OEP_UART_LINK_SYNCHRONIZING &&
        link->transmit_length != 0;

    if (!awaiting_sync && !link->waiting_for_ack) {
        return OEP_UART_TIMEOUT_IDLE;
    }
    if (link->retries >= link->retry_limit) {
        link->waiting_for_ack = false;
        link->transmit_length = 0;
        link->state = OEP_UART_LINK_FAILED;
        return OEP_UART_TIMEOUT_FAILED;
    }

    link->retries++;
    link->wire_send(
        link->callback_context,
        link->transmit_wire,
        link->transmit_length);
    return OEP_UART_TIMEOUT_RETRIED;
}

void oep_uart_stopwait_reset_epoch(struct oep_uart_stopwait *link)
{
    reset_transport_state(link);
    link->state = OEP_UART_LINK_UNSYNCHRONIZED;
}
