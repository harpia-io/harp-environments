import os

ENVIRONMENT_UPDATE_TOPIC = os.getenv('ENVIRONMENT_UPDATE_TOPIC', 'environment-update')
USERS_HOST = os.getenv('USERS_HOST', 'http://harp-users:8081/harp-users/api/v1/users')
SCENARIOS_HOST = os.getenv('SCENARIOS_HOST', 'http://harp-scenarios:8081/harp-scenarios/api/v1/scenarios')