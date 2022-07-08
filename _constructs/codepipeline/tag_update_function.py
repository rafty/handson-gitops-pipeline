import os
import subprocess
import aws_cdk
from constructs import Construct
from aws_cdk import aws_lambda
from aws_cdk import aws_iam
from util.configure.config import Config


class TagUpdateFunction(Construct):
    # ----------------------------------------------------------
    # Stage - Manifest Tag Update (GitHub)
    # ----------------------------------------------------------
    def __init__(self,
                 scope: Construct,
                 id: str,
                 config: Config,
                 **kwargs) -> None:
        super().__init__(scope, id)

        self.config = config

    def create(self):
        # ----------------------------------------------------------
        # Stage - Manifest Tag Update (GitHub)
        # ----------------------------------------------------------
        function = self.create_lambda_function()
        return function

    def create_lambda_function(self):
        lambda_role = self.create_lambda_role()
        git_layer = self.create_lambda_layer()
        powertools_layer = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            id='lambda-powertools',
            layer_version_arn=(f'arn:aws:lambda:{self.config.aws_env.region}:017000801446:'
                               'layer:AWSLambdaPowertoolsPython:19')
        )

        function = aws_lambda.Function(
            self,
            'LambdaInvokeFunction',
            function_name='GithubManifestTagUpdate',
            handler='function.lambda_handler',
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            # code=aws_lambda.Code.from_asset('./functions/manifest_update'),
            code=aws_lambda.Code.from_asset('./_constructs/codepipeline/functions/manifest_update'),
            role=lambda_role,
            layers=[powertools_layer, git_layer],
            environment={
                'POWERTOOLS_SERVICE_NAME': 'GitOpsPipelineAction',  # for Powertools
                'LOG_LEVEL': 'INFO',  # for Powertools
            },
            memory_size=128,
            timeout=aws_cdk.Duration.seconds(60),
            # dead_letter_queue_enabled=True
        )
        return function

    def create_lambda_role(self):
        lambda_role = aws_iam.Role(
            self,
            id='LambdaRole',
            assumed_by=aws_iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                # Adding Policies
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AWSLambdaBasicExecutionRole'),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchFullAccess'),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSCodePipeline_FullAccess'),
            ]
        )
        lambda_role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=['secretsmanager:GetSecretValue'],
                resources=["*"]))
        lambda_role.add_to_policy(aws_iam.PolicyStatement(
            resources=["*"],
            actions=["sts:AssumeRole"]))
        return lambda_role

    def create_lambda_layer(self) -> aws_lambda.LayerVersion:
        requirements_file = './_constructs/codepipeline/layers/git_command/requirements.txt'
        output_dir = "layer_pip/"

        # Install requirements for layer in the output_dir
        if not os.environ.get("SKIP_PIP"):
            # Note: Pip will create the output dir if it does not exist
            subprocess.check_call(
                f"pip install -r {requirements_file} -t {output_dir}/python".split()
            )
        layer = aws_lambda.LayerVersion(
            self,
            id='GitCommand',
            layer_version_name='GitCommand',
            code=aws_lambda.Code.from_asset(output_dir)
        )
        return layer
