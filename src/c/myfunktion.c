#include <stdint.h>
#include <stdlib.h>
#include "IF.h"
#include "mf.h"

int16_t histerese = 0;
int8_t ereignisBremsen = 0;
int8_t servoIgliedspeicher;
int8_t servoDgliedolde;
int8_t servoDgliedAbkling;

// <== Eigene Funktion und Bedingungen formulieren / schreiben
void fahren1(void) {
    uint16_t k1 = 1.09;
    uint16_t k2 = 1.09;
    uint16_t k3 = 1.09;
    uint16_t kp1 = 0.99;
    uint16_t kp2 = 0.99;
    int16_t sollwert1 = abstandvorne * 1.09;
    int16_t sollwert2 = abstandvorne * 1.09;
    int16_t sollwert3 = abstandvorne * 1.09;
    int16_t sollwert4 = 0;
    int16_t diff = abstandrechts - abstandlinks;
    int8_t leistung = 0;
    leistung = getFahr();

    if (abstandlinks < 130 || abstandrechts < 130) {
        servo((diff - sollwert4) * 0.99);
    }	

    if (abstandvorne >= 100) {
        if (leistung > 18 && leistung < 80) { // FIX: C-Vergleich statt 18 < leistung < 80
            fahr(leistung + (sollwert1 - abstandvorne) * 0.99 + 18);
            if ((leistung + (sollwert1 - abstandvorne) * 0.99 + 18) > 80)
                fahr(80);
        }
        else if (leistung < 0) {
            fahr(20);
        }
    }
    else if (abstandvorne > 50 && abstandvorne < 100) { // FIX: C-Vergleich statt 50 < abstandvorne < 100
        if (leistung >= 18) {
            fahr((leistung - (sollwert2 - abstandvorne) * 0.99));
            if ((leistung - (sollwert2 - abstandvorne) * 0.99) < 18)
                fahr(18);
        }
        else if (leistung < 0) {
            fahr(20);
        }
    }

    if (abstandvorne < 50 || ((abstandvorne < 80) && (leistung < -18))) {
        fahr((-1) * (sollwert3 - abstandvorne) * 0.99 - 18);
    }
}

uint16_t linearisierungVorne(uint16_t analogwert) {
    //TJ Linearisierung der Sensorwerte in cm
    //Variabel erzeugen und initialisieren 
    //Variabel erzeugen und initialisieren 
    if (analogwert < 163) {
        analogwert = 163;
    }

    if (analogwert > 770) {
        analogwert = 770;
    }
    abstandvorne = 23962 / (analogwert + 20);
    // 
    return abstandvorne; // Ergebnis zurückliefern
}

uint16_t linearisierungLinks(uint16_t analogwert, uint8_t cosAlpha) {
    //TJ Linearisierung der Sensorwerte in cm
    //Variabel erzeugen und initialisieren 
    //Variabel erzeugen und initialisieren 
    if (analogwert < 163) {
        analogwert = 163;
    }

    if (analogwert > 770) {
        analogwert = 770;
    }
    abstandlinks = 23962 / (analogwert + 20);
    // 
    return abstandlinks; // Ergebnis zurückliefern
}

uint16_t linearisierungRechts(uint16_t analogwert, uint8_t cosAlpha) {
    //TJ Linearisierung der Sensorwerte in cm
    //Variabel erzeugen und initialisieren 
    //Variabel erzeugen und initialisieren 
    if (analogwert < 163) {
        analogwert = 163;
    }

    if (analogwert > 770) {
        analogwert = 770;
    }
    abstandrechts = 23962 / (analogwert + 20);
    // 
    return abstandrechts; // Ergebnis zurückliefern
}

int8_t Iglied(int8_t e, int8_t K, int8_t eAkkumuliert, int8_t eMax){
    //I-Glied mit externen Speicher und Maximalwert
    int16_t zvar = 0;
    int8_t u = 0;
	
    zvar = (int16_t)e + eAkkumuliert;
    if(abs(zvar) > eMax){
        zvar = eMax;
    }	
    zvar = zvar * K;
    u = zvar / 100;
    return u;
}

int8_t Dglied(int8_t eold, int8_t e, int8_t K){
    //D-Glied mit einfacher Rückwärtsdifferation
    //Alle Werte in Prozent
    int16_t zvar = 0;
    int8_t  u = 0;
	
    zvar = (int16_t)e - eold;
    zvar = zvar/2;
    zvar = zvar * K;
    u = zvar / 100;
    return u;
}
