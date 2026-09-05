# RTX Video Enhancer

This tool uses NVIDIA RTX to make your videos look better. It upscales videos to a higher resolution and adds HDR colours.

## Get the Latest Files

1. **EXE File:** You can always check for the latest `.exe` file on the original [RTXVideoProcessor Releases page](https://github.com/DrC0ns0le/RTXVideoProcessor/releases).
2. **DLL Files:** You need two special NVIDIA files to make this tool work:
* `nvngx_vsr.dll`
* `nvngx_truehdr.dll`
* You can download them from the [NVIDIA RTX Video SDK page](https://developer.nvidia.com/rtx-video-sdk). Just extract them and keep both DLL files in the same folder as your `.exe` file.



## Simple Commands Guide

Open your command prompt in the folder where your `.exe` is located and run these commands:

**1. Basic Use (Upscale + HDR):**
`RTXVideoProcessor.exe input.mp4 output_hdr.mp4`

**2. Only HDR (Do not upscale):**
`RTXVideoProcessor.exe input.mp4 output.mp4 --no-vsr`

**3. Only Upscaling (Do not add HDR):**
`RTXVideoProcessor.exe input.mp4 output.mp4 --no-thdr`

**4. Normal Output (No RTX features):**
`RTXVideoProcessor.exe input.mp4 output_sdr.mp4 --no-vsr --no-thdr`

For more advance commands, you can read the guide on the main [RTXVideoProcessor project page](https://github.com/DrC0ns0le/RTXVideoProcessor).