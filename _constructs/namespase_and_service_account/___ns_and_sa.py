from constructs import Construct
from aws_cdk import aws_iam
from aws_cdk import aws_eks
from util.configure.config import Config


class NamespaceAndServiceAccount(Construct):
    # ----------------------------------------------------------
    # アプリケーションが使用するNameSpace, ServiceAccountを作成する。
    # ----------------------------------------------------------

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        # self.check_parameter(kwargs)
        self.region = kwargs.get('region')
        self.vpc_id = kwargs.get('vpc_id')
        self.config: Config = kwargs.get('config')
        self.cluster: aws_eks.Cluster = kwargs.get('cluster')

    def flask_backend_ns_sa(self):
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

        backend_service_account = self.cluster.add_service_account(
            # 'IamRoleForServiceAccount',  # この名前がIAM Role名に付加される
            'FlaskBackendIamRoleForServiceAccount',  # この名前がIAM Role名に付加される
            name=self.config.flask_backend.service_account,  # flask_backend
            namespace=self.config.flask_backend.namespace  # flask-backend
        )
        backend_service_account.node.add_dependency(namespace)

        dynamodb_messages_full_access_policy_statements = [
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

        for statement in dynamodb_messages_full_access_policy_statements:
            backend_service_account.add_to_principal_policy(
                aws_iam.PolicyStatement.from_json(statement)
            )
