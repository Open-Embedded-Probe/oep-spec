#ifndef OEP_EXPERIMENT_UART_STOPWAIT_H
#define OEP_EXPERIMENT_UART_STOPWAIT_H

#include "uart_frame.h"

#define OEP_UART_EPOCH_TOKEN_SIZE 4u

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

enum oep_uart_role {
    OEP_UART_ROLE_HOST = 0,
    OEP_UART_ROLE_PROBE = 1,
};

enum oep_uart_link_state {
    OEP_UART_LINK_UNSYNCHRONIZED = 0,
    OEP_UART_LINK_SYNCHRONIZING = 1,
    OEP_UART_LINK_ACTIVE = 2,
    OEP_UART_LINK_FAILED = 3,
};

struct oep_uart_stopwait {
    struct oep_uart_decoder decoder;
    uint8_t transmit_wire[OEP_UART_MAX_WIRE];
    uint8_t epoch_token[OEP_UART_EPOCH_TOKEN_SIZE];
    uint8_t transmit_length;
    uint8_t transmit_sequence;
    uint8_t expected_receive_sequence;
    uint8_t retries;
    uint8_t retry_limit;
    uint8_t role;
    uint8_t state;
    bool waiting_for_ack;
    oep_uart_wire_send_fn wire_send;
    oep_uart_deliver_fn deliver;
    void *callback_context;
};

void oep_uart_stopwait_init(
    struct oep_uart_stopwait *link,
    enum oep_uart_role role,
    uint8_t retry_limit,
    oep_uart_wire_send_fn wire_send,
    oep_uart_deliver_fn deliver,
    void *callback_context);

bool oep_uart_stopwait_start_sync(
    struct oep_uart_stopwait *link,
    const uint8_t token[OEP_UART_EPOCH_TOKEN_SIZE]);

bool oep_uart_stopwait_is_active(
    const struct oep_uart_stopwait *link);

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
