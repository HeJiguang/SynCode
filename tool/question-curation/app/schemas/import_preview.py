from __future__ import annotations

from pydantic import BaseModel


class ImportPreview(BaseModel):
    title: str
    content: str
    question_case: str
    default_code: str
    main_fuc: str
