"""
Manage session states
"""

import streamlit as st
import logging 
from enum import Enum
from typing import Any, Optional, TypeVar
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ValidationError
from src.ui.user_notifier import fail

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ==========================
# ENUMS
# ==========================
class Team(Enum):
    """
    Represents the different teams in the simulation.
    """
    BLUE = "Blue"
    RED = "Red"

# ==========================
# Models
# ==========================

# Provides clarification on the type of SensorDraft for type checking and validation. Prevents SensorDraft from being used directly without specifying a subclass.
SensorDraftT = TypeVar("SensorDraftT", bound="SensorDraft")
PlatformDraftT = TypeVar("PlatformDraftT", bound="PlatformDraft")


class SensorDraft(BaseModel):
    """
    Represents a draft of a sensor being created in the Streamlit application.
    """
    display_name: str = ""
    x_values: list[float] = Field(default_factory=list)
    pod: list[float] = Field(default_factory=list)
    sensor_type: str
    k: int = 3 
    n: int = 5

    @classmethod
    def create_from_dict(cls: type[SensorDraftT], data: dict[str, Any]) -> SensorDraftT:
        """
        Creates a sensor draft instance from a dictionary and validates it.
        """
        try:
            logger.info("Creating %s from dict: %s", cls.__name__, data)
            return cls.model_validate(data)
        except ValidationError:
            logger.exception("Error creating %s from dict", cls.__name__)
            raise


class GenericSensorDraft(SensorDraft):
    """
    Represents a draft of a generic sensor being created in the Streamlit application.
    """
    fov_start_angle: float = 0.0
    fov_end_angle: float = 360.0
    sensor_type: str = "generic"


class SpecificSensorDraft(SensorDraft):
    """
    Represents a draft of a specific sensor being created in the Streamlit application.
    """
    sensor_type: str = "specific"


class PlatformDraft(BaseModel):
    """
    Represents a draft of a platform being created in the Streamlit application.
    """
    display_name: str = ""
    speed: int = 0 # mps / metres per second
    team: Team = Team.BLUE
    movement_type: str = "Random Walk"
    movement_config: dict[str, Any] = Field(default_factory=dict)
    sensors : Optional[list[SensorDraft]] = None  # List of sensors, can be None if not specified

    @classmethod
    def create_from_dict(cls: type[PlatformDraftT], data: dict[str, Any]) -> PlatformDraftT:
        """
        Creates a sensor draft instance from a dictionary and validates it.
        """
        try:
            logger.info("Creating %s from dict: %s", cls.__name__, data)
            platform = cls.model_validate(data)
            for p in st.session_state.platform_draft_list:
                if p.display_name == platform.display_name:
                    logger.warning("Platform with display name '%s' already exists in session state.", platform.display_name)
                    fail("platform_creation_failed", f"Platform with display name '{platform.display_name}' already exists." )
                    raise ValueError(f"Platform with display name '{platform.display_name}' already exists.")

            return platform
        except ValidationError:
            logger.exception("Error creating %s from dict", cls.__name__)
            raise

# =================================
# Platform Movement Types
# =================================
class IntruderEndCondition(Enum):
    """
    Represents the end conditions for an intruder search movement type.
    """
    CROSS_BARRIER = "Cross Barrier"
    CROSS_WORLD = "Cross World"

@dataclass
class Waypoint:
    """
    Represents a waypoint with x and y coordinates.
    """
    x: float
    y: float    

@dataclass
class RandomWalkMovement:
    """
    Represents a random walk movement type for a platform.
    """
    pass    

@dataclass
class IntruderSearchMovement:
    """
    Represents an intruder search movement type for a platform.
    """
    start_distance: float = 0.0
    end_condition: IntruderEndCondition = IntruderEndCondition.CROSS_WORLD

@dataclass
class BarrierPatrollerMovement:
    """
    Represents a barrier patroller movement type for a platform.
    """
    start_x_pos: float = 0.0
    start_y_pos: float = 0.0
    length: float = 100.0
    height: float = 100.0

@dataclass
class UserDefinedWaypointsMovement:
    """
    Represents a user-defined waypoints movement type for a platform.
    """
    waypoints: list[Waypoint] = field(default_factory=list)  # List of waypoints representing user-defined path


# =================================
# Session State Management
# =================================

def establish_session_state() -> None:
    """
    Establishes the session state for the Streamlit application.
    """
    session_defaults = {
        # Monte Carlo simulation state
        "number_of_replications": 10,
        "time_limit": 10,
        "run_simulation": False,
        # Platform creation state
        "platform_created": False,
        "platform_draft": {},
        "platform_draft_list": [],
        # Sensor creation state
        "number_of_sensors": 0,
        "sensor_draft_list": [],
        "sensor_edit_index": -1,
        "sensor_save_message": "",
    }

    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value





    