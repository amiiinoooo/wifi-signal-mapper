import requests
import random

URL = "http://127.0.0.1:5000/data"

# Fake Wi-Fi networks (like real scan)
wifi_names = [
    "MyWifi",
    "Home_5G",
    "GuestNet",
    "Cafe_Free_WiFi",
    "OfficeNet",
    "TP-Link_1234",
    "OrangeFiber",
    "Vodafone_WiFi",
    "Neighbor_WiFi",
    "HiddenNet"
]

# Generate fake RSSI values
networks = []
for name in wifi_names:
    networks.append({
        "ssid": name,
        "bssid": f"AA:BB:CC:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}",
        "rssi": random.randint(-85, -40)
    })

# Sort strongest first
networks = sorted(networks, key=lambda x: x["rssi"], reverse=True)

# Keep top 10 (already 10, but realistic)
networks = networks[:10]

data = {
    "location": "kitchen",  # 👈 change this manually to test different rooms
    "networks": networks
}

try:
    response = requests.post(URL, json=data)
    print("Sent successfully:", response.json())
except Exception as e:
    print("Error:", e)
