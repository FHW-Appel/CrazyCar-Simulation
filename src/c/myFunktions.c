/* myFunktions.c — Simulation (DLL), ohne AVR-Header
 *
 * Enthält:
 *  - fahren1(): dein Fahrverhalten (Integer/Festkomma statt Float)
 *  - linearisierungAD(): zentrale Linearisierung + cos-Korrektur (ANPASSPUNKT)
 *  - Wrapper: linearisierungVorne/Links/Rechts -> nutzen linearisierungAD()
 *  - P/I/D-Glieder (Integer)
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

/* ===== Konstante Parameter Sind aus der Alten MyFunktions AnalogWerte (wie bisher, aber benannt) ===== */
#define LINEAR_A         23962u   /* frühere Zahl Hyperbel */
#define LINEAR_B         20u
#define ADC_MIN_CLAMP    163u
#define ADC_MAX_CLAMP    770u
#define COS_0_DEG        100u     /* cos(0°) * 100 */

/* Fahrverhalten-Faktoren (Festkomma statt Float): 1.09 -> 109/100; 0.99 -> 99/100 */
#define K_109            109
#define K_099             99

/* ===== kleine Helfer ===== */
static inline int16_t clamp_i16(int16_t v, int16_t lo, int16_t hi){
    return (v < lo) ? lo : (v > hi) ? hi : v;
}

/* =========================================================================
 *  ZENTRALE LINEARISIERUNG (ANPASSPUNKT FÜR STUDIERENDE)
 *    abstand_cm = (LINEAR_A / (messwert + LINEAR_B)) / (cosAlpha/100)
 *    cosAlpha: cos(theta) * 100   (0° => 100, 45° ≈ 70)
 * ========================================================================= */
uint16_t linearisierungAD(uint16_t messwert, uint8_t cosAlpha){
    /* 1) clamp wie früher */
    if (messwert < ADC_MIN_CLAMP) messwert = ADC_MIN_CLAMP;
    if (messwert > ADC_MAX_CLAMP) messwert = ADC_MAX_CLAMP;

    /* 2) Hyperbel */
    uint32_t cm = LINEAR_A / (uint32_t)(messwert + LINEAR_B);

    /* 3) Schrägprojektion rückrechnen: /cos -> *100 / cosAlpha */
    if (cosAlpha == 0) cosAlpha = 1;          /* Failsafe, /0 vermeiden */
    cm = (cm * 100u) / (uint32_t)cosAlpha;

    return (uint16_t)cm;
}

/* ========= Alte API-Wrapper (bleiben 1:1 erhalten) ========= */
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

/* ================== Fahrverhalten (wie bisher) ================== */
void fahren1(void){
    /* Festkomma: 1.09 -> 109/100 ; 0.99 -> 99/100 */
    const int16_t Kp_forw = K_109;
    const int16_t Kp_mix  = K_099;

    /* Sollwerte aus abstandvorne (entspricht deinem Code) */
    int16_t sollwert1 = (int16_t)((int32_t)abstandvorne * Kp_forw / 100);
    int16_t sollwert2 = (int16_t)((int32_t)abstandvorne * Kp_forw / 100);
    int16_t sollwert3 = (int16_t)((int32_t)abstandvorne * Kp_forw / 100);
    int16_t sollwert4 = 0;

    int16_t diff     = (int16_t)abstandrechts - (int16_t)abstandlinks;
    int8_t  leistung = getFahr();

    /* Lenkung (wie vorher): (diff - sollwert4) * 0.99 */
    {
        int16_t steer = (int16_t)((int32_t)(diff - sollwert4) * Kp_mix / 100);
        servo(steer);
    }

    if (abstandvorne >= 100) {
        if (leistung > 18 && leistung < 80) {
            /* leistung + (sollwert1 - abstandvorne)*0.99 + 18 */
            int16_t delta = (int16_t)((int32_t)(sollwert1 - (int16_t)abstandvorne) * Kp_mix / 100);
            int16_t cmd   = (int16_t)leistung + delta + 18;
            if (cmd > 80) cmd = 80;
            fahr(cmd);
        } else if (leistung < 0) {
            fahr(20);
        }
    }
    else if (abstandvorne > 50 && abstandvorne < 100) {
        if (leistung >= 18) {
            /* leistung - (sollwert2 - abstandvorne)*0.99 */
            int16_t delta = (int16_t)((int32_t)(sollwert2 - (int16_t)abstandvorne) * Kp_mix / 100);
            int16_t cmd   = (int16_t)leistung - delta;
            if (cmd < 18) cmd = 18;
            fahr(cmd);
        } else if (leistung < 0) {
            fahr(20);
        }
    }

    if (abstandvorne < 50 || ((abstandvorne < 80) && (leistung < -18))) {
        /* (-1) * (sollwert3 - abstandvorne)*0.99 - 18 */
        int16_t delta = (int16_t)((int32_t)(sollwert3 - (int16_t)abstandvorne) * Kp_mix / 100);
        int16_t cmd   = (int16_t)(-delta) - 18;
        fahr(cmd);
    }
}

/* ================== PID-Helfer ================== */
int8_t Pglied(int8_t e, int8_t K){
    /* y = K*e/100  (Integer) */
    int16_t z = (int16_t)K * (int16_t)e;
    return (int8_t)(z / 100);
}
int8_t Iglied(int8_t e, int8_t K, int8_t eAkkumuliert, int8_t eMax){
    int16_t z = (int16_t)e + (int16_t)eAkkumuliert;
    if (z >  eMax) z =  eMax;
    if (z < -eMax) z = -eMax;
    z = (int16_t)(z * K);
    return (int8_t)(z / 100);
}
int8_t Dglied(int8_t eold, int8_t e, int8_t K){
    int16_t z = (int16_t)e - (int16_t)eold;
    z = z / 2;
    z = (int16_t)(z * K);
    return (int8_t)(z / 100);
}

/* ================== Stubs/optional ================== */
int16_t ro(void){ return 0; }                     /* ggf. später aktivieren */
void akkuSpannungPruefen(uint16_t x){ (void)x; }  /* nicht genutzt in SIM */
void ledSchalterTest(void){ /* no-op in SIM */ }
