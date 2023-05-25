from dataclasses import dataclass, field


@dataclass
class UploadInfo:
    user_id: str
    filename: str
    file_ext: str
    file_with_ext: str
    video_save_path: str
    audio_save_path: str = field(default=None)
    saved_id: str = field(default=None)
