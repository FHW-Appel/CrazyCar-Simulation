/* myFunktions.c — Simulation (DLL), ohne AVR-Header
 *
 * Enthält:
 *  - linearisierungAD() + Wrapper
 *  - fahren1(): deine einfache Fahrlogik (wie im Beispiel)
 *  - notwendige Helfer: mo(), lo()
 *  - Stubs: ro(), akkuSpannungPruefen(), ledSchalterTest()
 */

#include <stdint.h>
#include <stdlib.h>
#include "cc-lib.h"        // fahr(), servo(), getFahr() + (ggf. externs)
#include "myFunktions.h"   // Prototypen

/* ==== Globale Zustände (Definition in sim_globals.c) ==== */
extern uint16_t abstandvorne;
extern uint16_t abstandlinks;
extern uint16_t abstandrechts;

/* ===== Konstante Parameter für die Linearisierung ===== */
#define LINEAR_A         23962u
#define LINEAR_B         20u
#define ADC_MIN_CLAMP    163u
#define ADC_MAX_CLAMP    770u
#define COS_0_DEG        100u     /* cos(0°) * 100 */

/* =========================================================================
 *  ZENTRALE LINEARISIERUNG
 *    abstand_cm = (LINEAR_A / (messwert + LINEAR_B)) / (cosAlpha/100)
 * ========================================================================= */
uint16_t linearisierungAD(uint16_t messwert, uint8_t cosAlpha){
    if (messwert < ADC_MIN_CLAMP) messwert = ADC_MIN_CLAMP;
    if (messwert > ADC_MAX_CLAMP) messwert = ADC_MAX_CLAMP;

    uint32_t cm = LINEAR_A / (uint32_t)(messwert + LINEAR_B);

    if (cosAlpha == 0) cosAlpha = 1;  /* /0 vermeiden */
    cm = (cm * 100u) / (uint32_t)cosAlpha;

    return (uint16_t)cm;
}

/* ========= Alte API-Wrapper ========= */
uint16_t linearisierungVorne(uint16_t analogwert){
    abstandvorne = linearisierungAD(analogwert, (uint8_t)COS_0_DEG);
    return abstandvorne;
}
uint16_t linearisierungLinks(uint16_t analogwert, uint8_t cosAlpha){
    abstandlinks = linearisierungAD(analogwert, cosAlpha);
    return abstandlinks;
}
uint16_t linearisierungRechts(uint16_t analogwert, uint8_t cosAlpha){
    abstandrechts = linearisierungAD(analogwert, cosAlpha);
    return abstandrechts;
}

/* ========= Benötigte Regler-Helfer (wie in Beispiel) ========= */
int16_t lo(uint16_t w){
    int16_t e; // Regelabweichung
    int16_t u; // Stellgröße
    int16_t y; // Regelgröße
    const uint8_t Kpz = 3;
    const uint8_t Kpn = 8;

    y = (int16_t)abstandlinks;
    e = (int16_t)w - y;
    u = (int16_t)(e * (int16_t)Kpz) / (int16_t)Kpn;
    return u;
}

int16_t mo(uint16_t w){
    int16_t e; // Regelabweichung
    int16_t u; // Stellgröße
    int16_t y; // Regelgröße
    const uint8_t Kpz = 3;
    const uint8_t Kpn = 8;

    y = (int16_t)abstandlinks - (int16_t)abstandrechts;
    e = (int16_t)w - y;
    u = (int16_t)(e * (int16_t)Kpz) / (int16_t)Kpn;
    return u;
}

/* ========= Deine einfache Fahrlogik (1:1 übertragen) ========= */
void fahren1(void){
    static int boot_sig = 30; // ~kurz nach Start
    if (boot_sig-- > 0){
        fahr(0);
        servo( (boot_sig % 10) < 5 ? 10 : -10 ); // 0.5s rechts/links "wackeln"
        return;
    }

    // --- ab hier deine echte Logik ---
    int8_t leistung = getFahr();
    if ( (abstandlinks  < 30 && leistung > 0) ||
         (abstandvorne  < 30 && leistung > 0) ||
         (abstandrechts < 30 && leistung > 0) ||
         (abstandlinks  < 40 && leistung < 0) ||
         (abstandvorne  < 40 && leistung < 0) ||
         (abstandrechts < 40 && leistung < 0) )
    {
        fahr(-20);
        servo(abstandlinks > abstandrechts ? 10 : -10);
    } else {
        fahr(12);
        servo(mo(0));
    }
}


/* ========= Stubs (einmalig) ========= */
int16_t ro(void){ return 0; }
void akkuSpannungPruefen(uint16_t x){ (void)x; }
void ledSchalterTest(void){ /* no-op */ }
