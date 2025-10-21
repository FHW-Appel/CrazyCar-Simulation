#include <stdint.h>
#include "cc-lib.h"
#include "myFunktions.h"

/* Globale Zustände kommen aus sim_globals.c */
extern int      fwert, swert;
extern int8_t   leistung_now, winkel_now;
extern uint16_t abstandvorne, abstandlinks, abstandrechts;

/* ----------------------------- Exports ----------------------------- */
__declspec(dllexport) void fahr(int f)                 { fwert = f; }
__declspec(dllexport) int  getfwert(void)              { return fwert; }

__declspec(dllexport) void servo(int s)                { swert = s; }
__declspec(dllexport) int  getswert(void)              { return swert; }

__declspec(dllexport) void getfahr(int8_t leistung)    { leistung_now = leistung; }
__declspec(dllexport) int8_t getFahr(void)             { return leistung_now; }

__declspec(dllexport) void getservo(int8_t winkel)     { winkel_now = winkel; }
__declspec(dllexport) int8_t getServo(void)            { return winkel_now; }

__declspec(dllexport) void getabstandvorne(uint16_t analogwert) {
    abstandvorne = linearisierungVorne(analogwert);
}
__declspec(dllexport) void getabstandrechts(uint16_t analogwert, uint8_t cosAlpha) {
    abstandrechts = linearisierungRechts(analogwert, cosAlpha);
}
__declspec(dllexport) void getabstandlinks(uint16_t analogwert, uint8_t cosAlpha) {
    abstandlinks = linearisierungLinks(analogwert, cosAlpha);
}

__declspec(dllexport) uint16_t get_abstandvorne(void)  { return abstandvorne; }
__declspec(dllexport) uint16_t get_abstandrechts(void) { return abstandrechts; }
__declspec(dllexport) uint16_t get_abstandlinks(void)  { return abstandlinks; }

__declspec(dllexport) void regelungtechnik(void) {
    /* alter Name bleibt erhalten → ruft dein Fahrverhalten */
    fahren1();
}
