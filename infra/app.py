#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.vpc_stack import VPCStack
from stacks.pipeline_stack import PipelineStack
from stacks.alb_stack import ALBStack
from stacks.asg_stack import ASGStack
from stacks.rds_stack import RDSStack

app = cdk.App()

# Deploy VPC Stack
vpc_stack = VPCStack(app, "VPCStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

# Deploy RDS Stack
rds_stack = RDSStack(app, "RDSStack",
    vpc=vpc_stack.vpc,
    db_security_group=vpc_stack.db_security_group,
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

# Deploy ALB Stack
alb_stack = ALBStack(app, "ALBStack",
    vpc=vpc_stack.vpc,
    alb_sg=vpc_stack.alb_security_group,
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

# Deploy ASG Stack
asg_stack = ASGStack(app, "ASGStack",
    vpc=vpc_stack.vpc,
    target_group=alb_stack.target_group,
    app_security_group=vpc_stack.app_security_group,
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

# Add dependencies
rds_stack.add_dependency(vpc_stack)
alb_stack.add_dependency(vpc_stack)
asg_stack.add_dependency(alb_stack)

# Deploy Pipeline Stack
pipeline_stack = PipelineStack(app, "PipelineStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

app.synth()
