import json

from microservice_template_core.tools.flask_restplus import api
from flask_restx import Resource
from harp_environment.models.environments import Environments, EnvironmentSchema
from flask import request
import traceback
from microservice_template_core.tools.logger import get_logger
from werkzeug.exceptions import NotFound, BadRequest
from microservice_template_core.decorators.auth_decorator import token_required
from microservice_template_core import KafkaProduceMessages
import harp_environment.settings as settings
import requests


logger = get_logger()
ns = api.namespace('api/v1/environments', description='Harp environments endpoints')
environments = EnvironmentSchema()


@ns.route('/create-organization')
class CreateOrganization(Resource):
    @staticmethod
    def put():
        """
        Add organization object
        Use this method to create new Env
        * Send a JSON object
        ```
            {
                "email": "some@gmail.com"
            }
        ```
        """
        org_data = request.get_json()
        logger.info(msg=f"Received request to create new free organization. Data: {org_data}")

        try:
            # Create new Env
            logger.info(msg=f"Start adding new free env. Env name: {org_data['email']}")
            obj_exist = Environments.get_env_by_name(environment_name=org_data['email'])
            if obj_exist:
                return f"Free account for user - {org_data['email']} was already registered", 400

            data = {
                "env_name": org_data['email'],
                "env_settings": {
                    "description": f"Separate env for free account - {org_data['email']}",
                    "default_scenario": 1
                },
                "available_for_users_id": {
                    "visible_only": [],
                    "hidden": []
                }
            }
            new_obj = Environments.add(data)
            create_new_env_result = environments.dump(new_obj.dict())

            # Create default scenario
            logger.info(msg=f"Start adding default scenario for new free user\nUsername: {org_data['email']}\nemail: {org_data['email']}")
            org_scenario_data = {
                "username": org_data['email'].split('@')[0],
                "scenario_name": f"Default scenario for - {org_data['email']}",
                "environment_id": create_new_env_result['id'],
                "description": "Automatically created default scenario for specific Env",
                "external_url": "http://some_url",
                "requested_by": "Default scenario",
                "tags": [],
                "scenario_type": 1,
                "scenario_actions": [
                    {
                        "execute_after_seconds": 0,
                        "type": "ui",
                        "body": {
                            "recipients": ["Duty OPS"],
                            "description": "asd",
                            "affected_func": "User can't login to the site",
                            "should_check": ["Check connection to the sile", "Notify OPS on duty"],
                            "players_expirience": "asd",
                            "not_handled_effects": "Lost user",
                            "notification_period": {},
                            "action_name": "The fist action after the alert triggered",
                            "players_experience": "Bad user experience"
                        }
                    }
                ]
            }
            req = requests.post(
                url=settings.SCENARIOS_HOST,
                data=json.dumps(org_scenario_data),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10
            )

            if req.status_code == 200:
                logger.info(msg=f"New default scenario for free user has been created")
            else:
                status = f"Can`t create new default scenario for new free user\nStatus code - {req.status_code}\norg_user_data: {org_scenario_data}"
                logger.info(msg=status)

                return {"msg": status}, 400

            # Create new user
            logger.info(msg=f"Start adding new free user\nUsername: {org_data['email']}\nemail: {org_data['email']}\nVisible env id: {create_new_env_result['id']}")
            url = f"{settings.USERS_HOST}/invite"
            org_user_data = {
                "email": org_data['email'],
                "username": org_data['email'].split('@')[0],
                "role": "user",
                "active_environment_ids": {
                    "visible_only": [create_new_env_result['id']],
                    "hidden": []
                }
            }
            req = requests.post(
                url=url,
                data=json.dumps(org_user_data),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10
            )

            if req.status_code == 200:
                logger.info(msg=f"New free user has been created")
            else:
                status = f"Can`t create new free user\nStatus code - {req.status_code}\norg_user_data: {org_user_data}\nurl: {url}"
                logger.info(msg=status)

                return {"msg": status}, 400

            # Finalize org creating
            return {"msg": f"New free Org has been created - {org_data['email']}"}, 200

        except ValueError as err:
            logger.warning(
                msg=f"Client error during adding new Organization - {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Client error during adding new Organization - {err}"}, 400
        except Exception as err:
            logger.critical(msg=f"Backend error during adding new Organization - {err}\nTrace: {traceback.format_exc()}")
            return {'msg': f'Client error during adding new Organization - {err}'}, 500

    @staticmethod
    def delete():
        """
        Delete organization object
        Use this method to delete existing free Env
        * Send a JSON object
        ```
            {
                "email": "some@gmail.com"
            }
        ```
        """
        org_data = request.get_json()
        logger.info(msg=f"Received request to delete existing free organization. Data: {org_data}")

        try:
            # Delete existing Env
            logger.info(msg=f"Start deleting existing free env. Env name: {org_data['email']}")
            obj = Environments.get_env_by_name(environment_name=org_data['email'])
            obj.delete_obj()
            logger.info(msg=f"Environment was deleted")

            # Finalize org creating
            return {"msg": f"Existing free Org has been delete - {org_data['email']}"}, 200

        except ValueError as err:
            logger.warning(
                msg=f"Client error during deleting new Organization - {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Client error during deleting new Organization - {err}"}, 400
        except Exception as err:
            logger.critical(msg=f"Backend error during deleting new Organization - {err}\nTrace: {traceback.format_exc()}")
            return {'msg': f'Client error during deleting new Organization - {err}'}, 500


@ns.route('')
class CreateEnvironment(Resource):
    @staticmethod
    @token_required()
    def put():
        """
        Add environment object
        Use this method to create new Env
        * Send a JSON object
        ```
            {
                "env_name": "Nova Street",
                "env_settings": {
                    "description": "Some Env Desc",
                    "default_scenario": 1
                },
                "available_for_users_id": {
                    "visible_only": [],
                    "hidden": []
                }
            }
        ```
        """
        try:
            data = environments.load(request.get_json())
            new_obj = Environments.add(data)
            result = environments.dump(new_obj.dict())

            message = {'type': 'add', 'body': result}
            produce_message = KafkaProduceMessages()
            produce_message.produce_message(topic=settings.ENVIRONMENT_UPDATE_TOPIC, message=message)
        except ValueError as err:
            logger.warning(
                msg=f"Client error during adding new env - {err}\nTrace: {traceback.format_exc()}")
            return {"msg": f"Client error during adding new env - {err}"}, 400
        except Exception as err:
            logger.critical(msg=f"Backend error during adding new env - {err}\nTrace: {traceback.format_exc()}")
            return {'msg': f'Client error during adding new env - {err}'}, 500

        return result, 200


@ns.route('/<int:environment_id>')
class EditEnvironment(Resource):

    @staticmethod
    def get(environment_id):
        """
            Return Environment object with specified id
        """
        if not environment_id:
            return {'msg': 'environment_id should be specified'}, 404
        obj = Environments.obj_exist(environment_id)
        if not obj:
            raise NotFound('object with specified_id is not found')
        result = environments.dump(obj.dict())
        return {"msg": result}, 200

    @staticmethod
    @token_required()
    def post(environment_id):
        """
        Updates existing object with specified environment_id
        Use this method to update existing Env
        * Send a JSON object
        ```
            {
                "env_name": "Nova Street 2",
                "env_settings": {
                    "description": "Some Env Desc 2",
                    "default_scenario": 1
                },
                "available_for_users_id": {
                    "visible_only": [],
                    "hidden": []
                }
            }
        ```
        """
        if not environment_id:
            raise NotFound('environment_id should be specified')
        obj = Environments.obj_exist(environment_id)
        if not obj:
            raise NotFound('Environment with specified id is not exist')
        try:
            data = environments.load(request.get_json())
            obj.update_obj(data=data, environment_id=environment_id)
            result = environments.dump(obj.dict())

            message = {'type': 'update', 'body': result}
            produce_message = KafkaProduceMessages()
            produce_message.produce_message(topic=settings.ENVIRONMENT_UPDATE_TOPIC, message=message)
        except ValueError as val_exc:
            logger.warning(
                msg=f"Environment updating exception - {val_exc}\nTrace: {traceback.format_exc()}")
            return {"msg": str(val_exc)}, 400
        except BadRequest as bad_request:
            logger.warning(
                msg=f"Environment updating exception - {bad_request}\nTrace: {traceback.format_exc()}")
            return {'msg': str(bad_request)}, 400
        except Exception as exc:
            logger.critical(
                msg=f"Environment updating exception - {exc}\nTrace: {traceback.format_exc()}")
            return {'msg': f'Exception raised - {exc}. Check logs for additional info'}, 500

        return result, 200

    @staticmethod
    @token_required()
    def delete(environment_id):
        """
            Delete Environment object with specified id
        """
        if not environment_id:
            raise NotFound('environment_id should be specified')
        obj = Environments.obj_exist(environment_id)
        try:
            if obj:
                obj.delete_obj()
                logger.info(msg=f"Environment deletion. Id: {environment_id}")

                message = {'type': 'delete', 'body': {'environment_id': environment_id}}
                produce_message = KafkaProduceMessages()
                produce_message.produce_message(topic=settings.ENVIRONMENT_UPDATE_TOPIC, message=message)
            else:
                raise NotFound('Object with specified environment_id is not found')
        except Exception as exc:
            logger.critical(
                msg=f"Environment deletion exception - {exc}\nTrace: {traceback.format_exc()}")
            return {'msg': f'Deletion of environment with id: {environment_id} failed. '
                           f'Exception: {str(exc)}'}, 500
        return {'msg': f"Environment with id: {environment_id} successfully deleted"}, 200


@ns.route('/all')
class GetAllEnvironments(Resource):
    @staticmethod
    @api.response(200, 'Info has been collected')
    def get():
        """
        Return All exist Environments
        """
        result = Environments.get_all_environments()

        return result, 200


@ns.route('/client/all')
class ClientAllEnvironments(Resource):
    @staticmethod
    @api.response(200, 'Info has been collected')
    @token_required()
    def get():
        """
        Return All exist Environments for client
        """
        result = Environments.get_all_environments_for_client()

        return result, 200


@ns.route('/<string:env_name>')
class GetEnvByName(Resource):

    @staticmethod
    def get(env_name):
        """
            Return Environment object with specified name
        """
        if not env_name:
            return {'msg': 'env_name should be specified'}, 404
        obj = Environments.get_env_by_name(env_name)
        if not obj:
            raise NotFound('object with env_name is not found')
        result = environments.dump(obj.dict())
        return {"msg": result}, 200
