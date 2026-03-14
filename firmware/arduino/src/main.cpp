#include <Arduino.h>
#include <ArduinoJson.h>

// Motor shield pins (adjust for your specific motor shield)
const int MOTOR_LEFT_PWM = 5;
const int MOTOR_LEFT_DIR = 4;
const int MOTOR_RIGHT_PWM = 6;
const int MOTOR_RIGHT_DIR = 7;

// Serial JSON buffer
JsonDocument doc;

void setupMotors() {
    pinMode(MOTOR_LEFT_PWM, OUTPUT);
    pinMode(MOTOR_LEFT_DIR, OUTPUT);
    pinMode(MOTOR_RIGHT_PWM, OUTPUT);
    pinMode(MOTOR_RIGHT_DIR, OUTPUT);
}

void setMotors(int leftSpeed, int rightSpeed) {
    // leftSpeed/rightSpeed: -255 to 255
    digitalWrite(MOTOR_LEFT_DIR, leftSpeed >= 0 ? HIGH : LOW);
    analogWrite(MOTOR_LEFT_PWM, abs(constrain(leftSpeed, -255, 255)));

    digitalWrite(MOTOR_RIGHT_DIR, rightSpeed >= 0 ? HIGH : LOW);
    analogWrite(MOTOR_RIGHT_PWM, abs(constrain(rightSpeed, -255, 255)));
}

void sendSensorData() {
    doc.clear();
    doc["type"] = "sensors";
    doc["motors"]["left_speed"] = 0;  // TODO: read encoder
    doc["motors"]["right_speed"] = 0;
    doc["battery_voltage"] = analogRead(A0) * (5.0 / 1023.0) * 2.0; // voltage divider
    doc["bump_sensors"]["front_left"] = false;   // TODO: wire bump sensor
    doc["bump_sensors"]["front_right"] = false;

    serializeJson(doc, Serial);
    Serial.println();
}

void handleCommand() {
    if (!Serial.available()) return;

    String input = Serial.readStringUntil('\n');
    DeserializationError error = deserializeJson(doc, input);
    if (error) return;

    const char* type = doc["type"];
    if (!type) return;

    if (strcmp(type, "motor") == 0) {
        int left = doc["left"] | 0;
        int right = doc["right"] | 0;
        setMotors(left, right);
    }
}

void setup() {
    Serial.begin(115200);
    setupMotors();

    // Announce ready
    doc.clear();
    doc["type"] = "status";
    doc["message"] = "Wall-A firmware ready";
    serializeJson(doc, Serial);
    Serial.println();
}

void loop() {
    handleCommand();

    // Send sensor data at ~10Hz
    static unsigned long lastSend = 0;
    if (millis() - lastSend >= 100) {
        sendSensorData();
        lastSend = millis();
    }
}
