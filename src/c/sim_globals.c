#include <stdint.h>

/* Stellgrößen + Sensorabstände (wie früher) */
int      fwert = 0;
int      swert = 0;
int8_t   leistung_now = 0;
int8_t   winkel_now = 0;
uint16_t abstandvorne = 0;
uint16_t abstandlinks = 0;
uint16_t abstandrechts = 0;

/* Optional: Für ro() / P-Regler, falls benutzt */
int16_t  m1 = 67;
int16_t  m2 = 100;
int16_t  e  = 0;
int16_t  y  = 0;
int16_t  sollwert = 35;
