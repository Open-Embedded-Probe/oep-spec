#ifndef OEP_EXPERIMENT_MESSAGE_HEADER_LAYOUT_H
#define OEP_EXPERIMENT_MESSAGE_HEADER_LAYOUT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define OEP_HEADER_ROLE_FUNCTION_REQUEST 0x10u
#define OEP_HEADER_ROLE_ACTIVITY_UPDATE 0x20u
#define OEP_HEADER_ROLE_ACTIVITY_OUTCOME 0x21u
#define OEP_HEADER_ROLE_NOTIFICATION 0x30u
#define OEP_HEADER_ROLE_DATA 0x40u
#define OEP_HEADER_ROLE_RESULT 0x90u

#define OEP_HEADER_SCOPE_NONE 0u
#define OEP_HEADER_SCOPE_OFFERED_FUNCTION 1u

#define OEP_HEADER_HAS_SCOPE 0x01u
#define OEP_HEADER_HAS_CORRELATION 0x02u
#define OEP_HEADER_HAS_REFERENCE 0x04u

#define OEP_UNIFORM_HEADER_SIZE 7u
#define OEP_ROLE_HEADER_REQUEST_SIZE 6u
#define OEP_ROLE_HEADER_RESULT_SIZE 4u
#define OEP_ROLE_HEADER_ACTIVITY_SIZE 4u
#define OEP_ROLE_HEADER_NOTIFICATION_SIZE 5u
#define OEP_ROLE_HEADER_DATA_SIZE 4u

struct oep_header_view {
    uint16_t correlation;
    uint16_t reference;
    uint8_t role;
    uint8_t detail;
    uint8_t scope;
    uint8_t present;
    uint8_t header_length;
};

#ifdef __cplusplus
extern "C" {
#endif

bool oep_decode_uniform_header(
    const uint8_t *message,
    size_t message_length,
    struct oep_header_view *view);

bool oep_decode_role_header(
    const uint8_t *message,
    size_t message_length,
    struct oep_header_view *view);

#ifdef __cplusplus
}
#endif

#endif
