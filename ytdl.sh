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

# Step 4: Prompt the user to select a format
echo "Enter the format code you want to download (e.g., 137 for video, 140 for audio):"
read -r FORMAT_CODE

# Validate the format code
if [[ -z "$FORMAT_CODE" ]]; then
    echo "Format code cannot be empty. Exiting."
    exit 1
fi

# Step 5: Download the video with the selected format
echo "Downloading the video..."
yt-dlp -f "$FORMAT_CODE" "$URL" --merge-output-format mp4

# Check if the download was successful
if [[ $? -eq 0 ]]; then
    echo "Download complete!"
else
    echo "Download failed. Please check the format code and try again."
fi
