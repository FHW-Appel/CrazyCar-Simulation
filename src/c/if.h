#ifndef IF_H
#define IF_H
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned short uint8_t;
typedef short int8_t;
extern int fwert;
extern int swert;
extern int8_t leistung_now;
extern int8_t winkel_now;
extern uint16_t abstandvorne;
extern uint16_t abstandlinks;
extern uint16_t abstandrechts;
__declspec(dllexport) void fahr(int f);
__declspec(dllexport) int getfwert();
__declspec(dllexport) void servo(int s);
__declspec(dllexport) int getswert();
__declspec(dllexport) void getfahr(int8_t leistung);
__declspec(dllexport) void getservo(int8_t winkel);
__declspec(dllexport) void getabstandvorne(uint16_t anlagwort);
__declspec(dllexport) void getabstandrechts(uint16_t anlagwort, uint8_t cosAlpha);
__declspec(dllexport) void getabstandlinks(uint16_t anlagwort, uint8_t cosAlpha);
__declspec(dllexport) void regelungtechnik();
__declspec(dllexport) int8_t getFahr();
__declspec(dllexport) int8_t getServo();
__declspec(dllexport) uint16_t get_abstandvorne();
__declspec(dllexport) uint16_t get_abstandrechts();
__declspec(dllexport) uint16_t get_abstandlinks();
#endif