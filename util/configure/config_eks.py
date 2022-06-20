class ConfigEks:

    def __init__(self, config) -> None:
        self.config = config

    @property
    def name(self):
        return self.config['name']

    @property
    def instance_type(self):
        return self.config['instance_type']

    @property
    def addon_enable_cwmetrics(self):
        return self.config.get('addon_enable_cwmetrics')

    @property
    def addon_enable_cwlogs(self):
        return self.config.get('addon_enable_cwlogs')

    @property
    def addon_enable_awslbclt(self):
        return self.config.get('addon_enable_awslbclt')

    @property
    def addon_enable_extdns(self):
        return self.config.get('addon_enable_extdns')

    # Todo: Should be changed to a better method
    @property
    def service_argocd(self):
        return self.config.get('service_argocd', False)

    @property
    def service_argocd_domain(self):
        return self.config.get('service_argocd_domain')

    @property
    def service_argocd_subdomain(self):
        return self.config.get('service_argocd_subdomain')

    @property
    def service_argocd_cert_arn(self):
        return self.config.get('service_argocd_cert_arn')

    @property
    def service_argocd_secret_name(self):
        return self.config.get('service_argocd_secret_name')
