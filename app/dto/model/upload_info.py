from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UploadInfo():
    user_id: str
    filename: str
    file_ext: str
    file_with_ext: str
    save_path: str
    saved_id: str = field(init=False)
