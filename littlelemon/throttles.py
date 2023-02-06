from rest_framework.throttling import UserRateThrottle


class TenCallsPerMinute(UserRateThrottle):
    scope = 'ten'


class FiveCallsPerMinute(UserRateThrottle):
    scope = 'five'


class OneCallsPerMinute(UserRateThrottle):
    scope = 'one'