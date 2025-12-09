/**
 * @file sim_globals.c
 * @brief Global state variables for car simulation controller
 * 
 * This file defines all global state variables used by the C controller:
 * - Control outputs (fwert, swert): Power and steering commands
 * - Sensor inputs (abstandvorne, abstandlinks, abstandrechts): Distance measurements
 * - Controller state variables for P-controller implementation
 * 
 * These variables are declared as extern in cc-lib.h and accessed by
 * the controller logic in myFunktions.c.
 */
#include <stdint.h>
#include "cc-lib.h"   /* Contains extern declarations */

/* Control outputs + sensor distances */
int      fwert = 0;          /* Power command output (-100 to 100) */
int      swert = 0;          /* Steering command output (angle) */
int8_t   leistung_now = 0;   /* Current power setting */
int8_t   winkel_now = 0;     /* Current steering angle */
uint16_t abstandvorne = 0;   /* Front distance sensor (cm) */
uint16_t abstandlinks = 0;   /* Left distance sensor (cm) */
uint16_t abstandrechts = 0;  /* Right distance sensor (cm) */

/* Optional: For ro() / P-controller, if used */
int16_t  m1 = 67;            /* Controller parameter m1 */
int16_t  m2 = 100;           /* Controller parameter m2 */
int16_t  e  = 0;             /* Control error */
int16_t  y  = 0;             /* Control output */
int16_t  sollwert = 35;      /* Setpoint value (cm) */
