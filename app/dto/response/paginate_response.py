from dataclasses import dataclass, field

from app.dto.model.metadata import Metadata
from app.dto.response.base_response import BaseResponse


@dataclass
class PaginateResponse(BaseResponse):
    metadata: Metadata = field(default=None)

    def set_metadata(self, page, limit, total_elements, total_pages):
        self.metadata = Metadata(page, limit, total_elements, total_pages)
