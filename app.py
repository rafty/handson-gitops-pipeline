#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.eks_pipeline import EksClusterStack
from stacks.flask_app_stateful_stack import FlaskAppStatefulStack
from stacks.flask_app_stack import FlaskAppStack
from stacks.vpc_stack import VpcStack
from stacks.flask_codepipeline import CodepipelineStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

"""
 Stack分割の考え方
 - Lifecycleを考慮している
 - EKS ClusterのBlueGreen切り替えを考慮している"""

# ------------------------------------------------------
# AWS CodePipeline
# ------------------------------------------------------
codepipeline_stack_flask = CodepipelineStack(
    app,
    "CodepipelineStack-flask",
    env=env)

"""Production Environment"""

# ------------------------------------------------------
# VPC for Dev environment
# ------------------------------------------------------
vpc_stack_dev = VpcStack(
    app,
    "EksVpcStack-dev",
    vpc_name='app-dev',
    vpc_cidr='10.11.0.0/16',
    cluster_list=['app-dev-1', 'app-dev-2'],  # app-dev-2: for Cluster Blue Green Deployment
    env=env)


# ------------------------------------------------------
# for Dev environment - 1
# ------------------------------------------------------
eks_cluster_stack_dev_1 = EksClusterStack(
    app,
    "EksClusterStack-dev-1",
    sys_env='dev-1',
    env=env)
eks_cluster_stack_dev_1.add_dependency(vpc_stack_dev)

# ------------------------------------------------------
# Dev Stateful AWS Resource for App
#   本Stackは1つのAWS Accountで、dev-1, dev-2のClusterが共通で
#   利用するStatefulなリソースを構築する
# ------------------------------------------------------
flask_app_stateful_stack_dev = FlaskAppStatefulStack(
    app,
    "FlaskAppStatefulStack-Dev",
    sys_env='dev-1',  # Todo: 暫定 cdj.jsonの構成上このようにしている。本来はdevという属性にすべき。
    env=env)
flask_app_stateful_stack_dev.add_dependency(eks_cluster_stack_dev_1)

flask_app_stack_dev_1 = FlaskAppStack(
    app,
    "FlaskAppStack-dev-1",
    sys_env='dev-1',
    env=env)
flask_app_stack_dev_1.add_dependency(flask_app_stateful_stack_dev)

# ------------------------------------------------------
# for Dev environment - 2
# ------------------------------------------------------
eks_cluster_stack_dev_2 = EksClusterStack(
    app,
    "EksClusterStack-dev-2",
    sys_env='dev-2',
    env=env)
eks_cluster_stack_dev_2.add_dependency(flask_app_stack_dev_1)

flask_app_stack_dev_2 = FlaskAppStack(
    app,
    "FlaskAppStack-dev-2",
    sys_env='dev-2',
    env=env)
flask_app_stack_dev_2.add_dependency(eks_cluster_stack_dev_2)

"""Production Environment"""

# # ------------------------------------------------------
# # VPC for Prd environment
# # ------------------------------------------------------
# vpc_stack_prd = VpcStack(
#     app,
#     "EksVpcStack-prd",
#     vpc_name='app-prd',
#     vpc_cidr='10.12.0.0/16',
#     cluster_list=['app-prd-1', 'app-prd-2'],  # app-prd-2: for Cluster Blue Green Deployment
#     env=env)
#
# # ------------------------------------------------------
# # Prd Stateful AWS Resource for App
# #   本Stackは1つのAWS Accountで、dev-1, dev-2のClusterが共通で
# #   利用するStatefulなリソースを構築する
# # ------------------------------------------------------
# flask_app_stateful_stack_prd = FlaskAppStatefulStack(
#     app,
#     "FlaskAppStatefulStack-Prd",
#     sys_env='prd-1',  # Todo: 暫定 cdj.jsonの構成上このようにしている。本来はdevという属性にすべき。
#     env=env)
#
# # ------------------------------------------------------
# # for Prod environment
# # ------------------------------------------------------
# eks_cluster_stack_prd_1 = EksClusterStack(
#     app,
#     "EksClusterStack-prd-1",
#     sys_env='prd-1',
#     env=env)
# eks_cluster_stack_prd_1.add_dependency(vpc_stack_prd)
#
# flask_app_stack_prd_1 = FlaskAppStack(
#     app,
#     "FlaskAppStack-prd-1",
#     sys_env='prd-1',
#     env=env)
# flask_app_stack_prd_1.add_dependency(eks_cluster_stack_prd_1)


# ------------------------------------------------------
# cdk synth()
# ------------------------------------------------------
app.synth()
