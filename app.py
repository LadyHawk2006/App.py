from flask import Flask, request, jsonify, redirect
import subprocess
import re
import time
import random
from functools import lru_cache
import os

app = Flask(__name__)

# Improved caching: Store audio URLs for a longer time (24 hours)
cache = {}
last_request_time = 0  # For rate limiting

# Function to validate YouTube Video ID
def is_valid_youtube_id(video_id):
    return bool(re.match(r"^[a-zA-Z0-9_-]{11}$", video_id))

# Function to fetch audio URL using yt-dlp with cookies and rate limiting
def fetch_audio_url(video_id):
    global last_request_time
    
    # Rate limiting: Wait 1-3 seconds between requests
    elapsed = time.time() - last_request_time
    if elapsed < random.uniform(1, 3):
        time.sleep(random.uniform(1, 3) - elapsed)
    
    # Updated command with cookies and anti-bot measures
    command = (
        f'yt-dlp --cookies youtube.com_cookies.txt '
        f'--user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" '
        f'--extractor-args "youtube:skip=webpage" '
        f'-f "bestaudio[ext=m4a]/bestaudio[ext=webm]" '
        f'--get-url "https://www.youtube.com/watch?v={video_id}"'
    )
    
    try:
        last_request_time = time.time()
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.stderr:
            print(f"⚠️ yt-dlp Warning: {result.stderr}")
        
        audio_url = result.stdout.strip()
        return audio_url if audio_url and audio_url.startswith("http") else None
        
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

        # Fetch the audio URL (with retry logic)
        for attempt in range(3):
            audio_url = fetch_audio_url(video_id)
            if audio_url:
                break
            time.sleep(2 ** attempt)  # Exponential backoff

        if not audio_url:
            print("🚨 Failed after 3 attempts")
            return jsonify({"error": "YouTube request failed. Try again later."}), 503

        print(f"✅ Audio URL: {audio_url}")

        # Cache the result for 24 hours
        cache[video_id] = {'url': audio_url, 'timestamp': time.time()}

        return redirect(audio_url)

    except Exception as e:
        print(f"🚨 Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    # Verify cookies file exists
    if not os.path.exists("youtube.com_cookies.txt"):
        print("❌ Error: youtube.com_cookies.txt not found!")
        print("Please export cookies from your browser and save them in this directory.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)