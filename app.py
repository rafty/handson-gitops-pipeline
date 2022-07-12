#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.eks_stack import EksClusterStack
from stacks.flask_app_stateful_stack import FlaskAppStatefulStack
from stacks.flask_app_stack import FlaskAppStack
from stacks.vpc_stack import VpcStack
from stacks.flask_codepipeline import CodepipelineStack

from configration import codepipeline_stack_configuration
from configration import dev_env_configuration
from configration import prd_env_configuration

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
    config=codepipeline_stack_configuration,
    env=env)

"""
Develop Environment
"""

# ------------------------------------------------------
# VPC for Dev environment
# ------------------------------------------------------
vpc_stack_dev = VpcStack(
    app,
    "EksVpcStack-dev",
    vpc_config=dev_env_configuration['vpc'],
    env=env)

# ----------------------------------------------------------
# Dev Stateful AWS Resource for App
#   本Stackは1つのAWS Accountで、dev-1, dev-2のClusterが共通で
#   利用するStatefulなリソースを構築する
# ----------------------------------------------------------
flask_app_stateful_stack_dev = FlaskAppStatefulStack(
    app,
    "FlaskAppStatefulStack-Dev",
    vpc_config=dev_env_configuration['vpc'],
    flask_stateful_config=dev_env_configuration['flask-stateful'],
    env=env)
flask_app_stateful_stack_dev.add_dependency(vpc_stack_dev)

# ------------------------------------------------------
# for Dev environment - 1
# ------------------------------------------------------
eks_cluster_stack_dev_1 = EksClusterStack(
    app,
    "EksClusterStack-dev-1",
    vpc_config=dev_env_configuration['vpc'],
    cluster_config=dev_env_configuration['cluster-1'],
    env=env)
eks_cluster_stack_dev_1.add_dependency(flask_app_stateful_stack_dev)


flask_app_stack_dev_1 = FlaskAppStack(
    app,
    "FlaskAppStack-dev-1",
    vpc_config=dev_env_configuration['vpc'],
    cluster_config=dev_env_configuration['cluster-1'],
    flask_config=dev_env_configuration['flask-1'],
    env=env)
flask_app_stack_dev_1.add_dependency(eks_cluster_stack_dev_1)

# ------------------------------------------------------
# for Dev environment - 2
# ------------------------------------------------------
eks_cluster_stack_dev_2 = EksClusterStack(
    app,
    "EksClusterStack-dev-2",
    vpc_config=dev_env_configuration['vpc'],
    cluster_config=dev_env_configuration['cluster-2'],
    env=env)
eks_cluster_stack_dev_2.add_dependency(flask_app_stack_dev_1)

flask_app_stack_dev_2 = FlaskAppStack(
    app,
    "FlaskAppStack-dev-2",
    vpc_config=dev_env_configuration['vpc'],
    cluster_config=dev_env_configuration['cluster-2'],
    flask_config=dev_env_configuration['flask-2'],
    env=env)
flask_app_stack_dev_2.add_dependency(eks_cluster_stack_dev_2)


"""
Production Environment
"""

# ------------------------------------------------------
# VPC for Prd environment
# ------------------------------------------------------
vpc_stack_prd = VpcStack(
    app,
    "EksVpcStack-prd",
    vpc_config=prd_env_configuration['vpc'],
    env=env)
vpc_stack_prd.node.add_dependency(flask_app_stack_dev_2)

# ------------------------------------------------------
# Prd Stateful AWS Resource for App
#   本Stackは1つのAWS Accountで、dev-1, dev-2のClusterが共通で
#   利用するStatefulなリソースを構築する
# ------------------------------------------------------
flask_app_stateful_stack_prd = FlaskAppStatefulStack(
    app,
    "FlaskAppStatefulStack-Prd",
    vpc_config=prd_env_configuration['vpc'],
    flask_stateful_config=prd_env_configuration['flask-stateful'],
    env=env)
flask_app_stateful_stack_prd.add_dependency(vpc_stack_prd)

# ------------------------------------------------------
# for Prod environment
# ------------------------------------------------------
eks_cluster_stack_prd_1 = EksClusterStack(
    app,
    "EksClusterStack-prd-1",
    vpc_config=prd_env_configuration['vpc'],
    cluster_config=prd_env_configuration['cluster-1'],
    env=env)
eks_cluster_stack_prd_1.add_dependency(flask_app_stateful_stack_prd)

flask_app_stack_prd_1 = FlaskAppStack(
    app,
    "FlaskAppStack-prd-1",
    vpc_config=prd_env_configuration['vpc'],
    cluster_config=prd_env_configuration['cluster-1'],
    flask_config=prd_env_configuration['flask-1'],
    env=env)
flask_app_stack_prd_1.add_dependency(eks_cluster_stack_prd_1)


# ------------------------------------------------------
# cdk synth()
# ------------------------------------------------------
app.synth()
