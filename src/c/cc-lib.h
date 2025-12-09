/**
 * @file cc-lib.h
 * @brief Public C API for car simulation controller
 * 
 * This header defines the public interface for the car controller library:
 * - Control functions (fahr, servo, getfahr, getservo)
 * - Sensor input functions (getabstandvorne, getabstandrechts, getabstandlinks)
 * - Main controller entry point (regelungtechnik)
 * - Getter functions for current state
 * - External declarations for global state variables
 * 
 * Platform support:
 * - Windows: __declspec(dllexport/dllimport)
 * - GCC/Linux: __attribute__((visibility("default")))
 */
/* src/c/cc-lib.h */
#ifndef CC_LIB_H_
#define CC_LIB_H_

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Platform-specific API export/import macros */
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

/* --- Public C API (Functions) ------------------------------------------- */
CC_API void     fahr(int f);                /* Set power command */
CC_API int      getfwert(void);             /* Get power command */
CC_API void     servo(int s);               /* Set steering command */
CC_API int      getswert(void);             /* Get steering command */
CC_API void     getfahr(int8_t leistung);   /* Set current power */
CC_API void     getservo(int8_t winkel);    /* Set current angle */
CC_API void     getabstandvorne(uint16_t analogwert);               /* Update front sensor */
CC_API void     getabstandrechts(uint16_t analogwert, uint8_t cosAlpha);  /* Update right sensor */
CC_API void     getabstandlinks(uint16_t analogwert, uint8_t cosAlpha);   /* Update left sensor */
CC_API void     regelungtechnik(void);      /* Main controller entry point */
CC_API int8_t   getFahr(void);              /* Get current power */
CC_API int8_t   getServo(void);             /* Get current angle */
CC_API uint16_t get_abstandvorne(void);     /* Get front distance (cm) */
CC_API uint16_t get_abstandrechts(void);    /* Get right distance (cm) */
CC_API uint16_t get_abstandlinks(void);     /* Get left distance (cm) */

/* --- External globals (declarations only) ------------------------------- */
/* Definitions are in sim_globals.c */
extern int      fwert;          /* Power command output (-100 to 100) */
extern int      swert;          /* Steering command output (angle) */
extern int8_t   leistung_now;   /* Current power setting */
extern int8_t   winkel_now;     /* Current steering angle */
extern uint16_t abstandvorne;   /* Front distance sensor (cm) */
extern uint16_t abstandlinks;   /* Left distance sensor (cm) */
extern uint16_t abstandrechts;  /* Right distance sensor (cm) */

/* Optional controller helper variables */
extern int16_t  m1, m2, e, y, sollwert;  /* Controller parameters & state */

#ifdef __cplusplus
}
#endif
#endif /* CC_LIB_H_ */
