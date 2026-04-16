#include <Arduino.h>
#include <ArduinoJson.h>
#include <AFMotor.h>

// Motor Shield v1 (L293D) — motors on M1 and M2
AF_DCMotor motorLeft(1);
AF_DCMotor motorRight(2);

// Serial JSON buffer
JsonDocument doc;

void setMotors(int leftSpeed, int rightSpeed) {
    // leftSpeed/rightSpeed: -255 to 255
    leftSpeed = constrain(leftSpeed, -255, 255);
    rightSpeed = constrain(rightSpeed, -255, 255);

    motorLeft.setSpeed(abs(leftSpeed));
    if (leftSpeed > 0) motorLeft.run(FORWARD);
    else if (leftSpeed < 0) motorLeft.run(BACKWARD);
    else motorLeft.run(RELEASE);

    motorRight.setSpeed(abs(rightSpeed));
    if (rightSpeed > 0) motorRight.run(FORWARD);
    else if (rightSpeed < 0) motorRight.run(BACKWARD);
    else motorRight.run(RELEASE);
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

    // Stop all motors
    setMotors(0, 0);

    // Announce ready
    doc.clear();
    doc["type"] = "status";
    doc["message"] = "Wall-A firmware ready (Motor Shield v1, M1+M2)";
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
