import aws_cdk
from constructs import Construct
from util.configure.config_aws_env import ConfigAwsEnv
from util.configure.config_vpc import ConfigVpc
from util.configure.config_eks import ConfigEks
from util.configure.config_env import ConfigEnv
from util.configure.config_flask_app import ConfigFlaskApp
from util.configure.config_codepipeline import ConfigCodePipeline


class Config(Construct):
    # Stackに必要なDefineを保管する。
    # cdk.jsonに保管された環境毎の設定を保管する。
    # Stack毎に異なるawsのaccount,regionなどはStackの最初に保管する。
    # 動的な変数は管理しない。

    def __init__(self, scope: Construct, id: str, sys_env: str, _aws_env: aws_cdk.Environment) -> None:
        super().__init__(scope, id)

        if sys_env is not None:  # eks clusterのconfig
            self.sys_env = sys_env  # dev-1, stg-1, prd-1
            self.env_config = self.node.try_get_context(key=sys_env)  # from cdk.json

        self._aws_env: aws_cdk.Environment = _aws_env  # region, account
        self.codepipeline_config = self.node.try_get_context(key='codepipeline')  # from cdk.json

    @property
    def aws_env(self):
        return ConfigAwsEnv(self._aws_env)

    @property
    def codepipeline(self):
        return ConfigCodePipeline(self.codepipeline_config)

    @property
    def env(self):
        if not self.env_config.get('env'):
            raise
        return ConfigEnv(self.env_config['env'])

    @property
    def vpc(self):
        if not self.env_config.get('vpc'):
            raise
        return ConfigVpc(self.env_config['vpc'])

    @property
    def eks(self):
        if not self.env_config.get('eks'):
            raise
        return ConfigEks(self.env_config['eks'])

    @property
    def flask_app(self):
        if not self.env_config.get('flask_app'):
            return None
        return ConfigFlaskApp(self.env_config['flask_app'])

