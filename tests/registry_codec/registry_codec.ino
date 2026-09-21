// Generated OEP v0 codec: every registry vector must round-trip (or be
// rejected) identically in the C library. The Python module is checked by
// test_registry_codec.py against the same vectors.json.
#include <Arduino.h>

#include <oep_v0.h>
#include <oep_v0_vectors.h>

void setup() {
    Serial.begin(115200);
    unsigned int total = 0, passed = 0;
    for (size_t i = 0; i < OEP_V0_VECTOR_COUNT; ++i) {
        const struct oep_v0_vector *v = &oep_v0_vectors[i];
        ++total;
        const int rc = v->roundtrip(v->bytes, v->length);
        const bool ok = v->expect_reject ? (rc == 1) : (rc == 0);
        if (ok) {
            ++passed;
        } else {
            Serial.print("FAIL ");
            Serial.print(v->name);
            Serial.print(" rc=");
            Serial.println(rc);
        }
    }
    ++total;
    if (oep_v0_message_role((const uint8_t *)"\x01", 1) == OEP_V0_ROLE_REQUEST &&
        oep_v0_message_role((const uint8_t *)"\x7f", 1) == 0 && oep_v0_message_role(NULL, 0) == 0) {
        ++passed;
    } else {
        Serial.println("FAIL message_role");
    }
    Serial.print("TEST done ");
    Serial.print(passed);
    Serial.print("/");
    Serial.println(total);
}

void loop() {}
