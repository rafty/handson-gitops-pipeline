from constructs import Construct
from aws_cdk import aws_iam
from aws_cdk import aws_eks


class ExternalDnsController(Construct):
    # ----------------------------------------------------------
    # ExternalDNS
    # ExternalDNSは TLS証明書持つALBのレコードをR53に登録する
    # ----------------------------------------------------------
    def __init__(self,
                 scope: Construct,
                 id: str,
                 region: str,
                 cluster: aws_eks.Cluster,
                 **kwargs) -> None:
        super().__init__(scope, id)

        self.region = region
        self.cluster: aws_eks.Cluster = cluster

    def deploy(self, dependency: Construct) -> Construct:
        # External DNS Controller sets A-Record in the Hosted Zone of Route 53.
        # how to use:
        #   Set DomainName in annotations of Ingress Manifest.
        #   ex.
        #       external-dns.alpha.kubernetes.io/hostname: DOMAIN_NAME
        # see more info
        #   ('https://aws.amazon.com/jp/premiumsupport/'
        #    'knowledge-center/eks-set-up-externaldns/')

        external_dns_service_account = self.cluster.add_service_account(
            'external-dns',
            name='external-dns',
            namespace='kube-system'
        )
        if dependency is not None:
            external_dns_service_account.node.add_dependency(dependency)

        external_dns_policy_statement_json_1 = {
            'Effect': 'Allow',
            'Action': [
                'route53:ChangeResourceRecordSets'
            ],
            'Resource': [
                'arn:aws:route53:::hostedzone/*'
            ]
        }

        external_dns_policy_statement_json_2 = {
            'Effect': 'Allow',
            'Action': [
                'route53:ListHostedZones',
                'route53:ListResourceRecordSets'
            ],
            'Resource': ["*"]
        }

        external_dns_service_account.add_to_principal_policy(
            aws_iam.PolicyStatement.from_json(
                external_dns_policy_statement_json_1)
        )
        external_dns_service_account.add_to_principal_policy(
            aws_iam.PolicyStatement.from_json(
                external_dns_policy_statement_json_2)
        )

        external_dns_chart = self.cluster.add_helm_chart(
            'external-dns"',
            chart='external-dns',
            version='1.7.1',  # change to '1.9.0'
            # version=None,  # latest
            release='externaldns',
            repository='https://kubernetes-sigs.github.io/external-dns/',
            namespace='kube-system',
            values={
                'serviceAccount': {
                    'name': external_dns_service_account.service_account_name,
                    'create': False,
                },
                # 'resources': {
                #     'requests': {
                #         'cpu': '0.25',
                #         'memory': '0.5Gi'
                #     }
                # }
            }

        )
        external_dns_chart.node.add_dependency(external_dns_service_account)

        return external_dns_chart
