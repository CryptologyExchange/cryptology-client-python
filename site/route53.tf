data "aws_route53_zone" "cryptology_com" {
  name = "cryptology.com."
}
resource "aws_route53_record" "domain" {
  zone_id = "${data.aws_route53_zone.cryptology_com.id}"
  name = "client-python.docs.cryptology.com"
  type = "A"
  alias {
    name = "${aws_s3_bucket.site.website_domain}"
    zone_id = "${aws_s3_bucket.site.hosted_zone_id}"
    evaluate_target_health = false
  }
}
