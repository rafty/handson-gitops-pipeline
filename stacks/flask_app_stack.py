import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_iam


class FlaskAppStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            vpc_config: dict,
            cluster_config: dict,
            flask_config: dict,
            # sys_env: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc_conf = vpc_config
        self.cluster_conf = cluster_config
        self.flask_conf = flask_config

        self.vpc = self.get_vpc_cross_stack()
        self.cluster = self.get_cluster_cross_stack()

        dependency = self.create_ns_and_sa_for_dynamodb()
        dependency = self.create_argocd_application(dependency)

        # AWS LoadBalancer Controller - TargetGroupBinding
        # ALB TargetGroupのTargetにk8s serviceを登録する
        self.application_target_group_binding(dependency)

    def get_vpc_cross_stack(self):
        # from_vpc_attributesを使用する際、３つのAZがあることを前提とする
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

    def get_cluster_cross_stack(self) -> aws_eks.Cluster:
        # Cross Stack Reference - eks cluster attributes

        cluster_name = aws_cdk.Fn.import_value(
            f'EksClusterName-{self.cluster_conf["name"]}')
        # ClusterName-dev-1, ClusterName-dev-2,

        kubectl_role_arn = aws_cdk.Fn.import_value(
            f'EksClusterKubectlRoleArn-{self.cluster_conf["name"]}')
        # KubectlRoleArn-dev-1, KubectlRoleArn-dev-2

        kubectl_security_group_id = aws_cdk.Fn.import_value(
            f'EksClusterKubectlSecurityGroupId-{self.cluster_conf["name"]}')
        # KubectlSecurityGroupId-dev-1, KubectlSecurityGroupId-dev-2

        oidc_provider_arn = aws_cdk.Fn.import_value(
            f'EksClusterOidcProviderArn-{self.cluster_conf["name"]}')
        # OidcProviderArn-dev-1, OidcProviderArn-dev-2

        oidc_provider = aws_eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self,
            'OidcProvider',
            open_id_connect_provider_arn=oidc_provider_arn)

        cluster = aws_eks.Cluster.from_cluster_attributes(
            self,
            'GetCluster',
            cluster_name=cluster_name,
            open_id_connect_provider=oidc_provider,
            kubectl_role_arn=kubectl_role_arn,
            kubectl_security_group_id=kubectl_security_group_id,
            vpc=self.vpc
        )
        return cluster

    def create_ns_and_sa_for_dynamodb(self):
        # flaskがDynamoDBにアクセスできるServiceAccountを追加
        # Service Accountに必要なNamespaceを登録
        # namespace, service_accountはmanifestと一致すること

        # Namespace of flask
        namespace_manifest = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': self.flask_conf['namespace'],
                'labels': {
                    'name': self.flask_conf['namespace']
                }
            }
        }
        namespace = self.cluster.add_manifest('FlaskAppNamespace', namespace_manifest)

        # Service Account for flask
        flask_app_sa = self.cluster.add_service_account(
            'FlaskAppSA',  # この名前がIAM Role名になる
            name=self.flask_conf['service_account'],
            namespace=self.flask_conf['namespace']
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
                "Resource": ["arn:aws:dynamodb:*:*:table/messages-*"]
            }
        ]

        for statement in dynamodb_full_access_policy_statements:
            flask_app_sa.add_to_principal_policy(
                aws_iam.PolicyStatement.from_json(statement)
            )

        return flask_app_sa  # dependency

    def create_argocd_application(self, dependency):
        # Argo CD Application

        argocd_app_manifest = self.argocd_application_manifest()
        argocd_app = self.cluster.add_manifest(
                  argocd_app_manifest['metadata']['name'],
                  argocd_app_manifest)

        argocd_app.node.add_dependency(dependency)

        return argocd_app  # dependency

    def argocd_application_manifest(self):
        argocd_namespace = 'argocd'
        application_name = self.flask_conf['name']  # flask
        application_namespace = self.flask_conf['namespace']  # flask
        repo = self.flask_conf['repo']
        repo_path = self.flask_conf['repo_path']  # prd/

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
                    'server': 'https://kubernetes.default.svc',
                    # ArgoCDが動作するClusterにAppをDeployする際のurl
                    'namespace': application_namespace
                },
                'syncPolicy': {
                    'automated': {}
                }
            }
        }
        return flask_app_manifest

    def application_target_group_binding(self, dependency):
        # AWS Load Balancer Controller - TargetGroupBinding
        # ALB TargetGroupのTargetにk8s serviceを登録する
        # see more information:
        # https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/targetgroupbinding/targetgroupbinding/
        # targetGroupARN: ALBのTargetGroup, 環境毎にBule, Green用に２つ作成
        # - ALB-TargetGroupArn-dev-1
        # - ALB-TargetGroupArn-dev-2
        # - ALB-TargetGroupArn-prd-1
        # - ALB-TargetGroupArn-prd-2

        service_name = self.flask_conf['name']
        namespace = self.flask_conf['namespace']

        tgb_manifest = {
            'apiVersion': 'elbv2.k8s.aws/v1beta1',
            'kind': 'TargetGroupBinding',
            'metadata': {
                'name': service_name,
                'namespace': namespace
            },
            'spec': {
                'serviceRef': {
                    'name': service_name,  # route traffic to k8s service (clusterIP=None)
                    'port': 80
                },
                'targetGroupARN': aws_cdk.Fn.import_value(
                    f'ALB-TargetGroupArn-{self.flask_conf["eks_cluster"]}'),
                # ALB-TargetGroupArn-dev-1, ALB-TargetGroupArn-dev-2, ...
                'networking': {
                    'ingress': [
                        {
                            'from': [
                                {
                                    'securityGroup': {
                                        'groupID': aws_cdk.Fn.import_value(
                                            f'AlbSecurityGroupId-{self.flask_conf["env"]}')  # <ALB_SG_ID>
                                    }
                                }
                            ],
                            'ports': [
                                {
                                    'protocol': 'TCP',
                                    # 'port': 80  # cooment out: Allow all TCP traffic from ALB SG
                                }
                            ]
                        }
                    ]
                }
            }
        }

        flask_tgb = self.cluster.add_manifest('flask-TargetGroupBinding', tgb_manifest)
        flask_tgb.node.add_dependency(dependency)
