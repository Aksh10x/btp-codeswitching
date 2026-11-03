import os
import glob
import json
import subprocess
import numpy as np

def analyze_audio_stream(file_path):
    # Extract 16kHz mono 16-bit PCM
    cmd = [
        "ffmpeg", "-nostats", "-loglevel", "quiet",
        "-i", file_path,
        "-vn", "-sn", "-dn",
        "-ar", "16000", "-ac", "1", "-f", "s16le", "-"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw_data, _ = proc.communicate()
    
    if not raw_data:
        return None
    
    samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    n_samples = len(samples)
    duration_s = n_samples / 16000.0
    
    if n_samples == 0:
        return None

    # Peak level
    peak = np.max(np.abs(samples))
    peak_dbfs = 20 * np.log10(peak) if peak > 0 else -100.0
    
    # Clipping detection (samples hitting full scale within 1 bit)
    clipped_count = int(np.sum(np.abs(samples) >= (32760 / 32768.0)))
    
    # Mean RMS loudness
    rms_total = np.sqrt(np.mean(samples**2))
    rms_dbfs = 20 * np.log10(rms_total) if rms_total > 0 else -100.0
    
    # Frame-level RMS (50ms frames with 25ms hop)
    frame_len = int(16000 * 0.05) # 800 samples = 50ms
    hop_len = int(16000 * 0.025)  # 400 samples = 25ms
    
    if n_samples < frame_len:
        frame_rms = np.array([rms_total])
    else:
        # Vectorized or strided frame RMS
        num_frames = 1 + (n_samples - frame_len) // hop_len
        # Using stride tricks or simple loop
        frames = np.lib.stride_tricks.sliding_window_view(samples[:num_frames * hop_len + frame_len - hop_len], frame_len)[::hop_len]
        frame_rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
        
    frame_db = 20 * np.log10(frame_rms + 1e-9)
    
    # Background noise floor: 10th-15th percentile of frame energy
    noise_floor_db = float(np.percentile(frame_db, 15))
    
    # Adaptive speech threshold: halfway between noise floor and 90th percentile, or noise floor + 10dB
    p90 = float(np.percentile(frame_db, 90))
    speech_threshold_db = max(noise_floor_db + 8.0, min(noise_floor_db + 15.0, (noise_floor_db + p90) / 2.0))
    
    speech_frames = np.sum(frame_db > speech_threshold_db)
    total_frames = len(frame_db)
    speech_fraction = float(speech_frames / total_frames) if total_frames > 0 else 0.0
    silence_fraction = 1.0 - speech_fraction
    
    # Estimated SNR
    snr_db = float(p90 - noise_floor_db)
    
    return {
        "duration_s": float(round(duration_s, 2)),
        "peak_dbfs": float(round(peak_dbfs, 2)),
        "clipped_samples": int(clipped_count),
        "clipping_detected": bool(clipped_count > 0),
        "rms_loudness_dbfs": float(round(rms_dbfs, 2)),
        "estimated_noise_floor_dbfs": float(round(noise_floor_db, 2)),
        "estimated_snr_db": float(round(snr_db, 2)),
        "speech_fraction": float(round(speech_fraction, 3)),
        "silence_fraction": float(round(silence_fraction, 3))
    }

def main():
    with open("analysis/inventory_technical_report.json") as f:
        data = json.load(f)
        
    for item in data:
        fpath = item["file"]
        print(f"Analyzing acoustics for {fpath}...")
        res = analyze_audio_stream(fpath)
        if res:
            item["acoustics"] = res
            
            # Refined plain verdict
            issues = []
            dur = res["duration_s"]
            if dur < 15.0:
                issues.append(f"Short snippet ({dur}s) - likely a false start/test recording")
            if res["clipped_samples"] > 100:
                issues.append(f"Audio clipping detected ({res['clipped_samples']} samples)")
            elif res["peak_dbfs"] > -0.2:
                issues.append(f"Near-clipping peak ({res['peak_dbfs']} dBFS)")
            if res["estimated_snr_db"] < 12.0:
                issues.append(f"Poor SNR ({res['estimated_snr_db']} dB, high background noise)")
            if res["speech_fraction"] < 0.35:
                issues.append(f"Low speech activity ({res['speech_fraction']*100:.1f}%)")
            if res["rms_loudness_dbfs"] < -35.0:
                issues.append(f"Very quiet audio ({res['rms_loudness_dbfs']} dBFS)")
                
            item["clean_for_transcription"] = (len(issues) == 0) or (len(issues) == 1 and "Near-clipping peak" in issues[0])
            item["technical_issues"] = issues
            
    with open("analysis/inventory_technical_report.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Updated inventory_technical_report.json")

if __name__ == "__main__":
    main()
