#ifndef OEP_EXPERIMENT_MESSAGE_ROUTING_H
#define OEP_EXPERIMENT_MESSAGE_ROUTING_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define OEP_ROUTING_HEADER_SIZE 6u
#define OEP_ROUTING_ROLE_FUNCTION_REQUEST 0x10u
#define OEP_ROUTING_ROLE_RESULT 0x90u

enum oep_routing_result {
    OEP_ROUTING_COMPLETED = 0,
    OEP_ROUTING_REJECTED_TARGET = 1,
    OEP_ROUTING_REJECTED_OPERATION = 2,
    OEP_ROUTING_REJECTED_PAYLOAD = 3,
};

typedef enum oep_routing_result (*oep_routing_handler)(
    void *context,
    uint8_t operation,
    uint8_t *payload,
    size_t *payload_length,
    size_t payload_capacity);

struct oep_routing_target {
    uint16_t offered_function_reference;
    oep_routing_handler handler;
    void *context;
};

#ifdef __cplusplus
extern "C" {
#endif

bool oep_routing_table_is_valid(
    const struct oep_routing_target *targets,
    size_t target_count);

size_t oep_route_function_request(
    uint8_t *message,
    size_t message_length,
    size_t message_capacity,
    const struct oep_routing_target *targets,
    size_t target_count);

#ifdef __cplusplus
}
#endif

#endif
