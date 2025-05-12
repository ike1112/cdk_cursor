from aws_cdk import (
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecs as ecs,
    aws_iam as iam,
    App, CfnOutput, Duration, Stack
)
from constructs import Construct

class EcsStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create VPC with 2 Availability Zones
        vpc = ec2.Vpc(
            self, "MyVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # Create ECS cluster in the VPC
        cluster = ecs.Cluster(
            self, 'EcsCluster',
            vpc=vpc,
            container_insights=True
        )

        
        # Create Auto Scaling Group for ECS cluster
        asg = autoscaling.AutoScalingGroup(
            self, "DefaultAutoScalingGroup",
            vpc=vpc,
            launch_template=ec2.LaunchTemplate(
                self, "LaunchTemplate",
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.BURSTABLE3,
                    ec2.InstanceSize.MICRO
                ),
                machine_image=ecs.EcsOptimizedImage.amazon_linux2023(),
                user_data=ec2.UserData.for_linux(),
                role=iam.Role(
                    self, "LaunchTemplateRole",
                    assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                    managed_policies=[
                        iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"),
                        iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
                    ]
                )
            ),
            min_capacity=1,
            max_capacity=4,
            desired_capacity=2,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # Add capacity provider to the cluster
        capacity_provider = ecs.AsgCapacityProvider(
            self, "AsgCapacityProvider",
            auto_scaling_group=asg,
            enable_managed_termination_protection=True,
            capacity_provider_name="my-ecs-capacity-provider"
        )
        cluster.add_asg_capacity_provider(capacity_provider)

        # Create ECS Task Definition
        task_definition = ecs.Ec2TaskDefinition(
            self, "TaskDef",
            network_mode=ecs.NetworkMode.AWS_VPC
        )

        # Add container to task definition
        container = task_definition.add_container(
            "web",
            image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),
            memory_limit_mib=256,
            cpu=256,
            essential=True
        )

        # Add port mapping
        container.add_port_mappings(
            ecs.PortMapping(
                container_port=80,
                protocol=ecs.Protocol.TCP
            )
        )

        # Create security group for the ECS service
        service_sg = ec2.SecurityGroup(
            self, "ServiceSG",
            vpc=vpc,
            description="Security group for ECS service",
            allow_all_outbound=True
        )

        # Create Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(
            self, "ALB",
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        # Add listener to ALB
        listener = alb.add_listener(
            "Listener",
            port=80,
            open=True
        )

        # Create target group
        target_group = elbv2.ApplicationTargetGroup(
            self, "TargetGroup",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3
            )
        )

        # Create ECS Service
        service = ecs.Ec2Service(
            self, "Service",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=2,
            security_groups=[service_sg],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # Add service to target group
        target_group.add_target(service)

        # Add target group to listener
        listener.add_target_groups(
            "DefaultTargetGroup",
            target_groups=[target_group]
        )

        # Allow traffic from ALB to ECS service
        service_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(alb.connections.security_groups[0].security_group_id),
            connection=ec2.Port.tcp(80),
            description="Allow traffic from ALB"
        )

        # Output the ALB DNS name
        CfnOutput(
            self, "LoadBalancerDNS",
            value=f"http://{alb.load_balancer_dns_name}"
        )

# Create the app and stack
app = App()
EcsStack(app, "EcsStack")
app.synth() 