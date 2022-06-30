import aws_cdk
from aws_cdk import aws_iam
from constructs import Construct
from aws_cdk import aws_codebuild
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codepipeline_actions
from buildspec.test_spec import test_spec_object
from util.configure.config import Config


class TestStage(Construct):
    # ----------------------------------------------------------
    # ----------------------------------------------------------

    # def __init__(self, scope: Construct, id: str, source_output, env, **kwargs) -> None:
    def __init__(self, scope: Construct, id: str, source_output, config: Config, **kwargs) -> None:
        super().__init__(scope, id)

        self.config = config
        # self._account = env.get('account')
        # self._region = env.get('region')
        self._account = self.config.aws_env.account
        self._region = self.config.aws_env.region

        self.source_output = source_output
        self.test_output = aws_codepipeline.Artifact('test_output')

    def creation(self):

        pytest_group = aws_codebuild.ReportGroup(
            self,
            'TestCoverageGroup',
            report_group_name='pytest_reports',
            removal_policy=aws_cdk.RemovalPolicy.DESTROY)
        # test_specに同じ名前を登録する　'pytest_reports'

        test_spec = aws_codebuild.BuildSpec.from_object(test_spec_object)

        test_project = aws_codebuild.PipelineProject(
            self,
            id='sample_test_project',
            project_name='sample_test_project',
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_4_0,
                privileged=True  # for docker build
            ),
            environment_variables={
                'AWS_ACCOUNT_ID': {'value': self._account},  # Todo: 必要ない！！
            },
            build_spec=test_spec,
        )
        test_project.role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name(
            'AmazonEC2ContainerRegistryPowerUser'))

        # test_project.add_to_role_policy(
        #     aws_iam.PolicyStatement(
        #         resources=['*'],
        #         actions=['codebuild:????????']
        #     )
        # )
        pytest_group.grant_write(test_project.grant_principal)
        aws_iam.Grant.add_to_principal(
            grantee=test_project.grant_principal,
            actions=[
                'codebuild:CreateReportGroup',
                'codebuild:CreateReport',
                'codebuild:UpdateReport',
                'codebuild:BatchPutTestCases',
                'codebuild:BatchPutCodeCoverages'  # todo: add pytest-cov
            ],
            resource_arns=[pytest_group.report_group_arn]
        )

        test_action = aws_codepipeline_actions.CodeBuildAction(
            action_name='Testing',
            project=test_project,
            input=self.source_output,
            outputs=[self.test_output],
            # variables_namespace='ContainerImage'  # BuildEnvironmentVariable
        )

        return test_action
