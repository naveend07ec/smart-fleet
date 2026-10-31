import json
import urllib.request
import time

BASE_URL = "http://127.0.0.1:8000/api/security/ibe"

payloads = {
    "128B": json.dumps({"vehicle_id": 1, "lat": 40.7128, "lng": -74.0060, "speed": 45.2, "status": "active", "timestamp": "2026-10-29T12:00:00Z"}),
    "512B": json.dumps({"vehicle_id": 1, "fleet": "EastCoast-Fleet-01", "lat": 40.7128, "lng": -74.0060, "speed": 45.2, "battery": 92.4, "status": "active", "diagnostics": {"engine_temp_c": 88.5, "tire_pressure_psi": [32.1, 32.0, 31.9, 32.2], "voltage": 13.8, "errors": []}, "route": "NYC-BOS-EXPRESS", "payload_padding": "x" * 200}),
    "2KB": json.dumps({"vehicle_id": 1, "fleet": "EastCoast-Fleet-01", "lat": 40.7128, "lng": -74.0060, "speed": 45.2, "readings": [{"sensor": f"s_{i}", "val": i * 1.5, "ok": True} for i in range(50)], "padding": "y" * 1200})
}

results = []

for name, payload in payloads.items():
    print(f"\n--- Testing Payload {name} ({len(payload.encode('utf-8'))} bytes) ---")
    data = json.dumps({
        "recipient_identity": f"traffic-control-{name.lower()}",
        "unauthorized_identity": "rogue-vehicle-node",
        "payload": payload,
        "notes": f"Evaluation trial for payload {name}"
    }).encode("utf-8")

    req = urllib.request.Request(f"{BASE_URL}/experiments", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        results.append(res)
        print(f"Trial ID: {res['experiment_id']}")
        print(f"Payload Size: {res['payload_size_bytes']} bytes")
        print(f"Ciphertext Size: {res['ciphertext_size_bytes']} bytes")
        print(f"Encryption Time: {res['encryption_duration_ms']:.2f} ms")
        print(f"Decryption Time: {res['decryption_duration_ms']:.2f} ms")
        print(f"Authorized Decryption Success: {res['authorized_success']}")
        print(f"Unauthorized Decryption Rejected: {res['unauthorized_rejected']}")
        print(f"Tamper Check Passed: {res['tamper_check_passed']}")

print("\nSummary Results:")
print(json.dumps(results, indent=2))
