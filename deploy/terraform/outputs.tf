output "public_ip" {
  value = aws_instance.worker.public_ip
}

output "cloud_worker_url" {
  value       = "http://${aws_instance.worker.public_ip}:8000"
  description = "Put this in .env as CLOUD_WORKER_URL (port 8000 is plain HTTP; put TLS in front for anything beyond a lab)."
}
