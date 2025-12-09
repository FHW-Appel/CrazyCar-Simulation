/**
 * @file cc-lib.c
 * @brief C API implementation for CrazyCar controller
 *
 * This file provides the implementation of the public C API that bridges
 * the Python simulation environment with the C controller logic.
 *
 * Architecture:
 * - Global state variables are defined in sim_globals.c
 * - Function implementations connect Python calls to C controller
 * - Sensor preprocessing uses linearization from myFunktions.c
 * - Main controller entry point delegates to fahren1() driving logic
 *
 * API Categories:
 * 1. Motor control: fahr/getfwert (propulsion)
 * 2. Steering control: servo/getswert (steering angle)
 * 3. Command feedback: getfahr/getFahr, getservo/getServo (current commands)
 * 4. Sensor input: getabstand* (distance sensor ADC → cm conversion)
 * 5. Controller entry: regelungtechnik (main entry point)
 */
/* src/c/cc-lib.c */
#include <stdint.h>
#include "cc-lib.h"
#include "myFunktions.h"

/* Fallback CC_API definition if not already defined by cc-lib.h */
#ifndef CC_API
# if defined(_WIN32) || defined(__CYGWIN__)
#   define CC_API __declspec(dllexport)
# else
#   define CC_API __attribute__((visibility("default")))
# endif
#endif

/* === Function implementations only – globals come from sim_globals.c === */

/* Motor control API: Set and get propulsion command */

CC_API void  fahr(int f)                     { fwert = f; }
CC_API int   getfwert(void)                  { return fwert; }

/* Steering control API: Set and get steering angle command */

CC_API void  servo(int s)                    { swert = s; }
CC_API int   getswert(void)                  { return swert; }

/* Command feedback API: Store and retrieve current drive/steer commands */

CC_API void   getfahr(int8_t leistung)       { leistung_now = leistung; }
CC_API int8_t getFahr(void)                  { return leistung_now; }

CC_API void   getservo(int8_t winkel)        { winkel_now = winkel; }
CC_API int8_t getServo(void)                 { return winkel_now; }

/* Sensor input API: Convert ADC values to distances (cm) with angle compensation */

CC_API void getabstandvorne(uint16_t analogwert) {
    abstandvorne = linearisierungVorne(analogwert);
}
CC_API void getabstandrechts(uint16_t analogwert, uint8_t cosAlpha) {
    abstandrechts = linearisierungRechts(analogwert, cosAlpha);
}
CC_API void getabstandlinks(uint16_t analogwert, uint8_t cosAlpha) {
    abstandlinks = linearisierungLinks(analogwert, cosAlpha);
}

/* Sensor readback API: Get processed distance values */

CC_API uint16_t get_abstandvorne(void)       { return abstandvorne; }
CC_API uint16_t get_abstandrechts(void)      { return abstandrechts; }
CC_API uint16_t get_abstandlinks(void)       { return abstandlinks; }

/* Main controller entry point: Compatible "main controller" entry → calls your driving behavior */

CC_API void regelungtechnik(void) {
    /* Delegates to fahren1() from myFunktions.c which implements the driving logic */
    fahren1();
}
