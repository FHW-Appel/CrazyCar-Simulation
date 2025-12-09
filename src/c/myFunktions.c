/**
 * @file myFunktions.c
 * @brief Controller logic implementation and sensor linearization
 * 
 * STUDENTS: Main customization areas:
 * 1. Linearization parameters (LINEAR_A, LINEAR_B, ADC_MIN_CLAMP, ADC_MAX_CLAMP)
 * 2. P-controller gains in lo() and mo() functions (Kpz, Kpn)
 * 3. Driving logic in fahren1() function
 * 4. Collision avoidance thresholds and behavior
 * 
 * Do NOT change:
 * - Function signatures (API compatibility)
 * - Global variable names/types
 * - API calls fahr() and servo()
 */
#include <stdint.h>
#include <stdlib.h>
#include "cc-lib.h"        /* fahr(), servo(), getFahr() + (possibly externs) */
#include "myFunktions.h"   /* Function prototypes */

/* ==== Global state (definition in sim_globals.c) ====
 * These variables are set by linearization wrappers during simulation
 * and used by driving logic. Do NOT change names/types.
 */
extern uint16_t abstandvorne;   /* Front distance sensor (cm) */
extern uint16_t abstandlinks;   /* Left distance sensor (cm) */
extern uint16_t abstandrechts;  /* Right distance sensor (cm) */

/* ===== Constant parameters for linearization =====
 * STUDENTS: CUSTOMIZE these for your linearization!
 * - LINEAR_A / LINEAR_B: Characteristic curve parameters for your conversion formula
 * - ADC_MIN_CLAMP / ADC_MAX_CLAMP: Input limits to reject outliers
 * - COS_0_DEG: Scaling for "cos(0°) * 100" (convention: 100 == 1.0)
 */
#define LINEAR_A         23962u  /* Linearization coefficient A */
#define LINEAR_B         20u     /* Linearization coefficient B */
#define ADC_MIN_CLAMP    163u    /* Minimum ADC value (outlier protection) */
#define ADC_MAX_CLAMP    770u    /* Maximum ADC value (outlier protection) */
#define COS_0_DEG        100u    /* cos(0°) * 100 (100 == 1.0) */

/* =========================================================================
 *  CENTRAL LINEARIZATION FUNCTION
 *  STUDENTS: THIS is the main place for your modifications.
 *  Goal: Convert ADC measurement to distance in cm. Angle factor cosAlpha is
 *        scaled (100 ≙ 1.0). Division by 0 is prevented.
 *
 *  Example formula:
 *    distance_cm = (LINEAR_A / (messwert + LINEAR_B)) / (cosAlpha/100)
 *
 *  IMPORTANT:
 *  - Keep the function signature (API compatibility).
 *  - Use integer arithmetic carefully (uint32_t for intermediate values).
 * ========================================================================= */
uint16_t linearisierungAD(uint16_t messwert, uint8_t cosAlpha){
    /* Clamp input to valid range (outlier protection) */
    if (messwert < ADC_MIN_CLAMP) messwert = ADC_MIN_CLAMP;
    if (messwert > ADC_MAX_CLAMP) messwert = ADC_MAX_CLAMP;

    /* Calculate distance in cm using characteristic curve */
    uint32_t cm = LINEAR_A / (uint32_t)(messwert + LINEAR_B);

    /* Avoid division by zero */
    if (cosAlpha == 0) cosAlpha = 1;
    /* Apply angle compensation */
    cm = (cm * 100u) / (uint32_t)cosAlpha;

    return (uint16_t)cm;
}

/* ========= Legacy API wrappers =========
 * These wrappers update global distance variables and return them.
 * Do NOT change signatures (called from Python).
 */
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

/* ========= Required controller helpers (as in example) =========
 * STUDENTS: If you want to influence your lateral/center guidance,
 *          you can carefully adjust the simple P-controller gains (Kpz/Kpn).
 *          Keep signatures unchanged.
 */
int16_t lo(uint16_t w){
    int16_t e; /* Control error */
    int16_t u; /* Control output */
    int16_t y; /* Process variable */
    const uint8_t Kpz = 3;   /* <- STUDENTS: adjust gain carefully */
    const uint8_t Kpn = 8;   /* <- STUDENTS: adjust divisor carefully */

    y = (int16_t)abstandlinks;
    e = (int16_t)w - y;
    u = (int16_t)(e * (int16_t)Kpz) / (int16_t)Kpn;
    return u;
}

int16_t mo(uint16_t w){
    int16_t e; /* Control error */
    int16_t u; /* Control output */
    int16_t y; /* Process variable */
    const uint8_t Kpz = 3;   /* <- STUDENTS: adjust gain carefully */
    const uint8_t Kpn = 8;   /* <- STUDENTS: adjust divisor carefully */

    y = (int16_t)abstandlinks - (int16_t)abstandrechts;
    e = (int16_t)w - y;
    u = (int16_t)(e * (int16_t)Kpz) / (int16_t)Kpn;
    return u;
}

/* ========= Your simple driving logic (1:1 transfer) =========
 * STUDENTS: This block is the place for your "driving logic" customizations.
 * - DO NOT change: the API calls fahr(...) (propulsion) and servo(...) (steering)
 * - Allowed: calculation of control outputs (e.g. mo(0), lo(target), thresholds)
 * - Attention deadzone: In Python there is a default startup deadzone (≈18).
 *   Therefore this example requests at least fahr(18) so the vehicle
 *   actually starts rolling in the simulation.
 */
void fahren1(void){
    /* Small "warm start" phase for quick movement in demo.
     * STUDENTS: You can change the duration, but don't have to.
     */
    /*
     * For debugging purposes we set boot_sig=0 so the actual driving logic
     * executes immediately and no warmup with fahr(0) masks the controller
     * outputs in the first iterations. This is temporary and can be reset
     * to 5 or another value later.
     */
    static int boot_sig = 0; /* Reduce warmup (0 => no warmup) */
    if (boot_sig-- > 0){
        fahr(0);
        servo( (boot_sig % 10) < 5 ? 10 : -10 ); /* 0.5s right/left "wiggle" */
        return;
    }

    /* --- From here: your real logic (control output formation) --- */
    int8_t leistung = getFahr();

    /* Collision/distance logic:
     * STUDENTS: You can adjust thresholds or steering strategy.
     * Keep the fahr(...)/servo(...) calls.
     */
    /*
    * Avoidance trigger:
    * - If any sensor sees a close obstacle (<50) trigger avoidance regardless
    *   of the current drive command. This prevents the case where getFahr()
    *   happens to be 0 and the car ignores immediate obstacles.
    * - Additionally, if reversing (leistung < 0) and any sensor sees <50,
    *   also trigger avoidance (keep previous behavior for reverse safety).
    */
        if ( (abstandlinks  < 50) ||
            (abstandvorne  < 50) ||
            (abstandrechts < 50) ||
            ( (leistung < 0) && (abstandlinks  < 50 ||
             abstandvorne < 50 || 
             abstandrechts < 50) ) )
    {
        /* Reverse freely & avoid */
        fahr(-20);
        servo(abstandlinks > abstandrechts ? 10 : -10);
    } else {
        /* Request propulsion safely above Python deadzone
         * (default: 18 ≙ startup threshold). Adjust if needed.
         */
        fahr(25);

        /* Steering from your center/lateral guidance:
         * STUDENTS: Here you can use e.g. mo(0) / lo(target) with different targets
         * or adjust controller parameters in mo/lo above.
         */
        servo(mo(0));
    }
}

/* ========= Stubs (one-time) =========
 * These functions are placeholders for other platforms/tests.
 * Keep signatures; contents here are not relevant for simulation.
 */
int16_t ro(void){ return 0; }
void akkuSpannungPruefen(uint16_t x){ (void)x; }
void ledSchalterTest(void){ /* no-op */ }