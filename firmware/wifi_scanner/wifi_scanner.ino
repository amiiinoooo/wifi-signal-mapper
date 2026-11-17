#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#define BUTTON_PIN 23
#define LED_PIN 4

const char* ssid = "YOUR_WIFI_SSID";        // network the ESP32 joins to reach the server
const char* password = "YOUR_WIFI_PASSWORD";

const char* serverUrl = "http://YOUR_SERVER_IP:5000";

WebServer server(80);

String currentRoom = "";
bool isScanning = false;

unsigned long lastButtonPress = 0;
const int debounceDelay = 200;

// ================= STRUCT =================
struct NetworkData {
  String ssid;
  int totalRSSI;
  int count;
};

std::vector<NetworkData> networks;

// ================= HELPERS =================
void addOrUpdateNetwork(String ssid, int rssi) {
  for (auto &net : networks) {
    if (net.ssid == ssid) {
      net.totalRSSI += rssi;
      net.count++;
      return;
    }
  }
  networks.push_back({ssid, rssi, 1});
}

// ================= SCAN =================
void performScan() {
  if (isScanning || currentRoom == "") return;

  isScanning = true;
  networks.clear();

  Serial0.println("=== STARTING SCAN ===");

  for (int i = 0; i < 3; i++) {
    Serial0.printf("Scan #%d\n", i + 1);

    digitalWrite(LED_PIN, HIGH);
    int n = WiFi.scanNetworks();
    digitalWrite(LED_PIN, LOW);

    for (int j = 0; j < n; j++) {
      String s = WiFi.SSID(j);
      int r = WiFi.RSSI(j);

      if (s != "") {
        addOrUpdateNetwork(s, r);
      }
    }

    WiFi.scanDelete();

    for (int b = 0; b < 6; b++) {
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      delay(50);
    }
  }

  struct Result {
    String ssid;
    int avgRSSI;
  };

  std::vector<Result> results;

  for (auto &net : networks) {
    int avg = net.totalRSSI / net.count;
    results.push_back({net.ssid, avg});
  }

  std::sort(results.begin(), results.end(), [](Result a, Result b) {
    return a.avgRSSI > b.avgRSSI;
  });

  DynamicJsonDocument doc(1024);
  doc["room"] = currentRoom;
  JsonArray arr = doc.createNestedArray("networks");

  int limit = min(5, (int)results.size());

  for (int i = 0; i < limit; i++) {
    JsonObject obj = arr.createNestedObject();
    obj["ssid"] = results[i].ssid;
    obj["rssi"] = results[i].avgRSSI;
  }

  String json;
  serializeJson(doc, json);

  Serial0.println("Sending to Flask:");
  Serial0.println(json);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    int response = http.POST(json);

    Serial0.print("HTTP Response: ");
    Serial0.println(response);

    http.end();
  }

  Serial0.println("=== SCAN DONE ===");

  isScanning = false;
  digitalWrite(LED_PIN, HIGH);
}

// ================= SET ROOM =================
void handleSetRoom() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "No body");
    return;
  }

  DynamicJsonDocument doc(256);
  deserializeJson(doc, server.arg("plain"));

  currentRoom = doc["room"].as<String>();

  Serial0.print("Room SET to: ");
  Serial0.println(currentRoom);

  server.send(200, "text/plain", "ROOM SET");
}

// ================= CLEAR ROOM =================
void handleClearRoom() {
  currentRoom = "";
  Serial0.println("Room CLEARED");

  server.send(200, "text/plain", "ROOM CLEARED");
}

// ================= SETUP =================
void setup() {
  Serial0.begin(115200);
  delay(2000);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);

  digitalWrite(LED_PIN, HIGH);

  WiFi.begin(ssid, password);

  Serial0.print("Connecting");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial0.print(".");
  }

  Serial0.println("\nCONNECTED!");
  Serial0.print("IP: ");
  Serial0.println(WiFi.localIP());

  server.on("/set_room", HTTP_POST, handleSetRoom);
  server.on("/clear_room", HTTP_POST, handleClearRoom);

  server.begin();
  Serial0.println("HTTP SERVER STARTED");
}

// ================= LOOP =================
void loop() {
  server.handleClient();

  if (digitalRead(BUTTON_PIN) == LOW &&
      millis() - lastButtonPress > debounceDelay) {

    lastButtonPress = millis();

    if (currentRoom != "") {
      Serial0.println("Button → scan");
      performScan();
    } else {
      Serial0.println("⚠ No room selected → ignoring");

      for (int i = 0; i < 3; i++) {
        digitalWrite(LED_PIN, LOW);
        delay(100);
        digitalWrite(LED_PIN, HIGH);
        delay(100);
      }
    }
  }
}
