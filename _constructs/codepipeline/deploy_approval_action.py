from constructs import Construct
from aws_cdk import aws_codepipeline_actions
from util.configure.config import Config


class DeployApprovalAction(Construct):
    # ----------------------------------------------------------
    # Stage - Manifest Tag Update (GitHub)
    # ----------------------------------------------------------

    def __init__(self, scope: Construct, id: str, stage: str, config: Config, **kwargs) -> None:
        super().__init__(scope, id)

        self.config = config
        self.stage = stage

    def create(self) -> aws_codepipeline_actions.ManualApprovalAction:
        # SNS Topic -> Lambda Action, Notifyを行っても良い

        action = aws_codepipeline_actions.ManualApprovalAction(
            action_name=f'DeployApproval-{self.stage}',
        )
        return action
