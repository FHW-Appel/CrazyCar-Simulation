/* src/c/cc-lib.h */
#ifndef CC_LIB_H_
#define CC_LIB_H_

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(_WIN32) || defined(__CYGWIN__)
  #ifdef CC_EXPORTS
    #define CC_API __declspec(dllexport)
  #else
    #define CC_API __declspec(dllimport)
  #endif
#elif defined(__GNUC__)
  #define CC_API __attribute__((visibility("default")))
#else
  #define CC_API
#endif

/* --- Öffentliche C-API (Funktionen) ------------------------------------- */
CC_API void     fahr(int f);
CC_API int      getfwert(void);
CC_API void     servo(int s);
CC_API int      getswert(void);
CC_API void     getfahr(int8_t leistung);
CC_API void     getservo(int8_t winkel);
CC_API void     getabstandvorne(uint16_t analogwert);
CC_API void     getabstandrechts(uint16_t analogwert, uint8_t cosAlpha);
CC_API void     getabstandlinks(uint16_t analogwert, uint8_t cosAlpha);
CC_API void     regelungtechnik(void);
CC_API int8_t   getFahr(void);
CC_API int8_t   getServo(void);
CC_API uint16_t get_abstandvorne(void);
CC_API uint16_t get_abstandrechts(void);
CC_API uint16_t get_abstandlinks(void);

/* --- (Neu) Externe Globals (nur Deklaration!) --------------------------- */
/* Definitionen stehen in sim_globals.c */
extern int      fwert;
extern int      swert;
extern int8_t   leistung_now;
extern int8_t   winkel_now;
extern uint16_t abstandvorne;
extern uint16_t abstandlinks;
extern uint16_t abstandrechts;

/* optionale Regler-Helper-Variablen */
extern int16_t  m1, m2, e, y, sollwert;

#ifdef __cplusplus
}
#endif
#endif /* CC_LIB_H_ */
