# ytdl-terminal

`ytdl-terminal` is a simple Bash script that facilitates downloading videos (along with audio) using `yt-dlp`. The script provides an interactive terminal-based experience where you can select the desired video quality, and it ensures the best audio is always downloaded and merged with your chosen video.

## Features

- **Format Selection**: Lets you choose the desired video quality from the available options.
- **Audio Merging**: Automatically includes the best audio (`140` format) when downloading the selected video format.
- **Installation Check**: Validates whether `yt-dlp` is installed; if not, it provides a link to the official repository.
- **Easy Merging**: Ensures video and audio are merged into a single `mp4` file for compatibility.

## Requirements

- **yt-dlp**: The script depends on `yt-dlp` for downloading videos and merging audio.
- **Bash**: A Bash shell is required to run the script (supported on Linux and macOS).

## Installation Instructions

1. **Ensure `yt-dlp` is Installed**: 
   The script checks if `yt-dlp` is already installed. If not, it will prompt you with a link to install it:
   - Follow the instructions on the [yt-dlp GitHub page](https://github.com/yt-dlp/yt-dlp).

2. **Save the Script**:
   Download or copy the script and save it as `ytdl`.

3. **Make the Script Executable**:
   Run the following command to make the script executable:
   ```bash
   chmod +x ytdl

4. **Run the Script: Execute the script with**:
    ```bash
    ./ytdl


## How to Use
    Enter the URL: The script will prompt you to enter the URL of the video you want to download.

    Select Format: After fetching the available formats, the script will display them in a list. Enter the format code corresponding to your desired video quality.

    Download: The script will automatically download your chosen video format, merge it with the best available audio, and save it as a single mp4 file.

## Example usage
```bash
    $ ./ytdl

Enter the URL of the video:
https://www.youtube.com/watch?v=dQw4w9WgXcQ

Fetching available formats...
[1] 1080p video
[2] 720p video
[3] 480p video
[4] audio-only (m4a)

Enter the format code you want to download:
1

Downloading the video and audio...
Download complete!
```
The resulting file will include both video and audio in a single mp4 file.

## Notes
1.    Audio Inclusion: The script automatically appends +140 to the selected video format to ensure the best audio is downloaded and merged with the video.
2.    Merged Output: The merged file is output in the mp4 format for compatibility with most devices and players.
3.    Supported Sites: This script works with all websites supported by yt-dlp, including YouTube, Vimeo, and others.

## Contributing
    Feel free to fork this repository and submit pull requests if you'd like to improve or add features to the script.
