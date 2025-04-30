from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    CfnOutput,
    Duration
)
from constructs import Construct
import os



class ASGStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 vpc: ec2.Vpc, 
                 target_group: elbv2.ApplicationTargetGroup,
                 app_security_group: ec2.SecurityGroup,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for EC2 instances
        # This role enables AWS Systems Manager (SSM) which is useful for:
        # 1. Production environments: 
        #    - Remote server management without SSH
        #    - Secure access through AWS IAM
        #    - Running system updates and patches
        # 2. Troubleshooting:
        #    - Access server logs
        #    - Debug application issues
        #    - Monitor system performance
        # 3. Maintenance:
        #    - Install/update software
        #    - Configure system settings
        #    - Run administrative commands
        role = iam.Role(
            self, "AppServerRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        
        # Add SSM managed policy to allow managing instances
        # This eliminates the need for:
        # - SSH key management
        # - Opening port 22 in security groups
        # - Direct internet access for management
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )

        # Add S3 read access for the specific bucket
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject"],
            resources=["arn:aws:s3:::vpcbucket100/*"]
        ))

        # Add RDS policy to allow describing DB clusters
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["rds:DescribeDBClusters"],
            resources=["*"]
        ))

        # Get the absolute path to userdata.sh
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        userdata_path = os.path.join(current_dir, 'application', 'userdata.sh')
        
        # Read and process userdata script
        with open(userdata_path, "r") as f:
            user_data = f.readlines()
            
        # Add each line from the script to ec2 UserData
        ec2_user_data = ec2.UserData.for_linux()
        for line in user_data:
            if line.strip() and not line.strip().startswith('#'):
                ec2_user_data.add_commands(line.strip())
        
        # Create Launch Template
        launch_template = ec2.LaunchTemplate(
            self, "AppServerTemplate",
            instance_type=ec2.InstanceType("t3.micro"),  # Cost-effective instance type
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023
            ),
            role=role,
            user_data=ec2_user_data,
            security_group=app_security_group
        )

        # Create Auto Scaling Group
        self.asg = autoscaling.AutoScalingGroup(
            self, "AppServerASG",
            vpc=vpc,
            # Place ASG instances in the private subnets created in VPC Stack
            # These subnets have NAT Gateway access for updates but no direct internet access
            vpc_subnets=ec2.SubnetSelection(
                subnets=vpc.private_subnets
            ),
            launch_template=launch_template,
            # Minimum number of instances running at all times
            # Set to 1 for cost optimization, increase to 2+ for high availability
            min_capacity=1,
            # Maximum number of instances that ASG can scale to
            # Limits the scaling to control costs
            max_capacity=2,
            # Initial and desired number of instances
            # Starts with 1 instance and scales based on demand
            desired_capacity=1,
            # Health check settings for the ALB to monitor instance health
            # Grace period gives instance 60 seconds to start up before checking
            health_check=autoscaling.HealthCheck.elb(
                grace=Duration.seconds(60)
            ),
            # Cooldown period between scaling activities (in seconds)
            # Prevents rapid scaling up/down by waiting 5 minutes between actions
            cooldown=Duration.seconds(300)
        )

        # Add ASG to ALB target group
        self.asg.attach_to_application_target_group(target_group)

        # Add scaling policies
        self.asg.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            cooldown=Duration.seconds(300)
        )

        # Output ASG name
        CfnOutput(
            self, "AutoScalingGroupName",
            value=self.asg.auto_scaling_group_name,
            description="Name of the Auto Scaling Group"
        ) 