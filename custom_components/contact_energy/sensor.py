"""Contact Energy sensors"""
from datetime import datetime, timedelta

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.const import ENERGY_KILO_WATT_HOUR, CURRENCY_DOLLAR
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    clear_statistics,
    day_start_end,
    get_last_statistics,
    list_statistic_ids,
    month_start_end,
    statistics_during_period,
)
import homeassistant.util.dt as dt_util
import math

from .api import ContactEnergyApi

from .const import (
    DOMAIN,
    SENSOR_USAGE_NAME,
    SENSOR_SOLD_NAME,
    SENSOR_PRICES_NAME,
    CONF_USAGE,
    CONF_SOLD,
    CONF_PRICES,
    CONF_DATE_FORMAT, 
    CONF_TIME_FORMAT, 
    CONF_USAGE_DAYS,
    CONF_SOLD_MEASURE, 
    CONF_SHOW_HOURLY, 
    CONF_SOLD_DAILY, 
    CONF_HOURLY_OFFSET_DAYS,
    MONITORED_CONDITIONS_DEFAULT
)

NAME = DOMAIN
ISSUEURL = "https://github.com/codyc1515/hacs_contact_energy/issues"

STARTUP = f"""
-------------------------------------------------------------------
{NAME}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUEURL}
-------------------------------------------------------------------
"""

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_USAGE_DAYS, default=10): cv.positive_int,
})

SCAN_INTERVAL = timedelta(hours=3)

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    
    usage_days = config.get(CONF_USAGE_DAYS)
        
    api = ContactEnergyApi(email, password)

    _LOGGER.debug('Setting up sensor(s)...')

    sensors = []
    sensors.append(ContactEnergyUsageSensor(SENSOR_USAGE_NAME, api, usage_days))
    async_add_entities(sensors, True)

class ContactEnergyUsageSensor(SensorEntity):
    def __init__(self, name, api, usage_days):
        self._name = name
        self._icon = "mdi:meter-electric"
        self._state = 0
        self._unit_of_measurement = 'kWh'
        self._unique_id = DOMAIN
        self._device_class = "energy"
        self._state_class = "total"
        self._state_attributes = {}
        self._usage_days = usage_days
        self._api = api

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._state_attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement
    
    @property
    def state_class(self):
        """Return the state class."""
        return self._state_class
    
    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class
        
    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id
        
    def update(self):
        _LOGGER.debug('Beginning usage update')
        if self._api.check_auth():
            # Get todays date
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            _LOGGER.debug('Fetching usage data')
            
            kWhStatistics = []
            kWhRunningSum = 0
            
            freeKWhStatistics = []
            freeKWhRunningSum = 0
            
            for i in range(self._usage_days):
                previous_day = today - timedelta(days=self._usage_days - i)
                response = self._api.get_usage(str(previous_day.year), str(previous_day.month), str(previous_day.day))
                if response and response[0]:
                    for point in response:
                        if point['value']:
                            # If the off peak value is '0.00' then the energy is free.
                            # HASSIO statistics requires us to add values as a sum of all previous values. 
                            if point['offpeakValue'] == '0.00':
                                kWhRunningSum = kWhRunningSum + float(point['value'])
                            else:
                                freeKWhRunningSum = freeKWhRunningSum + float(point['value'])
                            
                            freeKWhStatistics.append(StatisticData(
                                start=datetime.strptime(point['date'], '%Y-%m-%dT%H:%M:%S.%f%z'),
                                sum=freeKWhRunningSum
                            ))
                            kWhStatistics.append(StatisticData(
                                start=datetime.strptime(point['date'], '%Y-%m-%dT%H:%M:%S.%f%z'),
                                sum=kWhRunningSum
                            ))

            kWhMetadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name="ContactEnergy",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:energy_consumption",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR
            )
            async_add_external_statistics(self.hass, kWhMetadata, kWhStatistics)
            
            freeKWHMetadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name="FreeContactEnergy",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:free_energy_consumption",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR
            )
            async_add_external_statistics(self.hass, freeKWHMetadata, freeKWhStatistics)
        else:
            _LOGGER.error('Unable to log in')