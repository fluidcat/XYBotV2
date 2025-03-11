from dynaconf import Dynaconf


def loadConfig(toml=None):
    return Dynaconf(
        settings_files=[toml],
        environments=False,
        envvar_prefix='XYBOT',
        load_dotenv=True,
    )


env_config = loadConfig()
