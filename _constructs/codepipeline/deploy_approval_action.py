from constructs import Construct
from aws_cdk import aws_codepipeline_actions


class DeployApprovalAction(Construct):
    # ----------------------------------------------------------
    # Stage - Manifest Tag Update (GitHub)
    # ----------------------------------------------------------

    def __init__(self, scope: Construct, id: str, stage: str, config: dict) -> None:
        super().__init__(scope, id)

        self.stage = stage
        self.config: dict = config

    def create(self) -> aws_codepipeline_actions.ManualApprovalAction:
        # SNS Topic -> Lambda Action, Notifyを行っても良い

        action = aws_codepipeline_actions.ManualApprovalAction(
            action_name=f'DeployApproval-{self.stage}',
        )
        return action
