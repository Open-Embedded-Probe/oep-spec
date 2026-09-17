#include "uart_stopwait.h"

static struct oep_uart_stopwait link;
static uint8_t captured_wire[OEP_UART_STOPWAIT_MAX_WIRE];
static volatile uint8_t sink;

static void wire_send(void *context, const uint8_t *wire, size_t length)
{
    (void)context;
    if (length != 0) {
        sink ^= wire[0];
    }
}

static bool deliver(void *context, const uint8_t *message, uint16_t length)
{
    (void)context;
    if (length != 0) {
        sink ^= message[0];
    }
    return true;
}

int main(void)
{
    static const uint8_t message[4] = {0x4f, 0x45, 0x50, 0x21};

    oep_uart_stopwait_init(
        &link, OEP_UART_ROLE_HOST, 2, wire_send, deliver, 0);
    link.state = OEP_UART_LINK_ACTIVE;
    (void)oep_uart_stopwait_send(&link, message, sizeof(message));
    (void)oep_uart_stopwait_timeout(&link);
    sink ^= captured_wire[0];
    for (;;) {
    }
}
