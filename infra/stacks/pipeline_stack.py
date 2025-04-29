from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sns as sns,
    RemovalPolicy,
    SecretValue,
    Environment
)
from constructs import Construct

class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create artifact bucket with encryption
        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False
        )

        # Create the pipeline
        pipeline = codepipeline.Pipeline(
            self, "VPCInfraPipeline",
            pipeline_name="vpc-infrastructure-pipeline",
            artifact_bucket=artifact_bucket,
            cross_account_keys=True
        )

        # Source stage
        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.GitHubSourceAction(
            action_name="GitHub_Source",
            owner="ike1112",
            repo="cdk_cursor",
            branch="main",
            oauth_token=SecretValue.secrets_manager("github-token"),
            output=source_output,
            trigger=codepipeline_actions.GitHubTrigger.WEBHOOK
        )

        # Add source stage
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Build stage
        build_output = codepipeline.Artifact()
        
        # Create CodeBuild IAM role with necessary permissions
        build_role = iam.Role(
            self, "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com")
        )
        
        # Add specific permissions instead of AdministratorAccess
        build_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "cloudformation:*",
                "s3:*",
                "iam:PassRole",
                "sts:AssumeRole",
                "ec2:*",
                "logs:*",
                "ssm:*"
            ]
        ))
        
        build_project = codebuild.PipelineProject(
            self, "BuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True,
                compute_type=codebuild.ComputeType.SMALL
            ),
            environment_variables={
                "ENV": codebuild.BuildEnvironmentVariable(value="prod"),
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=Stack.of(self).account),
                "AWS_REGION": codebuild.BuildEnvironmentVariable(value=Stack.of(self).region)
            },
            role=build_role,
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "python": "3.11",
                            "nodejs": "18"
                        },
                        "commands": [
                            "npm install -g aws-cdk",
                            "pip install --upgrade pip",
                            "pip install -r infra/requirements.txt"
                        ]
                    },
                    "pre_build": {
                        "commands": [
                            "cd infra",
                            "aws sts get-caller-identity",
                            "echo 'Running pre-build checks...'"
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo 'Starting CDK deployment...'",
                            "cdk synth || exit 1",
                            "cdk deploy --require-approval never --all || exit 1",
                            "echo 'Deployment completed successfully'"
                        ]
                    }
                },
                "artifacts": {
                    "base-directory": "infra/cdk.out",
                    "files": ["**/*"]
                }
            })
        )

        build_action = codepipeline_actions.CodeBuildAction(
            action_name="Build_and_Deploy",
            project=build_project,
            input=source_output,
            outputs=[build_output]
        )

        # Add build stage
        pipeline.add_stage(
            stage_name="Build_and_Deploy",
            actions=[build_action]
        ) 