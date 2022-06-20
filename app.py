#!/usr/bin/env python3
import os
import aws_cdk as cdk
from _stacks.eks_pipeline import EksClusterStack
from _stacks.flask_app_stack import FlaskAppStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

eks_cluster_stack_gitops = EksClusterStack(
    app,
    "EksGitopsStack",
    sys_env='gitops',
    env=env)  # cdk.Environmentにすること

eks_cluster_stack_dev = EksClusterStack(
    app,
    "EksAppStack",
    sys_env='dev',
    env=env)  # cdk.Environmentにすること

flask_app_stack_dev = FlaskAppStack(
    app,
    "FlaskAppStack",
    sys_env='dev',
    env=env)
flask_app_stack_dev.add_dependency(eks_cluster_stack_dev)

app.synth()
