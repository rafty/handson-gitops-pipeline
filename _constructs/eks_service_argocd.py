from passlib.context import CryptContext
from constructs import Construct
from aws_cdk import aws_eks
from util.configure.config import Config
import boto3


class ArgoCd(Construct):
    # ----------------------------------------------------------
    # Argo CD Helm Chart
    # https://artifacthub.io/packages/helm/argo/argo-cd
    # ----------------------------------------------------------
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        # platform parameter
        self.check_parameter(kwargs)
        self.region = kwargs.get('region')
        self.cluster: aws_eks.Cluster = kwargs.get('cluster')
        self.config: Config = kwargs.get('config')
        # Argo cd fixed value
        self.labels = {'app.kubernetes.io/name': 'argocd-server'}
        self.ingress_name = 'argocd'
        self.namespace = 'argocd'
        self.repository = 'https://argoproj.github.io/argo-helm'
        self.chart_name = 'argo-cd'
        self.chart_version = None  # '4.6.0' , None: latest
        self.release = 'argocd'  # deploy name: Ingressの指定があるので'argocd'に固定する。
        # Argo CD Ingress fixed value
        self.labels = {'app.kubernetes.io/name': 'argocd-server'}
        self.ingress_name = 'argocd'

    def deploy(self, dependency: Construct) -> Construct:

        # ----------------------------------------------------------------
        # Argo CD helm chart
        # ----------------------------------------------------------------
        _argocd_helm_chart = self.cluster.add_helm_chart(
            'ArgocdHelmChart',
            namespace=self.namespace,
            # repository=self.configure.get('argocd_repository'),
            repository=self.repository,
            chart=self.chart_name,  # 'argo-cd'
            release=self.release,  # Ingressの指定があるので'argocd'に固定する。
            # version=self.chart_version,  # No version parameter is latest.
            values={
                'configs': {
                    'secret': {
                        'argocdServerAdminPassword': self.get_argocd_admin_password()
                    }
                }
            }
        )
        if dependency is not None:
            _argocd_helm_chart.node.add_dependency(dependency)

        dependency = self.add_alb_ingress_to_argocd(_argocd_helm_chart)
        return dependency

    def get_argocd_admin_password(self):
        # ------------------------------------------------------
        # ASM Secret - argocdServerAdminPassword
        # ArgocdServerAdminPassword must be Bcrypt hashed password.
        # https://artifacthub.io/packages/helm/argo/argo-cd
        # ------------------------------------------------------
        _secret_name = self.config.eks.service_argocd_secret_name
        secret_string = self.get_asm_value_by_awssdk(_secret_name)
        try:
            pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
            bcrypt_hashed = pwd_context.hash(secret_string)
        except Exception as e:
            print(f'passlib exception: {e}')
            raise e
        return bcrypt_hashed

    @staticmethod
    def get_asm_value_by_awssdk(secret_name: str):
        # hash変換したものをConfigMapに登録しなければならないのでCfnのASM動的参照は使えない
        # AWS SDKで値を取得する必要がある
        client = boto3.client('secretsmanager')
        secret_value = client.get_secret_value(SecretId=secret_name)
        try:
            secret_string = secret_value['SecretString']
        except KeyError as e:
            raise KeyError('must be set ASM:ArgocdServerAdminPassword')
        return secret_string

    # ------------------------------------------------------------------
    #  Provisioning ALB
    #       by AWS Load Balancer Controller
    #       by External DNS
    #  Must be set annotations
    # ------------------------------------------------------------------
    def add_alb_ingress_to_argocd(self, dependency: Construct) -> Construct:
        # _cluster = self.cluster
        # _namespace = self.namespace
        # _cert_arn = self.config.eks.service_argocd_cert_arn
        # _sub_domain = self.config.eks.service_argocd_subdomain

        # print('#-----------Ingress---------------------------\n')
        # print(f'cluster: {self.cluster}')
        # print(f'ingress_name: {self.ingress_name}')
        # print(f'namespace: {self.namespace}')
        # print(f'labels: {self.labels}')
        # print(f'service_argocd_cert_arn: {self.config.eks.service_argocd_cert_arn}')
        # print(f'service_argocd_subdomain: {self.config.eks.service_argocd_subdomain}')

        ingress_argocd_server_manifest = {
            'apiVersion': 'networking.k8s.io/v1',
            'kind': 'Ingress',
            'metadata': {
                'name': self.ingress_name,
                'namespace': self.namespace,
                'labels': self.labels,
                'annotations': {
                    'kubernetes.io/ingress.class': 'alb',
                    'alb.ingress.kubernetes.io/scheme': 'internet-facing',
                    'alb.ingress.kubernetes.io/target-type': 'ip',
                    'alb.ingress.kubernetes.io/listen-ports': '[{"HTTPS":443}, {"HTTP":80}]',
                    'alb.ingress.kubernetes.io/healthcheck-path': '/healthz',
                    'alb.ingress.kubernetes.io/healthcheck-protocol': 'HTTPS',
                    'alb.ingress.kubernetes.io/backend-protocol': 'HTTPS',
                    'alb.ingress.kubernetes.io/actions.ssl-redirect': '{"Type": "redirect", "RedirectConfig": { "Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}',
                    'alb.ingress.kubernetes.io/certificate-arn': self.config.eks.service_argocd_cert_arn,
                    'external-dns.alpha.kubernetes.io/hostname': self.config.eks.service_argocd_subdomain,
                },
            },
            'spec': {
                'rules': [
                    {
                        'host': self.config.eks.service_argocd_subdomain,
                        'http': {
                            'paths': [
                                {
                                    'backend': {
                                        'service': {
                                            'name': 'argocd-server',
                                            'port': {
                                                'number': 80,
                                            }
                                        }
                                    },
                                    'path': '/*',
                                    'pathType': 'ImplementationSpecific',
                                },
                                {
                                    'backend': {
                                        'service': {
                                            'name': 'argocd-server',
                                            'port': {
                                                'number': 443,
                                            }
                                        }
                                    },
                                    'path': '/*',
                                    'pathType': 'ImplementationSpecific',
                                }
                            ]
                        }
                    }
                ]
            }
        }
        argocd_ingress = self.cluster.add_manifest('ArgocdIngress',
                                                   ingress_argocd_server_manifest)
        if dependency is not None:
            argocd_ingress.node.add_dependency(dependency)

        return argocd_ingress

    @staticmethod
    def check_parameter(key):
        if type(key.get('region')) is not str:
            raise TypeError('Must be set region.')
        if key.get('region') == '':
            raise TypeError('Must be set region.')
        if type(key.get('cluster')) is not aws_eks.Cluster:
            raise TypeError('Must be set region.')
