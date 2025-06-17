import json
import base64
import boto3
import re

s3 = boto3.client('s3')
BUCKET_NAME = 'pet-image-api-bucket'
FILE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']


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

        # Split into parts using bytes
        parts = body_bytes.split(boundary_bytes)

        label_value = None
        file_data = None
        file_name = None
        content_type_value = None

        for part in parts:
            # Skip empty parts
            if not part or part == b'--\r\n' or part == b'--':
                continue

            header_body_split = part.split(b'\r\n\r\n', 1)

            if len(header_body_split) != 2:
                continue  # skip malformed part

            header_section = header_body_split[0].decode(
                'utf-8', errors='ignore')
            body_section = header_body_split[1]

            # Do not strip CRLF for file part
            if 'name="label"' in header_section:
                label_value = body_section.decode('utf-8').strip()

            if 'name="file"' in header_section:
                for line in header_section.split('\r\n'):
                    match = re.search(r'filename="([^"]+)"', line)
                    if match:
                        file_name = match.group(1)  # extract filename
                    if line.lower().startswith('content-type:'):
                        content_type_value = line.split(':', 1)[1].strip()

                # Validate file type
                if content_type_value not in FILE_TYPES:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({'error': 'Invalid file type — only .jpg, .jpeg, .png, and .webp are allowed'})
                    }

                file_data = body_section

        # Ensure label and file are present
        if not label_value or not file_data or not file_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing label and/or file'})
            }

        # Validate label value
        label_value = label_value.lower()
        if label_value not in ['cat', 'dog']:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': "Invalid label value — must be 'cat' or 'dog'"})
            }

        # Upload to S3 in respective folder
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{label_value}/{file_name}",
            Body=file_data,
            ContentType=content_type_value or 'application/octet-stream'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'File uploaded successfully',
                'label': label_value,
                'filename': file_name
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
