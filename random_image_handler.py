import json
import base64
import boto3
import random
import os

s3 = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
print(f"Using bucket: {BUCKET_NAME}")
if not BUCKET_NAME:
    raise ValueError("Environment variable BUCKET_NAME is not set")
VALID_LABELS = ['cat', 'dog']
METADATA_KEY = 'weights.json'

# RETURNING BINARY IMAGES - USED IN ORIGINAL FUNCTION

# weights_cache = None  # Cache weights to reduce warm S3 calls


# def load_weights():
#     global weights_cache
#     if weights_cache is None:
#         try:
#             response = s3.get_object(Bucket=BUCKET_NAME, Key=METADATA_KEY)
#             weights_cache = json.loads(response['Body'].read().decode('utf-8'))
#         except Exception as e:
#             print("Error loading weights:", str(e))
#             weights_cache = {}
#     return weights_cache


# def lambda_handler(event, context):
#     try:
#         print("Event:", event)
#         # Get query parameter
#         params = event.get('queryStringParameters') or {}
#         label = params.get('label')

#         if not label:
#             print("No label provided")
#             return {
#                 'statusCode': 400,
#                 'body': json.dumps({'error': 'Missing label'}),
#                 'headers': {'Content-Type': 'application/json'}
#             }

#         if label not in VALID_LABELS:
#             print("Invalid label:", label)
#             return {
#                 'statusCode': 400,
#                 'body': json.dumps({'error': "Invalid label value — must be 'cat' or 'dog'"}),
#                 'headers': {'Content-Type': 'application/json'}
#             }

#         # Load weights from S3
#         weights = load_weights()

#         if label not in weights or not weights[label]:
#             return {
#                 'statusCode': 404,
#                 'body': json.dumps({'error': 'No images found for this label'}),
#                 'headers': {'Content-Type': 'application/json'}
#             }

#         # Extract keys and weights for the label
#         images = weights[label]
#         keys = [item['key'] for item in images]
#         weights_list = [item['weight'] for item in images]

#         # Select a key using weighted randomness
#         random_key = random.choices(keys, weights=weights_list, k=1)[0]

#         # Get the image binary
#         image_obj = s3.get_object(Bucket=BUCKET_NAME, Key=random_key)
#         image_data = image_obj['Body'].read()

#         # Get the content type
#         content_type = image_obj['ContentType']

#         return {
#             'statusCode': 200,
#             'headers': {
#                 'Content-Type': content_type,
#                 'Content-Disposition': f'attachment; filename="{random_key.split("/")[-1]}"'
#             },
#             'body': base64.b64encode(image_data).decode('utf-8'),
#             'isBase64Encoded': True
#         }

#     except Exception as e:
#         return {
#             'statusCode': 500,
#             'body': json.dumps({'error': str(e)}),
#             'headers': {'Content-Type': 'application/json'}
#         }

# PRE-SIGNED URL METHOD FOR EFFICIENCY - USED IN NEW FUNCTION

def lambda_handler(event, context):
    try:
        params = event.get('queryStringParameters') or {}
        label = params.get('label')

        if not label:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing label'}),
                'headers': {'Content-Type': 'application/json'}
            }

        if label not in VALID_LABELS:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': "Invalid label value — must be 'cat' or 'dog'"}),
                'headers': {'Content-Type': 'application/json'}
            }

        # Load weights.json
        try:
            weights_obj = s3.get_object(Bucket=BUCKET_NAME, Key=METADATA_KEY)
            weights = json.loads(weights_obj['Body'].read().decode('utf-8'))
        except s3.exceptions.NoSuchKey:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No weights file found'}),
                'headers': {'Content-Type': 'application/json'}
            }

        # Get list for label
        images = weights.get(label, [])
        if not images:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f'No images found for {label}'}),
                'headers': {'Content-Type': 'application/json'}
            }

        # Extract keys and weights
        keys = [item['key'] for item in images]
        weight_values = [item.get('weight', 1) for item in images]

        # Choose a file using weighted randomness
        random_key = random.choices(keys, weights=weight_values, k=1)[0]

        # Generate a pre-signed URL
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': random_key
            },
            ExpiresIn=300,  # 5 mins
            HttpMethod='GET'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'imageUrl': presigned_url}),
            'headers': {'Content-Type': 'application/json'}
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json'}
        }
