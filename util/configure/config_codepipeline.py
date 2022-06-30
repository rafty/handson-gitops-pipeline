class ConfigCodePipeline:

    def __init__(self, config) -> None:
        self.config = config  # codepipeline dict in cdk.json

    @property
    def pipeline_name(self):
        return self.config['pipeline_name']

    @property
    def github_token_name(self):
        return self.config['github_token_name']

    @property
    def github_source_repository(self):
        return self.config['github_source_repository']

    @property
    def github_source_repository_name(self):
        return self.config['github_source_repository_name']

    @property
    def github_owner(self):
        return self.config['github_owner']

    @property
    def github_target_repository(self):
        return self.config.get('github_target_repository')

    @property
    def github_target_manifest_dev(self):
        return self.config.get('github_target_manifest_dev')

    @property
    def github_target_manifest_prd(self):
        return self.config.get('github_target_manifest_prd')

    @property
    def ecr_repository_name(self):
        return self.config.get('ecr_repository_name')
