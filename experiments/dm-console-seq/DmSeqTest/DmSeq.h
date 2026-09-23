// EXPERIMENT (2026-09-24): sequenced debug-module console, target side.
// Spec draft: ../SPEC-draft.md. DMSEQ_CRC selects framing 3 (1) or 2 (0).
#pragma once
#include <Arduino.h>

#ifndef DMSEQ_CRC
#define DMSEQ_CRC 1
#endif
#ifndef DMSEQ_CRC_TABLE
#define DMSEQ_CRC_TABLE 0
#endif
#ifndef DMSEQ_WAIT_MS
#define DMSEQ_WAIT_MS 20u
#endif
#ifndef DMSEQ_HOST_WAIT_MS
#define DMSEQ_HOST_WAIT_MS 1000u
#endif
#ifndef DMSEQ_RX_SIZE
#define DMSEQ_RX_SIZE 16u
#endif

class DmSeq : public Print {
public:
    void begin()
    {
        *d0() = 0;
        _s = 0;
        _last_h = 1;
        _posted = false;
        _syn = true;
        _host = false;
        _latched = false;
        _long = false;
        _wrote = false;
        _head = _tail = 0;
    }

    int available()
    {
        service();
        // An empty frame (the host's turn to answer) only when idle: not right after a write.
        // A sketch that alternates available() and print() would otherwise pay a round trip
        // for an empty frame before every print; input rides on the data frames' answers.
        if (!_posted) {
            if (!_wrote) {
                post(nullptr, 0);
            }
            _wrote = false;
        }
        return buffered();
    }

    int read()
    {
        service();
        if (!buffered()) {
            return -1;
        }
        const uint8_t c = _rx[_head];
        _head = (uint8_t)((_head + 1u) % DMSEQ_RX_SIZE);
        return c;
    }

    size_t write(uint8_t c) override { return write(&c, 1); }

    size_t write(const uint8_t *buf, size_t size) override
    {
        size_t sent = 0;
        while (sent < size) {
            if (!waitAcked()) {
                return sent;
            }
            const size_t chunk = size - sent > kMax ? kMax : size - sent;
            post(buf + sent, (uint8_t)chunk);
            _wrote = true;
            sent += chunk;
        }
        return sent;
    }
    using Print::write;

    void flush() { waitAcked(); }

    // Experiment counters.
    uint32_t reposts = 0, timeouts = 0;

private:
#if DMSEQ_CRC
    static constexpr uint8_t kMax = 6;
    static constexpr uint8_t kHostMax = 2;
#else
    static constexpr uint8_t kMax = 7;
    static constexpr uint8_t kHostMax = 3;
#endif
    uint8_t _s, _last_h, _head, _tail;
    bool _posted, _syn, _host, _latched, _long, _wrote;

    uint8_t buffered() const { return (uint8_t)((_tail - _head + DMSEQ_RX_SIZE) % DMSEQ_RX_SIZE); }
    uint32_t _w0, _w1;                    // the frame outstanding, to post again
    uint8_t _rx[DMSEQ_RX_SIZE];

    static volatile uint32_t *d0() { return (volatile uint32_t *)CH32_DM_DATA0_ADDR; }
    static volatile uint32_t *d1() { return (volatile uint32_t *)(CH32_DM_DATA0_ADDR + 4u); }

#if DMSEQ_CRC_TABLE == 2
    // The same CRC-8, four bits at a time: a 16-entry table, two lookups per byte.
    static uint8_t crc8(const uint8_t *p, uint8_t n)
    {
        static const uint8_t t[16] = {0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15,
                                      0x38, 0x3f, 0x36, 0x31, 0x24, 0x23, 0x2a, 0x2d};
        uint8_t crc = 0xff;
        while (n--) {
            crc ^= *p++;
            crc = (uint8_t)(crc << 4) ^ t[crc >> 4];
            crc = (uint8_t)(crc << 4) ^ t[crc >> 4];
        }
        return crc;
    }
#elif DMSEQ_CRC_TABLE == 1
    static uint8_t crc8(const uint8_t *p, uint8_t n)
    {
        // Literal values (poly 0x07). Do not generate this with nested macros: a C1 that uses
        // its argument three times, nested eight deep, expands one entry to 190 KB and the
        // table to ~48 MB of constant expression - the compile ate the WSL VM's memory and took
        // it down four times (2026-09-24).
        static const uint8_t t[256] = {
            0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15, 0x38, 0x3f, 0x36, 0x31, 0x24, 0x23, 0x2a, 0x2d,
            0x70, 0x77, 0x7e, 0x79, 0x6c, 0x6b, 0x62, 0x65, 0x48, 0x4f, 0x46, 0x41, 0x54, 0x53, 0x5a, 0x5d,
            0xe0, 0xe7, 0xee, 0xe9, 0xfc, 0xfb, 0xf2, 0xf5, 0xd8, 0xdf, 0xd6, 0xd1, 0xc4, 0xc3, 0xca, 0xcd,
            0x90, 0x97, 0x9e, 0x99, 0x8c, 0x8b, 0x82, 0x85, 0xa8, 0xaf, 0xa6, 0xa1, 0xb4, 0xb3, 0xba, 0xbd,
            0xc7, 0xc0, 0xc9, 0xce, 0xdb, 0xdc, 0xd5, 0xd2, 0xff, 0xf8, 0xf1, 0xf6, 0xe3, 0xe4, 0xed, 0xea,
            0xb7, 0xb0, 0xb9, 0xbe, 0xab, 0xac, 0xa5, 0xa2, 0x8f, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9d, 0x9a,
            0x27, 0x20, 0x29, 0x2e, 0x3b, 0x3c, 0x35, 0x32, 0x1f, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0d, 0x0a,
            0x57, 0x50, 0x59, 0x5e, 0x4b, 0x4c, 0x45, 0x42, 0x6f, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7d, 0x7a,
            0x89, 0x8e, 0x87, 0x80, 0x95, 0x92, 0x9b, 0x9c, 0xb1, 0xb6, 0xbf, 0xb8, 0xad, 0xaa, 0xa3, 0xa4,
            0xf9, 0xfe, 0xf7, 0xf0, 0xe5, 0xe2, 0xeb, 0xec, 0xc1, 0xc6, 0xcf, 0xc8, 0xdd, 0xda, 0xd3, 0xd4,
            0x69, 0x6e, 0x67, 0x60, 0x75, 0x72, 0x7b, 0x7c, 0x51, 0x56, 0x5f, 0x58, 0x4d, 0x4a, 0x43, 0x44,
            0x19, 0x1e, 0x17, 0x10, 0x05, 0x02, 0x0b, 0x0c, 0x21, 0x26, 0x2f, 0x28, 0x3d, 0x3a, 0x33, 0x34,
            0x4e, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5c, 0x5b, 0x76, 0x71, 0x78, 0x7f, 0x6a, 0x6d, 0x64, 0x63,
            0x3e, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2c, 0x2b, 0x06, 0x01, 0x08, 0x0f, 0x1a, 0x1d, 0x14, 0x13,
            0xae, 0xa9, 0xa0, 0xa7, 0xb2, 0xb5, 0xbc, 0xbb, 0x96, 0x91, 0x98, 0x9f, 0x8a, 0x8d, 0x84, 0x83,
            0xde, 0xd9, 0xd0, 0xd7, 0xc2, 0xc5, 0xcc, 0xcb, 0xe6, 0xe1, 0xe8, 0xef, 0xfa, 0xfd, 0xf4, 0xf3};
        uint8_t crc = 0xff;
        while (n--) crc = t[crc ^ *p++];
        return crc;
    }
#else
    static uint8_t crc8(const uint8_t *p, uint8_t n)
    {
        uint8_t crc = 0xff;
        while (n--) {
            crc ^= *p++;
            for (uint8_t b = 0; b < 8; b++) {
                crc = (uint8_t)((crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1);
            }
        }
        return crc;
    }
#endif

    uint32_t polls() const
    {
        const uint64_t per_ms = (uint64_t)F_CPU / 1000u / 8u;
        return (uint32_t)(per_ms * (_host ? DMSEQ_HOST_WAIT_MS : DMSEQ_WAIT_MS));
    }

    void post(const uint8_t *p, uint8_t n)
    {
        uint8_t b[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        b[0] = (uint8_t)(0x80u | (_s << 5) | (_last_h << 4) | (_syn ? 0x08u : 0u) | n);
        for (uint8_t i = 0; i < n; i++) {
            b[1 + i] = p[i];
        }
#if DMSEQ_CRC
        b[1 + n] = crc8(b, (uint8_t)(1 + n));   // right after the payload
        _long = n >= 3;                          // does anything reach DATA1?
#else
        _long = n > 3;
#endif
        _w1 = (uint32_t)b[4] | ((uint32_t)b[5] << 8) | ((uint32_t)b[6] << 16) | ((uint32_t)b[7] << 24);
        _w0 = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
        if (_long) {
            *d1() = _w1;
        }
        *d0() = _w0;
        _posted = true;
    }

    // Look at DATA0 once. Returns true when nothing is outstanding any more.
    bool service()
    {
        if (!_posted) {
            return true;
        }
        const uint32_t w = *d0();
        if (w & 0x80u) {
            return false;                 // still ours: not answered yet
        }
        const uint8_t a[4] = {(uint8_t)w, (uint8_t)(w >> 8), (uint8_t)(w >> 16), (uint8_t)(w >> 24)};
        const uint8_t k = (a[0] >> 5) & 1u, h = (a[0] >> 4) & 1u, m = a[0] & 7u;
        bool valid = k == _s && m <= kHostMax;
#if DMSEQ_CRC
        valid = valid && m <= 2 && crc8(a, (uint8_t)(1 + m)) == a[1 + m];
#endif
        if (!valid) {
            if (_long) {
                *d1() = _w1;              // post the same frame again; the host
            }
            *d0() = _w0;                  // reads it as a duplicate if it had it
            reposts++;
            return false;
        }
        _posted = false;
        _syn = false;
        _host = true;
        _latched = false;
        _s ^= 1u;
        if (m && h != _last_h) {
            const uint8_t used = (uint8_t)(_tail - _head + DMSEQ_RX_SIZE) % DMSEQ_RX_SIZE;
            if (DMSEQ_RX_SIZE - 1u - used >= m) {
                for (uint8_t i = 0; i < m; i++) {
                    _rx[_tail] = a[1 + i];
                    _tail = (uint8_t)((_tail + 1u) % DMSEQ_RX_SIZE);
                }
                _last_h = h;
            }                             // no room: not taken; the host sends it again
        }
        return true;
    }

    bool waitAcked()
    {
        if (_latched) {
            return service();             // free until a host answers
        }
        for (uint32_t spin = polls(); spin; spin--) {
            if (service()) {
                return true;
            }
        }
        _latched = true;
        _host = false;
        timeouts++;
        // Say so, in the frame itself: same payload and sequence bit, TO set, CRC redone.
        uint8_t b[8] = {(uint8_t)(_w0 | 0x40u), (uint8_t)(_w0 >> 8), (uint8_t)(_w0 >> 16), (uint8_t)(_w0 >> 24),
                        (uint8_t)_w1, (uint8_t)(_w1 >> 8), (uint8_t)(_w1 >> 16), (uint8_t)(_w1 >> 24)};
#if DMSEQ_CRC
        const uint8_t n = b[0] & 7u;
        b[1 + n] = crc8(b, (uint8_t)(1 + n));
        _w1 = (uint32_t)b[4] | ((uint32_t)b[5] << 8) | ((uint32_t)b[6] << 16) | ((uint32_t)b[7] << 24);
        if (_long) {
            *d1() = _w1;
        }
#endif
        _w0 = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
        *d0() = _w0;
        return false;
    }
};
