import aws_cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_ec2
from aws_cdk import Tags


class VpcStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            vpc_config: dict,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.aws_env = {'account': self.account, 'region': self.region}
        self.vpc_conf = vpc_config

        self.vpc = aws_ec2.Vpc(
            self,
            'Vpc',
            vpc_name=self.vpc_conf['name'],
            cidr=self.vpc_conf['cidr'],
            max_azs=self.vpc_conf['azs'],  # aws_ec2.Vpc.from_vpc_attributesを使用する際、３つのAZがあることを前提とする
            nat_gateways=self.vpc_conf['nat_gateways'],
            subnet_configuration=[
                aws_ec2.SubnetConfiguration(
                    name="Front",
                    subnet_type=aws_ec2.SubnetType.PUBLIC,
                    cidr_mask=24),
                aws_ec2.SubnetConfiguration(
                    name="Application",
                    subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_NAT,
                    cidr_mask=24),
                aws_ec2.SubnetConfiguration(
                    name="DataStore",
                    subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24),
            ]
        )
        self.tag_subnet_for_eks_cluster()
        self.vpc_outputs()

    def tag_subnet_for_eks_cluster(self):
        # ---------------- Subnet Tagging -----------------------
        # VPCに複数のEKS Clusterがある場合、Tag:"kubernetes.io/cluster/cluster-name": "shared"が必要
        # PrivateSubnetにはTag "kubernetes.io/role/internal-elb": '1'
        # PublicSubnetには"kubernetes.io/role/elb": '1'
        # https://docs.aws.amazon.com/ja_jp/eks/latest/userguide/network_reqs.html
        # https://docs.aws.amazon.com/ja_jp/eks/latest/userguide/alb-ingress.html

        self.tag_all_subnets(self.vpc.public_subnets, 'kubernetes.io/role/elb', '1')
        self.tag_all_subnets(self.vpc.private_subnets, 'kubernetes.io/role/internal-elb', '1')

        for cluster_name in self.vpc_conf['cluster_name_list']:
            self.tag_all_subnets(self.vpc.public_subnets,
                                 f'kubernetes.io/cluster/{cluster_name}', 'shared')
            self.tag_all_subnets(self.vpc.private_subnets,
                                 f'kubernetes.io/cluster/{cluster_name}', 'shared')

    @staticmethod
    def tag_all_subnets(subnets, tag_name, tag_value):
        for subnet in subnets:
            Tags.of(subnet).add(tag_name, tag_value)

    def vpc_outputs(self):
        # Cross Stack Output
        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputVpcId',
            value=self.vpc.vpc_id,
            description="VPD ID",
            export_name=f'VpcId-{self.vpc_conf["name"]}'
        )

        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputAZs',
            value=','.join(map(str, self.vpc.availability_zones)),
            # value = "ap-northeast-1a,ap-northeast-1c,ap-northeast-1d"
            description="AZs of VPC",
            export_name=f'AZs-{self.vpc_conf["name"]}'
        )

        public_subnet_ids = [subnet.subnet_id for subnet in self.vpc.public_subnets]
        public_subnet_ids_string = ','.join(public_subnet_ids)
        # "public_subnet_id_1,public_subnet_id_1,public_subnet_id_1"

        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputPublicSubnets',
            value=public_subnet_ids_string,
            description="Public Subnets of VPC",
            export_name=f'PublicSubnets-{self.vpc_conf["name"]}'
        )

        private_subnet_id_list = [i_subnet.subnet_id for i_subnet in self.vpc.private_subnets]
        private_subnets_string = ','.join(private_subnet_id_list)
        # "private_subnet_id_1,private_subnet_id_2,private_subnet_id_3"

        aws_cdk.CfnOutput(
            self,
            id=f'CfnOutputPrivateSubnets',
            value=private_subnets_string,
            description="Private Subnets of VPC",
            export_name=f'PrivateSubnets-{self.vpc_conf["name"]}'
        )
