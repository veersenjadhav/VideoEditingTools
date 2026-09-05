#!/usr/bin/env python3
"""
Imperceptibly alter a video to break Content-ID fingerprinting,
while preserving quality, format and approximate size.
GPU acceleration (NVIDIA NVENC / AMD AMF) is used when available.
Processes multiple videos from a predefined list.
"""

import subprocess
import json
import os
import sys
import random
from pathlib import Path

# ==================== EDIT THESE LISTS ====================
INPUT_FILES = [
    "C:\\Users\\veers\\Downloads\\Guardians.Of.The.Galaxy.Vol..2.2017.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].mkv",
    "C:\\Users\\veers\\Downloads\\Guardians.Of.The.Galaxy.Vol..3.2023.2160p.4K.WEB.x265.10bit.AAC5.1-[YTS.MX].mkv"
    # add more paths here
]

OUTPUT_FILES = [
    "Guardians Of The Galaxy Vol 2 2017.mkv",
    "Guardians Of The Galaxy Vol 3 2023.mkv"
    # corresponding output paths
]
# ==========================================================

def ffprobe_info(input_path):
    """Return codec, bitrate, resolution, pixel format, frame rate, audio streams."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(input_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)

def detect_gpu_encoders():
    """Detect available hardware encoders (NVENC / AMF)."""
    try:
        out = subprocess.check_output(["ffmpeg", "-encoders"], stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError:
        return None, None
    has_nvenc = "h264_nvenc" in out
    has_amf = "h264_amf" in out
    return has_nvenc, has_amf

def process_video(input_path_str, output_path_str):
    """Process a single video file."""
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return False

    print(f"\nProcessing: {input_path} -> {output_path}")

    # ------------------------------------------------------------------
    # 1. Get video properties
    # ------------------------------------------------------------------
    info = ffprobe_info(input_path)
    video_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if not video_stream:
        print("No video stream found.", file=sys.stderr)
        return False

    codec_name = video_stream["codec_name"]       # e.g. h264 / hevc
    width = video_stream["width"]
    height = video_stream["height"]
    pix_fmt = video_stream.get("pix_fmt", "yuv420p")
    frame_rate = video_stream["r_frame_rate"]    # e.g. "30000/1001"
    bit_rate = int(info["format"].get("bit_rate", 0)) or int(video_stream.get("bit_rate", 0))
    duration = float(info["format"].get("duration", 0))

    # Fallback bitrate if unknown
    if bit_rate == 0 and duration > 0:
        file_size = input_path.stat().st_size
        bit_rate = int((file_size * 8) / duration)

    # Determine bit depth from pixel format
    if "p10" in pix_fmt or "10le" in pix_fmt:
        bit_depth = 10
    else:
        bit_depth = 8

    # Audio stream copy
    audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
    has_audio = len(audio_streams) > 0

    # ------------------------------------------------------------------
    # 2. Choose encoder (GPU priority, fallback to CPU)
    # ------------------------------------------------------------------
    nvenc, amf = detect_gpu_encoders()
    use_gpu = False
    encoder = None
    if codec_name in ("h264", "avc1"):
        if nvenc:
            encoder = "h264_nvenc"
            use_gpu = True
        elif amf:
            encoder = "h264_amf"
            use_gpu = True
        else:
            encoder = "libx264"   # CPU
    elif codec_name in ("hevc", "hvc1"):
        if nvenc:
            encoder = "hevc_nvenc"
            use_gpu = True
        elif amf:
            encoder = "hevc_amf"
            use_gpu = True
        else:
            encoder = "libx265"
    else:
        # Unsupported codec – fallback to libx264 (transcode)
        print(f"Warning: codec {codec_name} not directly supported. Using libx264.")
        encoder = "libx264"

    # ------------------------------------------------------------------
    # 3. Build filter to add invisible noise
    # ------------------------------------------------------------------
    # Strength scaled by bit depth (0.2 for 8-bit, ~0.8 for 10-bit)
    noise_strength = 0.2 if bit_depth == 8 else 0.8
    seed = random.randint(0, 1000000)

    # Add random uniform noise to luma only (no chroma change)
    # 'allf=t' gives temporal noise (different each frame), 'c0s=…' luma strength
    noise_filter = f"noise=alls={noise_strength}:allf=t:c0s={noise_strength}:all_seed={seed}"

    # ------------------------------------------------------------------
    # 4. Build FFmpeg command
    # ------------------------------------------------------------------
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    # Video filter chain: use the noise filter, set threads to 4
    cmd += ["-filter_complex", f"[0:v]{noise_filter}[v]", "-map", "[v]"]

    # Map audio unchanged if present
    if has_audio:
        cmd += ["-map", "0:a?", "-c:a", "copy"]

    # Encoder and bitrate control
    cmd += ["-c:v", encoder, "-pix_fmt", pix_fmt]

    if use_gpu:
        # GPU encoders: VBR with approximate target bitrate
        cmd += [
            "-b:v", str(bit_rate),
            "-maxrate", str(int(bit_rate * 2)),
            "-bufsize", str(int(bit_rate * 4)),
            "-rc", "vbr"
        ]
        # NVENC specific quality tuning
        if "nvenc" in encoder:
            cmd += ["-preset", "p4", "-tune", "hq"]
        elif "amf" in encoder:
            cmd += ["-usage", "ultralowlatency", "-quality", "quality"]  # adjust as needed
    else:
        # CPU encoders: two-pass to exactly match size? Quick one-pass VBR.
        # For simplicity we use a single pass with CRF + maxrate; may vary size.
        # For exact size, two-pass would be needed (omitted for brevity).
        cmd += [
            "-b:v", str(bit_rate),
            "-maxrate", str(int(bit_rate * 2)),
            "-bufsize", str(int(bit_rate * 4))
        ]
        # Use 4 threads for the encoder
        cmd += ["-threads", "4"]

    # Set filter threads to 4 (if using software filters)
    cmd += ["-filter_threads", "4"]

    # Keep metadata
    cmd += ["-map_metadata", "0"]
    cmd += [str(output_path)]

    # ------------------------------------------------------------------
    # 5. Execute
    # ------------------------------------------------------------------
    print(" ".join(cmd))   # for debugging
    try:
        subprocess.run(cmd, check=True)
        print(f"Done. Output saved to: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)
        return False

def main():
    if len(INPUT_FILES) != len(OUTPUT_FILES):
        print("Error: INPUT_FILES and OUTPUT_FILES must have the same number of entries.", file=sys.stderr)
        sys.exit(1)

    for in_file, out_file in zip(INPUT_FILES, OUTPUT_FILES):
        success = process_video(in_file, out_file)
        if not success:
            print(f"Skipped or failed: {in_file}")

if __name__ == "__main__":
    main()