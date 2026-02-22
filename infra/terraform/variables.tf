###############################################################################
# General
###############################################################################

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Name used as a prefix for all resources"
  type        = string
  default     = "solarpros"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

###############################################################################
# Database
###############################################################################

variable "db_username" {
  description = "Master username for the RDS PostgreSQL instance"
  type        = string
}

variable "db_password" {
  description = "Master password for the RDS PostgreSQL instance"
  type        = string
  sensitive   = true
}

###############################################################################
# Networking
###############################################################################

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

###############################################################################
# ECS - API
###############################################################################

variable "ecs_api_cpu" {
  description = "CPU units for the API ECS Fargate task (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "ecs_api_memory" {
  description = "Memory (MiB) for the API ECS Fargate task"
  type        = number
  default     = 1024
}

###############################################################################
# ECS - Worker
###############################################################################

variable "ecs_worker_cpu" {
  description = "CPU units for the worker ECS Fargate tasks (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "ecs_worker_memory" {
  description = "Memory (MiB) for the worker ECS Fargate tasks"
  type        = number
  default     = 1024
}

###############################################################################
# RDS
###############################################################################

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

###############################################################################
# ElastiCache
###############################################################################

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}
