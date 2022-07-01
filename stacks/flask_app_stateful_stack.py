import yaml
import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_dynamodb
from aws_cdk import aws_iam
from util.configure.config import Config


class FlaskAppStatefulStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            sys_env: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = Config(self, 'Config', sys_env=sys_env, _aws_env=kwargs.get('env'))
        self.dynamodb = self.create_dynamodb()

    def create_dynamodb(self) -> aws_dynamodb.Table:
        # --------------------------------------------------------------
        #
        # DynamoDB
        #
        # --------------------------------------------------------------
        _dynamodb = aws_dynamodb.Table(
            self,
            id='DynamoDbTable',
            table_name=self.config.flask_app.dynamodb_table,
            partition_key=aws_dynamodb.Attribute(
                name=self.config.flask_app.dynamodb_partition,
                type=aws_dynamodb.AttributeType.STRING),
            read_capacity=1,
            write_capacity=1,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY
        )
        return _dynamodb
