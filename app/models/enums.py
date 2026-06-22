from enum import Enum


class GenderType(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class PatientStatus(str, Enum):
    STABLE = "Stable"
    CRITICAL = "Critical"
    SCHEDULED = "Scheduled"
    TESTING = "Testing"


class CognitiveDomain(str, Enum):
    ATTENTION = "Attention"
    MEMORY = "Memory"
    REASONING = "Reasoning"
    COORDINATION = "Coordination"
    PERCEPTION = "Perception"


class TaskId(str, Enum):
    CPT = "cpt"
    GO_NO_GO = "go-no-go"
    N_BACK = "n-back"
    TOWER_PUZZLE = "tower-puzzle"
    SHAPE_MATCH = "shape-match"
    WORD_RECALL = "word-recall"
    DIVIDED_ATTENTION = "divided-attention"
    UPDATING = "updating"


class SessionStatus(str, Enum):
    INITIALIZED = "initialized"
    STARTED = "started"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QuestionnaireSlug(str, Enum):
    PHQ_9 = "phq-9"
    GAD_7 = "gad-7"
    PSS_10 = "pss-10"


class ScoreStatus(str, Enum):
    ABOVE_AVERAGE = "Above Average"
    AVERAGE = "Average"
    BELOW_AVERAGE = "Below Average"


class LanguageCode(str, Enum):
    EN = "en"
    HI = "hi"
    MR = "mr"
    TE = "te"


class AuditActorType(str, Enum):
    DOCTOR = "doctor"
    PATIENT = "patient"
    SYSTEM = "system"


class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    PATIENT_CREATE = "patient_create"
    PATIENT_UPDATE = "patient_update"
    PATIENT_DELETE = "patient_delete"
    SESSION_START = "session_start"
    SESSION_COMPLETE = "session_complete"
    SESSION_ABANDON = "session_abandon"
    TASK_SUBMIT = "task_submit"
    QUESTIONNAIRE_SUBMIT = "questionnaire_submit"
    REPORT_GENERATE = "report_generate"
    REPORT_VIEW = "report_view"
    OTP_REQUEST = "otp_request"
    OTP_VERIFY = "otp_verify"
    TOKEN_REFRESH = "token_refresh"


class OtpPurpose(str, Enum):
    EMAIL_VERIFY = "email_verify"
    PHONE_VERIFY = "phone_verify"
    LOGIN = "login"


class OtpChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"

