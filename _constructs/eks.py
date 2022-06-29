import aws_cdk
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_iam
from util.configure.config import Config
from _constructs.eks_addon_awslbctl import AwsLoadBalancerController
from _constructs.eks_addon_extdns import  ExternalDnsController
from _constructs.eks_addon_cwmetrics import CloudWatchContainerInsightsMetrics
from _constructs.eks_addon_cwlogs import CloudWatchContainerInsightsLogs
from _constructs.eks_addon_argocd import ArgoCd


class EksCluster(Construct):

    def __init__(self, scope: Construct, id: str, config: Config) -> None:
        super().__init__(scope, id)

        self.config: Config = config
        self.cluster: aws_eks.Cluster = None
        self.vpc = self.get_vpc_cross_stack()
        self.vpc_id = self.get_vpc_id_cross_stack()

    def provisioning(self):

        _owner_role = aws_iam.Role(
            scope=self,
            id='EksClusterOwnerRole',
            role_name=f'{self.config.env.name}EksClusterOwnerRole',
            assumed_by=aws_iam.AccountRootPrincipal())

        self.cluster = aws_eks.Cluster(
            self,
            'EksCluster',
            cluster_name=self.config.eks.cluster_name,
            version=aws_eks.KubernetesVersion.V1_21,
            default_capacity_type=aws_eks.DefaultCapacityType.NODEGROUP,
            default_capacity=1,
            default_capacity_instance=aws_ec2.InstanceType(self.config.eks.instance_type),
            vpc=self.vpc,
            masters_role=_owner_role)

        # CI/CDでClusterを作成する際、IAM Userでkubectlを実行する際に追加する。
        # kubectl commandを実行できるIAM Userを追加
        # self.cluster.aws_auth.add_user_mapping(
        #         user=aws_iam.User.from_user_name(
        #                 self, 'K8SUser-yagitatakashi', 'yagitatakashi'),
        #         groups=['system:masters']
        # )

        self.cluster_outputs_for_cross_stack()
        self.deploy_addons()

    def deploy_addons(self):
        # --------------------------------------------------------------------
        # EKS Add On
        #   - AWS Load Balancer Controller
        #   - External DNS
        #   - CloudWatch Container Insight Metrics
        #   - CloudWatch Container Insight Logs
        # --------------------------------------------------------------------

        dependency = None

        if self.config.eks.addon_awslbclt_enable:
            alb_ctl = AwsLoadBalancerController(
                self,
                'AwsLbController',
                region=self.config.aws_env.region,
                cluster=self.cluster,
                vpc_id=self.vpc.vpc_id)  # Todo: vpc_idが取れてるか確認すること
            dependency = alb_ctl.deploy(dependency)

        if self.config.eks.addon_extdns_enable:
            ext_dns = ExternalDnsController(
                self,
                'ExternalDNS',
                region=self.config.aws_env.region,
                cluster=self.cluster)
            dependency = ext_dns.deploy(dependency)

        if self.config.eks.addon_cwmetrics_enable:
            insight_metrics = CloudWatchContainerInsightsMetrics(
                self,
                'CloudWatchInsightsMetrics',
                region=self.config.aws_env.region,
                cluster=self.cluster)
            dependency = insight_metrics.deploy(dependency)

        if self.config.eks.addon_cwlogs_enable:
            insight_logs = CloudWatchContainerInsightsLogs(
                self,
                'CloudWatchInsightLogs',
                region=self.config.aws_env.region,
                cluster=self.cluster)
            dependency = insight_logs.deploy(dependency)

        if self.config.eks.addon_argocd_enable:
            argocd = ArgoCd(
                self,
                'ArgoCd',
                region=self.config.aws_env.region,
                cluster=self.cluster,
                config=self.config
            )
            dependency = argocd.deploy(dependency)

    def get_existing_vpc(self):
        vpc = aws_ec2.Vpc.from_lookup(self, 'VPC1', vpc_name=self.config.vpc.name)
        return vpc

    def get_vpc_cross_stack(self):
        # Todo: from_vpc_attributesを使用する際、３つのAZがあることを前提とする
        vpc = aws_ec2.Vpc.from_vpc_attributes(
            self,
            'VpcId',
            vpc_id=aws_cdk.Fn.import_value(f'VpcId-{self.config.vpc.name}'),
            availability_zones=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'AZs-{self.config.vpc.name}'),
                assumed_length=3
            ),
            public_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PublicSubnets-{self.config.vpc.name}'),
                assumed_length=3
            ),
            private_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PrivateSubnets-{self.config.vpc.name}'),
                assumed_length=3
            )
        )
        return vpc

    # Todo これはうまくいった！！
    # def get_vpc_cross_stack(self):
    #     # VPC Cross Stack 参照 - from_vpc_attributes()
    #     vpc_id: str = aws_cdk.Fn.import_value(f'VpcId-{self.config.vpc.name}')  # VpcId-app-dev
    #     availability_zones_string: str = aws_cdk.Fn.import_value(f'AZs-{self.config.vpc.name}')
    #     public_subnets_string: str = aws_cdk.Fn.import_value(
    #         f'PublicSubnets-{self.config.vpc.name}')
    #     private_subnets_string: str = aws_cdk.Fn.import_value(
    #         f'PrivateSubnets-{self.config.vpc.name}')
    #
    #     # Todo: from_vpc_attributesを使用する際、３つのAZがあることを前提とする
    #     vpc = aws_ec2.Vpc.from_vpc_attributes(
    #         self,
    #         'VpcId',
    #         vpc_id=vpc_id,
    #         availability_zones=aws_cdk.Fn.split(',', availability_zones_string, 3),
    #         public_subnet_ids=aws_cdk.Fn.split(',', public_subnets_string, 3),
    #         private_subnet_ids=aws_cdk.Fn.split(',', private_subnets_string, 3)
    #     )
    #     return vpc

    def get_vpc_id_cross_stack(self):
        vpc_id: str = aws_cdk.Fn.import_value(f'VpcId-{self.config.vpc.name}')  # VpcId-app-dev
        return vpc_id

    def cluster_outputs_for_cross_stack(self):
        _env = self.config.env.name  # dev-1, prd-1
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
