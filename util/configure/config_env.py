class ConfigEnv:

    def __init__(self, config_env) -> None:
        self._config_env = config_env

    @property
    def name(self):
        return self._config_env['name']
