from aws_cdk import aws_iam
from constructs import Construct
from aws_cdk import aws_codebuild
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codepipeline_actions
from buildspec.buildspec import buildspec_object
from util.configure.config import Config


class BuildStage(Construct):
    # ----------------------------------------------------------
    # ----------------------------------------------------------

    # def __init__(self, scope: Construct, id: str, source_output, env, **kwargs) -> None:
    def __init__(self, scope: Construct, id: str, source_output, config: Config,  **kwargs) -> None:
        super().__init__(scope, id)

        # self._account = env.get('account')
        # self._region = env.get('region')
        self.config: Config = config
        self._account = self.config.aws_env.account
        self._region = self.config.aws_env.region

        self.source_output = source_output
        self.build_spec = aws_codebuild.BuildSpec.from_object(buildspec_object)

        # self.ecr_repository_name = self.node.try_get_context('ecr_repository_name')
        self.ecr_repository_name = self.config.codepipeline.ecr_repository_name

        self.build_output = aws_codepipeline.Artifact('build_output')

    def creation(self):
        build_project = aws_codebuild.PipelineProject(
            self,
            id='sample_build_project',
            project_name='sample_build_project',
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_4_0,
                privileged=True  # for docker build
            ),
            environment_variables={
                'AWS_ACCOUNT_ID': {'value': self._account},
                'CONTAINER_IMAGE_NAME': {'value': self.ecr_repository_name}
            },
            build_spec=self.build_spec,
        )
        build_project.role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name(
            'AmazonEC2ContainerRegistryPowerUser'))

        # build_specでDockerHubのパスワードをSSMから取得するために必要
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
        # -----------------------------------------------------------------
        # BuildEnvironmentVariable
        #   buildspecの中で出力した変数を環境変数として出力し、後段のStageに値を渡す。
        #   namespace: ContainerImage
        #   variable: VAR_CONTAINER_IMAGE_NAME
        #   variable: VAR_CONTAINER_IMAGE_TAG
        # -----------------------------------------------------------------

        return build_action
