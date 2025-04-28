from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    SecretValue,
    Environment
)
from constructs import Construct

class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create the pipeline
        pipeline = codepipeline.Pipeline(
            self, "VPCInfraPipeline",
            pipeline_name="vpc-infrastructure-pipeline"
        )

        # Source stage
        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.GitHubSourceAction(
            action_name="GitHub_Source",
            owner="ike1112",  # Replace with your GitHub username
            repo="cdk_cursor",  # Replace with your repository name
            branch="main",
            oauth_token=SecretValue.secrets_manager("github-token"),  # Create this secret in AWS Secrets Manager
            output=source_output
        )

        # Add source stage
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Build stage
        build_output = codepipeline.Artifact()
        build_project = codebuild.PipelineProject(
            self, "BuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                privileged=True
            ),
            environment_variables={
                "ENV": codebuild.BuildEnvironmentVariable(value="prod")
            },
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "python": "3.9"
                        },
                        "commands": [
                            "cd infra",
                            "pip install -r requirements.txt"
                        ]
                    },
                    "build": {
                        "commands": [
                            "npm install -g aws-cdk",
                            "cdk synth",
                            "cdk deploy --require-approval never"
                        ]
                    }
                },
                "artifacts": {
                    "files": ["infra/cdk.out/**/*"]
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