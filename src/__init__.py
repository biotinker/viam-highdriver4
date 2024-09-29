"""
This file registers the model with the Python SDK.
"""

from viam.components.motor import Motor
from viam.resource.registry import Registry, ResourceCreatorRegistration

from .highdriver import HIGHDRIVER

Registry.register_resource_creator(Motor.SUBTYPE, HIGHDRIVER.MODEL, ResourceCreatorRegistration(HIGHDRIVER.new, HIGHDRIVER.validate))
