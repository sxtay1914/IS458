variable "name" {
  type = string
}

variable "callback_urls" {
  description = "OAuth redirect URIs: the CloudFront URL's /auth/callback plus localhost for development."
  type        = list(string)
}

variable "logout_urls" {
  type = list(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}
