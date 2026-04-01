import enum


class RoleCode(str, enum.Enum):
    CUSTOMER  = "customer"
    AGENT     = "agent"
    TEAM_LEAD = "team_lead"
    ADMIN     = "admin"


class TierName(str, enum.Enum):
    STARTER    = "starter"
    STANDARD   = "standard"
    ENTERPRISE = "enterprise"


class PreferredContact(str, enum.Enum):
    EMAIL  = "email"
    IN_APP = "in_app"
