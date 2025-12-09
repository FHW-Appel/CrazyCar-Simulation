/**
 * @file myFunktions.h
 * @brief Controller logic and sensor linearization functions
 * 
 * This header declares:
 * - Driving behavior functions (fahren1, fahren2, uebung1-3)
 * - Sensor linearization functions (ADC to distance conversion)
 * - P/I/D controller building blocks
 * - Utility functions (battery check, LED test)
 * 
 * STUDENTS: Main customization areas:
 * - Driving logic in fahren1() (myFunktions.c)
 * - Linearization parameters in linearisierungAD() (myFunktions.c)
 * - P-controller gains in lo()/mo() functions (myFunktions.c)
 */
/* src/c/myFunktions.h */
#ifndef MYFUNKTIONS_H_
#define MYFUNKTIONS_H_

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* --- Driving behavior functions --- */
void      fahren1(void);      /* Main driving logic (STUDENTS: customize here) */
void      fahren2(void);      /* Optional alternative driving logic */
void      uebung1(void);      /* Optional exercise 1 */
void      uebung2(void);      /* Optional exercise 2 */
void      uebung3(void);      /* Optional exercise 3 */

/* --- Sensor linearization --- */
/**
 * @brief Convert ADC value to distance with angle compensation
 * @param messwert ADC raw value (0-1023)
 * @param cosAlpha Angle factor scaled as uint8_t (100 = cos(0°) = 1.0)
 * @return Distance in centimeters
 * 
 * STUDENTS: Customize linearization parameters LINEAR_A, LINEAR_B in myFunktions.c
 */
uint16_t  linearisierungAD(uint16_t messwert, uint8_t cosAlpha);

/* Legacy API wrappers – call linearisierungAD() internally */
uint16_t  linearisierungVorne(uint16_t analogwert);  /* Front sensor (0° angle) */
uint16_t  linearisierungLinks(uint16_t analogwert, uint8_t cosAlpha);  /* Left sensor */
uint16_t  linearisierungRechts(uint16_t analogwert, uint8_t cosAlpha); /* Right sensor */

/* --- Utility functions --- */
void      akkuSpannungPruefen(uint16_t messwertAkku);  /* Battery voltage check (stub) */
void      ledSchalterTest(void);                       /* LED switch test (stub) */
int16_t   ro(void);                                    /* Right P-controller (optional) */

/* --- Simple controller building blocks (integer arithmetic) --- */
int8_t    Pglied(int8_t e, int8_t K);                              /* Proportional term */
int8_t    Iglied(int8_t e, int8_t K, int8_t eAkkumuliert, int8_t eMax);  /* Integral term */
int8_t    Dglied(int8_t eold, int8_t e, int8_t K);                 /* Derivative term */

#ifdef __cplusplus
}
#endif
#endif /* MYFUNKTIONS_H_ */
