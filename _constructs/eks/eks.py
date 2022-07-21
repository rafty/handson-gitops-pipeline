import aws_cdk
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_iam
from _constructs.eks.eks_addon_awslbctl import AwsLoadBalancerController
from _constructs.eks.eks_addon_extdns import ExternalDnsController
from _constructs.eks.eks_addon_cwmetrics import CloudWatchContainerInsightsMetrics
from _constructs.eks.eks_addon_cwlogs import CloudWatchContainerInsightsLogs
from _constructs.eks.eks_addon_argocd import ArgoCd


class EksCluster(Construct):

    def __init__(self,
                 scope: Construct,
                 id: str,
                 vpc_config: dict,
                 cluster_config: dict,
                 aws_env: dict) -> None:
        super().__init__(scope, id)

        self.vpc_conf = vpc_config
        self.cluster_conf = cluster_config
        self.aws_env = aws_env

        self.cluster: aws_eks.Cluster = None
        self.vpc = self.get_vpc_cross_stack()
        self.vpc_id = self.get_vpc_id_cross_stack()

    def provisioning(self):

        owner_role = aws_iam.Role(
            scope=self,
            id='EksClusterOwnerRole',
            role_name=f'EksClusterOwnerRole-{self.cluster_conf["name"]}',  # EksClusterOwnerRole-dev-1
            assumed_by=aws_iam.AccountRootPrincipal())

        self.cluster = aws_eks.Cluster(
            self,
            'EksCluster',
            cluster_name=self.cluster_conf['name'],
            version=aws_eks.KubernetesVersion.of(self.cluster_conf['version']),  # 1.21, 1.22
            default_capacity_type=aws_eks.DefaultCapacityType.NODEGROUP,
            default_capacity=1,
            default_capacity_instance=aws_ec2.InstanceType(self.cluster_conf['instance_type']),
            vpc=self.vpc,
            masters_role=owner_role)

        # CI/CDでClusterを作成する際、IAM Userでkubectlを実行する際に追加する。
        # kubectl commandを実行できるIAM Userを追加
        # self.cluster.aws_auth.add_user_mapping(
        #         user=aws_iam.User.from_user_name(
        #                 self, 'K8SUser-yagitatakashi', 'yagitatakashi'),
        #         groups=['system:masters']
        # )

        self.cluster_outputs()
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

        if self.cluster_conf['addon_awslbclt_enable']:
            alb_ctl = AwsLoadBalancerController(
                self,
                'AwsLbController',
                region=self.aws_env['region'],
                cluster=self.cluster,
                vpc_id=self.vpc_id
            )
            dependency = alb_ctl.deploy(dependency)

        if self.cluster_conf['addon_extdns_enable']:
            ext_dns = ExternalDnsController(
                self,
                'ExternalDNS',
                region=self.aws_env['region'],
                cluster=self.cluster)
            dependency = ext_dns.deploy(dependency)

        if self.cluster_conf['addon_cwmetrics_enable']:
            insight_metrics = CloudWatchContainerInsightsMetrics(
                self,
                'CloudWatchInsightsMetrics',
                region=self.aws_env['region'],
                cluster=self.cluster)
            dependency = insight_metrics.deploy(dependency)

        if self.cluster_conf['addon_cwlogs_enable']:
            insight_logs = CloudWatchContainerInsightsLogs(
                self,
                'CloudWatchInsightLogs',
                region=self.aws_env['region'],
                cluster=self.cluster)
            dependency = insight_logs.deploy(dependency)

        # Todo: ↓ comment out & cdk deploy before deleting stack (cdk destroy)
        if self.cluster_conf['addon_argocd_enable']:
            argocd = ArgoCd(
                self,
                'ArgoCd',
                cluster=self.cluster,
                cluster_config=self.cluster_conf,
            )
            dependency = argocd.deploy(dependency)
        # Todo: ↑ comment out & cdk deploy before deleting stack (cdk destroy)

    def get_vpc_cross_stack(self):
        """(attention)
            from_vpc_attributesを使用する際、３つのAZがあることを前提とする。
            Cfn Templateを作成する際、AZの数が決定されてなければならない。"""

        vpc = aws_ec2.Vpc.from_vpc_attributes(
            self,
            'VpcId',
            vpc_id=aws_cdk.Fn.import_value(f'VpcId-{self.vpc_conf["name"]}'),
            availability_zones=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'AZs-{self.vpc_conf["name"]}'),
                assumed_length=3
            ),
            public_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PublicSubnets-{self.vpc_conf["name"]}'),
                assumed_length=3
            ),
            private_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PrivateSubnets-{self.vpc_conf["name"]}'),
                assumed_length=3
            )
        )
        return vpc

    def get_vpc_id_cross_stack(self):
        vpc_id: str = aws_cdk.Fn.import_value(f'VpcId-{self.vpc_conf["name"]}')  # VpcId-dev
        return vpc_id

    def cluster_outputs(self):

        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputClusterName',
            value=self.cluster_conf['name'],  # dev-1, dev-2, prd-1, prd-2
            description="Name of EKS Cluster",
            export_name=f'EksClusterName-{self.cluster_conf["name"]}'
            # EksClusterName-dev-1, EksClusterName-dev-2,...
        )
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputKubectlRoleArn',
            value=self.cluster.kubectl_role.role_arn,
            description="Kubectl Role Arn of EKS Cluster",
            export_name=f'EksClusterKubectlRoleArn-{self.cluster_conf["name"]}'
            # EksClusterKubectlRoleArn-dev-1, EksClusterKubectlRoleArn-dev-2,...
        )
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputKubectlSecurityGroupId',
            value=self.cluster.kubectl_security_group.security_group_id,
            description="Kubectl Security Group Id of EKS Cluster",
            export_name=f'EksClusterKubectlSecurityGroupId-{self.cluster_conf["name"]}'
            # EksClusterKubectlSecurityGroupId-dev-1, EksClusterKubectlSecurityGroupId-dev-2,...
        )
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputOidcProviderArn',
            value=self.cluster.open_id_connect_provider.open_id_connect_provider_arn,
            description="OIDC Provider ARN of EKS Cluster",
            export_name=f'EksClusterOidcProviderArn-{self.cluster_conf["name"]}'
            # EksClusterOidcProviderArn-dev-1, EksClusterOidcProviderArn-dev-2,...
        )
