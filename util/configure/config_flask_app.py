class ConfigFlaskApp:

    def __init__(self, config) -> None:
        self.config = config

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
    def dynamodb_table(self):
        return self.config.get('dynamodb_table')

    @property
    def dynamodb_partition(self):
        return self.config.get('dynamodb_partition')
