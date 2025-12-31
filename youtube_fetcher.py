import yt_dlp
import re

def fetch_channel_videos(channel_url):
    """
    Fetches all videos from a YouTube channel.
    Returns a list of dictionaries with 'title' and 'url'.
    """
    
    if not channel_url.endswith('/videos') and not 'watch?v=' in channel_url:
        if re.search(r'youtube\.com/(channel/|user/|c/|@)[^/]+/?$', channel_url):
            channel_url = channel_url.rstrip('/') + '/videos'

    ydl_opts = {
        'extract_flat': True,
        'ignoreerrors': True,
        'quiet': True,
        'http_headers': {
            'Accept-Language': 'fr-FR,fr;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'extractor_args': {
            'youtube': {
                'lang': ['fr']
            }
        }
    }

    videos = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Fetching metadata from: {channel_url}")
            info = ydl.extract_info(channel_url, download=False)
            
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        title = entry.get('title')
                        url = entry.get('url')
                        if url and not url.startswith('http'):
                            url = f"https://www.youtube.com/watch?v={url}"
                            
                        if title and url and entry.get('_type') != 'playlist':
                            videos.append({'title': title, 'url': url})
            else:
                title = info.get('title')
                url = info.get('webpage_url') or info.get('url')
                if title and url:
                    videos.append({'title': title, 'url': url})
                    
    except Exception as e:
        print(f"Error fetching channel: {e}")
        return []

    return videos
