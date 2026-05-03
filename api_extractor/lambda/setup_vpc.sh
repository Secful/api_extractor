#!/bin/bash
set -e

source lambda-config.sh

echo "Setting up VPC for Lambda and S3 Files..."

# Create VPC
echo "Creating VPC..."
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=${FUNCTION_NAME}-vpc}]" \
    --query 'Vpc.VpcId' \
    --output text)

echo "VPC created: $VPC_ID"

# Enable DNS
aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-hostnames

# Create subnets in 2 AZs
AZ1="${AWS_REGION}a"
AZ2="${AWS_REGION}b"

echo "Creating subnets..."
SUBNET1=$(aws ec2 create-subnet \
    --vpc-id "$VPC_ID" \
    --cidr-block 10.0.1.0/24 \
    --availability-zone "$AZ1" \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${FUNCTION_NAME}-subnet-1}]" \
    --query 'Subnet.SubnetId' \
    --output text)

SUBNET2=$(aws ec2 create-subnet \
    --vpc-id "$VPC_ID" \
    --cidr-block 10.0.2.0/24 \
    --availability-zone "$AZ2" \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${FUNCTION_NAME}-subnet-2}]" \
    --query 'Subnet.SubnetId' \
    --output text)

echo "Subnets created: $SUBNET1, $SUBNET2"

# Create Internet Gateway (for Lambda to access CloudWatch)
echo "Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=${FUNCTION_NAME}-igw}]" \
    --query 'InternetGateway.InternetGatewayId' \
    --output text)

aws ec2 attach-internet-gateway --vpc-id "$VPC_ID" --internet-gateway-id "$IGW_ID"

# Create NAT Gateway for Lambda outbound access
echo "Creating NAT Gateway..."
EIP_ALLOC=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)

NAT_GW=$(aws ec2 create-nat-gateway \
    --subnet-id "$SUBNET1" \
    --allocation-id "$EIP_ALLOC" \
    --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=${FUNCTION_NAME}-nat}]" \
    --query 'NatGateway.NatGatewayId' \
    --output text)

echo "Waiting for NAT Gateway to be available..."
aws ec2 wait nat-gateway-available --nat-gateway-ids "$NAT_GW"

# Create route tables
echo "Creating route tables..."
ROUTE_TABLE=$(aws ec2 create-route-table \
    --vpc-id "$VPC_ID" \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${FUNCTION_NAME}-rt}]" \
    --query 'RouteTable.RouteTableId' \
    --output text)

# Add route to NAT Gateway
aws ec2 create-route \
    --route-table-id "$ROUTE_TABLE" \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id "$NAT_GW"

# Associate with subnets
aws ec2 associate-route-table --subnet-id "$SUBNET1" --route-table-id "$ROUTE_TABLE"
aws ec2 associate-route-table --subnet-id "$SUBNET2" --route-table-id "$ROUTE_TABLE"

# Create security group
echo "Creating security group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name "${FUNCTION_NAME}-sg" \
    --description "Security group for API Extractor Lambda" \
    --vpc-id "$VPC_ID" \
    --query 'GroupId' \
    --output text)

# Allow NFS traffic (port 2049) within security group
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 2049 \
    --source-group "$SG_ID"

# Allow outbound traffic
aws ec2 authorize-security-group-egress \
    --group-id "$SG_ID" \
    --protocol -1 \
    --cidr 0.0.0.0/0

# Save VPC configuration
echo "export VPC_ID=$VPC_ID" >> lambda-config.sh
echo "export SUBNET_IDS=\"$SUBNET1 $SUBNET2\"" >> lambda-config.sh
echo "export SECURITY_GROUP_ID=$SG_ID" >> lambda-config.sh

echo ""
echo "VPC setup complete!"
echo "VPC ID: $VPC_ID"
echo "Subnets: $SUBNET1, $SUBNET2"
echo "Security Group: $SG_ID"
