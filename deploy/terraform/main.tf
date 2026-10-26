provider "aws" {
  region = var.region
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

data "aws_vpc" "default" {
  default = true
}

# Only the worker port, only from your address. No SSH rule unless you opt in via key_name.
resource "aws_security_group" "worker" {
  name_prefix = "scheduler-worker-"
  description = "AI scheduler worker: 8000 from a single CIDR"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "worker API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  dynamic "ingress" {
    for_each = var.key_name == null ? [] : [1]
    content {
      description = "ssh"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.allowed_cidr]
    }
  }

  # The worker runs untrusted code, so restrict egress to what setup needs:
  # HTTPS (packages, git, container base images) and DNS.
  egress {
    description = "https"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description = "dns"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "worker" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.worker.id]

  # No iam_instance_profile: code running on the box has no AWS credentials to steal.

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 only
    http_put_response_hop_limit = 1          # containers cannot reach the metadata service
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    api_key = var.worker_api_key
    repo    = var.repo_url
    branch  = var.repo_branch
  })
  user_data_replace_on_change = true

  tags = {
    Name = "ai-scheduler-worker"
  }
}
