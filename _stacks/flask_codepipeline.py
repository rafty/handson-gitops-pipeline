import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_ecr
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codebuild
from util.configure.config import Config
from _constructs.codepipeline.source_stage import SourceStage
from _constructs.codepipeline.build_stage import BuildStage
from _constructs.codepipeline.tag_update_stage import TagUpdateStage
from _constructs.codepipeline.test_stage import TestStage


class CodepipelineStack(Stack):

    def __init__(self,
                 scope: Construct,
                 construct_id: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = Config(self, 'Config', sys_env=None, _aws_env=kwargs.get('env'))

        # env = {
        #     'account': self.account,
        #     'region': self.region
        # }
        region = self.config.aws_env.region,
        account = self.config.aws_env.account,

        # ------------------------------------------------------------
        # ECR Repositoryの作成
        # ------------------------------------------------------------
        # ecr_repository_name = self.node.try_get_context('ecr_repository_name')
        ecr_repository_name = self.config.codepipeline.ecr_repository_name

        self.__ecr_repo = aws_ecr.Repository(
            self,
            id=f'{ecr_repository_name}-Stack',
            repository_name=ecr_repository_name,
            # image_scan_on_push=True,  # Image Scan
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,  # stack削除時の動作
            # lifecycle_rules=[removal_old_image]  # imageの世代管理
        )

        # ------------------------------------------------------------
        # CodePipelineの作成
        # ------------------------------------------------------------
        # pipeline_name = self.node.try_get_context('pipeline_name')
        pipeline_name = self.config.codepipeline.pipeline_name

        codepipeline = aws_codepipeline.Pipeline(
            self,
            id=pipeline_name,
            pipeline_name=pipeline_name,
            # cross_account_keys=False
        )

        # ------------------------------------------------------------
        # Stage - Source
        # ------------------------------------------------------------
        source_stage = SourceStage(self, 'SourceStage', config=self.config)
        source_action = source_stage.github_source_action()
        codepipeline.add_stage(
            stage_name='Source',
            actions=[source_action]
        )

        # ------------------------------------------------------------
        # Stage - Unit Test
        # ------------------------------------------------------------
        test_stage = TestStage(
            self,
            'TestStage',
            source_output=source_stage.source_output,
            # env=env
            config=self.config
        )

        test_action = test_stage.creation()
        codepipeline.add_stage(
            stage_name='Test',
            actions=[test_action]
        )

        # ------------------------------------------------------------
        # Stage - Build
        # ------------------------------------------------------------
        build_stage = BuildStage(
            self,
            'BuildStage',
            source_output=source_stage.source_output,
            # env=env
            config=self.config
        )
        build_action = build_stage.creation()
        codepipeline.add_stage(
            stage_name='Build',
            actions=[build_action]
        )

        # ------------------------------------------------------------
        # Stage - Manifest Tag Update (GitHub)
        # ------------------------------------------------------------
        info = {
            'container_image_name': aws_codebuild.BuildEnvironmentVariable(
                value=build_action.variable('VAR_CONTAINER_IMAGE_NAME')),
            'container_image_tag': aws_codebuild.BuildEnvironmentVariable(
                value=build_action.variable('VAR_CONTAINER_IMAGE_TAG'))
        }
        tag_update_stage = TagUpdateStage(
            self,
            'TagUpdateStage',
            info=info,
            # env=env
            config=self.config
        )
        tag_update_action = tag_update_stage.github_tag_update_action()
        codepipeline.add_stage(
            stage_name='TagUpdate',
            actions=[tag_update_action]
        )
