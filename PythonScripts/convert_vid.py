#!/usr/bin/env python3
"""
Convert all videos (SDR and HDR) to HEVC (H.265) format.
Checks for unsupported audio formats and converts them to AAC if needed.
Saves as MP4 and preserves HDR color details.
Optionally adds invisible noise to break Content-ID fingerprinting.
"""

import subprocess
import json
import os
import sys
import random
from pathlib import Path

# ==================== EDIT THESE LISTS ====================
INPUT_FILES = [
    "C:\\Users\\veers\\Downloads\\The.Fantastic.Four.First.Steps.2025.Hybrid.2160p.WEB-DL.DV.HDR.DDP5.1.Atmos.H265-AOC.mkv"
    # add more paths here
]

OUTPUT_FILES = [
    "The Fantastic Four First Steps 2025 HDR.mp4"
]
# ==========================================================

# List of audio formats that work perfectly in MP4
SAFE_MP4_AUDIO = ["aac", "ac3", "eac3", "mp3", "alac"]

def safe_int(value):
    """Safely convert a value to an integer, returning 0 if it fails (like 'N/A')."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def safe_float(value):
    """Safely convert a value to a float, returning 0.0 if it fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

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
    """Detect available hardware HEVC encoders (NVENC / AMF)."""
    try:
        out = subprocess.check_output(["ffmpeg", "-encoders"], stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError:
        return None, None
    
    has_nvenc = "hevc_nvenc" in out
    has_amf = "hevc_amf" in out
    return has_nvenc, has_amf

def process_video(input_path_str, output_path_str, add_noise, convert_audio):
    """Process a single video file."""
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)
    
    print(f"\nProcessing: {input_path} -> {output_path}")

    # 1. Get video properties
    info = ffprobe_info(input_path)
    video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    
    if not video_stream:
        print("No video stream found.", file=sys.stderr)
        return False

    pix_fmt = video_stream.get("pix_fmt", "yuv420p")
    
    # Safely get bit_rate and duration (handles 'N/A' issues)
    fmt_info = info.get("format", {})
    bit_rate = safe_int(fmt_info.get("bit_rate")) or safe_int(video_stream.get("bit_rate"))
    duration = safe_float(fmt_info.get("duration"))

    color_space = video_stream.get("color_space")
    color_transfer = video_stream.get("color_transfer")
    color_primaries = video_stream.get("color_primaries")

    # Fallback bitrate calculation
    if bit_rate == 0 and duration > 0:
        file_size = input_path.stat().st_size
        bit_rate = int((file_size * 8) / duration)
        
    # If it is still 0, give it a default safe value of 5 Mbps
    if bit_rate == 0:
        bit_rate = 5000000 

    if "p10" in pix_fmt or "10le" in pix_fmt:
        bit_depth = 10
    else:
        bit_depth = 8

    audio_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    has_audio = len(audio_streams) > 0

    # 2. Choose encoder (Force HEVC / H.265)
    nvenc, amf = detect_gpu_encoders()
    use_gpu = False
    
    if nvenc:
        encoder = "hevc_nvenc"
        use_gpu = True
    elif amf:
        encoder = "hevc_amf"
        use_gpu = True
    else:
        encoder = "libx265"

    # 3. Build FFmpeg command
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    # Check if user wants noise
    if add_noise:
        noise_strength = 0.2 if bit_depth == 8 else 0.8
        seed = random.randint(0, 1000000)
        noise_filter = f"noise=alls={noise_strength}:allf=t:c0s={noise_strength}:all_seed={seed}"
        cmd += ["-filter_complex", f"[0:v]{noise_filter}[v]", "-map", "[v]"]
        cmd += ["-filter_threads", "4"]
    else:
        cmd += ["-map", "0:v"]

    # Map audio correctly depending on if it needs conversion
    if has_audio:
        if convert_audio:
            # Convert bad audio format to standard AAC for MP4
            cmd += ["-map", "0:a?", "-c:a", "aac", "-b:a", "256k"]
        else:
            # Safe to copy directly
            cmd += ["-map", "0:a?", "-c:a", "copy"]

    # Encoder and pixel format
    cmd += ["-c:v", encoder, "-pix_fmt", pix_fmt]

    # Add HDR Color Settings if they exist
    if color_primaries:
        cmd += ["-color_primaries", color_primaries]
    if color_transfer:
        cmd += ["-color_trc", color_transfer]
    if color_space:
        cmd += ["-colorspace", color_space]

    cmd += ["-tag:v", "hvc1"]

    if use_gpu:
        if bit_depth == 10:
            cmd += ["-profile:v", "main10"]

        cmd += [
            "-b:v", str(bit_rate),
            "-maxrate", str(int(bit_rate * 2)),
            "-bufsize", str(int(bit_rate * 4)),
            "-rc", "vbr"
        ]
        
        if "nvenc" in encoder:
            cmd += ["-preset", "p4", "-tune", "hq"]
        elif "amf" in encoder:
            cmd += ["-usage", "ultralowlatency", "-quality", "quality"]
    else:
        cmd += [
            "-b:v", str(bit_rate),
            "-maxrate", str(int(bit_rate * 2)),
            "-bufsize", str(int(bit_rate * 4)),
            "-threads", "4"
        ]

    cmd += ["-map_metadata", "0"]
    cmd += [str(output_path)]

    # 4. Execute
    print("Running command:", " ".join(cmd))
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

    files_to_process = []

    # Step 1: Check audio formats for each file before doing anything
    print("Checking videos for audio compatibility...")
    for in_file, out_file in zip(INPUT_FILES, OUTPUT_FILES):
        input_path = Path(in_file)
        
        if not input_path.is_file():
            print(f"File not found, skipping: {in_file}")
            continue

        try:
            info = ffprobe_info(input_path)
        except RuntimeError:
            print(f"Could not read info for {in_file}, skipping.")
            continue

        audio_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
        unsupported_audios = []

        for audio in audio_streams:
            codec = audio.get("codec_name", "unknown")
            if codec not in SAFE_MP4_AUDIO:
                unsupported_audios.append(codec)

        if unsupported_audios:
            print(f"\nWarning: The video '{in_file}' has audio format(s) not supported by MP4: {', '.join(unsupported_audios)}")
            ans = input("Do you want to proceed and convert the audio to a supported format (AAC)? (Y/N): ").strip().lower()
            if ans == 'y':
                files_to_process.append((in_file, out_file, True)) # True means convert audio
            else:
                print(f"Skipped video: {in_file}")
        else:
            files_to_process.append((in_file, out_file, False)) # False means just copy audio

    if not files_to_process:
        print("\nNo videos left to process. Closing program.")
        sys.exit(0)

    # Step 2: Ask the user once about adding noise
    print("\n---")
    user_choice = input("Do you want to add invisible video noise? (Y/N): ").strip().lower()
    add_noise = (user_choice == 'y')
    print("---\n")

    # Step 3: Process the approved videos
    for in_file, out_file, convert_audio in files_to_process:
        success = process_video(in_file, out_file, add_noise, convert_audio)
        if not success:
            print(f"Failed to process: {in_file}")

if __name__ == "__main__":
    main()