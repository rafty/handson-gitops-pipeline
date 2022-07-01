from constructs import Construct
from aws_cdk import aws_codepipeline_actions
from aws_cdk import aws_lambda
from util.configure.config import Config


class TagUpdateAction(Construct):
    # ----------------------------------------------------------
    # Stage - Manifest Tag Update (GitHub)
    # ----------------------------------------------------------
    def __init__(self,
                 scope: Construct,
                 id: str,
                 function: aws_lambda.Function,
                 container_info: dict,
                 target_manifest_info: dict,
                 config: Config,
                 **kwargs) -> None:
        super().__init__(scope, id)

        self.config = config
        self._region = self.config.aws_env.region

        self.function = function
        self._container_image_tag = container_info.get('container_image_tag')  # from Build Stage
        self.github_target_repository = target_manifest_info.get('github_target_repository')
        self.github_target_manifest = target_manifest_info.get('github_target_manifest')
        self.github_token_name = target_manifest_info.get('github_token_name')

    def create(self):
        # ----------------------------------------------------------
        # Stage - Manifest Tag Update (GitHub)
        # ----------------------------------------------------------
        lambda_invoke_action = aws_codepipeline_actions.LambdaInvokeAction(
            action_name='github-manifest-tag-update',
            user_parameters={
                'github_target_repository': self.github_target_repository,
                'github_target_manifest': self.github_target_manifest,
                'github_branch': 'master',
                'github_token_name': self.github_token_name,
                'container_image_tag': self._container_image_tag,  # from Build Stage
            },
            lambda_=self.function,
        )
        return lambda_invoke_action
