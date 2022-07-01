import yaml
import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_dynamodb
from aws_cdk import aws_iam
from util.configure.config import Config


class FlaskAppStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            sys_env: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = Config(self, 'Config', sys_env=sys_env, _aws_env=kwargs.get('env'))
        self.vpc = self.get_vpc_cross_stack()
        self.cluster = self.get_cluster_cross_stack()

        self.dynamodb = self.create_dynamodb()
        self.argocd_application()

    def get_existing_vpc(self) -> aws_ec2.Vpc:
        # Existing VPC取得する
        return aws_ec2.Vpc.from_lookup(self, 'Vpc', vpc_name=self.config.vpc.name)

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

    # def get_vpc_cross_stack(self):
    #     # VPC Cross Stack 参照 - from_vpc_attributes()
    #     vpc_id: str = aws_cdk.Fn.import_value(f'VpcId-{self.config.vpc.name}')  # VpcId-app-dev
    #     availability_zones_string: str = aws_cdk.Fn.import_value(f'AZs-{self.config.vpc.name}')
    #     public_subnets_string: str = aws_cdk.Fn.import_value(f'PublicSubnets-{self.config.vpc.name}')
    #     private_subnets_string: str = aws_cdk.Fn.import_value(f'PrivateSubnets-{self.config.vpc.name}')
    #
    #     # from_vpc_attributesを使用する際、３つのAZがあることを前提とする
    #     vpc = aws_ec2.Vpc.from_vpc_attributes(
    #         self,
    #         'VpcId',
    #         vpc_id=vpc_id,
    #         availability_zones=aws_cdk.Fn.split(',', availability_zones_string, 3),
    #         public_subnet_ids=aws_cdk.Fn.split(',', public_subnets_string, 3),
    #         private_subnet_ids=aws_cdk.Fn.split(',', private_subnets_string, 3)
    #     )
    #     return vpc

    def get_cluster_cross_stack(self) -> aws_eks.Cluster:
        pass
        _env = self.config.env.name  # dev-1, prd-1
        _vpc = self.vpc

        # eks cluster attributes
        _cluster_name = aws_cdk.Fn.import_value(f'EksClusterName-{_env}')  # ClusterName-dev
        _kubectl_role_arn = aws_cdk.Fn.import_value(f'EksClusterKubectlRoleArn-{_env}')  # KubectlRoleArn-dev
        _kubectl_security_group_id = aws_cdk.Fn.import_value(f'EksClusterKubectlSecurityGroupId-{_env}')  # KubectlSecurityGroupId-dev
        _oidc_provider_arn = aws_cdk.Fn.import_value(f'EksClusterOidcProviderArn-{_env}')  # OidcProviderArn-dev
        _oidc_provider = aws_eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self,
            'OidcProvider',
            open_id_connect_provider_arn=_oidc_provider_arn)

        cluster = aws_eks.Cluster.from_cluster_attributes(
            self,
            'GetCluster',
            cluster_name=_cluster_name,
            open_id_connect_provider=_oidc_provider,
            kubectl_role_arn=_kubectl_role_arn,
            kubectl_security_group_id=_kubectl_security_group_id,
            vpc=_vpc
        )
        return cluster

    def create_dynamodb(self) -> aws_dynamodb.Table:
        # --------------------------------------------------------------
        #
        # DynamoDB
        #
        # --------------------------------------------------------------

        self.namespace_and_service_account()

        _dynamodb = aws_dynamodb.Table(
            self,
            id='DynamoDbTable',
            table_name=self.config.flask_app.dynamodb_table,
            partition_key=aws_dynamodb.Attribute(
                name=self.config.flask_app.dynamodb_partition,
                type=aws_dynamodb.AttributeType.STRING),
            read_capacity=1,
            write_capacity=1,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY
        )
        return _dynamodb

    def namespace_and_service_account(self):
        # flask-appがDynamoDBにアクセスできるServiceAccountを追加
        # Service Accountに必要なNamespaceを登録
        # namespace, service_accountはmanifestと一致すること

        # Namespace of flask-app
        namespace_manifest = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': self.config.flask_app.namespace,
                'labels': {
                    'name': self.config.flask_app.namespace
                }
            }
        }
        namespace = self.cluster.add_manifest('FlaskAppNamespace',
                                              namespace_manifest)

        # Service Account for flask-app
        flask_app_sa = self.cluster.add_service_account(
            'FlaskAppSA',  # この名前がIAM Role名になる
            name=self.config.flask_app.service_account,
            namespace=self.config.flask_app.namespace
        )
        flask_app_sa.node.add_dependency(namespace)

        dynamodb_full_access_policy_statements = [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:List*",
                    "dynamodb:DescribeReservedCapacity*",
                    "dynamodb:DescribeLimits",
                    "dynamodb:DescribeTimeToLive"
                ],
                "Resource": ["*"]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:BatchGet*",
                    "dynamodb:DescribeStream",
                    "dynamodb:DescribeTable",
                    "dynamodb:Get*",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWrite*",
                    "dynamodb:CreateTable",
                    "dynamodb:Delete*",
                    "dynamodb:Update*",
                    "dynamodb:PutItem"
                ],
                # "Resource": [self.dynamodb.table_arn]
                # "Resource": ["arn:aws:dynamodb:*:*:table/messages"]
                "Resource": [
                    f"arn:aws:dynamodb:*:*:table/{self.config.flask_app.dynamodb_table}"
                ]
            }
        ]

        for statement in dynamodb_full_access_policy_statements:
            flask_app_sa.add_to_principal_policy(
                aws_iam.PolicyStatement.from_json(statement)
            )

    def argocd_application(self):
        # Argo CD Applicationを作成する

        # with open('./argocd_app/argocd-app-dev.yaml', 'r') as f:
        #     _yaml_docs = list(yaml.load_all(f, Loader=yaml.FullLoader))
        # for manifest in _yaml_docs:
        #     self.cluster.add_manifest(manifest['metadata']['name'], manifest)

        argocd_app_manifest = self.argocd_application_manifest()
        self.cluster.add_manifest(
                  argocd_app_manifest['metadata']['name'],
                  argocd_app_manifest)

    def argocd_application_manifest(self):
        # 複数アプリケーション対応
        argocd_namespace = 'argocd'
        # application_name = 'flask-app'
        application_name = self.config.flask_app.namespace
        # application_namespace = 'flask-app'
        application_namespace = self.config.flask_app.namespace
        # repo = 'https://github.com/rafty/handson-eks_app_manifest.git'
        repo = self.config.flask_app.repo
        # repo_path = 'flask/prd/'
        repo_path = self.config.flask_app.repo_path

        flask_app_manifest = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'Application',
            'metadata': {
                'name': application_name,
                'namespace': argocd_namespace,
            },
            'spec': {
                'project': 'default',
                'source': {
                    'repoURL': repo,
                    'targetRevision': 'HEAD',
                    'path': repo_path
                },
                'destination': {
                    'server': 'https://kubernetes.default.svc',  #  ArgoCDが動作するClusterにAppをDeployする際のurl
                    'namespace': application_namespace
                },
                'syncPolicy': {
                    'automated': {}
                }
            }
        }

        return flask_app_manifest
