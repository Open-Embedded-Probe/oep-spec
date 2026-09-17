#include "uart_stopwait.h"

static void send_ack(struct oep_uart_stopwait *link, uint8_t sequence)
{
    uint8_t ack[OEP_UART_ACK_WIRE_SIZE];
    size_t ack_length = oep_uart_encode_frame(
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

void oep_uart_stopwait_init(
    struct oep_uart_stopwait *link,
    uint8_t retry_limit,
    oep_uart_wire_send_fn wire_send,
    oep_uart_deliver_fn deliver,
    void *callback_context)
{
    oep_uart_decoder_init(&link->decoder);
    link->transmit_length = 0;
    link->transmit_sequence = 0;
    link->expected_receive_sequence = 0;
    link->retries = 0;
    link->retry_limit = retry_limit;
    link->waiting_for_ack = false;
    link->wire_send = wire_send;
    link->deliver = deliver;
    link->callback_context = callback_context;
}

bool oep_uart_stopwait_send(
    struct oep_uart_stopwait *link,
    const uint8_t *message,
    uint16_t message_length)
{
    size_t wire_length;

    if (link->waiting_for_ack || link->wire_send == NULL) {
        return false;
    }
    wire_length = oep_uart_encode_frame(
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
    enum oep_uart_decode_result result = oep_uart_decoder_feed(
        &link->decoder,
        byte,
        &frame);

    if (result != OEP_UART_DECODE_FRAME) {
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

enum oep_uart_timeout_result oep_uart_stopwait_timeout(
    struct oep_uart_stopwait *link)
{
    if (!link->waiting_for_ack) {
        return OEP_UART_TIMEOUT_IDLE;
    }
    if (link->retries >= link->retry_limit) {
        link->waiting_for_ack = false;
        link->transmit_length = 0;
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
    oep_uart_decoder_init(&link->decoder);
    link->transmit_length = 0;
    link->transmit_sequence = 0;
    link->expected_receive_sequence = 0;
    link->retries = 0;
    link->waiting_for_ack = false;
}
