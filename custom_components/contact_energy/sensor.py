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
    vol.Optional(CONF_USAGE): cv.boolean,
    vol.Optional(CONF_SOLD): cv.boolean,
    vol.Optional(CONF_PRICES): cv.boolean,
    vol.Optional(CONF_USAGE_DAYS, default=10): cv.positive_int,
    vol.Optional(CONF_SOLD_MEASURE, default=2): cv.positive_int,
    vol.Optional(CONF_SOLD_DAILY, default=False): cv.boolean,
    vol.Optional(CONF_DATE_FORMAT, default='%d %b %Y'): cv.string,
    vol.Optional(CONF_TIME_FORMAT, default='%H:%M'): cv.string,
    vol.Optional(CONF_SHOW_HOURLY, default=False): cv.boolean,
    vol.Optional(CONF_HOURLY_OFFSET_DAYS, default=1): cv.positive_int,
})

SCAN_INTERVAL = timedelta(hours=3)

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    
    date_format = config.get(CONF_DATE_FORMAT)
    time_format = config.get(CONF_TIME_FORMAT)
    show_usage = config.get(CONF_USAGE)
    show_sold = config.get(CONF_SOLD)
    show_prices = config.get(CONF_PRICES)
    usage_days = config.get(CONF_USAGE_DAYS)
    sold_measure = config.get(CONF_SOLD_MEASURE)
    show_hourly = config.get(CONF_SHOW_HOURLY)
    sold_daily = config.get(CONF_SOLD_DAILY)
    hourly_offset_days = config.get(CONF_HOURLY_OFFSET_DAYS)
    if hourly_offset_days > usage_days:
        hourly_offset_days = usage_days
        
    api = ContactEnergyApi(email, password)

    _LOGGER.debug('Setting up sensor(s)...')

    sensors = []
    #if show_usage:
    sensors .append(ContactEnergyUsageSensor(SENSOR_USAGE_NAME, api, usage_days, show_hourly, hourly_offset_days, date_format, time_format))
    #if show_sold:
    #    sensors .append(ContactEnergySoldSensor(SENSOR_SOLD_NAME, api, sold_measure, sold_daily, date_format))
    #if show_prices:
    #    sensors .append(ContactEnergyPricesSensor(SENSOR_PRICES_NAME, api, date_format))
    async_add_entities(sensors, True)

class ContactEnergyUsageSensor(SensorEntity):
    def __init__(self, name, api, usage_days, show_hourly, hourly_offset_days, date_format, time_format):
        self._name = name
        self._icon = "mdi:meter-electric"
        self._state = 0
        self._unit_of_measurement = 'kWh'
        self._unique_id = DOMAIN
        self._device_class = "energy"
        self._state_class = "total"
        self._state_attributes = {}
        self._usage_days = usage_days
        self._show_hourly = show_hourly
        self._date_format = date_format
        self._time_format = time_format
        self._hourly_offset_days = hourly_offset_days
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
            data = []
            kWhStatistics = []
            kWhRunningSum = 0
            
            freeKWhStatistics = []
            freeKWhRunningSum = 0
            
            for i in range(self._usage_days):
                previous_day = today - timedelta(days=self._usage_days - i)
                response = self._api.get_usage(str(previous_day.year), str(previous_day.month), str(previous_day.day))
                if response:
                    if response[0]:
                        for point in response:
                            if point['value']:
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
                                
                    usage = self.make_attribute(previous_day, today, response)
                    if usage:
                        data.append(usage)
            
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
            
            self._state_attributes['days'] = data
        else:
            _LOGGER.error('Unable to log in')
            
    def make_attribute(self, date, today, response):
        yesterday = today - timedelta(days = 1)
        daily_usage = 0.000
        data = {}
        if response[0]:
            
            priceStatistics = []
            for point in response:
                if point['value'] and date:
                    daily_usage += float(point['value']) - float(point['unchargedValue'])
                    
                    data['date'] = date.strftime(self._date_format)
                    data['usage'] = daily_usage
                    
                    if (date == yesterday) and daily_usage != 0:
                        self._state = data['usage']
            else:
                _LOGGER.debug('No usage data available for today')
                # %1', today)
            
        else:
            _LOGGER.warning('No data available for')
            # %1', today)
        return data
