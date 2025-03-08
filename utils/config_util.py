from dynaconf import Dynaconf


def loadConfig(toml):
    return Dynaconf(
        settings_files=[toml],
        environments=False,
        envvar_prefix='XYBOT',
        load_dotenv=True,
    )
