import os
import subprocess
import aws_cdk
from constructs import Construct
from aws_cdk import aws_codepipeline_actions
from aws_cdk import aws_lambda
from aws_cdk import aws_iam
from util.configure.config import Config


class DeployApprovalStage(Construct):
    # ----------------------------------------------------------
    # Stage - Manifest Tag Update (GitHub)
    # ----------------------------------------------------------

    def __init__(self, scope: Construct, id: str, stage: str, config: Config, **kwargs) -> None:
        super().__init__(scope, id)

        self.config = config
        self.stage = stage

    def deploy_approval_action(self) -> aws_codepipeline_actions.ManualApprovalAction:
        # SNS Topic -> Lambda　でアクションや通知をおこなってもよい。


        action = aws_codepipeline_actions.ManualApprovalAction(
            action_name=f'DeployApproval-{self.stage}',
        )
        return action
