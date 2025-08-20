#ifndef IF_H
#define IF_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

extern int      fwert;
extern int      swert;
extern int8_t   leistung_now;
extern int8_t   winkel_now;
extern uint16_t abstandvorne;
extern uint16_t abstandlinks;
extern uint16_t abstandrechts;

__declspec(dllexport) void     fahr(int f);
__declspec(dllexport) int      getfwert(void);
__declspec(dllexport) void     servo(int s);
__declspec(dllexport) int      getswert(void);
__declspec(dllexport) void     getfahr(int8_t leistung);
__declspec(dllexport) void     getservo(int8_t winkel);
__declspec(dllexport) void     getabstandvorne(uint16_t analogwert);
__declspec(dllexport) void     getabstandrechts(uint16_t analogwert, uint8_t cosAlpha);
__declspec(dllexport) void     getabstandlinks(uint16_t analogwert, uint8_t cosAlpha);
__declspec(dllexport) void     regelungtechnik(void);
__declspec(dllexport) int8_t   getFahr(void);
__declspec(dllexport) int8_t   getServo(void);
__declspec(dllexport) uint16_t get_abstandvorne(void);
__declspec(dllexport) uint16_t get_abstandrechts(void);
__declspec(dllexport) uint16_t get_abstandlinks(void);

#ifdef __cplusplus
}
#endif
#endif
