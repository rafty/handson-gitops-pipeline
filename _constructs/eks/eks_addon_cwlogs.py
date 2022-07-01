from constructs import Construct
from aws_cdk import aws_iam
from aws_cdk import aws_eks


class CloudWatchContainerInsightsLogs(Construct):
    # ----------------------------------------------------------
    # Cloudwatch Container Insights - Logs / fluentbit
    # ----------------------------------------------------------
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        self.check_parameter(kwargs)
        self.region = kwargs.get('region')
        self.cluster: aws_eks.Cluster = kwargs.get('cluster')

    def deploy(self, dependency: Construct) -> Construct:
        # --------------------------------------------------------------
        # Cloudwatch Logs - fluent bit
        #   Namespace
        #   Service Account
        #   Deployment
        #   Service
        # https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-logs-FluentBit.html
        # 1. namespace: amazon-cloudwatchを作成
        # 2. Service Account作成
        # --------------------------------------------------------------

        cloudwatch_namespace_name = 'amazon-cloudwatch'
        cloudwatch_namespace_manifest = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': cloudwatch_namespace_name,
                'labels': {
                    'name': cloudwatch_namespace_name
                }
            }
        }
        cloudwatch_namespace = self.cluster.add_manifest(
                  'CloudWatchNamespace', cloudwatch_namespace_manifest)
        if dependency is not None:
            cloudwatch_namespace.node.add_dependency(dependency)

        # Service Account for fluent bit
        fluentbit_service_account = self.cluster.add_service_account(
            'FluentbitServiceAccount',
            name='cloudwatch-sa',
            namespace=cloudwatch_namespace_name
        )
        fluentbit_service_account.node.add_dependency(cloudwatch_namespace)
        # FluentBitの場合は以下のPolicyを使う。kinesisなどを使う場合はPolicyは異なる
        fluentbit_service_account.role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                'CloudWatchAgentServerPolicy')
        )
        # logsの保持期間(logRetentionDays)の変更ポリシーを追加
        logs_retention_policy = {
            'Effect': 'Allow',
            'Action': [
                'logs:PutRetentionPolicy'
            ],
            'Resource': ["*"]
        }
        fluentbit_service_account.role.add_to_principal_policy(
            aws_iam.PolicyStatement.from_json(logs_retention_policy)
        )

        # aws-for-fluent-bit DaemonSetのデプロイ
        cloudwatch_helm_chart = self.cluster.add_helm_chart(
            'FluentBitHelmChart',
            namespace=cloudwatch_namespace_name,
            repository='https://aws.github.io/eks-charts',
            chart='aws-for-fluent-bit',
            release='aws-for-fluent-bit',
            version='0.1.16',
            values={
                'serviceAccount': {
                    'name': fluentbit_service_account.service_account_name,
                    'create': False
                },
                'cloudWatch': {
                    'enabled': True,
                    'match': "*",
                    'region': self.region,
                    'logGroupName': f'/aws/eks/fluentbit-cloudwatch/logs/{self.cluster.cluster_name}/application',
                    'logStreamPrefix': 'log-',
                    'logRetentionDays': 7,
                    'autoCreateGroup': True,
                },
                'kinesis': {'enabled': False},
                'elasticsearch': {'enabled': False},
                'firehose': {'enabled': False},
            }
        )
        cloudwatch_helm_chart.node.add_dependency(fluentbit_service_account)

        return cloudwatch_helm_chart

    @staticmethod
    def check_parameter(key):
        if type(key.get('region')) is not str:
            raise TypeError('Must be set region.')
        if key.get('region') == '':
            raise TypeError('Must be set region.')
        if type(key.get('cluster')) is not aws_eks.Cluster:
            raise TypeError('Must be set region.')
