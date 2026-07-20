import enum


class DocumentType(str, enum.Enum):
    CC = "CC"
    CE = "CE"
    TI = "TI"
    PASSPORT = "PASSPORT"


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    UNKNOWN = "UNKNOWN"


class PetSex(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    UNKNOWN = "UNKNOWN"


class PetSize(str, enum.Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class NotificationType(str, enum.Enum):
    NEW_MESSAGE = "NEW_MESSAGE"
    FOUND_MATCH = "FOUND_MATCH"
    SYSTEM = "SYSTEM"


class LostReportStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    FOUND = "FOUND"
    CLOSED = "CLOSED"


class FoundReportStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    MATCHED = "MATCHED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class ImageEntityType(str, enum.Enum):
    USER_PROFILE = "USER_PROFILE"
    PET = "PET"
    LOST_REPORT = "LOST_REPORT"
    FOUND_REPORT = "FOUND_REPORT"
    MESSAGE = "MESSAGE"
