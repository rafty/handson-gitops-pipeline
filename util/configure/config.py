import aws_cdk
from constructs import Construct
from util.configure.config_aws_env import ConfigAwsEnv
from util.configure.config_vpc import ConfigVpc
from util.configure.config_eks import ConfigEks
from util.configure.config_env import ConfigEnv
from util.configure.config_flask_backend import ConfigFlaskBackend


class Config(Construct):
    # Stackに必要なDefineを保管する。
    # cdk.jsonに保管された環境毎の設定を保管する。
    # Stack毎に異なるawsのaccount,regionなどはStackの最初に保管する。
    # 動的な変数は管理しない。

    def __init__(self, scope: Construct, id: str, sys_env: str, _aws_env: aws_cdk.Environment) -> None:
        super().__init__(scope, id)

        self.sys_env = sys_env  # dev, stg, prd, ops, gitops
        self._aws_env: aws_cdk.Environment = _aws_env  # region, account
        self.env_config = self.node.try_get_context(key=sys_env)  # from cdk.json
        # pass

        # # todo: 削除すること
        # if not self.env_config:
        #     if 'dev' in sys_env:
        #         self.env_config = {
        #             "env": {
        #                 "name": "dev"
        #             },
        #             "eks": {
        #                 "name": "app_eks",
        #                 "instance_type": "t3.small",
        #                 "addon_enable_cwmetrics": True,
        #                 "addon_enable_cwlogs": True,
        #                 "addon_enable_awslbclt": True,
        #                 "addon_enable_extdns": True
        #
        #             },
        #             "vpc": {
        #                 "name": "gitops_pipeline"
        #             },
        #             "flask_backend": {
        #                 "eks_cluster": "app_eks",
        #                 "namespace": "flask_backend",
        #                 "service_account": "flask-backend",
        #                 "dynamodb_table": "messages",
        #                 "dynamodb_partition": "uuid"
        #             }
        #         }
        #     # sys_env: gitops
        #     if 'gitops' in sys_env:
        #         self.env_config = {
        #             "env": {
        #               "name": "gitops"
        #             },
        #             "eks": {
        #               "name": "gitops_eks",
        #               "instance_type": "t3.medium",
        #               "addon_enable_cwmetrics": True,
        #               "addon_enable_cwlogs": True,
        #               "addon_enable_awslbclt": True,
        #               "addon_enable_extdns": True,
        #               "service_argocd": True,
        #               "service_argocd_domain": "yamazon.tk",
        #               "service_argocd_subdomain": "argocd.yamazon.tk",
        #               "service_argocd_cert_arn": "arn:aws:acm:ap-northeast-1:338456725408:certificate/124163b3-7ec8-4cf7-af6e-f05d8bc6ce8f",
        #               "service_argocd_secret_name": "ArgocdServerAdminPassword"
        #             },
        #             "vpc": {
        #               "name": "gitops_pipeline"
        #             }
        #         }

    @property
    def aws_env(self):
        return ConfigAwsEnv(self._aws_env)

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
    def flask_backend(self):
        if not self.env_config.get('flask_backend'):
            return None
        return ConfigFlaskBackend(self.env_config['flask_backend'])
