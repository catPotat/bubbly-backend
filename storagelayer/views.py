from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

import os
import boto3
from botocore.config import Config


s3 = boto3.client('s3',
    aws_access_key_id = os.getenv('AWS_KEY_ID'),
    aws_secret_access_key = os.getenv('AWS_SECRET_KEY'),
    region_name = os.getenv('AWS_REGION'),
    config = Config(signature_version='s3v4'),
)

class CreatePresignedS3UrlAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self, request, *args, **kwargs):
        file_name = request.query_params.get('file')
        file_type = request.query_params.get('type', "")
        if not file_name:
            return Response(status=status.HTTP_417_EXPECTATION_FAILED)
        if "image" not in file_type:
            return Response(status=status.HTTP_403_FORBIDDEN)

        presigned = s3.generate_presigned_post(
            Bucket = os.getenv('AWS_BUCKET_NAME'),
            Key = "pu/"+file_name,
            Conditions = [
                # honestly the documentation sucks
                {"Content-Type": file_type},
                ["starts-with", "$Cache-Control", "max-age="]
            ],
            ExpiresIn = 300 # seconds
        )
        return Response(data=presigned, status=status.HTTP_200_OK)
