import yaml
import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_eks
from aws_cdk import aws_ec2
from aws_cdk import aws_dynamodb
from aws_cdk import aws_iam
from aws_cdk import aws_elasticloadbalancingv2
from aws_cdk import aws_elasticloadbalancingv2_targets
from aws_cdk import aws_route53
from aws_cdk import aws_route53_targets
from aws_cdk import aws_certificatemanager
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
        self.vpc = self.get_vpc_cross_stack()

        self.create_stateful_alb()
        self.dynamodb = self.create_dynamodb()

    def create_dynamodb(self) -> aws_dynamodb.Table:
        # --------------------------------------------------------------
        # DynamoDB
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

    def create_stateful_alb(self) -> aws_elasticloadbalancingv2.ApplicationLoadBalancer:
        # --------------------------------------------------------------
        # Application Load Balancer
        # --------------------------------------------------------------
        alb = self.create_alb()
        self.create_blue_green_target_group(alb=alb)
        self.register_subdomain(alb=alb)

    def create_alb(self) -> aws_elasticloadbalancingv2.ApplicationLoadBalancer:

        # Security Group for ALB
        alb_security_group = aws_ec2.SecurityGroup(
            self,
            'alb-sg',
            vpc=self.vpc,
            description='ALB Security Group',
            security_group_name='flask-alb'
        )
        alb_security_group.add_ingress_rule(
            peer=aws_ec2.Peer.ipv4('0.0.0.0/0'),
            connection=aws_ec2.Port.tcp(443)
        )

        # # get subnets. non exist vpc subnets. cross stack reference.
        # public_subnet_ids_string = aws_cdk.Fn.import_value(f'PublicSubnets-{self.config.vpc.name}')
        # public_subnet_ids = public_subnet_ids_string.split(',')
        # subnets = [
        #     aws_ec2.Subnet.from_subnet_attributes(
        #         self,
        #         f'public-subnet-{i+1}',
        #         subnet_id=public_subnet_id,)
        #     for i, public_subnet_id in enumerate(public_subnet_ids)
        # ]
        # subnets = []
        # for i, public_subnet_id in enumerate(public_subnet_ids):
        #     subnets.append(
        #         aws_ec2.Subnet.from_subnet_attributes(
        #             self,
        #             f'public-subnet-{i+1}',
        #             subnet_id=public_subnet_id)
        #     )
        # subnets = [
        #     aws_ec2.Subnet.from_subnet_attributes(
        #         self,
        #         f'public-subnet-{i+1}',
        #         subnet_id=public_subnet_id)
        # ]

        # ALB
        alb = aws_elasticloadbalancingv2.ApplicationLoadBalancer(
            self,
            'Alb',
            load_balancer_name='flask-app',
            internet_facing=True,
            security_group=alb_security_group,
            vpc=self.vpc,
            # vpc_subnets=aws_ec2.SubnetSelection(subnets)
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PUBLIC)  # Todo: これでいいの？
        )

        aws_cdk.CfnOutput(
            self,
            id='CfnOutputAlbSecurityGroupId',
            value=alb_security_group.security_group_id,
            description="Security GroupId of ALB",
            export_name='AlbSecurityGroupId'
        )

        return alb

    def create_blue_green_target_group(
            self,
            alb: aws_elasticloadbalancingv2.ApplicationLoadBalancer):

        # Todo: health checkを指定してるが適用されてないようだ。
        health_check = aws_elasticloadbalancingv2.HealthCheck(
            interval=aws_cdk.Duration.seconds(30),
            path='/healthz',
            timeout=aws_cdk.Duration.seconds(5)
        )

        # k8s Manifest TargetGroupBindingでserviceとTargetGroupArnで接続する
        # Cluster BlueGreen用に事前に作成する
        target_group_1 = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            'BlueGreenTargetGroup-1',
            target_group_name='blue-green-tg-1',
            # targets=xxxx,  # k8s Manifest TargetGroupBindingで接続するため必要なし
            target_type=aws_elasticloadbalancingv2.TargetType.IP,  # k8s service type ClusterIp
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTP,
            port=80,
            vpc=self.vpc,
            health_check=health_check
        )

        target_group_2 = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            'BlueGreenTargetGroup-2',
            target_group_name='blue-green-tg-2',
            # targets=xxxx,  # k8s Manifest TargetGroupBindingで接続するため必要なし
            target_type=aws_elasticloadbalancingv2.TargetType.IP,  # k8s service type ClusterIp
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTP,
            port=80,
            vpc=self.vpc,
            health_check=health_check
        )

        # wildcard certification
        cert = aws_certificatemanager.Certificate.from_certificate_arn(
            self,
            'Certificate',
            certificate_arn=self.config.flask_app.wildcard_cert_arn
        )

        # listener
        https_listener = alb.add_listener(
            'Listener443',
            port=443,
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTPS,
            default_action=aws_elasticloadbalancingv2.ListenerAction.weighted_forward([  # todo: これでいいのか？
                {'targetGroup': target_group_1, 'weight': 100},
            ]),
            certificates=[cert]  # Certification
        )
        # Listener needs at least one default action or target group  # Todo: TargetGroupを指定するほうがよいのか？

        # ApplicationListenerRuleでlistenerとtarget_groupを連携する
        listener_rule = aws_elasticloadbalancingv2.ApplicationListenerRule(
            self,
            'ApplicationListenerRule',
            listener=https_listener,
            priority=1,  # Priority of the rule.
            action=aws_elasticloadbalancingv2.ListenerAction.weighted_forward([
                    {'targetGroup': target_group_1, 'weight': 100},  # Blue
                    {'targetGroup': target_group_2, 'weight': 0},    # Green
                 ]),
            conditions=[
                aws_elasticloadbalancingv2.ListenerCondition.path_patterns(['/*']),
                aws_elasticloadbalancingv2.ListenerCondition.host_headers([
                    self.config.flask_app.sub_domain,  # flask.yamazon.tkからのアクセスを許可。
                                                       # alb-dns名でのアクセスを拒否する
                ])
            ]
        )

        aws_cdk.CfnOutput(
            self,
            id='CfnOutputTargetGroupArn-1',
            value=target_group_1.target_group_arn,
            description="ALB Target Group for cluster blue green",
            export_name='ALB-TargetGroupArn-1'
        )

        aws_cdk.CfnOutput(
            self,
            id='CfnOutputTargetGroupArn-2',
            value=target_group_2.target_group_arn,
            description="ALB Target Group for cluster blue green",
            export_name='ALB-TargetGroupArn-2'
        )

    def register_subdomain(self, alb: aws_elasticloadbalancingv2.ApplicationLoadBalancer):

        hosted_zone = aws_route53.HostedZone.from_lookup(
            self,
            'ApexHostedZone',
            domain_name=self.config.flask_app.apex_domain  # yamazon.tk
        )

        record = aws_route53.ARecord(
            self,
            'AliasRecord',
            record_name=self.config.flask_app.sub_domain,  # flask.yamazon.th
            zone=hosted_zone,
            # delete_existing=True,  # manualにあるが指定できない！
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.LoadBalancerTarget(alb))
        )
        # record.node.default_child.override_logical_id(record.node.id)
        record.node.default_child.override_logical_id('OverrideExistingRecord')
        # Todo: これで上書きができるのか？
        # https://github.com/aws/aws-cdk/issues/12564

    def get_vpc_cross_stack(self):
        # Todo: from_vpc_attributesを使用する際、３つのAZがあることを前提とする
        vpc = aws_ec2.Vpc.from_vpc_attributes(
            self,
            'VpcId',
            vpc_id=aws_cdk.Fn.import_value(f'VpcId-{self.config.vpc.name}'),
            availability_zones=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'AZs-{self.config.vpc.name}'),
                assumed_length=3
            ),
            public_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PublicSubnets-{self.config.vpc.name}'),
                assumed_length=3
            ),
            private_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PrivateSubnets-{self.config.vpc.name}'),
                assumed_length=3
            )
        )
        return vpc

