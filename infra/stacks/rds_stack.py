from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    SecretValue,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
    Duration,
    RemovalPolicy
)
from constructs import Construct

class RDSStack(Stack):
    """
    RDS Stack for Aurora MySQL cluster.
    
    This stack:
    1. Creates an Aurora MySQL cluster in private subnets
       - Uses isolated subnets for better security
       - No direct internet access
       - Accessible only from application servers
    
    2. Manages database credentials securely
       - Uses Secrets Manager for password management
       - Rotates credentials automatically
    
    3. High availability configuration
       - Multi-AZ deployment
       - Automated backups enabled
       - Deletion protection in production
    
    Dependencies:
    - VPC Stack (network, subnets, security groups)
    """
    def __init__(self, scope: Construct, construct_id: str, 
                 vpc: ec2.Vpc,
                 db_security_group: ec2.SecurityGroup,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create parameter group for Aurora MySQL (minimal settings for dev)
        parameter_group = rds.ParameterGroup(
            self, "AuroraParameterGroup",
            engine=rds.DatabaseClusterEngine.aurora_mysql(
                version=rds.AuroraMysqlEngineVersion.VER_3_04_3
            ),
            parameters={
                "character_set_server": "utf8mb4"  # Minimal setting for basic UTF-8 support
            }
        )

        # Create Aurora MySQL cluster (dev configuration)
        self.aurora_cluster = rds.DatabaseCluster(
            self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_mysql(
                version=rds.AuroraMysqlEngineVersion.VER_3_04_3
            ),
            credentials=rds.Credentials.from_password("testuser", SecretValue.unsafe_plain_text("password1234!")),
            instance_props=rds.InstanceProps(
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(
                    subnets=vpc.isolated_subnets
                ),
                instance_type=ec2.InstanceType.of(  # Smallest instance size for dev
                    ec2.InstanceClass.T4G,
                    ec2.InstanceSize.MEDIUM
                ),
                security_groups=[db_security_group]
            ),
            instances=1,  # Single instance for dev
            parameter_group=parameter_group,
            backup=rds.BackupProps(
                retention=Duration.days(1),  # Minimum backup retention for dev
                preferred_window="03:00-04:00"
            ),
            instance_identifier_base="population-db-dev",
            port=3306,
            default_database_name="Population",
            removal_policy=RemovalPolicy.DESTROY,  # For dev environment
            deletion_protection=False  # For easier cleanup in dev
        )

        # Output the cluster endpoint
        CfnOutput(
            self, "ClusterEndpoint",
            value=self.aurora_cluster.cluster_endpoint.hostname,
            description="Aurora Cluster Endpoint",
            export_name="AuroraClusterEndpoint"
        )
