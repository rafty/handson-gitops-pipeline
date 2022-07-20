from constructs import Construct
from aws_cdk import aws_codepipeline_actions
from aws_cdk import aws_lambda


class TagUpdateAction(Construct):
    # ----------------------------------------------------------
    # Stage - Manifest Tag Update (GitHub)
    # ----------------------------------------------------------
    def __init__(self,
                 scope: Construct,
                 id: str,
                 function: aws_lambda.Function,
                 container_info: dict,
                 cd_manifest_info: dict,
                 config: dict,
                 aws_env: dict) -> None:
        super().__init__(scope, id)

        self.config: dict = config
        self.region = aws_env['region']

        self.function = function
        self.container_image_tag = container_info.get('container_image_tag')  # from Build Stage
        self.github_cd_repository = cd_manifest_info.get('github_cd_repository')
        self.github_cd_branch = cd_manifest_info.get('github_cd_branch')
        self.github_cd_manifest = cd_manifest_info.get('github_cd_manifest')
        self.github_token_name = cd_manifest_info.get('github_token_name')

    def create(self):
        # ----------------------------------------------------------
        # Stage - Manifest Tag Update (GitHub)
        # ----------------------------------------------------------
        lambda_invoke_action = aws_codepipeline_actions.LambdaInvokeAction(
            action_name='github-manifest-tag-update',
            user_parameters={
                'github_cd_repository': self.github_cd_repository,
                'github_cd_manifest': self.github_cd_manifest,
                'github_branch': self.github_cd_branch,
                'github_token_name': self.github_token_name,
                'container_image_tag': self.container_image_tag,  # from Build Stage
            },
            lambda_=self.function,
        )
        return lambda_invoke_action
