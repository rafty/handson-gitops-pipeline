class ConfigFlaskApp:

    def __init__(self, config) -> None:
        self.config = config

    @property
    def service_name(self):
        return self.config['service_name']

    @property
    def eks_cluster(self):
        return self.config['eks_cluster']

    @property
    def namespace(self):
        return self.config['namespace']

    @property
    def service_account(self):
        return self.config['service_account']

    @property
    def repo(self):
        return self.config['repo']

    @property
    def repo_path(self):
        return self.config['repo_path']

    @property
    def dynamodb_table(self):
        return self.config.get('dynamodb_table')

    @property
    def dynamodb_partition(self):
        return self.config.get('dynamodb_partition')

    @property
    def wildcard_cert_arn(self):
        return self.config.get('wildcard_cert_arn')

    @property
    def apex_domain(self):
        return self.config.get('apex_domain')

    @property
    def sub_domain(self):
        return self.config.get('sub_domain')
