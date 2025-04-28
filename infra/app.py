#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.vpc_stack import VPCStack
from stacks.pipeline_stack import PipelineStack

app = cdk.App()

# Deploy VPC Stack
vpc_stack = VPCStack(app, "VPCStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

# Deploy Pipeline Stack
pipeline_stack = PipelineStack(app, "PipelineStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

app.synth()
