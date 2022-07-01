import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from util.configure.config import Config
from _constructs.eks.eks import EksCluster


class EksClusterStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            sys_env: str,  # dev-1, dev-2, prd-1 ...
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.check_parameter(kwargs)
        # Stackの設定値をConfigに保存
        self.config = Config(self, 'Config', sys_env=sys_env, _aws_env=kwargs.get('env'))

        _eks_cluster = EksCluster(self, 'EksCluster', config=self.config)
        _eks_cluster.provisioning()

    @staticmethod
    def check_parameter(key):
        if type(key.get('env')) is not aws_cdk.Environment:
            raise TypeError('Set aws_cdk.Environment.')
