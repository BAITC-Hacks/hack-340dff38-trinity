from enum import StrEnum


class Role(StrEnum):
    STUDENT = "STUDENT"
    COMPANY = "COMPANY"
    ADMIN = "ADMIN"


class ProblemStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class SubmissionStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    WINNER = "WINNER"
    NOT_SELECTED = "NOT_SELECTED"


class ModerationStatus(StrEnum):
    CLEAN = "CLEAN"
    FLAGGED = "FLAGGED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    HIDDEN = "HIDDEN"
