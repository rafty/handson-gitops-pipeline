import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_dynamodb
from aws_cdk import aws_iam
from util.configure.config import Config


class FlaskBackendAppStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            sys_env: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = Config(self, 'Config', sys_env=sys_env, _aws_env=kwargs.get('env'))
        self.vpc = self.get_existing_vpc()
        self.cluster = self.get_existing_cluster()
        self.add_namespace_and_service_account()
        self.dynamodb = self.create_dynamodb()

    def add_namespace_and_service_account(self):
        # flask-backendがDynamoDBにアクセスできるServiceAccountを追加
        # Service Accountに必要なNamespaceを登録
        # flask-frontendのnamespaceは作成せずargocdに作成してもらうこととする。

        # Namespace of flask-backend
        namespace_manifest = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': self.config.flask_backend.namespace,
                'labels': {
                    'name': self.config.flask_backend.namespace
                }
            }
        }
        namespace = self.cluster.add_manifest('FlaskBackendNamespace',
                                              namespace_manifest)

        # Service Account for flask-backend
        backend_sa = self.cluster.add_service_account(
            'FlaskBackendSA',  # この名前がIAM Role名に付加される
            name=self.config.flask_backend.service_account,  # flask_backend
            namespace=self.config.flask_backend.namespace  # flask-backend
        )
        backend_sa.node.add_dependency(namespace)

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
                "Resource": ["arn:aws:dynamodb:*:*:table/messages"]
            }
        ]

        for statement in dynamodb_full_access_policy_statements:
            backend_sa.add_to_principal_policy(
                aws_iam.PolicyStatement.from_json(statement)
            )

    def get_existing_vpc(self) -> aws_ec2.Vpc:
        return aws_ec2.Vpc.from_lookup(self, 'Vpc', vpc_name=self.config.vpc.name)

    def get_existing_cluster(self) -> aws_eks.Cluster:
        pass
        _env = self.config.env.name  # dev
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
        _dynamodb = aws_dynamodb.Table(
            self,
            id='DynamoDbTable',
            table_name=self.config.flask_backend.dynamodb_table,
            partition_key=aws_dynamodb.Attribute(
                name=self.config.flask_backend.dynamodb_partition,
                type=aws_dynamodb.AttributeType.STRING),
            read_capacity=1,
            write_capacity=1,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY  # 削除
        )
        return _dynamodb
