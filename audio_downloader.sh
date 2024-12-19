#!/bin/bash

# Check if yt-dlp is installed
if ! command -v yt-dlp &> /dev/null; then
    echo "yt-dlp is not installed. Please install it from https://github.com/yt-dlp/yt-dlp."
    exit 1
fi

# Prompt the user for the URL
echo "Enter the URL of the video:"
read URL

# Confirm FFmpeg is installed (needed for audio processing)
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is not installed. Please install it to proceed."
    exit 1
fi

# Download the highest quality audio
echo "Downloading the highest quality audio..."
yt-dlp -f bestaudio --extract-audio --audio-format best --audio-quality 0 -o "%(title)s.%(ext)s" "$URL"

if [ $? -eq 0 ]; then
    echo "Audio downloaded successfully!"
else
    echo "An error occurred during the download."
fi
