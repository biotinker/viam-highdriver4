from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, cast
from typing_extensions import Self

from viam.module.types import Reconfigurable
from viam.proto.common import ResourceName
from viam.proto.app.robot import ComponentConfig
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from viam.components.board import Board
from viam.components.motor import Motor
from viam.components.generic import Generic
from viam.logging import getLogger
from viam.utils import struct_to_dict, dict_to_struct, ValueTypes

import statistics
import asyncio
from smbus import SMBus

LOGGER = getLogger(__name__)

# Registers
default_address = 0x78

i2c_devideid = 0x00
i2c_powermode = 0x01
i2c_frequency = 0x02
i2c_shape = 0x03
i2c_boost = 0x04
i2c_audio = 0x05
i2c_p1voltage = 0x06
i2c_p2voltage = 0x07
i2c_p3voltage = 0x08
i2c_p4voltage = 0x09
i2c_updatedvoltage = 0x0A

class HIGHDRIVER(Motor, Reconfigurable):
    MODEL: ClassVar[Model] = Model(ModelFamily("biotinker", "motor"), "highdriver")

    # Constructor
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        motor = cls(config.name)
        motor.reconfigure(config, dependencies)
        return motor

    # Validates JSON Configuration
    @classmethod
    def validate(cls, config: ComponentConfig):
        i2c_bus = config.attributes.fields["i2c_bus"].string_value
        if i2c_bus == "":
            raise Exception("An i2c_bus must be defined")
        index = int(config.attributes.fields["index"].number_value)
        if index != 1 and index != 2 and index != 3 and index != 4:
            raise Exception("index must be 1, 2, 3, or 4")
        
        return

    # Handles attribute reconfiguration
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        # ~ i2c_bus_idx = config.attributes.fields["i2c_bus"].number_value
        index = config.attributes.fields["index"].number_value
        freq = config.attributes.fields["frequency"].number_value
        freq = 255 - int((freq / 800) * 255)
        i2c_bus_idx = 1
        # ~ index = 1
        self.i2c_bus = SMBus(i2c_bus_idx)
        if index == 1:
            self.v_idx = i2c_p1voltage
        if index == 2:
            self.v_idx = i2c_p2voltage
        if index == 3:
            self.v_idx = i2c_p3voltage
        if index == 4:
            self.v_idx = i2c_p4voltage
        self.power = False
        
        self.address = default_address
        
        # update settings at the registers
        # TODO: make this configurable
        
        self.i2c_bus.write_byte_data(self.address, i2c_devideid, 0xb2)
        # ~ self.i2c_bus.write_byte_data(self.address, i2c_frequency, 0xaf)  # 400Hz freq
        self.i2c_bus.write_byte_data(self.address, i2c_frequency, freq)  # 400Hz freq
        # ~ self.i2c_bus.write_byte_data(self.address, i2c_shape, 0x47)  # square wave
        self.i2c_bus.write_byte_data(self.address, i2c_shape, 0x00)  # square wave
        # ~ self.i2c_bus.write_byte_data(self.address, i2c_boost, 0x80)  # 1/32 spread spectrum 800kHz
        self.i2c_bus.write_byte_data(self.address, i2c_boost, 0x00)  # 1/32 spread spectrum 800kHz
        self.i2c_bus.write_byte_data(self.address, i2c_audio, 0x00)  # disabled so set to default because it can't be used
        self.i2c_bus.write_byte_data(self.address, self.v_idx, 0x00)  # Turned off
        
        # ~ self.i2c_bus.write_byte_data(self.address, i2c_powermode, 0x01) # power on
        return

    """ Implement the methods the Viam RDK defines for the sensor API (rdk:component:sensor) """
    async def set_power(self, power: float, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, **kwargs):
        if power == 0:
            return await self.stop()
        if power < 0:
            power = power * -1
        if power > 1:
            power = 1
        power = 255-int(power * 31)
        self.i2c_bus.write_byte_data(self.address, i2c_powermode, 0x01) # power on
        self.i2c_bus.write_byte_data(self.address, self.v_idx, power)
        
        # updated voltage
        self.i2c_bus.write_byte_data(self.address, i2c_updatedvoltage, 0x01)
        self.power = True
        return

    async def go_for(self,rpm: float,revolutions: float,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs):
        return

    async def go_to(self,rpm: float,position_revolutions: float,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs):
        return
        
    async def set_rpm(self,rpm: float,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs):
        return
    
    async def reset_zero_position(self,offset: float,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs):
        return

    async def get_position(self,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs) -> float:
        return 0

    async def get_properties(self,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs) -> Motor.Properties:
        return

    async def stop(self,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs):
        self.power = False
        self.i2c_bus.write_byte_data(self.address, i2c_powermode, 0x00) # power off
        self.i2c_bus.write_byte_data(self.address, self.v_idx, 0x00)
        return

    async def is_powered(self,extra: Optional[Dict[str, Any]] = None,timeout: Optional[float] = None,**kwargs) -> tuple[bool, float]:
        return self.power, 0
    async def is_moving(self) -> bool:
        return self.power

    async def close(self):
        self.power = False
        self.i2c_bus.write_byte_data(self.address, i2c_powermode, 0x00)  # turn off
        
