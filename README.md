# Pet Image API
A serverless AWS-based image upload and retrieval API built using Lambda, API Gateway, and S3. It supports random image retrieval (weighted) and secure photo uploads by label (cat or dog), with two deployment versions:
- **Pre-Deployed**: Already hosted on API Gateway (_pet-image-api_).
- **CloudFormation Stack**: Deployable via YAML template with code improvements and performance gains (_PetImageApiStack_).

## Authentication
This API requires an API key for all endpoints (both GET and POST), and you must include it in every request:
```http
x-api-key: <API_KEY>
```
Keys are not included in this repo. They can either be generated yourself (CloudFormation) or are given during the demo.

## API endpoint
```http
base_url: https://bloids9g1k.execute-api.us-east-2.amazonaws.com/dev
``` 

## Uploading Images
POST ```/upload```
- Headers: ```x-api-key```: Your API key
- Body: ```multipart/form-data```
  - file: Image file (JPEG/JPG, PNG, WEBP)
  - label: Either cat or dog
### Example (using curl):
```bash
curl -X POST "https://bloids9g1k.execute-api.us-east-2.amazonaws.com/dev/upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@path/to/cat.webp;type=image/webp" \
  -F "label=cat"
```
Use -F for both file and label. Postman handles this automatically when using form-data.

## Retrieving Random Images
GET ```/random?label=<label>```
- Required headers:
  - x-api-key: <API_KEY>
  - Accept: image/* (or specify an exact type like image/png)
### Example:
```bash
curl -OJ -X GET "https://bloids9g1k.execute-api.us-east-2.amazonaws.com/dev/random?label=cat" \
  -H "x-api-key: <API_KEY>" \
  -H "Accept: image/*"
```
-OJ saves the image with its original filename. Use --output filename.png instead for a custom name.

## YAML Stack Deployment (Optimized)
This version returns pre-signed URLs instead of the image binary data, which is faster and more scalable.
Ensure the user has the correct permissions (role management and policies) to be able to create the stack.
### Steps:
- Upload lambda code to your S3 bucket:
- Deploy with CloudFormation:
  ```bash
  aws cloudformation deploy \
    --template-file template.yaml \
    --stack-name PetImageApiStack \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
      UploadLambdaCodeBucket=<your-bucket> \
      UploadLambdaCodeKey=upload_image_handler.zip \
      RandomLambdaCodeBucket=<your-bucket> \
      RandomLambdaCodeKey=random_image_handler.zip
  ```
API endpoints/keys will appear in the deployment output.

## Known Constraints
| Version	| Limitation |
|---------|------------|
| Pre-Deployed | weights.json is hardcoded --> new uploads won't affect random image selection |
| YAML Stack | weights.json is updated on upload --> deleted images aren’t reflected (would require seperate function) |

## Cost Estimates (USD)
| Scale	| Uploads | Retrievals | Storage | Data Out	| Monthly Cost |
|-------|---------|------------|---------|----------|--------------|
| Dev/Test | 500 |	1,000 |	300 MB |	~0 GB |	~$0 (Free Tier) |
| Small App |	10K	| 50K	| 25 GB |	5 GB |	~$4.34 |
| Medium App | 100K |	500K | 200 GB |	50 GB |	~$41.85 |
| Enterprise |	1M |	10M |	2 TB |	500 GB |	~$693.50 |

## Solutions to Technical Challenges
- Manually parsed multipart/form-data in Lambda (no external parsers used)
- IAM permissions carefully scoped (PutObject, GetObject, ListBucket, CloudWatch Logs)
- Cold starts observed and mitigated with caching (weights.json)
- Optimized file serving using pre-signed URLs instead of base64
- Eplicit MIME type filtering based on Accept header
- Binary encoding handled by API Gateway via binaryMediaTypes

## Key Edge Cases Handled
- Invalid Uploads: Rejects missing files or unsupported types (jpeg/jpg, png, webp only)
- Multipart Parsing: Validates Content-Type and gracefully handles malformed inputs
- Weighted Random Image Selection: Random weights (1–10) assigned on upload; existing entries replaced
- Environment Variable Validation: Fails early if BUCKET_NAME is not set, avoiding runtime surprises
- Error Handling and Logging: The code has many try-except blocks that catch unexpected exceptions, returning 500 Internal Server Error with the error message in JSON
