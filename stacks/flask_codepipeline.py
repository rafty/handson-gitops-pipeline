import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_ecr
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codebuild
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
                 config: dict,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.aws_env = {'account': self.account, 'region': self.region}

        # ------------------------------------------------------------
        # ECR Repositoryの作成
        # ------------------------------------------------------------
        aws_ecr.Repository(
            self,
            id=f"{config['ecr_repository_name']}-Stack",
            repository_name=config['ecr_repository_name'],
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,  # stack削除時の動作
            # image_scan_on_push=True,  # Image Scan
            # lifecycle_rules=[removal_old_image]  # imageの世代管理
        )

        # ------------------------------------------------------------
        # CodePipelineの作成
        # ------------------------------------------------------------
        codepipeline = aws_codepipeline.Pipeline(
            self,
            id=config['pipeline_name'],
            pipeline_name=config['pipeline_name'],
            # cross_account_keys=False
        )

        # ------------------------------------------------------------
        # Stage - Source
        # ------------------------------------------------------------
        source = SourceAction(self, 'SourceStage', config=config)
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
            config=config,
            aws_env=self.aws_env
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
            config=config,
            aws_env=self.aws_env
        )
        build_action = build.create()
        codepipeline.add_stage(
            stage_name='Build',
            actions=[build_action]
        )

        # ------------------------------------------------------------
        # Stage - Dev Manifest Tag Update (GitHub)
        # ------------------------------------------------------------
        tag_update_function = TagUpdateFunction(
            self,
            'TagUpdateFunction',
            config=config,
            aws_env=self.aws_env
        )
        tag_update_action_function = tag_update_function.create()

        container_info = {
            'container_image_name': aws_codebuild.BuildEnvironmentVariable(
                value=build_action.variable('VAR_CONTAINER_IMAGE_NAME')),
            'container_image_tag': aws_codebuild.BuildEnvironmentVariable(
                value=build_action.variable('VAR_CONTAINER_IMAGE_TAG'))
        }
        cd_manifest_info = {
            'github_cd_repository': config['github_cd_repository'],
            'github_cd_manifest': config['github_cd_manifest_dev'],
            'github_token_name': config['github_token_name'],
        }
        tag_update = TagUpdateAction(
            self,
            'TagUpdateStage-Dev',
            function=tag_update_action_function,
            container_info=container_info,
            cd_manifest_info=cd_manifest_info,
            config=config,
            aws_env=self.aws_env,
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
            config=config
        )
        deploy_approval_action = prd_deploy_approval.create()
        codepipeline.add_stage(
            stage_name=f'DeployManualApproval-{stage}',
            actions=[deploy_approval_action]
        )

        # ------------------------------------------------------------
        # Stage - Prd Manifest Tag Update (on GitHub)
        # ------------------------------------------------------------
        cd_manifest_info = {
            'github_cd_repository': config['github_cd_repository'],
            'github_cd_manifest': config['github_cd_manifest_prd'],
            'github_token_name': config['github_token_name'],
        }
        tag_update = TagUpdateAction(
            self,
            'TagUpdateStage-Prd',
            function=tag_update_action_function,
            container_info=container_info,
            cd_manifest_info=cd_manifest_info,
            config=config,
            aws_env=self.aws_env
        )
        tag_update_action = tag_update.create()
        codepipeline.add_stage(
            stage_name='TagUpdate-Prd',
            actions=[tag_update_action]
        )
