#!/usr/bin/env python3
import os
import aws_cdk as cdk
from _stacks.eks_pipeline import EksClusterStack
from _stacks.flask_app_stack import FlaskAppStack
from _stacks.vpc_stack import VpcStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

# ------------------------------------------------------
# VPC for Dev environment
# ------------------------------------------------------
vpc_stack_dev = VpcStack(
    app,
    "EksVpcStack",
    vpc_name='app-dev',  # Todo:  クロススタック参照で使う！問題ないか？
    vpc_cidr='10.11.0.0/16',
    cluster_list=['app-dev-1', 'app-dev-2'],  # app-dev-2: for Cluster Blue Green Deployment
    env=env)

# # ------------------------------------------------------
# # VPC for Prd environment
# # ------------------------------------------------------
# vpc_stack_prd = VpcStack(
#     app,
#     "EksVpcStack",
#     vpc_name='app-prd',
#     vpc_cidr='10.12.0.0/16',
#     cluster_list=['app-prd-1', 'app-prd-2'],  # app-dev-2: for Cluster Blue Green Deployment
#     env=env)

# ------------------------------------------------------
# for Dev environment
# ------------------------------------------------------
eks_cluster_stack_dev_1 = EksClusterStack(
    app,
    "EksAppStack",
    sys_env='dev-1',
    env=env)
eks_cluster_stack_dev_1.add_dependency(vpc_stack_dev)

flask_app_stack_dev_1 = FlaskAppStack(
    app,
    "FlaskAppStack",
    sys_env='dev-1',
    env=env)
flask_app_stack_dev_1.add_dependency(eks_cluster_stack_dev_1)

# ------------------------------------------------------
# for Prod environment
# ------------------------------------------------------
# eks_cluster_stack_prd_1 = EksClusterStack(
#     app,
#     "EksAppStack",
#     sys_env='prd-1',
#     env=env)
# eks_cluster_stack_prd_1.add_dependency(vpc_stack_prd)
#
# flask_app_stack_prd_1 = FlaskAppStack(
#     app,
#     "FlaskAppStack",
#     sys_env='prd-1',
#     env=env)
# flask_app_stack_prd_1.add_dependency(eks_cluster_stack_dev_1)

app.synth()
