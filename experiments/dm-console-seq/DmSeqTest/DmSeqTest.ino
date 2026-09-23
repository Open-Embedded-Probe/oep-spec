// EXPERIMENT: exercise the sequenced DM console. RUN streams a fixed text the host knows
// byte for byte (repeated characters, single-character writes, exactly-full frames);
// "E <text>" is echoed back as "R <text>".
#ifdef DMSEQ_BASELINE                     // the same test over today's SerialDMDATA (framing 1)
#include <SerialDMDATA.h>
#define Con SerialDMDATA
struct { uint32_t reposts = 0, timeouts = 0; } Stats;
#define CON_BEGIN() SerialDMDATA.begin(0)
#define REPOSTS Stats.reposts
#define TIMEOUTS Stats.timeouts
#else
#include "DmSeq.h"
static DmSeq Con;
#define CON_BEGIN() Con.begin()
#define REPOSTS Con.reposts
#define TIMEOUTS Con.timeouts
#endif

#include <CH32.h>

static char line[64];
static uint8_t len;

static void run()
{
    for (int i = 0; i < 40; i++) {
        Con.print('L');
        if (i < 10) Con.print('0');
        Con.print(i);
        Con.print(' ');
        for (int k = 0; k < i % 9 + 1; k++) Con.write('a');   // one frame per character
        Con.print(" 2.00 deadbeef ");
        Con.write((const uint8_t *)"0123456", 7);              // exactly one plain frame
        Con.write('\n');
    }
    Con.print("END reposts=");
    Con.print(REPOSTS);
    Con.print(" timeouts=");
    Con.println(TIMEOUTS);
}

void setup() { CON_BEGIN(); }

void loop()
{
    static uint32_t next;
    while (Con.available()) {
        const char c = (char)Con.read();
        if (c == '\r') continue;
        if (c != '\n') { if (len < sizeof line - 1) line[len++] = c; continue; }
        line[len] = 0;
        len = 0;
        if (!strcmp(line, "RUN")) run();
        else if (!strcmp(line, "RESTART")) { Con.flush(); CH32.restart(); }   // SYN again, host attached
        else if (line[0] == 'E' && line[1] == ' ') { Con.print("R "); Con.println(line + 2); }
        else if (line[0]) { Con.print("? "); Con.println(line); }
    }
    if ((int32_t)(millis() - next) >= 0) { next = millis() + 500; Con.println("dmseq READY"); }
}
