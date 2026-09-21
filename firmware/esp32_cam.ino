/*
  EyeGUARDIAN Vision - ESP32-CAM Firmware
  Target Board: AI-Thinker ESP32-CAM with OV2640 Camera Module
  
  IMPORTANT HARDWARE NOTICE:
  Confirm the board pinout matches your exact board before flashing.
  When flashing via FTDI programmer:
  - Connect GPIO 0 to GND while uploading firmware.
  - Disconnect GPIO 0 from GND and press RESET button to run.
  - Power supply must provide at least 5V @ 2A cleanly to avoid brownout resets.

  DEVICE CONFIGURATION:
  - For Left Eye Camera Board:   #define DEVICE_ID "LEFT_CAM_01"
  - For Right Eye Camera Board:  #define DEVICE_ID "RIGHT_CAM_01"
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ==========================================
// 1. NETWORK & BACKEND CONFIGURATION
// ==========================================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend Server IP and Port (Ensure ESP32 and Backend PC are on the same Wi-Fi)
const char* BACKEND_HOST = "192.168.1.100";  // Change to your computer's local IP address
const int   BACKEND_PORT = 8000;

// Device Identity: change to "RIGHT_CAM_01" for the right-eye board
#define DEVICE_ID "LEFT_CAM_01"

// Current Screening ID (Can be updated via Serial or configured before screening)
String currentScreeningId = "abc123";

// Capture interval in milliseconds (default: 15 seconds periodic capture)
const unsigned long CAPTURE_INTERVAL_MS = 15000;
unsigned long lastCaptureTime = 0;

// ==========================================
// 2. AI-THINKER ESP32-CAM PIN DEFINITIONS
// ==========================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Flash LED pin
#define FLASH_LED_PIN      4

// ==========================================
// 3. CAMERA INITIALIZATION
// ==========================================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Frame quality & size (VGA: 640x480 suitable for external eye screening)
  if (psramFound()) {
    config.frame_size   = FRAMESIZE_VGA;  // 640x480
    config.jpeg_quality = 10;             // 0-63 lower number means higher quality
    config.fb_count     = 2;
  } else {
    config.frame_size   = FRAMESIZE_SVGA; // Fallback
    config.jpeg_quality = 12;
    config.fb_count     = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Camera init failed with error 0x%x\n", err);
    return false;
  }

  sensor_t * s = esp_camera_sensor_get();
  // External eye camera sensor tweaks
  s->set_brightness(s, 1);     // -2 to 2
  s->set_contrast(s, 1);       // -2 to 2
  s->set_saturation(s, 0);     // -2 to 2
  s->set_whitebal(s, 1);       // Enable AWB

  Serial.println("[INFO] OV2640 Camera initialized successfully.");
  return true;
}

// ==========================================
// 4. CAPTURE & UPLOAD FUNCTION
// ==========================================
bool captureAndUpload(const String& screeningId) {
  Serial.println("[INFO] Capturing frame from OV2640...");
  
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[ERROR] Frame buffer acquisition failed.");
    return false;
  }

  Serial.printf("[INFO] Frame captured: %u bytes (%dx%d)\n", fb->len, fb->width, fb->height);

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERROR] Wi-Fi not connected. Skipping upload.");
    esp_camera_fb_return(fb);
    return false;
  }

  WiFiClient client;
  HTTPClient http;

  String serverUrl = "http://" + String(BACKEND_HOST) + ":" + String(BACKEND_PORT) +
                     "/api/screenings/" + screeningId + "/images";

  Serial.print("[INFO] Uploading to: ");
  Serial.println(serverUrl);

  http.begin(client, serverUrl);
  http.addHeader("X-Device-Id", DEVICE_ID);

  // Prepare multipart form data payload
  String boundary = "----EyeGuardianBoundaryXYZ";
  String head = "--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"file\"; filename=\"" +
                String(DEVICE_ID) + "_capture.jpg\"\r\n" +
                "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  uint32_t totalLen = head.length() + fb->len + tail.length();

  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.addHeader("Content-Length", String(totalLen));

  // Stream multipart body
  uint8_t * payload = (uint8_t *)malloc(totalLen);
  if (!payload) {
    Serial.println("[ERROR] Failed to allocate memory for multipart upload buffer.");
    http.end();
    esp_camera_fb_return(fb);
    return false;
  }

  memcpy(payload, head.c_str(), head.length());
  memcpy(payload + head.length(), fb->buf, fb->len);
  memcpy(payload + head.length() + fb->len, tail.c_str(), tail.length());

  int httpResponseCode = http.POST(payload, totalLen);
  free(payload);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.printf("[SUCCESS] HTTP Status: %d\n", httpResponseCode);
    Serial.printf("[RESPONSE] %s\n", response.c_str());
  } else {
    Serial.printf("[ERROR] HTTP POST failed, error: %s (code %d)\n",
                  http.errorToString(httpResponseCode).c_str(), httpResponseCode);
  }

  http.end();
  esp_camera_fb_return(fb);
  return (httpResponseCode == 200 || httpResponseCode == 201);
}

// ==========================================
// 5. ARDUINO SETUP & MAIN LOOP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=============================================");
  Serial.println("  EyeGUARDIAN Vision - ESP32-CAM Client Node ");
  Serial.printf("  Device ID: %s\n", DEVICE_ID);
  Serial.println("=============================================");

  // Initialize camera
  if (!initCamera()) {
    Serial.println("[CRITICAL] Camera initialization failed. Halting.");
    while (true) { delay(1000); }
  }

  // Connect to Wi-Fi
  Serial.printf("[INFO] Connecting to Wi-Fi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 25) {
    delay(500);
    Serial.print(".");
    retry++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[INFO] Wi-Fi connected successfully!");
    Serial.print("[INFO] IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WARNING] Wi-Fi connection timed out. Will retry in loop.");
  }
}

void loop() {
  // Allow screening ID update via Serial Monitor
  // Input format: ID:your_screening_id
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command.startsWith("ID:")) {
      currentScreeningId = command.substring(3);
      Serial.printf("[INFO] Updated active screening ID to: %s\n", currentScreeningId.c_str());
      // Trigger immediate capture for new screening
      captureAndUpload(currentScreeningId);
      lastCaptureTime = millis();
    } else if (command == "CAPTURE") {
      captureAndUpload(currentScreeningId);
      lastCaptureTime = millis();
    }
  }

  // Periodic automatic capture for prototype
  unsigned long now = millis();
  if (now - lastCaptureTime >= CAPTURE_INTERVAL_MS) {
    lastCaptureTime = now;
    if (WiFi.status() == WL_CONNECTED && currentScreeningId.length() > 0) {
      captureAndUpload(currentScreeningId);
    }
  }

  delay(100);
}
