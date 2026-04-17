from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

try:
    from curl_cffi import requests as cffi_requests
    _IMPERSONATE = "chrome124"
except ImportError:
    raise RuntimeError("curl_cffi not installed. Run: pip3 install curl_cffi")

BASE_URL = "https://claude.ai"
ORGS_ENDPOINT = f"{BASE_URL}/api/organizations"


class AuthError(Exception):
    pass


class FetchError(Exception):
    pass


@dataclass
class UsageData:
    five_hour_pct: Optional[float]       # 0–100
    five_hour_resets_at: Optional[datetime]
    seven_day_pct: Optional[float]       # 0–100
    seven_day_resets_at: Optional[datetime]
    plan_name: str = "Unknown"

    def time_until_reset(self, resets_at: Optional[datetime]) -> Optional[str]:
        if resets_at is None:
            return None
        now = datetime.now(timezone.utc)
        if resets_at <= now:
            return "now"
        delta = resets_at - now
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes = rem // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def five_hour_reset_str(self) -> Optional[str]:
        return self.time_until_reset(self.five_hour_resets_at)

    @property
    def seven_day_reset_str(self) -> Optional[str]:
        return self.time_until_reset(self.seven_day_resets_at)

    @property
    def primary_pct(self) -> Optional[float]:
        """The most constraining (highest) utilization across active windows."""
        candidates = [p for p in (self.five_hour_pct, self.seven_day_pct) if p is not None]
        return max(candidates) if candidates else None


class ClaudeClient:
    def __init__(self, session_key: str):
        self._session_key = session_key
        self._session = cffi_requests.Session(impersonate=_IMPERSONATE)
        self._session.headers.update({
            "Cookie": f"sessionKey={session_key}",
            "Accept": "application/json",
            "Referer": "https://claude.ai/",
        })
        self._org_id: Optional[str] = None

    def fetch_usage(self) -> UsageData:
        try:
            org_id = self._get_org_id()
            resp = self._session.get(
                f"{ORGS_ENDPOINT}/{org_id}/usage", timeout=10
            )
            if resp.status_code in (401, 403):
                raise AuthError("Session expired. Please re-login to Claude.ai in Chrome.")
            if not resp.ok:
                raise FetchError(f"Usage endpoint returned {resp.status_code}")

            return self._parse(resp.json())
        except (AuthError, FetchError):
            raise
        except Exception as e:
            raise FetchError(f"Unexpected error: {e}") from e

    def _get_org_id(self) -> str:
        if self._org_id:
            return self._org_id
        resp = self._session.get(ORGS_ENDPOINT, timeout=10)
        if resp.status_code in (401, 403):
            raise AuthError("Session expired. Please re-login to Claude.ai in Chrome.")
        if not resp.ok:
            raise FetchError(f"Organizations endpoint returned {resp.status_code}")
        orgs = resp.json()
        org = orgs[0] if isinstance(orgs, list) else orgs
        org_id = org.get("uuid") or org.get("id")
        if not org_id:
            raise FetchError("Could not determine organization ID")
        self._org_id = org_id
        return self._org_id

    @staticmethod
    def _parse(data: dict) -> UsageData:
        five_h = data.get("five_hour") or {}
        seven_d = data.get("seven_day") or {}

        return UsageData(
            five_hour_pct=five_h.get("utilization"),
            five_hour_resets_at=_parse_dt(five_h.get("resets_at")),
            seven_day_pct=seven_d.get("utilization"),
            seven_day_resets_at=_parse_dt(seven_d.get("resets_at")),
        )


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
