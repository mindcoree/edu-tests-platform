from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from s3.schemas import ImageUploadResponse
from utils.s3 import s3_client
from auth.models import AuthEntity
from auth.dependencies import get_auth_service
import io
from fastapi.responses import StreamingResponse

router = APIRouter(
    prefix="/s3",
    tags=["S3"],
)


@router.get("/image/{image_key}")
async def get_image(image_key: str):
    """
    Возвращает изображение по ключу из S3.
    """
    obj = s3_client.client.get_object(Bucket=s3_client.bucket_name, Key=image_key)
    return StreamingResponse(obj["Body"], media_type="image/jpeg")


@router.post(
    "/upload/image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    current_user: AuthEntity = Depends(get_auth_service),
):
    """
    Uploads an image to the S3 storage.

    - **file**: The image file to upload (e.g., .jpg, .png).
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File provided is not an image.",
        )

    # Upload the file and get the object key
    object_key = s3_client.upload_file(file=file)

    # Get the public URL for the uploaded file
    public_url = s3_client.get_public_url(object_key)

    return ImageUploadResponse(image_key=object_key, image_url=public_url)
