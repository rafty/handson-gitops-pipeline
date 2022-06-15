import aws_cdk
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_iam
from aws_cdk import Tags
import boto3
from util.configure.config import Config
from _constructs.eks_addon_awslbctl import AwsLoadBalancerController
from _constructs.eks_addon_extdns import  ExternalDnsController
from _constructs.eks_addon_cwmetrics import CloudWatchContainerInsightsMetrics
from _constructs.eks_addon_cwlogs import CloudWatchContainerInsightsLogs
from _constructs.eks_service_argocd import ArgoCd
# from _constructs.namespase_and_service_account.ns_and_sa import NamespaceAndServiceAccount


class EksCluster(Construct):
    # --------------------------------------------------------------
    # EKS Cluster
    # --------------------------------------------------------------
    def __init__(self, scope: Construct, id: str, config: Config) -> None:
        super().__init__(scope, id)

        self.config: Config = config
        self.cluster: aws_eks.Cluster = None

    def provisioning(self):
        vpc = aws_ec2.Vpc.from_lookup(self, 'VPC1', vpc_name=self.config.vpc.name)
        # 注意: from_lookup()で参照したvpcのsubnetにtagが付けられなかった。
        # VPC作成CDKプロジェクトでTagを設定する。
        # self.tag_subnet_for_eks_cluster(vpc)

        _owner_role = aws_iam.Role(
            scope=self,
            id='EksClusterOwnerRole',
            role_name=f'{self.config.env.name}EksClusterOwnerRole',
            assumed_by=aws_iam.AccountRootPrincipal())

        self.cluster = aws_eks.Cluster(
            self,
            'EksCluster',
            cluster_name=self.config.eks.name,
            version=aws_eks.KubernetesVersion.V1_21,
            default_capacity_type=aws_eks.DefaultCapacityType.NODEGROUP,
            default_capacity=1,
            default_capacity_instance=aws_ec2.InstanceType(self.config.eks.instance_type),
            vpc=vpc,
            masters_role=_owner_role)

        # CI/CDでClusterを作成する際、IAM Userでkubectlを実行する際に追加する。
        # kubectl commandを実行できるIAM Userを追加
        # self.cluster.aws_auth.add_user_mapping(
        #         user=aws_iam.User.from_user_name(
        #                 self, 'K8SUser-yagitatakashi', 'yagitatakashi'),
        #         groups=['system:masters']
        # )

        self.cfn_outputs_eks_cluster_attributes()
        self.deploy_addons()

    def cfn_outputs_eks_cluster_attributes(self):
        _env = self.config.env.name  # dev, gitops
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputClusterName',
            value=self.cluster.cluster_name,
            description="Name of EKS Cluster",
            export_name=f'EksClusterName-{_env}'
        )
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputKubectlRoleArn',
            value=self.cluster.kubectl_role.role_arn,
            description="Kubectl Role Arn of EKS Cluster",
            export_name=f'EksClusterKubectlRoleArn-{_env}'
        )
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputKubectlSecurityGroupId',
            value=self.cluster.kubectl_security_group.security_group_id,
            description="Kubectl Security Group Id of EKS Cluster",
            export_name=f'EksClusterKubectlSecurityGroupId-{_env}'
        )
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputOidcProviderArn',
            value=self.cluster.open_id_connect_provider.open_id_connect_provider_arn,
            description="OIDC Provider ARN of EKS Cluster",
            export_name=f'EksClusterOidcProviderArn-{_env}'
        )

    def deploy_addons(self):
        # --------------------------------------------------------------------
        # EKS Add On
        #   - AWS Load Balancer Controller
        #   - External DNS
        #   - CloudWatch Container Insight Metrics
        #   - CloudWatch Container Insight Logs
        # --------------------------------------------------------------------

        dependency = None

        if self.config.eks.addon_enable_awslbclt:
            vpc = aws_ec2.Vpc.from_lookup(self, 'VPC2', vpc_name=self.config.vpc.name)

            alb_ctl = AwsLoadBalancerController(
                self,
                'AwsLbController',
                region=self.config.aws_env.region,
                cluster=self.cluster,
                vpc_id=vpc.vpc_id)
            dependency = alb_ctl.deploy(dependency)

        if self.config.eks.addon_enable_extdns:
            ext_dns = ExternalDnsController(
                self,
                'ExternalDNS',
                region=self.config.aws_env.region,
                cluster=self.cluster)
            dependency = ext_dns.deploy(dependency)

        if self.config.eks.addon_enable_cwmetrics:
            insight_metrics = CloudWatchContainerInsightsMetrics(
                self,
                'CloudWatchInsightsMetrics',
                region=self.config.aws_env.region,
                cluster=self.cluster)
            dependency = insight_metrics.deploy(dependency)

        if self.config.eks.addon_enable_cwlogs:
            insight_logs = CloudWatchContainerInsightsLogs(
                self,
                'CloudWatchInsightLogs',
                region=self.config.aws_env.region,
                cluster=self.cluster)
            dependency = insight_logs.deploy(dependency)

        if self.config.eks.service_argocd:
            argocd = ArgoCd(
                self,
                'ArgoCd',
                region=self.config.aws_env.region,
                cluster=self.cluster,
                config=self.config
            )
            dependency = argocd.deploy(dependency)

    # def add_ns_and_sa(self):
    #
    #     print(f'--------Add NS and SA------{self.config.env.name}-----------------')
    #     # Todo: とりあえず if文を変える
    #     if self.config.flask_backend:
    #         ns_sa = NamespaceAndServiceAccount(
    #             self,
    #             'NamespaceAndServiceAccount',
    #             region=self.config.aws_env.region,
    #             cluster=self.cluster,
    #             config=self.config
    #         )
    #         ns_sa.flask_backend_ns_sa()



    # def tag_subnet_for_eks_cluster(self, vpc):
    #     # 注意: from_lookup()で参照したvpcのsubnetにtagが付けられなかった。
    #     # VPCに複数のEKS Clusterがある場合、Tag:"kubernetes.io/cluster/cluster-name": "shared"が必要
    #     # PrivateSubnetにはTag "kubernetes.io/role/internal-elb": '1'
    #     # PublicSubnetには"kubernetes.io/role/elb": '1'
    #     # https://docs.aws.amazon.com/ja_jp/eks/latest/userguide/network_reqs.html
    #     # https://docs.aws.amazon.com/ja_jp/eks/latest/userguide/alb-ingress.html
    #
    #     print('-----------subnet tagging-----------------------')
    #     print(f'eks cluster name: {self.config.eks.name}')
    #
    #     self.tag_all_subnets(vpc.public_subnets, 'kubernetes.io/role/elb', '1')
    #     self.tag_all_subnets(vpc.public_subnets, f'kubernetes.io/cluster/{self.config.eks.name}', 'shared')
    #     self.tag_all_subnets(vpc.private_subnets, 'kubernetes.io/role/internal-elb', '1')
    #     self.tag_all_subnets(vpc.private_subnets, f'kubernetes.io/cluster/{self.config.eks.name}', 'shared')
    #
    # @staticmethod
    # def tag_all_subnets(subnets, tag_name, tag_value):
    #     for subnet in subnets:
    #         Tags.of(subnet).add(tag_name, tag_value)




