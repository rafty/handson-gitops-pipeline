from aws_cdk import aws_iam
from constructs import Construct
from aws_cdk import aws_codebuild
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codepipeline_actions
from _constructs.codepipeline.buildspec.buildspec import buildspec


class BuildAction(Construct):
    # ----------------------------------------------------------
    # Build Action
    # ----------------------------------------------------------
    def __init__(self, scope: Construct, id: str, source_output, config: dict, aws_env: dict) -> None:
        super().__init__(scope, id)

        self.config: dict = config
        self.account = aws_env['account']
        self.region = aws_env['region']
        self.source_output = source_output
        self.buildspec = aws_codebuild.BuildSpec.from_object(buildspec)
        self.ecr_repository_name = config['ecr_repository_name']
        self.build_output = aws_codepipeline.Artifact('build_output')

    def create(self):
        build_project = aws_codebuild.PipelineProject(
            self,
            id='sample_build_project',
            project_name='sample_build_project',
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_4_0,
                privileged=True  # for docker build
            ),
            environment_variables={
                'AWS_ACCOUNT_ID': {'value': self.account},
                'CONTAINER_IMAGE_NAME': {'value': self.ecr_repository_name}
            },
            build_spec=self.buildspec,
        )
        build_project.role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name(
            'AmazonEC2ContainerRegistryPowerUser'))

        # build_specでDockerHubのパスワードをSSMから取得するため
        build_project.add_to_role_policy(
            aws_iam.PolicyStatement(
                resources=['*'],
                actions=['ssm:GetParameters']
            )
        )

        build_action = aws_codepipeline_actions.CodeBuildAction(
            action_name='ContainerBuild',
            project=build_project,
            input=self.source_output,
            outputs=[self.build_output],
            variables_namespace='ContainerImage'  # BuildEnvironmentVariable
        )
        return build_action
