import aws_cdk
from constructs import Construct
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codepipeline_actions
from aws_cdk import aws_secretsmanager
from util.configure.config import Config


class SourceStage(Construct):
    # ----------------------------------------------------------
    # ----------------------------------------------------------

    def __init__(self, scope: Construct, id: str, config: Config, **kwargs) -> None:
        super().__init__(scope, id)

        self.config: Config = config
        self.source_output = aws_codepipeline.Artifact('source_stage_output')

    def github_source_action(self):
        # owner = self.node.try_get_context('github_owner')
        # repo = self.node.try_get_context('github_source_repository_name')
        # asm_secret_name = self.node.try_get_context('github_token_name')
        owner = self.config.codepipeline.github_owner
        repo = self.config.codepipeline.github_source_repository_name
        asm_secret_name = self.config.codepipeline.github_token_name

        oauth_token = aws_cdk.SecretValue.secrets_manager(asm_secret_name)

        source_action = aws_codepipeline_actions.GitHubSourceAction(
            action_name='github-source-action',
            owner=owner,
            repo=repo,
            trigger=aws_codepipeline_actions.GitHubTrigger.POLL,
            oauth_token=oauth_token,
            output=self.source_output
        )
        return source_action
