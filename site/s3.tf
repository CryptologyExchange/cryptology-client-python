resource "aws_s3_bucket" "site" {
  bucket = "client-python.docs.cryptology.com"
  acl = "public-read"

  website {
    index_document = "index.html"
  }
}
