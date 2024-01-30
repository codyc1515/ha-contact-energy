"""Contact Energy API."""

import logging
import requests

_LOGGER = logging.getLogger(__name__)


class ContactEnergyApi:
    """Class for Contact Energy API."""

    def __init__(self, email, password):
        """Initialise Contact Energy API."""
        self._api_token = ""
        self._api_session = ""
        self._contractId = ""
        self._accountId = ""
        self._url_base = "https://api.contact-digital-prod.net"
        self._api_key = "z840P4lQCH9TqcjC9L2pP157DZcZJMcr5tVQCvyx"
        self._email = email
        self._password = password

    def login(self):
        """Login to the Contact Energy API."""
        result = False
        headers = {"x-api-key": self._api_key}
        data = {"username": self._email, "password": self._password}
        loginResult = requests.post(
            self._url_base + "/login/v2", json=data, headers=headers
        )
        if loginResult.status_code == requests.codes.ok:
            jsonResult = loginResult.json()
            self._api_token = jsonResult["token"]
            _LOGGER.debug("Logged in")
            self.refresh_session()
            result = True
        else:
            _LOGGER.error(
                "Failed to login - check the username and password are valid",
                loginResult.text,
            )
            return False
        return result

    def refresh_session(self):
        """Refresh the session."""
        result = False
        headers = {"x-api-key": self._api_key}
        data = {"username": self._email, "password": self._password}
        loginResult = requests.post(
            self._url_base + "/login/v2/refresh", json=data, headers=headers
        )
        if loginResult.status_code == requests.codes.ok:
            jsonResult = loginResult.json()
            self._api_session = jsonResult["session"]
            _LOGGER.debug("Refreshed session")
            self.get_accounts()
            result = True
        else:
            _LOGGER.error(
                "Failed to refresh session - check the username and password are valid",
                loginResult.text,
            )
            return False
        return result

    def get_accounts(self):
        """Get the first account that we see."""
        headers = {"x-api-key": self._api_key, "session": self._api_session}
        result = requests.get(
            self._url_base + "/customer/v2?fetchAccounts=true", headers=headers
        )
        if result.status_code == requests.codes.ok:
            _LOGGER.debug("Retrieved accounts")
            data = result.json()
            self._accountId = data["accounts"][0]["id"]
            self._contractId = data["accounts"][0]["contracts"][0]["contractId"]
        else:
            _LOGGER.error("Failed to fetch customer accounts %s", result.text)
            return False

    def get_usage(self, year, month, day):
        """Update our usage data."""
        headers = {"x-api-key": self._api_key, "authorization": self._api_token}
        response = requests.post(
            self._url_base
            + "/usage/v2/"
            + self._contractId
            + "?ba="
            + self._accountId
            + "&interval=hourly&from="
            + year
            + "-"
            + (month.zfill(2))
            + "-"
            + (day.zfill(2))
            + "&to="
            + year
            + "-"
            + (month.zfill(2))
            + "-"
            + (day.zfill(2)),
            headers=headers,
        )
        data = {}
        if response.status_code == requests.codes.ok:
            data = response.json()
            if not data:
                _LOGGER.info(
                    "Fetched usage data for %s/%s/%s, but got nothing back",
                    year,
                    month,
                    day,
                )
            return data
        else:
            _LOGGER.error("Failed to fetch usage data for %s/%s/%s", year, month, day)
            _LOGGER.debug(response)
            return False
