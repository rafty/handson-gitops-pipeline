"""Stack Configuration
Stackが参照する環境変数を定義する。
 - AWS Accountに環境毎にVPCを作成する構成
 - EKS Cluster Blue Green Deploymentによるe8s Upgrade

# --- CodePipeline Stack ---
codepipeline_stack_configuration = {}

# --- dev environment---
dev_env_configuration = {
        'vpc': {},                  # dev environment用VPC
        'flask-stateful': {},       # AppのStateful AWS Resource
        'cluster-1': {},            # BlueGreen switching用EKS Cluster
        'cluster-2': {},            # BlueGreen switching用EKS Cluster
        'flask-1': {},              # BlueGreen switching用App
        'flask-2': {},              # BlueGreen switching用App
}

# --- stg environment---
stg_env_configuration = {
        'vpc': {},                  # stg environment用VPC
        'flask-stateful': {},       # AppのStateful AWS Resource
        'cluster-1': {},            # BlueGreen switching用EKS Cluster
        'cluster-2': {},            # BlueGreen switching用EKS Cluster
        'flask-1': {},              # BlueGreen switching用App
        'flask-2': {},              # BlueGreen switching用App
}

# --- prd environment---
prd_env_configuration = {
        'vpc': {},                  # prd environment用VPC
        'flask-stateful': {},       # AppのStateful AWS Resource
        'cluster-1': {},            # BlueGreen switching用EKS Cluster
        'cluster-2': {},            # BlueGreen switching用EKS Cluster
        'flask-1': {},              # BlueGreen switching用App
        'flask-2': {},              # BlueGreen switching用App
}

"""

# Enter your repository, apex_domain, cert_arn.
github_owner = 'rafty'
ci_repository = 'https://github.com/rafty/handson-flask_ci.git'
cd_repository = 'https://github.com/rafty/handson-flask_cd.git'
apex_domain = 'yamazon.tk'
wildcard_cert_arn = 'arn:aws:acm:ap-northeast-1:338456725408:certificate/124163b3-7ec8-4cf7-af6e-f05d8bc6ce8f'

ci_repository_name = ci_repository.rsplit('.', 1)[0].rsplit('/', 1)[1]  # 'handson-flask_ci'

codepipeline_stack_configuration = {
    'pipeline_name': 'flask_codepipeline',
    'github_token_name': 'GithubPersonalAccessToken',
    'github_source_repository': ci_repository,
    'github_source_repository_name': ci_repository_name,
    'github_owner': github_owner,
    'github_cd_repository': cd_repository,
    'github_cd_target_manifest': 'deployment.yaml',
    'ecr_repository_name': 'flask'
}

# --- dev environment---
dev_env_configuration = {
    'vpc': {
        'name': 'dev',
        'cidr': '10.11.0.0/16',
        'azs': 3,    # aws_ec2.Vpc.from_vpc_attributesを使用する際、３つのAZがあることを前提とする
        'nat_gateways': 1,
        'cluster_name_list': ['dev-1', 'dev-2']  # SubnetにEKS用Tag付加
    },
    'cluster-1': {
        'name': 'dev-1',
        'version': '1.21',
        'instance_type': 't3.large',
        'addon_cwmetrics_enable': True,
        'addon_cwlogs_enable': True,
        'addon_awslbclt_enable': True,
        'addon_extdns_enable': True,
        'addon_argocd_enable': True,
        'addon_argocd_domain': apex_domain,
        'addon_argocd_subdomain': f'argocd-dev-1.{apex_domain}',
        'addon_argocd_cert_arn': wildcard_cert_arn,
        'addon_argocd_secret_name': 'ArgocdServerAdminPassword'
    },
    'cluster-2': {
        'name': 'dev-2',
        'version': '1.22',
        'instance_type': 't3.large',
        'addon_cwmetrics_enable': True,
        'addon_cwlogs_enable': True,
        'addon_awslbclt_enable': True,
        'addon_extdns_enable': True,
        'addon_argocd_enable': True,
        'addon_argocd_domain': apex_domain,
        'addon_argocd_subdomain': f'argocd-dev-2.{apex_domain}',
        'addon_argocd_cert_arn': wildcard_cert_arn,
        'addon_argocd_secret_name': 'ArgocdServerAdminPassword'
    },
    'flask-stateful': {
        'env': 'dev',
        'dynamodb_table': 'messages-dev',
        'dynamodb_partition': 'uuid',
        'wildcard_cert_arn': wildcard_cert_arn,
        'apex_domain': apex_domain,
        'sub_domain': f'flask-dev.{apex_domain}',
        'cluster_list': ['dev-1', 'dev-2']
    },
    'flask-1': {
        'env': 'dev',
        'eks_cluster': 'dev-1',
        'name': 'flask',
        'namespace': 'flask',
        'service_account': 'flask',
        'repo': cd_repository,
        'repo_path': '.',
        'repo_branch': 'dev'
    },
    'flask-2': {
        'env': 'dev',
        'eks_cluster': 'dev-2',
        'name': 'flask',
        'namespace': 'flask',
        'service_account': 'flask',
        'repo': cd_repository,
        'repo_path': '.',
        'repo_branch': 'dev',
    },
}

# --- prd environment---
prd_env_configuration = {
    'vpc': {
        'name': 'prd',
        'cidr': '10.12.0.0/16',
        'azs': 3,  # aws_ec2.Vpc.from_vpc_attributesを使用する際、３つのAZがあることを前提とする
        'nat_gateways': 1,
        'cluster_name_list': ['prd-1', 'prd-2']  # SubnetにEKS用Tag付加
    },
    'cluster-1': {
        'name': 'prd-1',
        'version': '1.21',
        'instance_type': 't3.large',
        'addon_cwmetrics_enable': True,
        'addon_cwlogs_enable': True,
        'addon_awslbclt_enable': True,
        'addon_extdns_enable': True,
        'addon_argocd_enable': True,
        'addon_argocd_domain': apex_domain,
        'addon_argocd_subdomain': f'argocd-prd-1.{apex_domain}',
        'addon_argocd_cert_arn': wildcard_cert_arn,
        'addon_argocd_secret_name': 'ArgocdServerAdminPassword'
    },
    'cluster-2': {
        'name': 'prd-2',
        'version': '1.22',
        'instance_type': 't3.large',
        'addon_cwmetrics_enable': True,
        'addon_cwlogs_enable': True,
        'addon_awslbclt_enable': True,
        'addon_extdns_enable': True,
        'addon_argocd_enable': True,
        'addon_argocd_domain': apex_domain,
        'addon_argocd_subdomain': f'argocd-prd-2.{apex_domain}',
        'addon_argocd_cert_arn': wildcard_cert_arn,
        'addon_argocd_secret_name': 'ArgocdServerAdminPassword'
    },
    'flask-stateful': {
        'env': 'prd',
        'dynamodb_table': 'messages-prd',
        'dynamodb_partition': 'uuid',
        'wildcard_cert_arn': wildcard_cert_arn,
        'apex_domain': apex_domain,
        'sub_domain': f'flask-prd.{apex_domain}',
        'cluster_list': ['prd-1', 'prd-2']  # BlueGreen Switching用にprd-2がなくても作成する。
    },
    'flask-1': {
        'env': 'prd',
        'eks_cluster': 'prd-1',
        'name': 'flask',
        'namespace': 'flask',
        'service_account': 'flask',
        'repo': cd_repository,
        'repo_path': '.',
        'repo_branch': 'prd',
    },
    'flask-2': {
        'env': 'prd',
        'eks_cluster': 'prd-2',
        'name': 'flask',
        'namespace': 'flask',
        'service_account': 'flask',
        'repo': cd_repository,
        'repo_path': '.',
        'repo_branch': 'prd',
    },
}
