# Video Downloader Script

This is a Bash script that allows you to download videos using `yt-dlp`. It prompts the user for a video URL, displays available formats, and lets the user choose the desired format for downloading.

## Prerequisites

Before using this script, ensure you have the following installed:

1. **`yt-dlp`**: A powerful command-line tool for downloading videos from various platforms like YouTube, Vimeo, and more.
   - Installation instructions: [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
   - You can install it using `pip`:
     ```bash
     pip install -U yt-dlp
     ```

2. **Bash**: This script is written for Unix-based systems (Linux, macOS). Ensure you have Bash installed.

---

## How to Use the Script

1. **Download the Script**:
   - Save the script to a file, e.g., `video_downloader.sh`.
   - Make the script executable:
     ```bash
     chmod +x video_downloader.sh
     ```

2. **Run the Script**:
   - Execute the script in your terminal:
     ```bash
     ./video_downloader.sh
     ```

3. **Follow the Prompts**:
   - Enter the URL of the video you want to download.
   - The script will display a list of available formats (video and audio).
   - Enter the format code for the quality you want to download.
   - The script will download the video and save it in the current directory.

---

## Example Usage

```bash
$ ./video_downloader.sh
Enter the URL of the video: https://www.youtube.com/watch?v=example
Fetching available formats...
[youtube] example: Downloading webpage
[youtube] example: Downloading android player API JSON
[info] Available formats for example:
format code  extension  resolution note
249          webm       audio only tiny   48k , webm_dash
140          m4a        audio only tiny  128k , m4a_dash
137          mp4        1920x1080  1080p 4.5M, mp4_dash
...
Enter the format code you want to download: 137
Downloading the video...
[download] Destination: example_video.mp4
[download] 100% of 123.45MiB in 00:10
Download complete!
```
## Features

- **Format Selection**: The script lists all available formats (video and audio) and lets you choose the one you want.
- **Error Handling**: The script checks for invalid URLs, empty inputs, and failed downloads.
- **Merge Output**: The script automatically merges video and audio streams into a single `.mp4` file.

---

## Customization

You can modify the script to suit your needs:

- **Default Format**: If you want to download the best quality by default, change the format prompt to:
  ```bash
  FORMAT_CODE=${FORMAT_CODE:-"best"}


## License
- This script is open-source and free to use. Feel free to modify and distribute it as needed.

