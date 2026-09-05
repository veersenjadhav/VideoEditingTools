import subprocess
import os

def process_videos(input_list, output_list):
    # Check if both lists have the same number of videos
    if len(input_list) != len(output_list):
        print("Please make sure both input and output lists have the same number of files.")
        return

    # Process each video one by one
    for i in range(len(input_list)):
        input_video = input_list[i]
        output_video = output_list[i]
        
        print(f"\n--- Starting work on: {input_video} ---")

        # Command 1: Run RTXVideoProcessor
        command1 = f"RTXVideoProcessor.exe {input_video} {output_video} --no-vsr"
        print("Step 1: Adding HDR using RTX...")
        subprocess.run(command1, shell=True)

        # Create the final YouTube ready file name
        # If output is "my_video.mp4", it becomes "my_video_youtube_ready.mp4"
        file_name, file_extension = os.path.splitext(output_video)
        youtube_ready_video = f"{file_name}_youtube_ready{file_extension}"

        # Command 2: Run FFmpeg to fix the file for YouTube
        command2 = f"ffmpeg -i {output_video} -c copy -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -movflags +faststart {youtube_ready_video}"
        print("Step 2: Making the video ready for YouTube...")
        subprocess.run(command2, shell=True)

        print(f"--- Finished: {youtube_ready_video} is ready! ---")

# Put your actual video file names here
my_input_videos = ["Avengers.Endgame.2019.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].mkv"]
my_output_videos = ["Avengers_Endgame_2019_4K_HDR10.mp4"]

# Run the program
process_videos(my_input_videos, my_output_videos)