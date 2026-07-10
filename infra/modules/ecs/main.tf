# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

data "aws_region" "current" {}

locals {
  run_container_name = "run"
}

resource "aws_ecs_cluster" "this" {
  name = var.name
}

resource "aws_ecs_task_definition" "fastapi" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([
    {
      name      = "fastapi"
      image     = var.image
      essential = true

      environment = var.environment
      secrets     = [for s in var.secrets : { name = s.name, valueFrom = s.value_from }]

      portMappings = [{
        containerPort = var.container_port
        protocol      = "tcp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = data.aws_region.current.region
          "awslogs-stream-prefix" = "fastapi"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "fastapi" {
  name            = var.name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.fastapi.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "fastapi"
    container_port   = var.container_port
  }

  # Manage desired_count via Terraform (remove ignore_changes unless desired_count is controlled by autoscaling).
}

resource "aws_ecs_task_definition" "run" {
  family                   = "${var.name}-${local.run_container_name}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([
    {
      name      = local.run_container_name
      image     = var.image
      essential = true

      environment = var.environment
      secrets = [
        for s in concat(var.secrets, var.run_extra_secrets) :
        { name = s.name, valueFrom = s.value_from }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = data.aws_region.current.region
          "awslogs-stream-prefix" = local.run_container_name
        }
      }

      command = var.run_command
    }
  ])
}
