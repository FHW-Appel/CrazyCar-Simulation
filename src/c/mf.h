#ifndef MF_H
#define MF_H
typedef unsigned short uint16_t;
typedef short int16_t;
typedef short int8_t;
typedef unsigned short uint8_t;

void fahren1(void); 
uint16_t  linearisierungRechts(uint16_t analogwert, uint8_t cosAlpha);
uint16_t  linearisierungLinks(uint16_t analogwert, uint8_t cosAlpha);
uint16_t linearisierungVorne(uint16_t analogwert);
void akkuSpannungPruefen(uint16_t);
void ledSchalterTest(void);
int16_t ro(void);
int8_t Pglied(int8_t e, int8_t K);
int8_t Iglied(int8_t e, int8_t K, int8_t eAkkumuliert, int8_t eMax);
int8_t Dglied(int8_t eold, int8_t e, int8_t K);
#endif