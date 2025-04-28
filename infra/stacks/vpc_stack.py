from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput
)
from constructs import Construct

class VPCStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC
        self.vpc = ec2.Vpc(
            self, 
            "MainVPC",
            max_azs=2,
            ip_addresses=ec2.IpAddresses.cidr("10.10.0.0/16"),
            nat_gateways=1,
            subnet_configuration=[
                # Public subnet for NAT Gateway and Load Balancers
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                # Private subnet with internet access through NAT Gateway
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                # Isolated subnet for RDS with no internet access
                ec2.SubnetConfiguration(
                    name="RDS",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )

        # Add tags to VPC
        self.vpc.add_tags({
            "Environment": "Production",
            "Project": "VPC Infrastructure",
            "ManagedBy": "CDK Pipeline",
            "LastModified": "2024-03-19"
        })

        # Output the VPC ID
        CfnOutput(
            self,
            "VPCId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name="VPCId"
        )

        # Output the Public Subnets
        CfnOutput(
            self,
            "PublicSubnets",
            value=','.join([subnet.subnet_id for subnet in self.vpc.public_subnets]),
            description="Public Subnets",
            export_name="PublicSubnets"
        )

        # Output the Private Subnets
        CfnOutput(
            self,
            "PrivateSubnets",
            value=','.join([subnet.subnet_id for subnet in self.vpc.private_subnets]),
            description="Private Subnets",
            export_name="PrivateSubnets"
        )

        # Output the Isolated Subnets (for RDS)
        CfnOutput(
            self,
            "IsolatedSubnets",
            value=','.join([subnet.subnet_id for subnet in self.vpc.isolated_subnets]),
            description="Isolated Subnets for RDS",
            export_name="IsolatedSubnets"
        ) 