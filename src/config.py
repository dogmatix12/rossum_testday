import os
from functools import cached_property

import requests
from dotenv import dotenv_values
from requests.adapters import HTTPAdapter
from urllib3 import Retry


class Config:
    def __init__(self):
        ...

    @cached_property
    def http_session(self) -> requests.Session:
        retry_strategy = Retry(
            total=4,  # maximum number of retries
            status_forcelist=[
                403,
                429,
                500,
                502,
                503,
                504,
            ],  # the HTTP status codes to retry on
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)

        return session

    @cached_property
    def _config(self) -> dict:
        config = {
            **{
                "ROSSUM_BASE_URL": "https://<example>.rossum.app",
                "ROSSUM_AUTH_TOKEN": "<your_auth_token>",
                "XML_ENCODING": "utf-8",
                "TARGET_ENDPOINT": "https://www.postb.in/XXXX-YYYY-ZZZZ",
            },
            **dotenv_values(".env_default"),
            **os.environ,
        }
        return config

    def __getattr__(self, key) -> str | None:
        key_upper = key.upper()

        if key_upper not in self._config.keys():
            raise KeyError

        return self._config.get(key_upper)
