import json
import yaml
from constructs import Construct
from aws_cdk import aws_iam
from aws_cdk import aws_eks


class CloudWatchContainerInsightsMetrics(Construct):
    # ----------------------------------------------------------
    # Cloudwatch Container Insights - Metrics / CloudWatch Agent
    # ----------------------------------------------------------
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        self.check_parameter(kwargs)
        self.region: str = kwargs.get('region')
        self.cluster: aws_eks.Cluster = kwargs.get('cluster')

    def deploy(self, dependency: Construct) -> Construct:
        # CloudWatch Agent
        # namespace: amazon-cloudwatch -> kube-system
        # See more info 'https://docs.aws.amazon.com/AmazonCloudWatch/latest'
        #               'monitoring/Container-Insights-setup-metrics.html'

        # Create the Service Account
        cloudwatch_container_insight_sa: aws_iam.Role = \
            self.cluster.add_service_account(
                id='cloudwatch-agent',
                name='cloudwatch-agent',
                namespace='kube-system',
            )
        if dependency is not None:
            cloudwatch_container_insight_sa.node.add_dependency(dependency)

        cloudwatch_container_insight_sa.role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                'CloudWatchAgentServerPolicy')
        )

        # ----------------------------------------------------------
        # CloudWatch ConfigMap Setting
        # ----------------------------------------------------------
        cwagentconfig_json = {
            'agent': {
                'region': self.region
            },
            'logs': {
                'metrics_collected': {
                    'kubernetes': {
                        'cluster_name': self.cluster.cluster_name,
                        'metrics_collection_interval': 60
                    }
                },
                'force_flush_interval': 5,
                'endpoint_override': f'logs.{self.region}.amazonaws.com'
            },
            'metrics': {
                'metrics_collected': {
                    'statsd': {
                        'service_address': ':8125'
                    }
                }
            }
        }
        cw_agent_configmap = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'cwagentconfig',
                'namespace': 'kube-system'
            },
            'data': {
                'cwagentconfig.json': json.dumps(cwagentconfig_json)
            }
        }
        self.cluster.add_manifest(
            'CloudwatchContainerInsightConfigMap',
            cw_agent_configmap)

        # ----------------------------------------------------------
        # Apply multiple yaml documents. - cloudwatch-agent.yaml
        # ----------------------------------------------------------
        cloudwatch_manifest = None
        with open('./manifests/cloudwatch-agent.yaml', 'r') as f:
            _yaml_docs = list(yaml.load_all(f, Loader=yaml.FullLoader))
        for i, _yaml_doc in enumerate(_yaml_docs, 1):
            cloudwatch_manifest = self.cluster.add_manifest(f'CWAgent{i}', _yaml_doc)

        return cloudwatch_manifest

    @staticmethod
    def check_parameter(key):
        if type(key.get('region')) is not str:
            raise TypeError('Must be set region.')
        if key.get('region') == '':
            raise TypeError('Must be set region.')
        if type(key.get('cluster')) is not aws_eks.Cluster:
            raise TypeError('Must be set Cluster.')
