/*
 * Glove Hand — ESP32 Firmware
 *
 * Reads 5 flex sensors via ADC and streams 13-byte binary packets
 * over USB Serial at 115200 baud, 50 Hz.
 *
 * Wiring (flex sensor voltage divider per finger):
 *   3.3V → flex sensor → ADC pin → 10kΩ → GND
 *
 * ADC pins (all on ADC1 — ADC2 conflicts with WiFi if used later):
 *   GPIO 36 (VP)  — thumb
 *   GPIO 39 (VN)  — index
 *   GPIO 34       — middle
 *   GPIO 35       — ring
 *   GPIO 32       — pinky
 *
 * Packet format (13 bytes):
 *   [0xAA][0xBB][T_H][T_L][I_H][I_L][M_H][M_L][R_H][R_L][P_H][P_L][CHK]
 *   CHK = XOR of bytes 2-11
 */

#define BAUD_RATE      115200
#define SAMPLE_HZ      50
#define SAMPLE_MS      (1000 / SAMPLE_HZ)
#define NUM_FINGERS    5
#define PACKET_SIZE    13

// ADC1 pins only — safe to use alongside WiFi/BLE
const int ADC_PINS[NUM_FINGERS] = {36, 39, 34, 35, 32};

// Smoothing: simple rolling average over N readings
#define SMOOTH_N 4
uint16_t history[NUM_FINGERS][SMOOTH_N];
uint8_t  histIdx = 0;

void setup() {
    Serial.begin(BAUD_RATE);

    // Initialise smoothing buffers with a first reading
    for (int f = 0; f < NUM_FINGERS; f++) {
        uint16_t raw = analogRead(ADC_PINS[f]);
        for (int n = 0; n < SMOOTH_N; n++) {
            history[f][n] = raw;
        }
    }
}

void loop() {
    static unsigned long lastSample = 0;
    unsigned long now = millis();

    if (now - lastSample < SAMPLE_MS) return;
    lastSample = now;

    uint16_t channels[NUM_FINGERS];

    // Read and smooth
    for (int f = 0; f < NUM_FINGERS; f++) {
        history[f][histIdx] = analogRead(ADC_PINS[f]);
        uint32_t sum = 0;
        for (int n = 0; n < SMOOTH_N; n++) sum += history[f][n];
        channels[f] = (uint16_t)(sum / SMOOTH_N);
    }
    histIdx = (histIdx + 1) % SMOOTH_N;

    sendPacket(channels);
}

void sendPacket(uint16_t channels[NUM_FINGERS]) {
    uint8_t buf[PACKET_SIZE];
    buf[0] = 0xAA;
    buf[1] = 0xBB;

    uint8_t checksum = 0;
    for (int i = 0; i < NUM_FINGERS; i++) {
        buf[2 + i * 2] = (channels[i] >> 8) & 0xFF;
        buf[3 + i * 2] =  channels[i]        & 0xFF;
        checksum ^= buf[2 + i * 2];
        checksum ^= buf[3 + i * 2];
    }
    buf[12] = checksum;

    Serial.write(buf, PACKET_SIZE);
}
