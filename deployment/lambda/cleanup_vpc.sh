#!/bin/bash
set -e

source lambda-config.sh

echo "Cleaning up VPC resources..."
echo "WARNING: This will delete all VPC resources created for the Lambda function."
read -p "Are you sure? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Get VPC ID
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Name,Values=${FUNCTION_NAME}-vpc" \
    --query 'Vpcs[0].VpcId' \
    --output text 2>/dev/null || echo "")

if [ -z "$VPC_ID" ] || [ "$VPC_ID" = "None" ]; then
    echo "VPC not found. Nothing to clean up."
    exit 0
fi

echo "Found VPC: $VPC_ID"

# Get NAT Gateway
NAT_GW=$(aws ec2 describe-nat-gateways \
    --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
    --query 'NatGateways[0].NatGatewayId' \
    --output text 2>/dev/null || echo "")

if [ -n "$NAT_GW" ] && [ "$NAT_GW" != "None" ]; then
    echo "Deleting NAT Gateway: $NAT_GW"
    aws ec2 delete-nat-gateway --nat-gateway-id "$NAT_GW"
    echo "Waiting for NAT Gateway deletion..."
    sleep 30
fi

# Release Elastic IPs
EIP_ALLOCS=$(aws ec2 describe-addresses \
    --filters "Name=domain,Values=vpc" \
    --query 'Addresses[?AssociationId==`null`].AllocationId' \
    --output text)

for EIP in $EIP_ALLOCS; do
    echo "Releasing Elastic IP: $EIP"
    aws ec2 release-address --allocation-id "$EIP" || true
done

# Delete subnets
SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].SubnetId' \
    --output text)

for SUBNET in $SUBNETS; do
    echo "Deleting subnet: $SUBNET"
    aws ec2 delete-subnet --subnet-id "$SUBNET" || true
done

# Detach and delete Internet Gateway
IGW=$(aws ec2 describe-internet-gateways \
    --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
    --query 'InternetGateways[0].InternetGatewayId' \
    --output text 2>/dev/null || echo "")

if [ -n "$IGW" ] && [ "$IGW" != "None" ]; then
    echo "Detaching Internet Gateway: $IGW"
    aws ec2 detach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$VPC_ID" || true
    echo "Deleting Internet Gateway: $IGW"
    aws ec2 delete-internet-gateway --internet-gateway-id "$IGW" || true
fi

# Delete route tables (except main)
ROUTE_TABLES=$(aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'RouteTables[?Associations[0].Main!=`true`].RouteTableId' \
    --output text)

for RT in $ROUTE_TABLES; do
    # Disassociate from subnets
    ASSOCIATIONS=$(aws ec2 describe-route-tables \
        --route-table-ids "$RT" \
        --query 'RouteTables[0].Associations[?!Main].RouteTableAssociationId' \
        --output text)

    for ASSOC in $ASSOCIATIONS; do
        echo "Disassociating route table association: $ASSOC"
        aws ec2 disassociate-route-table --association-id "$ASSOC" || true
    done

    echo "Deleting route table: $RT"
    aws ec2 delete-route-table --route-table-id "$RT" || true
done

# Delete security groups (except default)
SECURITY_GROUPS=$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[?GroupName!=`default`].GroupId' \
    --output text)

for SG in $SECURITY_GROUPS; do
    echo "Deleting security group: $SG"
    aws ec2 delete-security-group --group-id "$SG" || true
done

# Delete VPC
echo "Deleting VPC: $VPC_ID"
aws ec2 delete-vpc --vpc-id "$VPC_ID"

echo ""
echo "VPC cleanup complete!"
echo "Note: S3 Files mount targets should be deleted via 'aws s3api delete-mount-target' if no longer needed"
