import sys
import os
import time
import json
import base64
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from app.services.ibe_service import ibe_service

def generate_exact_payload(size_bytes: int) -> str:
    # Generates a JSON string of exactly `size_bytes` UTF-8 bytes
    prefix = '{"vehicle_id":"SIM-TEST-001","status":"active","telemetry":{"speed":55.0,"lat":13.0827,"lng":80.2707},"pad":"'
    suffix = '"}'
    overhead = len((prefix + suffix).encode("utf-8"))
    if size_bytes < overhead:
        raise ValueError(f"Target size {size_bytes} too small for minimal JSON envelope ({overhead} bytes)")
    padding_needed = size_bytes - overhead
    payload = prefix + ("x" * padding_needed) + suffix
    assert len(payload.encode("utf-8")) == size_bytes, f"Expected {size_bytes}, got {len(payload.encode('utf-8'))}"
    return payload

def run_benchmarks(trials_per_size: int = 5):
    payload_targets = [128, 512, 2048]
    summary_report = {}

    print(f"===============================================================")
    print(f"      IBE SCIENTIFIC BENCHMARK REPRODUCTION & AUDIT           ")
    print(f"===============================================================")
    print(f"Trials per payload size: {trials_per_size}")
    print(f"Scheme: {ibe_service.get_status()['scheme']}")
    print(f"Curve: BN128 (py_ecc pure Python)\n")

    for target_size in payload_targets:
        label = f"{target_size}B" if target_size < 1024 else f"{target_size // 1024}KB"
        payload = generate_exact_payload(target_size)
        payload_bytes_len = len(payload.encode("utf-8"))
        
        enc_times = []
        dec_times = []
        raw_ct_sizes = []
        bundle_sizes = []
        auth_successes = 0
        unauth_rejections = 0
        tamper_rejections = 0

        recipient = f"traffic-hub-{target_size}"
        unauth = "rogue-eavesdropper"

        print(f"\n--- Running {trials_per_size} trials for {label} (exact {payload_bytes_len} bytes) ---")

        for trial in range(1, trials_per_size + 1):
            t0 = time.perf_counter()
            bundle = ibe_service.encrypt(recipient, payload)
            t_enc = (time.perf_counter() - t0) * 1000.0

            raw_ct = base64.b64decode(bundle["ciphertext_b64"])
            raw_ct_sizes.append(len(raw_ct))
            bundle_json = json.dumps(bundle)
            bundle_sizes.append(len(bundle_json.encode("utf-8")))
            enc_times.append(t_enc)

            # Authorized decrypt
            t0 = time.perf_counter()
            dec_res = ibe_service.decrypt(bundle, recipient)
            t_dec = (time.perf_counter() - t0) * 1000.0
            dec_times.append(t_dec)

            if dec_res["success"] and dec_res["decrypted_payload"] == payload:
                auth_successes += 1

            # Unauthorized decrypt
            unauth_res = ibe_service.decrypt(bundle, unauth)
            if not unauth_res["success"]:
                unauth_rejections += 1

            # Tampered decrypt
            tampered = dict(bundle)
            tampered_ct = bytearray(raw_ct)
            tampered_ct[0] ^= 0x55
            tampered["ciphertext_b64"] = base64.b64encode(bytes(tampered_ct)).decode("ascii")
            tamper_res = ibe_service.decrypt(tampered, recipient)
            if not tamper_res["success"]:
                tamper_rejections += 1

            print(f"  Trial {trial}/{trials_per_size}: Enc={t_enc:.2f}ms, Dec={t_dec:.2f}ms, AuthOK={dec_res['success']}")

        summary_report[label] = {
            "exact_plaintext_bytes": payload_bytes_len,
            "raw_aesgcm_ciphertext_bytes": raw_ct_sizes[0],
            "raw_expansion_bytes": raw_ct_sizes[0] - payload_bytes_len,
            "full_json_bundle_bytes": bundle_sizes[0],
            "total_bundle_overhead_bytes": bundle_sizes[0] - payload_bytes_len,
            "bundle_overhead_percent": round(((bundle_sizes[0] - payload_bytes_len) / payload_bytes_len) * 100.0, 1),
            "sample_count": trials_per_size,
            "encryption_timing": {
                "median_ms": round(statistics.median(enc_times), 2),
                "mean_ms": round(statistics.mean(enc_times), 2),
                "stdev_ms": round(statistics.stdev(enc_times), 2) if len(enc_times) > 1 else 0.0,
                "min_ms": round(min(enc_times), 2),
                "max_ms": round(max(enc_times), 2),
            },
            "decryption_timing": {
                "median_ms": round(statistics.median(dec_times), 2),
                "mean_ms": round(statistics.mean(dec_times), 2),
                "stdev_ms": round(statistics.stdev(dec_times), 2) if len(dec_times) > 1 else 0.0,
                "min_ms": round(min(dec_times), 2),
                "max_ms": round(max(dec_times), 2),
            },
            "authorized_success_rate": f"{auth_successes}/{trials_per_size} ({auth_successes/trials_per_size*100:.1f}%)",
            "unauthorized_rejection_rate": f"{unauth_rejections}/{trials_per_size} ({unauth_rejections/trials_per_size*100:.1f}%)",
            "tamper_rejection_rate": f"{tamper_rejections}/{trials_per_size} ({tamper_rejections/trials_per_size*100:.1f}%)",
        }

    print("\n================== BENCHMARK AUDIT SUMMARY ==================")
    print(json.dumps(summary_report, indent=2))
    
    with open("benchmark_audit_results.json", "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

if __name__ == "__main__":
    run_benchmarks(trials_per_size=5)
