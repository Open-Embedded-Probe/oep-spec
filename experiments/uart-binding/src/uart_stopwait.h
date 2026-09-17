#ifndef OEP_EXPERIMENT_UART_STOPWAIT_H
#define OEP_EXPERIMENT_UART_STOPWAIT_H

#include "uart_frame.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*oep_uart_wire_send_fn)(
    void *context,
    const uint8_t *wire,
    size_t wire_length);

typedef bool (*oep_uart_deliver_fn)(
    void *context,
    const uint8_t *message,
    uint16_t message_length);

enum oep_uart_timeout_result {
    OEP_UART_TIMEOUT_IDLE = 0,
    OEP_UART_TIMEOUT_RETRIED = 1,
    OEP_UART_TIMEOUT_FAILED = 2,
};

struct oep_uart_stopwait {
    struct oep_uart_decoder decoder;
    uint8_t transmit_wire[OEP_UART_MAX_WIRE];
    uint8_t transmit_length;
    uint8_t transmit_sequence;
    uint8_t expected_receive_sequence;
    uint8_t retries;
    uint8_t retry_limit;
    bool waiting_for_ack;
    oep_uart_wire_send_fn wire_send;
    oep_uart_deliver_fn deliver;
    void *callback_context;
};

void oep_uart_stopwait_init(
    struct oep_uart_stopwait *link,
    uint8_t retry_limit,
    oep_uart_wire_send_fn wire_send,
    oep_uart_deliver_fn deliver,
    void *callback_context);

bool oep_uart_stopwait_send(
    struct oep_uart_stopwait *link,
    const uint8_t *message,
    uint16_t message_length);

void oep_uart_stopwait_feed(
    struct oep_uart_stopwait *link,
    uint8_t byte);

enum oep_uart_timeout_result oep_uart_stopwait_timeout(
    struct oep_uart_stopwait *link);

void oep_uart_stopwait_reset_epoch(struct oep_uart_stopwait *link);

#ifdef __cplusplus
}
#endif

#endif
