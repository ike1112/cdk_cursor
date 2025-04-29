#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.vpc_stack import VPCStack
from stacks.pipeline_stack import PipelineStack
from stacks.alb_stack import ALBStack

app = cdk.App()

# Deploy VPC Stack
vpc_stack = VPCStack(app, "VPCStack",
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

# VPC Stack must be deployed before ALB Stack because ALB Stack uses VPC Stack outputs
alb_stack.add_dependency(vpc_stack)

# Deploy Pipeline Stack
pipeline_stack = PipelineStack(app, "PipelineStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

app.synth()
