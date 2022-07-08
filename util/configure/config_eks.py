class ConfigEks:

    def __init__(self, config) -> None:
        self.config = config

    @property
    def cluster_name(self):
        return self.config['cluster_name']

    @property
    def cluster_version(self):
        return self.config['cluster_version']

    @property
    def instance_type(self):
        return self.config['instance_type']

    @property
    def addon_cwmetrics_enable(self):
        return self.config.get('addon_cwmetrics_enable', False)

    @property
    def addon_cwlogs_enable(self):
        return self.config.get('addon_cwlogs_enable', False)

    @property
    def addon_awslbclt_enable(self):
        return self.config.get('addon_awslbclt_enable', False)

    @property
    def addon_extdns_enable(self):
        return self.config.get('addon_extdns_enable', False)

    @property
    def addon_argocd_enable(self):
        return self.config.get('addon_argocd_enable', False)

    @property
    def addon_argocd_domain(self):
        return self.config.get('addon_argocd_domain')

    @property
    def addon_argocd_subdomain(self):
        return self.config.get('addon_argocd_subdomain')

    @property
    def addon_argocd_cert_arn(self):
        return self.config.get('addon_argocd_cert_arn')

    @property
    def addon_argocd_secret_name(self):
        return self.config.get('addon_argocd_secret_name')
