/* src/c/cc-lib.c */
#include <stdint.h>
#include "cc-lib.h"
#include "myFunktions.h"

/* Falls CC_API aus irgendeinem Grund noch nicht definiert ist: */
#ifndef CC_API
# if defined(_WIN32) || defined(__CYGWIN__)
#   define CC_API __declspec(dllexport)
# else
#   define CC_API __attribute__((visibility("default")))
# endif
#endif

/* === Nur Funktionen – Globals kommen aus sim_globals.c ================== */

CC_API void  fahr(int f)                     { fwert = f; }
CC_API int   getfwert(void)                  { return fwert; }

CC_API void  servo(int s)                    { swert = s; }
CC_API int   getswert(void)                  { return swert; }

CC_API void   getfahr(int8_t leistung)       { leistung_now = leistung; }
CC_API int8_t getFahr(void)                  { return leistung_now; }

CC_API void   getservo(int8_t winkel)        { winkel_now = winkel; }
CC_API int8_t getServo(void)                 { return winkel_now; }

CC_API void getabstandvorne(uint16_t analogwert) {
    abstandvorne = linearisierungVorne(analogwert);
}
CC_API void getabstandrechts(uint16_t analogwert, uint8_t cosAlpha) {
    abstandrechts = linearisierungRechts(analogwert, cosAlpha);
}
CC_API void getabstandlinks(uint16_t analogwert, uint8_t cosAlpha) {
    abstandlinks = linearisierungLinks(analogwert, cosAlpha);
}

CC_API uint16_t get_abstandvorne(void)       { return abstandvorne; }
CC_API uint16_t get_abstandrechts(void)      { return abstandrechts; }
CC_API uint16_t get_abstandlinks(void)       { return abstandlinks; }

CC_API void regelungtechnik(void) {
    /* kompatibler “Hauptregler”-Entry → ruft dein Fahrverhalten */
    fahren1();
}
