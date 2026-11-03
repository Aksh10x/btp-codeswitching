import os
import glob
import json
import subprocess
from pathlib import Path
import numpy as np

def run_cmd(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode, result.stdout, result.stderr

def get_ffprobe_info(file_path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path
    ]
    ret, stdout, stderr = run_cmd(cmd)
    if ret != 0:
        return None
    return json.loads(stdout)

def analyze_audio_volume_ebu(file_path):
    cmd_ebu = ["ffmpeg", "-nostats", "-i", file_path, "-filter_complex", "ebur128", "-vn", "-sn", "-dn", "-f", "null", "-"]
    ret_ebu, stdout_ebu, stderr_ebu = run_cmd(cmd_ebu)
    integrated_lufs = None
    loudness_range_lu = None
    true_peak_db = None
    for line in stderr_ebu.splitlines():
        if "I:" in line and "LUFS" in line:
            parts = line.split("I:")[1].split("LUFS")[0].strip()
            try:
                integrated_lufs = float(parts)
            except:
                pass
        elif "LRA:" in line and "LU" in line:
            parts = line.split("LRA:")[1].split("LU")[0].strip()
            try:
                loudness_range_lu = float(parts)
            except:
                pass
        elif "Peak:" in line and "dBFS" in line:
            parts = line.split("Peak:")[1].split("dBFS")[0].strip()
            try:
                true_peak_db = float(parts)
            except:
                pass

    return {
        "integrated_lufs": integrated_lufs,
        "loudness_range_lu": loudness_range_lu,
        "true_peak_db": true_peak_db
    }

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

    peak = float(np.max(np.abs(samples)))
    peak_dbfs = float(20 * np.log10(peak)) if peak > 0 else -100.0
    clipped_count = int(np.sum(np.abs(samples) >= (32760 / 32768.0)))
    
    rms_total = float(np.sqrt(np.mean(samples**2)))
    rms_dbfs = float(20 * np.log10(rms_total)) if rms_total > 0 else -100.0
    
    frame_len = int(16000 * 0.05)
    hop_len = int(16000 * 0.025)
    
    if n_samples < frame_len:
        frame_rms = np.array([rms_total])
    else:
        num_frames = 1 + (n_samples - frame_len) // hop_len
        frames = np.lib.stride_tricks.sliding_window_view(samples[:num_frames * hop_len + frame_len - hop_len], frame_len)[::hop_len]
        frame_rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
        
    frame_db = 20 * np.log10(frame_rms + 1e-9)
    noise_floor_db = float(np.percentile(frame_db, 15))
    p90 = float(np.percentile(frame_db, 90))
    speech_threshold_db = max(noise_floor_db + 6.0, min(noise_floor_db + 14.0, (noise_floor_db + p90) / 2.0))
    
    speech_frames = int(np.sum(frame_db > speech_threshold_db))
    total_frames = len(frame_db)
    speech_fraction = float(speech_frames / total_frames) if total_frames > 0 else 0.0
    silence_fraction = float(1.0 - speech_fraction)
    snr_db = float(p90 - noise_floor_db)
    
    return {
        "duration_s": round(duration_s, 2),
        "peak_dbfs": round(peak_dbfs, 2),
        "clipped_samples": clipped_count,
        "clipping_detected": clipped_count > 0,
        "rms_loudness_dbfs": round(rms_dbfs, 2),
        "estimated_noise_floor_dbfs": round(noise_floor_db, 2),
        "estimated_snr_db": round(snr_db, 2),
        "speech_fraction": round(speech_fraction, 3),
        "silence_fraction": round(silence_fraction, 3)
    }

def extract_frames(video_path, out_dir, duration):
    os.makedirs(out_dir, exist_ok=True)
    timestamps = [
        max(0.5, duration * 0.15),
        duration * 0.50,
        min(max(1.0, duration - 1.0), duration * 0.85)
    ]
    frame_paths = []
    for idx, ts in enumerate(timestamps, start=1):
        out_file = os.path.join(out_dir, f"frame_{idx}.jpg")
        cmd = [
            "ffmpeg", "-y", "-ss", f"{ts:.2f}",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_file
        ]
        ret, stdout, stderr = run_cmd(cmd)
        if ret == 0 and os.path.exists(out_file):
            frame_paths.append(out_file)
    return frame_paths

def main():
    root_dir = Path("/Users/tusharsurwase/Desktop/BTP")
    folders = ["BTP videos", "BTP videos 2", "BTP videos 3"]
    all_files = []
    for f in folders:
        d = root_dir / f
        for ext in ("*.MOV", "*.mov", "*.m4a", "*.mp4"):
            all_files.extend(glob.glob(str(d / ext)))
    all_files.sort()

    print(f"Found {len(all_files)} media files.")
    results = []

    for file_path in all_files:
        rel_path = os.path.relpath(file_path, root_dir)
        fname = os.path.basename(file_path)
        stem = Path(file_path).stem
        parent = Path(file_path).parent.name
        safe_id = f"{parent}_{stem}".replace(" ", "_")
        print(f"Processing: {rel_path} ...")

        info = get_ffprobe_info(file_path)
        if not info:
            print(f"Failed to probe {file_path}")
            continue

        format_info = info.get("format", {})
        duration = float(format_info.get("duration", 0.0))
        container = format_info.get("format_name", "unknown")
        size_bytes = int(format_info.get("size", 0))

        v_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)

        v_codec = v_stream.get("codec_name") if v_stream else None
        v_res = f"{v_stream.get('width')}x{v_stream.get('height')}" if v_stream else None

        a_codec = a_stream.get("codec_name") if a_stream else None
        a_sr = int(a_stream.get("sample_rate", 0)) if a_stream else None
        a_channels = int(a_stream.get("channels", 0)) if a_stream else None

        ebu_data = analyze_audio_volume_ebu(file_path)
        acoustics = analyze_audio_stream(file_path)

        frame_dir = root_dir / "extracted_frames" / safe_id
        frame_paths = []
        if v_stream:
            # Check if frames already exist
            existing = [os.path.join(frame_dir, f"frame_{i}.jpg") for i in (1, 2, 3)]
            if all(os.path.exists(p) for p in existing):
                frame_paths = existing
            else:
                frame_paths = extract_frames(file_path, str(frame_dir), duration)

        # Quality assessment
        dur = acoustics["duration_s"] if acoustics else duration
        issues = []
        if dur < 15.0:
            issues.append(f"Short snippet ({dur}s) - test recording or aborted start")
        if acoustics and acoustics["clipped_samples"] > 100:
            issues.append(f"Clipping detected ({acoustics['clipped_samples']} samples)")
        if acoustics and acoustics["estimated_snr_db"] < 12.0:
            issues.append(f"High background noise (SNR {acoustics['estimated_snr_db']} dB)")
        if acoustics and acoustics["rms_loudness_dbfs"] < -36.0:
            issues.append(f"Low overall volume ({acoustics['rms_loudness_dbfs']} dBFS)")

        if any("Short snippet" in iss for iss in issues):
            plain_verdict = "Discard / Too short for sociolinguistic analysis"
        elif any("Clipping detected" in iss for iss in issues):
            plain_verdict = "Usable with caution (mild clipping on loud syllables)"
        elif issues:
            plain_verdict = "Usable with minor acoustic limitations: " + "; ".join(issues)
        else:
            plain_verdict = "Clean / Readily transcribable"

        record = {
            "file": rel_path,
            "id": safe_id,
            "duration_s": dur,
            "size_mb": round(size_bytes / (1024*1024), 2),
            "container": container,
            "video_codec": v_codec,
            "resolution": v_res,
            "audio_codec": a_codec,
            "sample_rate_hz": a_sr,
            "channels": a_channels,
            "integrated_lufs": ebu_data.get("integrated_lufs"),
            "loudness_range_lu": ebu_data.get("loudness_range_lu"),
            "peak_dbfs": acoustics.get("peak_dbfs") if acoustics else None,
            "rms_loudness_dbfs": acoustics.get("rms_loudness_dbfs") if acoustics else None,
            "clipped_samples": acoustics.get("clipped_samples", 0) if acoustics else 0,
            "estimated_noise_floor_dbfs": acoustics.get("estimated_noise_floor_dbfs") if acoustics else None,
            "estimated_snr_db": acoustics.get("estimated_snr_db") if acoustics else None,
            "speech_fraction": acoustics.get("speech_fraction") if acoustics else None,
            "silence_fraction": acoustics.get("silence_fraction") if acoustics else None,
            "frames": [os.path.relpath(fp, root_dir) for fp in frame_paths],
            "plain_verdict": plain_verdict,
            "issues": issues
        }
        results.append(record)

    out_json = root_dir / "analysis" / "inventory_technical_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nAll done! Inventory report saved to {out_json}")

if __name__ == "__main__":
    main()
