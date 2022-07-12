import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_ec2
from aws_cdk import aws_dynamodb
from aws_cdk import aws_elasticloadbalancingv2
from aws_cdk import aws_route53
from aws_cdk import aws_route53_targets
from aws_cdk import aws_certificatemanager


class FlaskAppStatefulStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            vpc_config: dict,
            flask_stateful_config: dict,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc_conf = vpc_config
        self.flask_stateful_conf = flask_stateful_config

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
            table_name=self.flask_stateful_conf['dynamodb_table'],
            partition_key=aws_dynamodb.Attribute(
                name=self.flask_stateful_conf['dynamodb_partition'],
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
        self.create_alb_target_group(alb=alb)
        self.register_subdomain(alb=alb)

    def create_alb(self) -> aws_elasticloadbalancingv2.ApplicationLoadBalancer:

        # Security Group for ALB
        alb_security_group = aws_ec2.SecurityGroup(
            self,
            'alb-sg',
            vpc=self.vpc,
            description='ALB Security Group',
            security_group_name=f'flask-alb-{self.flask_stateful_conf["env"]}'
        )

        alb_security_group.add_ingress_rule(
            peer=aws_ec2.Peer.ipv4('0.0.0.0/0'),
            connection=aws_ec2.Port.tcp(443)
        )

        # AWS Application Load Balancer
        alb = aws_elasticloadbalancingv2.ApplicationLoadBalancer(
            self,
            'Alb',
            load_balancer_name=f'flask-{self.flask_stateful_conf["env"]}',
            internet_facing=True,
            security_group=alb_security_group,
            vpc=self.vpc,
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PUBLIC)
        )

        # cross stack reference. for TargetGroupBinding
        aws_cdk.CfnOutput(
            self,
            id='CfnOutputAlbSecurityGroupId',
            value=alb_security_group.security_group_id,
            description="Security GroupId of ALB",
            export_name=f'AlbSecurityGroupId-{self.flask_stateful_conf["env"]}'
        )
        return alb

    def create_alb_target_group(
            self,
            alb: aws_elasticloadbalancingv2.ApplicationLoadBalancer):
        """AWS Application Load Balancer Target Group for TargetGroupBinding
        https://www.google.com/search?q=aws+application+load+balancer+targetgroupbinding&oq=aws+application+load+balancer+targetgroupbinding&aqs=chrome..69i57j0i546l2.19813j0j7&sourceid=chrome&ie=UTF-8
        """

        # health check
        health_check = aws_elasticloadbalancingv2.HealthCheck(
            interval=aws_cdk.Duration.seconds(30),
            path='/healthz',
            timeout=aws_cdk.Duration.seconds(5)
        )

        # Cluster BlueGreen用に2つのTargetGroupを作成する
        # ALBの場合、Service typeはClusterIP
        # targets: TargetGroupBindingでTargetを登録するため必要なし
        target_group_1 = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            'BlueGreenTargetGroup-1',
            target_group_name=f'blue-green-tg-1-{self.flask_stateful_conf["env"]}',
            target_type=aws_elasticloadbalancingv2.TargetType.IP,  # k8s service type ClusterIP
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTP,
            port=80,
            vpc=self.vpc,
            health_check=health_check
        )

        target_group_2 = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            'BlueGreenTargetGroup-2',
            target_group_name=f'blue-green-tg-2-{self.flask_stateful_conf["env"]}',
            target_type=aws_elasticloadbalancingv2.TargetType.IP,  # k8s service type ClusterIP
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTP,
            port=80,
            vpc=self.vpc,
            health_check=health_check
        )

        # wildcard certification for ALB Listener
        cert = aws_certificatemanager.Certificate.from_certificate_arn(
            self,
            'Certificate',
            certificate_arn=self.flask_stateful_conf['wildcard_cert_arn']
        )

        # HTTPS ALB Listener
        # alb listener needs at least one default_action or target_group
        https_listener = alb.add_listener(
            'Listener443',
            port=443,
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTPS,
            default_action=aws_elasticloadbalancingv2.ListenerAction.weighted_forward([
                {'targetGroup': target_group_1, 'weight': 100},
            ]),
            certificates=[cert]  # Certification
        )

        # ApplicationListenerRuleでlistenerとtarget_groupを連携する
        listener_rule = aws_elasticloadbalancingv2.ApplicationListenerRule(
            self,
            'ApplicationListenerRule',
            listener=https_listener,
            priority=1,  # Priority of the rule.
            # Todo: --------- ↓ Blue Green Traffic switching ---------
            action=aws_elasticloadbalancingv2.ListenerAction.weighted_forward([
                    {'targetGroup': target_group_1, 'weight': 100},  # Blue
                    {'targetGroup': target_group_2, 'weight': 0},    # Green
                 ]),
            # action=aws_elasticloadbalancingv2.ListenerAction.weighted_forward([
            #         {'targetGroup': target_group_1, 'weight': 0},      # Blue
            #         {'targetGroup': target_group_2, 'weight': 100},    # Green
            #      ]),
            # Todo: --------- ↑ Blue Green Traffic switching ---------
            conditions=[
                aws_elasticloadbalancingv2.ListenerCondition.path_patterns(['/*']),
                aws_elasticloadbalancingv2.ListenerCondition.host_headers([
                    self.flask_stateful_conf['sub_domain'],
                    # flask.yamazon.tkからのアクセスを許可, alb dns名でのアクセスを拒否
                ])
            ]
        )

        # Cross Stack Reference for TargetGroupBinding manifest
        aws_cdk.CfnOutput(
            self,
            id='CfnOutputTargetGroupArn-1',
            value=target_group_1.target_group_arn,
            description="ALB Target Group for cluster blue green",
            export_name=f'ALB-TargetGroupArn-{self.flask_stateful_conf["cluster_list"][0]}',
            # ALB-TargetGroupArn-dev-1, ALB-TargetGroupArn-prd-1, ...
        )
        aws_cdk.CfnOutput(
            self,
            id='CfnOutputTargetGroupArn-2',
            value=target_group_2.target_group_arn,
            description="ALB Target Group for cluster blue green",
            export_name=f'ALB-TargetGroupArn-{self.flask_stateful_conf["cluster_list"][1]}',
            # ALB-TargetGroupArn-dev-2, ALB-TargetGroupArn-prd-2, ...
        )

    def register_subdomain(self, alb: aws_elasticloadbalancingv2.ApplicationLoadBalancer):
        # Route53 Hosted ZoneにApplicationのA Recordを追加する。
        # 既にA Recordが存在する場合はエラーとなるため、手動で削除する必要がある。
        # delete_existingパラメータがDocumentに存在するが現時点では指定不可
        hosted_zone = aws_route53.HostedZone.from_lookup(
            self,
            'ApexHostedZone',
            domain_name=self.flask_stateful_conf['apex_domain']  # yamazon.tk
        )

        record = aws_route53.ARecord(
            self,
            'AliasRecord',
            record_name=self.flask_stateful_conf['sub_domain'],  # flask.yamazon.th
            zone=hosted_zone,
            # delete_existing=True,  # Documentにあるが2022.07時点指定不可！ 将来対応
            # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_route53/ARecord.html
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.LoadBalancerTarget(alb))
        )

    def get_vpc_cross_stack(self):
        # Cross Stack Reference
        # from_vpc_attributesを使用する際、３つのAZがあることを前提
        vpc = aws_ec2.Vpc.from_vpc_attributes(
            self,
            'VpcId',
            vpc_id=aws_cdk.Fn.import_value(f'VpcId-{self.vpc_conf["name"]}'),
            availability_zones=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'AZs-{self.vpc_conf["name"]}'),
                assumed_length=3
            ),
            public_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PublicSubnets-{self.vpc_conf["name"]}'),
                assumed_length=3
            ),
            private_subnet_ids=aws_cdk.Fn.split(
                delimiter=',',
                source=aws_cdk.Fn.import_value(f'PrivateSubnets-{self.vpc_conf["name"]}'),
                assumed_length=3
            )
        )
        return vpc
