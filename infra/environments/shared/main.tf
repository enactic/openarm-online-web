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

# --- Route53 ---
resource "aws_route53_zone" "public" {
  name = var.route53_zone_name

  lifecycle {
    prevent_destroy = true
  }
}

output "route53_name_servers" {
  value = aws_route53_zone.public.name_servers
}

# --- Networking ---
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "${var.project}-${var.environment}"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags = {
    Name = "${var.project}-${var.environment}"
  }
}

resource "aws_subnet" "public" {
  count             = length(var.azs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]
  tags = {
    Name = "${var.project}-${var.environment}-public-${var.azs[count.index]}"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.azs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]
  tags = {
    Name = "${var.project}-${var.environment}-private-${var.azs[count.index]}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags = {
    Name = "${var.project}-${var.environment}-public"
  }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name = "${var.project}-${var.environment}-nat"
  }
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags = {
    Name = "${var.project}-${var.environment}"
  }
  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  tags = {
    Name = "${var.project}-${var.environment}-private"
  }
}

resource "aws_route" "private_nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this.id
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# VPC endpoints
resource "aws_security_group" "vpce" {
  name   = "${var.project}-${var.environment}-vpce"
  vpc_id = aws_vpc.this.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.this.cidr_block]
  }

  tags = {
    Name = "${var.project}-${var.environment}-vpce"
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset([
    "ecr.api",
    "ecr.dkr",
    "secretsmanager",
    "logs",
  ])

  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpce.id]
  private_dns_enabled = true

  tags = {
    Name = "${var.project}-${var.environment}-${each.value}"
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "${var.project}-${var.environment}-s3"
  }
}

# --- RDS ---
resource "aws_db_subnet_group" "db" {
  name       = "${var.project}-${var.environment}"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project}-${var.environment}"
  }
}

resource "aws_security_group" "db" {
  name   = "${var.project}-${var.environment}-db"
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.project}-${var.environment}-db"
  }
}

resource "aws_vpc_security_group_egress_rule" "db_all" {
  security_group_id = aws_security_group.db.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_db_instance" "db" {
  identifier     = "${var.project}-${var.environment}"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.db.id]
  multi_az               = var.rds_multi_az
  publicly_accessible    = false

  skip_final_snapshot       = var.rds_skip_final_snapshot
  final_snapshot_identifier = var.rds_skip_final_snapshot ? null : "${var.project}-${var.environment}-final"
  deletion_protection       = var.rds_deletion_protection
  backup_retention_period   = var.rds_backup_retention_period

  db_name                     = var.db_name
  username                    = var.db_username
  manage_master_user_password = true
}
