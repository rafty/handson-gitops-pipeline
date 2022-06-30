import aws_cdk


class ConfigAwsEnv:

    def __init__(self, config_aws_env: aws_cdk.Environment) -> None:

        self.check_parameter(config_aws_env)
        self._config_aws_env = config_aws_env

    @property
    def region(self):
        return self._config_aws_env.region

    @property
    def account(self):
        return self._config_aws_env.account

    @staticmethod
    def check_parameter(config_aws_env):
        if type(config_aws_env) is not aws_cdk.Environment:
            raise TypeError('Set aws_cdk.Environment to Stack.')
