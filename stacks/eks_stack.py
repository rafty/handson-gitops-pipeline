from aws_cdk import Stack
from constructs import Construct
from _constructs.eks.eks import EksCluster


class EksClusterStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            vpc_config: dict,
            cluster_config: dict,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.aws_env = {'account': self.account, 'region': self.region}

        eks_cluster = EksCluster(
            self,
            'EksCluster',
            vpc_config=vpc_config,
            cluster_config=cluster_config,
            aws_env=self.aws_env
        )

        eks_cluster.provisioning()

