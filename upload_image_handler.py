import json
import base64
import boto3
import re
import os
import random
from botocore.config import Config

config = Config(signature_version='s3v4', region_name='us-east-2')
s3 = boto3.client('s3', config=config)

BUCKET_NAME = os.environ['BUCKET_NAME']
FILE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
VALID_LABELS = ['cat', 'dog']
WEIGHTS_KEY = 'weights.json'  # file to store image weights


def lambda_handler(event, context):
    try:
        # Get the body as bytes
        if event.get('isBase64Encoded'):
            body_bytes = base64.b64decode(event['body'])
        else:
            raise Exception(
                'Expected base64-encoded body for multipart/form-data')

        # Extract boundary
        content_type_header = event['headers'].get(
            'content-type') or event['headers'].get('Content-Type')
        if not content_type_header.startswith('multipart/form-data'):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid Content-Type'})
            }

        boundary = content_type_header.split('boundary=')[1].strip()
        boundary_bytes = ('--' + boundary).encode('utf-8')
        parts = body_bytes.split(boundary_bytes)

        label_value = None
        file_data = None
        file_name = None
        content_type_value = None

        # Parse the multipart payload
        for part in parts:
            if not part or part == b'--\r\n' or part == b'--':
                continue

            header_body_split = part.split(b'\r\n\r\n', 1)
            if len(header_body_split) != 2:
                continue

            header_section = header_body_split[0].decode(
                'utf-8', errors='ignore')
            body_section = header_body_split[1]

            if 'name="label"' in header_section:
                label_value = body_section.decode('utf-8').strip()

            if 'name="file"' in header_section:
                for line in header_section.split('\r\n'):
                    match = re.search(r'filename="([^"]+)"', line)
                    if match:
                        file_name = match.group(1)
                    if line.lower().startswith('content-type:'):
                        content_type_value = line.split(':', 1)[1].strip()

                # Validate file type
                if content_type_value not in FILE_TYPES:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({'error': 'Invalid file type — only .jpg, .jpeg, .png, and .webp are allowed'})
                    }

                file_data = body_section

        if not label_value or not file_data or not file_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing label and/or file'})
            }

        label_value = label_value.lower()
        if label_value not in VALID_LABELS:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': "Invalid label value — must be 'cat' or 'dog'"})
            }

        # Upload image file to S3
        file_key = f"{label_value}/{file_name}"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_key,
            Body=file_data,
            ContentType=content_type_value or 'application/octet-stream'
        )

        # Assign a random weight between 1 and 10
        new_weight = random.randint(1, 10)

        # Load existing weights file or create new structure
        try:
            weights_obj = s3.get_object(Bucket=BUCKET_NAME, Key=WEIGHTS_KEY)
            weights = json.loads(weights_obj['Body'].read().decode('utf-8'))
        except s3.exceptions.NoSuchKey:
            weights = {label: [] for label in VALID_LABELS}

        # Remove any existing record for this file_key to avoid duplicates
        weights[label_value] = [
            img for img in weights[label_value] if img['key'] != file_key]

        # Append new file with weight
        weights[label_value].append({"key": file_key, "weight": new_weight})

        # Save back to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=WEIGHTS_KEY,
            Body=json.dumps(weights),
            ContentType='application/json'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'File uploaded successfully',
                'label': label_value,
                'filename': file_name,
                'assigned_weight': new_weight
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
