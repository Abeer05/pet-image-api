import json
import base64
import boto3
import random

s3 = boto3.client('s3')
BUCKET_NAME = 'pet-image-api-bucket'
VALID_LABELS = ['cat', 'dog']


def lambda_handler(event, context):
    try:
        print("Event:", event)
        # Get query parameter
        params = event.get('queryStringParameters') or {}
        label = params.get('label')

        if not label:
            print("No label provided")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing label'})
            }

        if label not in VALID_LABELS:
            print("Invalid label:", label)
            return {
                'statusCode': 400,
                'body': json.dumps({'error': "Invalid label value — must be 'cat' or 'dog'"}),
                'headers': {'Content-Type': 'application/json'}
            }

        # List images in the S3 folder
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"{label}/")
        contents = response.get('Contents')

        if not contents:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No images found'}),
                'headers': {'Content-Type': 'application/json'}
            }

        # Pick a random image key
        keys = [item['Key']
                for item in contents if not item['Key'].endswith('/')]
        random_key = random.choice(keys)

        # Get the image binary
        image_obj = s3.get_object(Bucket=BUCKET_NAME, Key=random_key)
        image_data = image_obj['Body'].read()

        # Get the content type
        content_type = image_obj['ContentType']

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename="{random_key.split("/")[-1]}"'
            },
            'body': base64.b64encode(image_data).decode('utf-8'),
            'isBase64Encoded': True
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json'}
        }
