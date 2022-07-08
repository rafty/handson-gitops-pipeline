import aws_cdk
from aws_cdk import aws_iam
from constructs import Construct
from aws_cdk import aws_codebuild
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codepipeline_actions
from _constructs.codepipeline.buildspec.testspec import testspec_object
from util.configure.config import Config


class TestAction(Construct):
    # ----------------------------------------------------------
    # Unit Test action
    # ----------------------------------------------------------
    def __init__(self, scope: Construct, id: str, source_output, config: Config, **kwargs) -> None:
        super().__init__(scope, id)

        self.config = config
        self._account = self.config.aws_env.account
        self._region = self.config.aws_env.region
        self.source_output = source_output
        self.test_output = aws_codepipeline.Artifact('test_output')

    def create(self):

        # testspec_objectに'pytest_reports'と同じ名前を登録すること
        pytest_group = aws_codebuild.ReportGroup(
            self,
            'TestCoverageGroup',
            report_group_name='pytest_reports',
            removal_policy=aws_cdk.RemovalPolicy.DESTROY)

        test_spec = aws_codebuild.BuildSpec.from_object(testspec_object)

        test_project = aws_codebuild.PipelineProject(
            self,
            id='sample_test_project',
            project_name='sample_test_project',
            environment=aws_codebuild.BuildEnvironment(
                build_image=aws_codebuild.LinuxBuildImage.STANDARD_4_0,
                privileged=True  # for docker build
            ),
            environment_variables={
                'AWS_ACCOUNT_ID': {'value': self._account},
            },
            build_spec=test_spec,
        )
        test_project.role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name(
            'AmazonEC2ContainerRegistryPowerUser'))

        pytest_group.grant_write(test_project.grant_principal)
        aws_iam.Grant.add_to_principal(
            grantee=test_project.grant_principal,
            actions=[
                'codebuild:CreateReportGroup',
                'codebuild:CreateReport',
                'codebuild:UpdateReport',
                'codebuild:BatchPutTestCases',
                'codebuild:BatchPutCodeCoverages'  # for pytest-cov
            ],
            resource_arns=[pytest_group.report_group_arn]
        )

        test_action = aws_codepipeline_actions.CodeBuildAction(
            action_name='Testing',
            project=test_project,
            input=self.source_output,
            outputs=[self.test_output],
        )

        return test_action
