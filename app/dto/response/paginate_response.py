from dataclasses import dataclass

from app.dto.response.base_response import BaseResponse
from app.dto.model.metadata import Metadata


@dataclass
class PaginateResponse(BaseResponse):
    metadata: Metadata = None

    def set_metadata(self, page, limit, total_elements, total_pages):
        self.metadata = Metadata(page, limit, total_elements, total_pages)
