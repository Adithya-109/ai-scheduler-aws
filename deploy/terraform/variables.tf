variable "region" {
  type        = string
  default     = "ap-south-1"
  description = "AWS region for the worker."
}

variable "allowed_cidr" {
  type        = string
  description = "CIDR allowed to reach the worker, e.g. \"203.0.113.7/32\" (your public IP). There is deliberately no default: 0.0.0.0/0 is rejected."

  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && var.allowed_cidr != "0.0.0.0/0" && var.allowed_cidr != "::/0"
    error_message = "allowed_cidr must be a valid CIDR and must not be open to the whole internet."
  }
}

variable "worker_api_key" {
  type        = string
  sensitive   = true
  description = "Shared secret sent as X-API-Key. Generate: python3 -c 'import secrets;print(secrets.token_urlsafe(32))'. Note: it is stored in Terraform state and in instance user-data; protect both."

  validation {
    condition     = length(var.worker_api_key) >= 24
    error_message = "worker_api_key must be at least 24 characters."
  }
}

variable "repo_url" {
  type        = string
  description = "Git URL of this project (HTTPS, public or reachable without credentials)."
}

variable "repo_branch" {
  type    = string
  default = "main"
}

variable "instance_type" {
  type    = string
  default = "t3.medium"
}

variable "key_name" {
  type        = string
  default     = null
  description = "Optional EC2 key pair for SSH. Leave null to run with no SSH at all (use SSM or rebuild instead)."
}
