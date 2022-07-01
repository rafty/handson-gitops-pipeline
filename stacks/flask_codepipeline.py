import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_ecr
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codebuild
from util.configure.config import Config
from _constructs.codepipeline.source_action import SourceAction
from _constructs.codepipeline.build_action import BuildAction
from _constructs.codepipeline.tag_update_action import TagUpdateAction
from _constructs.codepipeline.test_action import TestAction
from _constructs.codepipeline.deploy_approval_action import DeployApprovalAction
from _constructs.codepipeline.tag_update_function import TagUpdateFunction


class CodepipelineStack(Stack):

    def __init__(self,
                 scope: Construct,
                 construct_id: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = Config(self, 'Config', sys_env=None, _aws_env=kwargs.get('env'))

        # ------------------------------------------------------------
        # ECR Repositoryの作成
        # ------------------------------------------------------------
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
        codepipeline = aws_codepipeline.Pipeline(
            self,
            id=self.config.codepipeline.pipeline_name,
            pipeline_name=self.config.codepipeline.pipeline_name,
            # cross_account_keys=False
        )

        # ------------------------------------------------------------
        # Stage - Source
        # ------------------------------------------------------------
        source = SourceAction(self, 'SourceStage', config=self.config)
        source_action = source.create()
        codepipeline.add_stage(
            stage_name='Source',
            actions=[source_action]
        )

        # ------------------------------------------------------------
        # Stage - Unit Test
        # ------------------------------------------------------------
        test = TestAction(
            self,
            'TestStage',
            source_output=source.source_output,
            config=self.config
        )
        test_action = test.create()
        codepipeline.add_stage(
            stage_name='Test',
            actions=[test_action]
        )

        # ------------------------------------------------------------
        # Stage - Build
        # ------------------------------------------------------------
        build = BuildAction(
            self,
            'BuildStage',
            source_output=source.source_output,
            config=self.config
        )
        build_action = build.create()
        codepipeline.add_stage(
            stage_name='Build',
            actions=[build_action]
        )

        # ------------------------------------------------------------
        # Manifest Tag Update Function
        # ------------------------------------------------------------
        tag_update_function = TagUpdateFunction(self, 'TagUpdateFunction', config=self.config)
        tag_update_action_function = tag_update_function.create()

        # ------------------------------------------------------------
        # Stage - Dev Manifest Tag Update (GitHub)
        # ------------------------------------------------------------
        container_info = {
            'container_image_name': aws_codebuild.BuildEnvironmentVariable(
                value=build_action.variable('VAR_CONTAINER_IMAGE_NAME')),
            'container_image_tag': aws_codebuild.BuildEnvironmentVariable(
                value=build_action.variable('VAR_CONTAINER_IMAGE_TAG'))
        }
        target_manifest_info = {
            'github_target_repository': self.config.codepipeline.github_target_repository,
            'github_target_manifest': self.config.codepipeline.github_target_manifest_dev,
            'github_token_name': self.config.codepipeline.github_token_name,
        }
        tag_update = TagUpdateAction(
            self,
            'TagUpdateStage-Dev',
            function=tag_update_action_function,
            container_info=container_info,
            target_manifest_info=target_manifest_info,
            config=self.config
        )
        tag_update_action = tag_update.create()
        codepipeline.add_stage(
            stage_name='TagUpdate-Dev',
            actions=[tag_update_action]
        )

        # ------------------------------------------------------------
        # Stage - Prd Deploy Approval Stage
        # ------------------------------------------------------------
        stage = 'prd'
        prd_deploy_approval = DeployApprovalAction(
            self,
            f'DeployApprovalStage-{stage}',
            stage=stage,
            config=self.config
        )
        deploy_approval_action = prd_deploy_approval.create()
        codepipeline.add_stage(
            stage_name=f'DeployManualApproval-{stage}',
            actions=[deploy_approval_action]
        )

        # ------------------------------------------------------------
        # Stage - Prd Manifest Tag Update (on GitHub)
        # ------------------------------------------------------------
        target_manifest_info = {
            'github_target_repository': self.config.codepipeline.github_target_repository,
            'github_target_manifest': self.config.codepipeline.github_target_manifest_prd,
            'github_token_name': self.config.codepipeline.github_token_name,
        }
        tag_update = TagUpdateAction(
            self,
            'TagUpdateStage-Prd',
            function=tag_update_action_function,
            container_info=container_info,
            target_manifest_info=target_manifest_info,
            config=self.config
        )
        tag_update_action = tag_update.create()
        codepipeline.add_stage(
            stage_name='TagUpdate-Prd',
            actions=[tag_update_action]
        )
