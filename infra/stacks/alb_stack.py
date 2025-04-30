from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
    Duration
)
from constructs import Construct


# TODO: Add HTTPS listener and redirect HTTP to HTTPS


class ALBStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, alb_sg: ec2.SecurityGroup, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Application Load Balancer
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "ApplicationLoadBalancer",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
            # put this ALB in the public subnets created in the VPC Stack
            vpc_subnets=ec2.SubnetSelection(
                subnets=vpc.public_subnets
            )
        )

        # Create Target Group
        self.target_group = elbv2.ApplicationTargetGroup(
            self, "DefaultTargetGroup",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                port="80",
                protocol=elbv2.Protocol.HTTP,
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        # Add HTTP listener
        http_listener = self.alb.add_listener(
            "HttpListener",
            port=80,
            default_target_groups=[self.target_group]
        )

        # Output the ALB DNS name
        CfnOutput(
            self, "LoadBalancerDNS",
            value=self.alb.load_balancer_dns_name,
            description="DNS name of the load balancer"
        ) 