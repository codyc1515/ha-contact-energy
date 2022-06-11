"""Contact Energy API"""
import logging
from datetime import datetime, timedelta
import requests
import json

_LOGGER = logging.getLogger(__name__)

class ContactEnergyApi:
    def __init__(self, email, password):
        self._api_token = ''
        self._contract = ''
        self._url_base = 'https://api.contact-digital-prod.net'
        self._api_key = 'z840P4lQCH9TqcjC9L2pP157DZcZJMcr5tVQCvyx'
        self._email = email
        self._password = password
            
    def get_usage(self, year, month, day):
        headers = {
            "x-api-key": self._api_key,
            "Authorization": self._api_token
        }
        response = requests.post(self._url_base + "/usage/" + self._contract + "?interval=hourly&from=" + year + "-" + (month.zfill(2)) + "-" + (day.zfill(2)) + "&to=" + year + "-" + (month.zfill(2)) + "-" + (day.zfill(2)), headers=headers)
        data = {}
        if response.status_code == requests.codes.ok:
            data = response.json()
            if not data:
                _LOGGER.warning('Fetched usage data for %s/%s/%s, but got nothing back', year, month, day)
            return data
        else:
            _LOGGER.error('Failed to fetch usage data for %s/%s/%s', year, month, day)
            return data

    def get_facility_id(self):
        headers = {
            "x-api-key": self._api_key,
            "Authorization": self._api_token
        }
        result = requests.post(self._url_base + "/mcfu/profile", headers=headers)
        if result.status_code == requests.codes.ok:
            _LOGGER.debug('Login is valid')
            data = result.json()
            self._contract = data['customer']['account']['contracts'][0]['id']
        else:
            _LOGGER.error('Failed to fetch facility id %s', result.text)

    def check_auth(self):
        """Check to see if our API Token is valid."""
        if self._api_token:
            _LOGGER.debug('Login is valid')
            return True
        else: 
            if self.login() == False:
                _LOGGER.debug(result.text)
                return False
            return True
        
    def login(self):
        """Login to the Contact Energy API."""
        result = False
        headers = {
            "x-api-key": self._api_key
        }
        data = {
            "username": self._email,
            "password": self._password
        }
        loginResult = requests.post(self._url_base + "/login", json=data, headers=headers)
        if loginResult.status_code == requests.codes.ok:
            jsonResult = loginResult.json()
            self._api_token = jsonResult['token']
            _LOGGER.debug('Successfully logged in')
            self.get_facility_id()
            result = True           
        else:
            _LOGGER.error(loginResult.text)
        return result
