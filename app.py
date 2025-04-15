from flask import Flask, request, jsonify, redirect
import subprocess
import re
import time
from functools import lru_cache

app = Flask(__name__)

# Improved caching: Store audio URLs for a longer time (24 hours)
cache = {}

# Function to validate YouTube Video ID
def is_valid_youtube_id(video_id):
    return bool(re.match(r"^[a-zA-Z0-9_-]{11}$", video_id))

# Function to fetch audio URL using yt-dlp
def fetch_audio_url(video_id):
    command = f'yt-dlp -f "bestaudio[ext=m4a]/bestaudio[ext=webm]" --get-url "https://www.youtube.com/watch?v={video_id}"'
    try:
        # Run the command and get the output
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stderr:
            print(f"⚠️ yt-dlp Warning: {result.stderr}")
        audio_url = result.stdout.strip()
        if audio_url and audio_url.startswith("http"):
            return audio_url
        return None
    except Exception as e:
        print(f"🚨 yt-dlp Error: {e}")
        return None

@app.route('/audio', methods=['GET'])
def get_audio_url():
    try:
        video_id = request.args.get("id")

        # Validate Video ID
        if not video_id or not is_valid_youtube_id(video_id):
            return jsonify({"error": "Invalid or missing video ID"}), 400

        # Check cache before making an API call
        if video_id in cache and time.time() - cache[video_id]['timestamp'] < 24 * 60 * 60:
            print(f"🔄 Serving Cached Audio for {video_id}")
            return redirect(cache[video_id]['url'])

        print(f"🎵 Fetching Audio for {video_id} using yt-dlp")

        # Fetch the audio URL
        audio_url = fetch_audio_url(video_id)

        if not audio_url:
            print("🚨 Invalid audio URL received")
            return jsonify({"error": "Failed to retrieve audio"}), 500

        print(f"✅ Audio URL: {audio_url}")

        # Cache the result for 24 hours
        cache[video_id] = {'url': audio_url, 'timestamp': time.time()}

        return redirect(audio_url)

    except Exception as e:
        print(f"🚨 Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
