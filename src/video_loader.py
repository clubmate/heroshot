"""
Video loading functionality for YouTube and local files
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from tqdm import tqdm

from .utils import is_youtube_url, extract_youtube_id, sanitize_filename, get_video_info
from .config import get_config

logger = logging.getLogger(__name__)


class VideoLoader:
    """Video loader for YouTube URLs and local files"""
    
    def __init__(self):
        self.config = get_config()
    
    def load_video(self, source: str, output_dir: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Load video from source (YouTube URL or local file)
        
        Args:
            source: YouTube URL or local file path
            output_dir: Directory to save downloaded video (for YouTube)
            
        Returns:
            Tuple of (video_path, video_info)
        """
        if is_youtube_url(source):
            return self._load_youtube_video(source, output_dir)
        else:
            return self._load_local_video(source)
    
    def _load_youtube_video(self, url: str, output_dir: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Download video from YouTube
        
        Args:
            url: YouTube URL
            output_dir: Directory to save video
            
        Returns:
            Tuple of (video_path, video_info)
        """
        try:
            import yt_dlp
        except ImportError:
            logger.error("yt-dlp not installed. Please install with: pip install yt-dlp")
            raise ImportError("yt-dlp is required for YouTube video downloads")
        
        if output_dir is None:
            output_dir = self.config.get('output.base_directory', 'outputs')
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Extract video ID for consistent naming
        video_id = extract_youtube_id(url)
        if not video_id:
            logger.warning("Could not extract video ID from URL")
            video_id = "unknown"
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer mp4, fallback to best quality
            'outtmpl': str(output_path / f'{video_id}_%(title)s.%(ext)s'),
            'restrictfilenames': True,  # Use only ASCII characters in filenames
            'noplaylist': True,  # Download single video only
            'ignoreerrors': False,
        }
        
        # Add progress hook
        ydl_opts['progress_hooks'] = [self._youtube_progress_hook]
        
        logger.info(f"Downloading YouTube video: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                
                # Create safe filename
                title = info.get('title', 'Unknown Title')
                safe_title = sanitize_filename(title)
                
                # Update output template with safe title
                ydl_opts['outtmpl'] = str(output_path / f'{video_id}_{safe_title}.%(ext)s')
                
                # Download video
                ydl = yt_dlp.YoutubeDL(ydl_opts)
                ydl.download([url])
                
                # Find downloaded file
                downloaded_file = self._find_downloaded_file(output_path, video_id, safe_title)
                
                if not downloaded_file:
                    raise RuntimeError("Downloaded file not found")
                
                # Get video information
                video_info = get_video_info(downloaded_file)
                video_info.update({
                    'source': 'youtube',
                    'url': url,
                    'video_id': video_id,
                    'title': title,
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                })
                
                logger.info(f"Successfully downloaded: {downloaded_file}")
                return str(downloaded_file), video_info
                
            except Exception as e:
                logger.error(f"Failed to download YouTube video: {e}")
                raise
    
    def _youtube_progress_hook(self, d):
        """Progress hook for yt-dlp downloads"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                downloaded = d.get('downloaded_bytes', 0)
                percent = (downloaded / total) * 100
                logger.info(f"Download progress: {percent:.1f}%")
        elif d['status'] == 'finished':
            logger.info(f"Download completed: {d['filename']}")
    
    def _find_downloaded_file(self, output_path: Path, video_id: str, title: str) -> Optional[str]:
        """
        Find downloaded file in output directory
        
        Args:
            output_path: Output directory
            video_id: Video ID
            title: Video title
            
        Returns:
            Path to downloaded file or None
        """
        # Common video extensions
        extensions = ['.mp4', '.mkv', '.webm', '.avi', '.mov']
        
        # Search patterns
        patterns = [
            f"{video_id}_{title}",
            f"{video_id}",
            title,
        ]
        
        for pattern in patterns:
            for ext in extensions:
                potential_file = output_path / f"{pattern}{ext}"
                if potential_file.exists():
                    return str(potential_file)
        
        # Fallback: find any file with video_id
        for file_path in output_path.glob(f"*{video_id}*"):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                return str(file_path)
        
        return None
    
    def _load_local_video(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Load local video file
        
        Args:
            file_path: Path to local video file
            
        Returns:
            Tuple of (video_path, video_info)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        # Check if file is a video
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v']
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in video_extensions:
            logger.warning(f"File extension '{file_ext}' may not be a supported video format")
        
        # Get video information
        video_info = get_video_info(file_path)
        video_info.update({
            'source': 'local',
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'file_extension': file_ext,
        })
        
        logger.info(f"Loaded local video: {file_path}")
        return file_path, video_info


def detect_source_type(source: str) -> str:
    """
    Detect source type (YouTube or local file)
    
    Args:
        source: Source string (URL or file path)
        
    Returns:
        Source type: 'youtube' or 'local'
    """
    if is_youtube_url(source):
        return 'youtube'
    else:
        return 'local'


def validate_video_source(source: str) -> bool:
    """
    Validate video source
    
    Args:
        source: Source string (URL or file path)
        
    Returns:
        True if source is valid
    """
    source_type = detect_source_type(source)
    
    if source_type == 'youtube':
        return extract_youtube_id(source) is not None
    else:
        return os.path.exists(source)


# Alternative implementation using pytube (in case yt-dlp is not available)
class PyTubeVideoLoader:
    """Alternative YouTube video loader using pytube"""
    
    def __init__(self):
        self.config = get_config()
    
    def download_youtube_video(self, url: str, output_dir: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Download video from YouTube using pytube
        
        Args:
            url: YouTube URL
            output_dir: Directory to save video
            
        Returns:
            Tuple of (video_path, video_info)
        """
        try:
            from pytube import YouTube
            from pytube.exceptions import RegexMatchError, VideoUnavailable
        except ImportError:
            logger.error("pytube not installed. Please install with: pip install pytube")
            raise ImportError("pytube is required for YouTube video downloads")
        
        if output_dir is None:
            output_dir = self.config.get('output.base_directory', 'outputs')
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Downloading YouTube video with pytube: {url}")
            
            # Create YouTube object
            yt = YouTube(url, on_progress_callback=self._pytube_progress_hook)
            
            # Get highest quality mp4 stream
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                # Fallback to any available stream
                stream = yt.streams.first()
            
            if not stream:
                raise RuntimeError("No available streams found")
            
            # Create safe filename
            safe_title = sanitize_filename(yt.title)
            filename = f"{yt.video_id}_{safe_title}.mp4"
            
            # Download video
            downloaded_file = stream.download(output_path=str(output_path), filename=filename)
            
            # Get video information
            video_info = get_video_info(downloaded_file)
            video_info.update({
                'source': 'youtube',
                'url': url,
                'video_id': yt.video_id,
                'title': yt.title,
                'uploader': yt.author,
                'description': yt.description,
                'view_count': yt.views,
                'length': yt.length,
            })
            
            logger.info(f"Successfully downloaded: {downloaded_file}")
            return downloaded_file, video_info
            
        except (RegexMatchError, VideoUnavailable) as e:
            logger.error(f"YouTube video not available or invalid URL: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to download YouTube video with pytube: {e}")
            raise
    
    def _pytube_progress_hook(self, stream, chunk, bytes_remaining):
        """Progress hook for pytube downloads"""
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percent = (bytes_downloaded / total_size) * 100
        logger.debug(f"Download progress: {percent:.1f}%")