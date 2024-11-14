import os
import random
import re
import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
import logging
from PIL import Image
import requests
from io import BytesIO
import pickle

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your channel ID and Google API credentials
CHANNEL_ID = 'UCHScoXiPE9wsDFLUerNeodg'
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_PICKLE_FILE = 'token_youtube.pkl'
DOWNLOAD_LOG_FILE = 'downloaded_videos.txt'
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# File to store the last uploaded video number
UPLOAD_LOG_FILE = 'uploaded_videos_log.txt'

# Path to your cookies file (e.g., exported from your browser)
COOKIES_FILE = 'cookies.txt'  # Replace with your cookie file path

def get_next_video_number():
    """Get the next video number based on the previous uploads."""
    if not os.path.exists(UPLOAD_LOG_FILE):
        return 1  # Start from #1 if no previous uploads

    with open(UPLOAD_LOG_FILE, 'r') as file:
        lines = file.readlines()
        if not lines:
            return 1  # Start from #1 if the file is empty
        last_video_number = int(lines[-1].strip().split()[0].replace('#', ''))
        return last_video_number + 1

def update_upload_log(video_number):
    """Update the uploaded videos log with the new video number."""
    with open(UPLOAD_LOG_FILE, 'a') as file:
        file.write(f"#{video_number}\n")

def generate_title():
    video_number = get_next_video_number()
    title = f'SCARY TikTok Videos #{video_number} Don\'t Watch This At Night ⚠️😱'
    update_upload_log(video_number)
    return title

CUSTOM_DESCRIPTION = """Copyright Disclaimer under section 107 of the Copyright Act of 1976, allowance is made for "fair use" for purposes such as criticism, comment, news reporting, teaching, scholarship, education and research. Fair use is a use permitted by copyright statute that might otherwise be infringing.

Welcome to Chills and Thrills! Dive into the dark with bone-chilling, true horror stories that will haunt your nights. From paranormal encounters and ghost sightings to disturbing real-life horror stories and urban legends, each tale is crafted to keep you on the edge. Whether you're drawn to eerie mysteries, haunted locations, or tales of the unknown, Chills and Thrills brings you the scariest stories, perfect for late-night listening. Subscribe and experience true terror, the unknown, and the supernatural.

If you enjoyed this video, please give it a thumbs up and subscribe for more spine-chilling content every week! Don't forget to hit the bell icon to never miss a new upload

V I D E O S    T O    W A T C H    N E X T :  

https://youtu.be/4LS8PC0odKU
https://youtu.be/LXNPbX0KvOY
https://youtu.be/4boAhgFpj1I

"Sometimes you find yourself in a dark place and you think you've been buried. But actually, you've been planted."

Inquiries: abrarsafin2010@gmail.com

Tags: scary videos,ghost videos,scariest videos,horror,horror video,scary ghost videos,scary video,super scary videos,creepy videos,ghost video,horror movie,very scary video,horror short film,short horror film,horror film,best horror movie,horror story,short horror,short horror movie,5 scary ghost videos,horror short video,paranormal videos,horror stories,ghost in mirror,videos,caught on video,#horror,scary videos caught on camera"""

def get_authenticated_service():
    """Authenticate and return the YouTube service object."""
    creds = None
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token_file:
            creds = pickle.load(token_file)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=8080)
        with open(TOKEN_PICKLE_FILE, 'wb') as token_file:
            pickle.dump(creds, token_file)
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
    return youtube

def sanitize_filename(filename):
    """Sanitize the filename to remove invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def load_downloaded_video_ids():
    """Load the list of already downloaded video IDs."""
    if not os.path.exists(DOWNLOAD_LOG_FILE):
        return set()
    with open(DOWNLOAD_LOG_FILE, 'r') as file:
        return set(line.strip() for line in file)

def save_downloaded_video_id(video_id):
    """Save a video ID to the downloaded log file."""
    with open(DOWNLOAD_LOG_FILE, 'a') as file:
        file.write(f"{video_id}\n")

def download_random_video_from_channel():
    """Download a random video from the channel, skipping already downloaded ones."""
    downloaded_video_ids = load_downloaded_video_ids()

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'skip_download': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': '1.%(ext)s',
        'cookiefile': COOKIES_FILE,  # Add cookie file support here
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f'https://www.youtube.com/channel/{CHANNEL_ID}/videos', download=False)
        video_entries = result.get('entries', [])
        
    long_videos = [entry for entry in video_entries if 'duration' in entry and entry['duration'] >= 60 and entry['id'] not in downloaded_video_ids]

    if not long_videos:
        logger.error("No new long-form videos found on this channel.")
        return None, None

    selected_video = random.choice(long_videos)
    selected_video_url = selected_video['url']
    logger.info(f"Selected Video URL: {selected_video_url}")

    video_file, thumbnail_file = download_video_and_thumbnail(selected_video_url)
    if video_file:
        save_downloaded_video_id(selected_video['id'])
    return video_file, thumbnail_file

def download_thumbnail_and_convert(thumbnail_url, title):
    """Download the thumbnail and convert it to .jpg if it's .webp."""
    try:
        response = requests.get(thumbnail_url)
        img = Image.open(BytesIO(response.content))
        thumbnail_file = '2.jpg'
        img.convert("RGB").save(thumbnail_file, "JPEG")
        logger.info(f"Thumbnail saved as .jpg: {thumbnail_file}")
        return thumbnail_file
    except Exception as e:
        logger.error(f"Error downloading or converting thumbnail: {str(e)}")
        return None

def download_video_and_thumbnail(video_url):
    """Download the video and thumbnail from the given URL."""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': '1.%(ext)s',
        'cookiefile': COOKIES_FILE,  # Add cookie file support here
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        video_file = '1.mp4'
        thumbnail_file = download_thumbnail_and_convert(info['thumbnail'], info['title'])

    return video_file, thumbnail_file

def upload_video_to_youtube(video_file, thumbnail_file):
    """Upload the video to YouTube with the predefined title and description."""
    youtube = get_authenticated_service()

    title = generate_title()  # Get the dynamic title

    request_body = {
        'snippet': {
            'title': title,
            'description': CUSTOM_DESCRIPTION,
            'tags': ['horror', 'scary', 'creepy', 'paranormal'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'public'
        }
    }

    media = MediaFileUpload(video_file, mimetype='video/mp4', resumable=True)

    video_request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = video_request.execute()
    video_id = response['id']
    logger.info(f"Video uploaded successfully. Video ID: {video_id}")

    if thumbnail_file:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_file)
        ).execute()
        logger.info("Thumbnail uploaded successfully.")

    return video_id

def main():
    video_file, thumbnail_file = download_random_video_from_channel()
    if video_file:
        upload_video_to_youtube(video_file, thumbnail_file)
    else:
        logger.error("No video to upload.")

if __name__ == "__main__":
    main()
