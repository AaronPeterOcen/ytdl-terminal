#!/bin/bash

# Step 1: Check if yt-dlp is installed
if ! command -v yt-dlp &> /dev/null
then
    echo "yt-dlp is not installed."
    echo "You can install it by following the instructions at https://github.com/yt-dlp/yt-dlp"
    exit 1
fi

# Step 2: Ask for the video URL
echo "Enter the URL of the video:"
read URL

# Step 3: Display available formats
echo "Fetching available formats..."
yt-dlp -F "$URL"

# Step 4: Prompt the user to select a format
echo "Enter the format code you want to download:"
read FORMAT_CODE

# Step 5: Download the video with the selected format
echo "Downloading the video..."
yt-dlp -f "$FORMAT_CODE"+"140" "$URL" --merge-output-format mp4

echo "Download complete!"

