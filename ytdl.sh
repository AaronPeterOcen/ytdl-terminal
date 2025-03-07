#!/bin/bash

# Step 1: Check if yt-dlp is installed
if ! command -v yt-dlp &> /dev/null; then
    echo "yt-dlp is not installed."
    echo "You can install it by following the instructions at https://github.com/yt-dlp/yt-dlp"
    exit 1
fi

# Step 2: Ask for the video URL
echo "Enter the URL of the video:"
read -r URL

# Validate the URL
if [[ -z "$URL" ]]; then
    echo "URL cannot be empty. Exiting."
    exit 1
fi

# Step 3: Display available formats
echo "Fetching available formats..."
yt-dlp -F "$URL"

# Check if the format list was retrieved successfully
if [[ $? -ne 0 ]]; then
    echo "Failed to fetch formats. Please check the URL and try again."
    exit 1
fi

# Step 4: Ask the user to choose a video format
echo "Enter the format code for the video you want to download:"
read -r VIDEO_FORMAT

# Validate the video format selection
if [[ -z "$VIDEO_FORMAT" ]]; then
    echo "Video format cannot be empty. Exiting."
    exit 1
fi

# Step 5: Automatically select the best audio format
BEST_AUDIO_FORMAT=$(yt-dlp -F "$URL" | awk '/audio only/ {print $1}' | tail -1)

if [[ -z "$BEST_AUDIO_FORMAT" ]]; then
    echo "No audio format found. Exiting."
    exit 1
fi

# Step 6: Download the selected video format with the best audio
echo "Downloading video (format $VIDEO_FORMAT) and best audio (format $BEST_AUDIO_FORMAT)..."
yt-dlp -f "${VIDEO_FORMAT}+${BEST_AUDIO_FORMAT}" "$URL" --merge-output-format mp4

# Check if the download was successful
if [[ $? -eq 0 ]]; then
    echo "Download complete!"
else
    echo "Download failed. Please try again."
    exit 1
fi

