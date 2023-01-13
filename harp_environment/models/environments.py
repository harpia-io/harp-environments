import traceback
from flask import abort
from microservice_template_core import db
import datetime
import json
from marshmallow import Schema, fields
from microservice_template_core.tools.logger import get_logger

logger = get_logger()


class Environments(db.Model):
    __tablename__ = 'environments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    env_name = db.Column(db.VARCHAR(70), nullable=False, unique=True)
    env_settings = db.Column(db.Text(4294000000), default='{}')
    available_for_users_id = db.Column(db.Text(4294000000), default='{}')
    create_ts = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow(), nullable=False)
    last_update_ts = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow(), nullable=False)

    def __repr__(self):
        return f"{self.id}_{self.env_name}"

    def dict(self):
        return {
            'id': self.id,
            'env_name': self.env_name,
            'env_settings': json.loads(self.env_settings),
            'available_for_users_id': json.loads(self.available_for_users_id),
            'create_ts': self.create_ts,
            'last_update_ts': self.last_update_ts
        }

    def update_obj(self, data, environment_id):
        same_name_envs = Environments.query.filter_by(env_name=data['env_name']).all()
        if same_name_envs:
            if len(same_name_envs) == 1 and same_name_envs[0].id == self.id:
                pass
            else:
                abort(400, "Environment with the same name is already exist")

        if 'env_settings' in data:
            data['env_settings'] = json.dumps(data['env_settings'])

        if 'available_for_users_id' in data:
            data['available_for_users_id'] = json.dumps(data['available_for_users_id'])

        if environment_id:
            self.query.filter_by(id=environment_id).update(data)

        db.session.commit()

    @classmethod
    def add(cls, data):
        exist_env = cls.query.filter_by(env_name=data['env_name']).one_or_none()
        if exist_env:
            raise ValueError(f"Environment with name: {data['env_name']} already exist")
        new_obj = Environments(
            env_name=data['env_name'],
            env_settings=json.dumps(data['env_settings']),
            available_for_users_id=json.dumps(data['available_for_users_id'])
        )
        new_obj = new_obj.save()
        return new_obj

    @classmethod
    def get_all_environments(cls):
        all_environments = {}
        get_all_environments = cls.query.filter_by().all()

        for single_env in get_all_environments:
            all_environments[int(single_env.dict()['id'])] = single_env.dict()['env_name']

        return all_environments

    @classmethod
    def get_all_environments_for_client(cls):
        all_environments = []
        get_all_environments = cls.query.filter_by().all()

        for single_env in get_all_environments:
            all_environments.append({'name': single_env.dict()['env_name'], 'id': int(single_env.dict()['id'])})

        return all_environments

    @classmethod
    def obj_exist(cls, env_id):
        return cls.query.filter_by(id=env_id).one_or_none()

    @classmethod
    def get_env_by_name(cls, environment_name):
        return cls.query.filter_by(env_name=environment_name).one_or_none()

    def save(self):
        try:
            db.session.add(self)
            db.session.flush()
            db.session.commit()

            return self
        except Exception as exc:
            logger.critical(
                msg="Can't commit changes to DB",
                extra={'tags': {
                    'exception': str(exc),
                    'traceback': traceback.format_exc()
                }}
            )
            db.session.rollback()

    def delete_obj(self):
        db.session.delete(self)
        db.session.commit()


# ###### SCHEMAS #######


class EnvSet(Schema):
    env_des = fields.Str(required=True)
    proc_id = fields.Int()


class EnvironmentSchema(Schema):
    id = fields.Int(dump_only=True)
    env_name = fields.Str(required=True)
    env_settings = fields.Dict(
        description=fields.Str(),
        default_scenario=fields.Int(required=True)
    )
    available_for_users_id = fields.Dict(
        visible_only=fields.List(fields.Int),
        hidden=fields.List(fields.Int)
    )
    create_ts = fields.DateTime("%Y-%m-%d %H:%M:%S", dump_only=True)
    last_update_ts = fields.DateTime("%Y-%m-%d %H:%M:%S", dump_only=True)