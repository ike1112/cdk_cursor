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

        # Create ALB Security Group
        self.alb_security_group = ec2.SecurityGroup(
            self, "ALBSecurityGroup",
            vpc=self.vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True
        )

        # Allow inbound HTTP/HTTPS traffic to ALB
        self.alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic"
        )
        self.alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS traffic"
        )

        # Create Application Security Group
        self.app_security_group = ec2.SecurityGroup(
            self, "ApplicationSecurityGroup",
            vpc=self.vpc,
            description="Security group for Application servers",
            allow_all_outbound=True
        )

        # Allow inbound traffic from ALB to Application
        self.app_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS traffic from ALB"
        )

        # Create Database Security Group
        self.db_security_group = ec2.SecurityGroup(
            self, "DatabaseSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS database",
            allow_all_outbound=False  # Restrict all outbound traffic by default
        )

        # Allow inbound traffic from Application to Database
        self.db_security_group.add_ingress_rule(
            peer=self.app_security_group,
            connection=ec2.Port.tcp(3306),  # MySQL/Aurora default port
            description="Allow traffic from Application servers"
        )

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

        # Output Security Group IDs
        CfnOutput(
            self,
            "ALBSecurityGroup",
            value=self.alb_security_group.security_group_id,
            description="Security Group ID for ALB",
            export_name="ALBSecurityGroup"
        )

        CfnOutput(
            self,
            "AppSecurityGroup",
            value=self.app_security_group.security_group_id,
            description="Security Group ID for Application",
            export_name="AppSecurityGroup"
        )

        CfnOutput(
            self,
            "DBSecurityGroup",
            value=self.db_security_group.security_group_id,
            description="Security Group ID for Database",
            export_name="DBSecurityGroup"
        ) 