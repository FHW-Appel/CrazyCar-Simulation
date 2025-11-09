#include <stdint.h>
#include <stdlib.h>
#include "cc-lib.h"        // fahr(), servo(), getFahr() + (ggf. externs)
#include "myFunktions.h"   // Prototypen

/* ==== Globale Zustände (Definition in sim_globals.c) ====
 * Diese Variablen werden im Simulationslauf von den Linearisierungs-Wrappern
 * gesetzt und von der Fahrlogik genutzt. Bitte Namen/Typen nicht ändern.
 */
extern uint16_t abstandvorne;
extern uint16_t abstandlinks;
extern uint16_t abstandrechts;

/* ===== Konstante Parameter für die Linearisierung =====
 * STUDIERENDE: HIER dürft ihr für eure Linearisierung ansetzen!
 * - LINEAR_A / LINEAR_B: Kennlinienparameter eurer Umrechnung (Beispielformel).
 * - ADC_MIN_CLAMP / ADC_MAX_CLAMP: Eingangsbegrenzungen gegen Ausreißer.
 * - COS_0_DEG: Skalierung für „cos(0°) * 100“ (Konvention: 100 == 1.0).
 */
#define LINEAR_A         23962u
#define LINEAR_B         20u
#define ADC_MIN_CLAMP    163u
#define ADC_MAX_CLAMP    770u
#define COS_0_DEG        100u     /* cos(0°) * 100 */

/* =========================================================================
 *  ZENTRALE LINEARISIERUNG
 *  STUDIERENDE: HIER ist der Haupt-Ort für eure Änderungen.
 *  Ziel: Messwert (ADC) → Abstand in cm. Der Winkel-Faktor cosAlpha ist
 *       skaliert (100 ≙ 1.0). Division durch 0 wird vermieden.
 *
 *  Beispiel-Formel:
 *    abstand_cm = (LINEAR_A / (messwert + LINEAR_B)) / (cosAlpha/100)
 *
 *  WICHTIG:
 *  - Behaltet die Funktionssignatur bei (API!).
 *  - Achtet auf ganzzahlige Divisionen (uint32_t verwenden).
 * ========================================================================= */
uint16_t linearisierungAD(uint16_t messwert, uint8_t cosAlpha){
    if (messwert < ADC_MIN_CLAMP) messwert = ADC_MIN_CLAMP;
    if (messwert > ADC_MAX_CLAMP) messwert = ADC_MAX_CLAMP;

    uint32_t cm = LINEAR_A / (uint32_t)(messwert + LINEAR_B);

    if (cosAlpha == 0) cosAlpha = 1;  /* /0 vermeiden */
    cm = (cm * 100u) / (uint32_t)cosAlpha;

    return (uint16_t)cm;
}

/* ========= Alte API-Wrapper =========
 * Diese Wrapper aktualisieren die globalen Abstände und geben sie zurück.
 * Bitte Signaturen unverändert lassen (werden von Python aufgerufen).
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

/* ========= Benötigte Regler-Helfer (wie in Beispiel) =========
 * STUDIERENDE: Falls ihr eure Seiten-/Mittelführung beeinflussen wollt,
 *              dürft ihr hier die einfachen P-Regler-Gewinne (Kpz/Kpn)
 *              vorsichtig anpassen. Signaturen bitte beibehalten.
 */
int16_t lo(uint16_t w){
    int16_t e; // Regelabweichung
    int16_t u; // Stellgröße
    int16_t y; // Regelgröße
    const uint8_t Kpz = 3;   /* <- STUDIERENDE: hier Gain (vorsichtig) ändern */
    const uint8_t Kpn = 8;   /* <- STUDIERENDE: hier Teiler (vorsichtig) ändern */

    y = (int16_t)abstandlinks;
    e = (int16_t)w - y;
    u = (int16_t)(e * (int16_t)Kpz) / (int16_t)Kpn;
    return u;
}

int16_t mo(uint16_t w){
    int16_t e; // Regelabweichung
    int16_t u; // Stellgröße
    int16_t y; // Regelgröße
    const uint8_t Kpz = 3;   /* <- STUDIERENDE: hier Gain (vorsichtig) ändern */
    const uint8_t Kpn = 8;   /* <- STUDIERENDE: hier Teiler (vorsichtig) ändern */

    y = (int16_t)abstandlinks - (int16_t)abstandrechts;
    e = (int16_t)w - y;
    u = (int16_t)(e * (int16_t)Kpz) / (int16_t)Kpn;
    return u;
}

/* ========= Deine einfache Fahrlogik (1:1 übertragen) =========
 * STUDIERENDE: In diesem Block ist der Platz für eure „Fahrlogik“-Anpassungen.
 * - NICHT ändern: die API-Aufrufe fahr(...) (Vortrieb) und servo(...) (Lenkung)
 * - Erlaubt: die Berechnung der Stellgrößen (z. B. mo(0), lo(zielwert), Schwellwerte)
 * - Achtung Totzone: In Python gibt es standardmäßig eine Anfahr-Totzone (≈18).
 *   Deswegen fordert dieses Beispiel mindestens fahr(18), damit das Fahrzeug
 *   in der Simulation wirklich anrollt.
 */
void fahren1(void){
    /* Kleine „Wärmestart“-Phase, damit in der Demo schnell Bewegung sichtbar ist.
     * STUDIERENDE: Ihr könnt die Dauer ändern, müsst aber nicht.
     */
    /*
     * Für Debug-Zwecke setzen wir boot_sig=0, damit die eigentliche Fahrlogik
     * sofort ausgeführt wird und kein Warmup mit fahr(0) die ersten Iterationen
     * die Regler-Ausgaben verdeckt. Dies ist temporär und kann später wieder
     * auf 5 oder einen anderen Wert zurückgesetzt werden.
     */
    static int boot_sig = 0; // mindert warmup (0 => kein Warmup)
    if (boot_sig-- > 0){
        fahr(0);
        servo( (boot_sig % 10) < 5 ? 10 : -10 ); // 0.5s rechts/links "wackeln"
        return;
    }

    // --- ab hier eure echte Logik (Stellgrößenbildung) ---
    int8_t leistung = getFahr();

    /* Kollisions-/Abstandslogik:
     * STUDIERENDE: Schwellwerte oder Lenkstrategie dürft ihr anpassen.
     * Behaltet aber die fahr(...)/servo(...) Aufrufe bei.
     */
    /*
    * Avoidance trigger:
    * - If any sensor sees a close obstacle (<30) trigger avoidance regardless
    *   of the current drive command. This prevents the case where getFahr()
    *   happens to be 0 and the car ignores immediate obstacles.
    * - Additionally, if reversing (leistung < 0) and any sensor sees <40,
    *   also trigger avoidance (keep previous behavior for reverse safety).
    */
        if ( (abstandlinks  < 50) ||
            (abstandvorne  < 50) ||
            (abstandrechts < 50) ||
            ( (leistung < 0) && (abstandlinks  < 50 ||
             abstandvorne < 50 || 
             abstandrechts < 50) ) )
    {
        /* Rückwärts frei fahren & ausweichen */
        fahr(-20);
        servo(abstandlinks > abstandrechts ? 10 : -10);
    } else {
        /* Vortrieb sicher über der Python-Totzone anfordern
         * (Standard: 18 ≙ Anfahrgrenze). Bei Bedarf anpassen.
         */
        fahr(25);

        /* Lenkung aus eurer Mittel-/Seitenführung:
         * STUDIERENDE: Hier könnt ihr z. B. mo(0) / lo(zielwert) anderer Zielwerte
         * verwenden oder die Regelparameter in mo/lo oben anpassen.
         */
        servo(mo(0));
    }
}

/* ========= Stubs (einmalig) =========
 * Diese Funktionen sind Platzhalter für andere Plattformen/Tests.
 * Bitte Signaturen lassen; Inhalte hier sind für die Simulation ohne Relevanz.
 */
int16_t ro(void){ return 0; }
void akkuSpannungPruefen(uint16_t x){ (void)x; }
void ledSchalterTest(void){ /* no-op */ }