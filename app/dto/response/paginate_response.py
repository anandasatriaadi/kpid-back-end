from dataclasses import dataclass, field

from app.dto.model.metadata import Metadata
from app.dto.response.base_response import BaseResponse


@dataclass
class PaginateResponse(BaseResponse):
    metadata: Metadata = field(default=None)

    def set_metadata(self, page: int, limit: int, total_elements: int, total_pages: int):
        self.metadata = Metadata(page, limit, total_elements, total_pages)

    def set_metadata_direct(self, metadata: Metadata):
        self.metadata = metadata
