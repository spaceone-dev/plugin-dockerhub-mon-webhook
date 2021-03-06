import logging
import hashlib
from datetime import datetime
from spaceone.core.manager import BaseManager
from spaceone.monitoring.model.event_model import EventModel
from spaceone.monitoring.error.event import *


_LOGGER = logging.getLogger(__name__)


class EventManager(BaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse(self, options: dict, raw_data: dict) -> list:
        """
        raw_data example)
            {
              "callback_url": "https://registry.hub.docker.com/u/nigasa12/prs-manager/hook/20a4ccf24e26442fbed482baa234c373/",
              "push_data": {
                "pusher": "spaceoneadmin",
                "pushed_at": 1656906946,
                "tag": "v1.0.0",
                "images": [],
                "media_type": "application/vnd.docker.distribution.manifest.v2+json"
              },
              "repository": {
                "status": "Active",
                "namespace": "spaceone",
                "name": "plugin-dockerhub-mon-webhook",
                "repo_name": "spaceone/plugin-dockerhub-mon-webhook",
                "repo_url": "https://hub.docker.com/r/spaceone/plugin-dockerhub-mon-webhook",
                "description": "",
                "full_description": null,
                "star_count": 0,
                "comment_count": 0,
                "is_private": false,
                "is_trusted": false,
                "is_official": false,
                "owner": "spaceoneadmin",
                "date_created": 1656296314
              }
            }
        """

        base_info = self._generate_base_info(raw_data)
        generated_data = self._generate_data(base_info)

        _LOGGER.debug(f'[parse] {generated_data}')

        return [self._validate_data(generated_data)]

    def _generate_base_info(self, raw_data: dict) -> dict:

        return {
            'repo_name': raw_data['repository']['repo_name'],
            'repo_url': raw_data['repository']['repo_url'],
            'tag': raw_data['push_data']['tag'],
            'event_key': self._get_event_key(raw_data['repository']['repo_name'], raw_data['push_data']['tag']),
            'namespace': raw_data['repository']['namespace'],
            'pushed_at': datetime.fromtimestamp(raw_data['push_data']['pushed_at']).isoformat(),
            'pusher': raw_data['push_data']['pusher']
        }

    @staticmethod
    def _validate_data(data: dict) -> dict:
        try:
            event_model = EventModel(data, strict=False)
            event_model.validate()
            return event_model.to_native()

        except Exception as e:
            raise ERROR_EVENT_PARSE()

    @staticmethod
    def _generate_data(info: dict) -> dict:
        event_key = info['event_key']
        repo_name = info['repo_name']
        tag = info['tag']
        title = f'New image tag({tag}) has been pushed to {repo_name}'
        repo_url = info['repo_url']
        namespace = info['namespace']
        occurred_at = info['pushed_at']
        pusher = info['pusher']

        return {
            'event_key': event_key,
            'event_type': 'ALERT',  # ALERT only, docker hub event doesn't have RECOVERY type
            'title': title,
            'description': title,
            'severity': 'INFO',
            'rule': '',
            'resource': {
                'name': f'{repo_name}:{tag}'
            },
            'additional_info': {
                'repo_url': repo_url,
                'namespace': namespace,
                'repo_name': repo_name,
                'pusher': pusher,
                'tag': tag
            },
            'occurred_at': occurred_at
        }

    @staticmethod
    def _get_event_key(repo_name: str, tag: str):
        """
        Generate the Index Key through Hashing
            {repo_name}:{tag}
        """

        raw_event_key = f'{repo_name}:{tag}'
        hash_object = hashlib.md5(raw_event_key.encode())
        md5_hash = hash_object.hexdigest()

        return md5_hash
