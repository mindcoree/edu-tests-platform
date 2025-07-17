from pydantic import BaseModel, HttpUrl


class ImageUploadResponse(BaseModel):
    image_key: str
    image_url: HttpUrl
