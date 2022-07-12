import aws_cdk
from constructs import Construct
from aws_cdk import aws_codepipeline
from aws_cdk import aws_codepipeline_actions


class SourceAction(Construct):

    def __init__(self, scope: Construct, id: str, config: dict) -> None:
        super().__init__(scope, id)

        self.config: dict = config
        self._source_output = aws_codepipeline.Artifact('source_stage_output')

    def create(self):

        source_action = aws_codepipeline_actions.GitHubSourceAction(
            action_name='github-source-action',
            owner=self.config['github_owner'],
            repo=self.config['github_source_repository_name'],
            trigger=aws_codepipeline_actions.GitHubTrigger.POLL,
            oauth_token=aws_cdk.SecretValue.secrets_manager(self.config['github_token_name']),
            output=self._source_output
        )
        return source_action

    @property
    def source_output(self):
        return self._source_output
