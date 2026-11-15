#!/bin/sh
set -e
cat > /etc/seaweedfs/s3.json <<JSON
{
  "identities": [
    {
      "name": "any",
      "credentials": [
        {
          "accessKey": "${S3_ACCESS_KEY}",
          "secretKey": "${S3_SECRET_KEY}"
        }
      ],
      "actions": ["Admin", "Read", "Write"]
    }
  ]
}
JSON
exec weed server -dir=/data -s3 -s3.config=/etc/seaweedfs/s3.json "$@"