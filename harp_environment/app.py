from microservice_template_core import Core
from microservice_template_core.settings import ServiceConfig, FlaskConfig, DbConfig
from harp_environment.endpoints.environments import ns as environments
from harp_environment.endpoints.health import ns as health


def main():
    ServiceConfig.configuration['namespaces'] = [environments, health]
    FlaskConfig.FLASK_DEBUG = False
    DbConfig.USE_DB = True
    app = Core()
    app.run()


if __name__ == '__main__':
    main()

