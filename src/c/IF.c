#include"IF.h"
#include"mf.h"
int fwert;
int swert;
int8_t leistung_now;
int8_t winkel_now;
uint16_t abstandvorne;
uint16_t abstandlinks;
uint16_t abstandrechts;

__declspec(dllexport) void fahr(int f) {
	fwert = f;
}
__declspec(dllexport) int getfwert() {
	return fwert;
}
__declspec(dllexport) void getfahr(int8_t leistung) {
	leistung_now = leistung;
}
__declspec(dllexport) void servo(int s) {
	swert = s;
}
__declspec(dllexport) int getswert() {
	return swert;
}
__declspec(dllexport) void getabstandvorne(uint16_t anlagwort) {
	abstandvorne = linearisierungVorne(anlagwort);
}
__declspec(dllexport) void getabstandrechts(uint16_t anlagwort, uint8_t cosAlpha) {
	abstandrechts = linearisierungRechts(anlagwort, cosAlpha);
}
__declspec(dllexport) void getabstandlinks(uint16_t anlagwort, uint8_t cosAlpha) {
	abstandlinks = linearisierungLinks(anlagwort, cosAlpha);
}
__declspec(dllexport) void regelungtechnik() {
	fahren1();
}
__declspec(dllexport) int8_t getFahr() {
	return leistung_now;
}
__declspec(dllexport) uint16_t get_abstandvorne() {
	return abstandvorne;
}
__declspec(dllexport) uint16_t get_abstandrechts() {
	return abstandrechts;
}
__declspec(dllexport) uint16_t get_abstandlinks() {
	return abstandlinks;
}
__declspec(dllexport) void getservo(int8_t winkel) {
	winkel_now = winkel;
}
__declspec(dllexport) int8_t getServo() {
	return winkel_now;
}