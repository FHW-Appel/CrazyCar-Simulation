#ifndef MYFUNKUNKTIONS_H_
#define MYFUNKUNKTIONS_H_

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* --- Fahrverhalten --- */
void      fahren1(void);
void      fahren2(void);      /* optional – nur deklarieren, falls implementiert */
void      uebung1(void);      /* optional */
void      uebung2(void);      /* optional */
void      uebung3(void);      /* optional */

/* --- Linearisierung --- */
/* Zentrale, von Studierenden anzupassende Funktion */
uint16_t  linearisierungAD(uint16_t messwert, uint8_t cosAlpha);

/* Kompatible Alt-API – ruft intern linearisierungAD() */
uint16_t  linearisierungVorne(uint16_t analogwert);
uint16_t  linearisierungLinks(uint16_t analogwert, uint8_t cosAlpha);
uint16_t  linearisierungRechts(uint16_t analogwert, uint8_t cosAlpha);

/* --- Sonstige Helfer --- */
void      akkuSpannungPruefen(uint16_t messwertAkku);
void      ledSchalterTest(void);
int16_t   ro(void);           /* P-Regler rechts (optional nutzbar) */

/* --- einfache Regelbausteine (Integer) --- */
int8_t    Pglied(int8_t e, int8_t K);
int8_t    Iglied(int8_t e, int8_t K, int8_t eAkkumuliert, int8_t eMax);
int8_t    Dglied(int8_t eold, int8_t e, int8_t K);

#ifdef __cplusplus
}
#endif

#endif /* MYFUNKUNKTIONS_H_ */
