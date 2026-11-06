output "alarm_names" {
  value = [for a in aws_cloudwatch_metric_alarm.this : a.alarm_name]
}

output "dashboard_name" {
  value = aws_cloudwatch_dashboard.this.dashboard_name
}
