"""Execution context for multi-service E2E test scenarios."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from harness.client import request
from harness.compose import fetch_service_logs, get_base_url, parse_json_logs, run_compose


@dataclass
class E2EContext:
    root: Path
    project: str
    env: dict
    identity_url: str
    events_url: str
    purchases_url: str
    admin_email: str
    admin_password: str
    admin_token: str
    events_secret: str
    purchases_secret: str
    csrf_secret: str
    rollback_ref: str | None = None
    state: dict = field(default_factory=dict)

    def resolve_base_url(self, target: str) -> str:
        target_lower = target.lower()
        if target_lower in ("identity", "identity-service"):
            return self.identity_url
        if target_lower in ("events", "events-service"):
            return self.events_url
        if target_lower in ("purchases", "compras", "compras-service"):
            return self.purchases_url
        return target

    def request(
        self,
        service: str,
        method: str,
        path: str,
        payload: dict | list | None = None,
        token: str | None = None,
        expected: int = 200,
        headers: dict | None = None,
    ):
        base = self.resolve_base_url(service)
        return request(
            base,
            method,
            path,
            payload=payload,
            token=token,
            expected=expected,
            headers=headers,
        )

    def register_user(self, email: str, role: str) -> tuple[str, dict]:
        account = self.request(
            "identity",
            "POST",
            "/auth/register",
            {"email": email, "password": self.admin_password, "role": role},
            expected=201,
        )
        tokens = self.request(
            "identity",
            "POST",
            "/auth/login",
            {"email": email, "password": self.admin_password},
            expected=200,
        )
        return account["account_id"], tokens

    def enable_organizer(self, account_id: str):
        return self.request(
            "identity",
            "PATCH",
            f"/admin/organizers/{account_id}/status",
            {"status": "habilitado"},
            token=self.admin_token,
            expected=200,
        )

    def compose(self, *args, capture: bool = False) -> str | None:
        return run_compose(self.root, self.project, self.env, *args, capture=capture)

    def refresh_urls(self):
        self.identity_url = get_base_url(self.root, self.project, self.env, "identity-service")
        self.events_url = get_base_url(self.root, self.project, self.env, "events-service")
        self.purchases_url = get_base_url(self.root, self.project, self.env, "compras-service")

    def fetch_logs(self, *services) -> str:
        svc_names = services or ("identity-service", "events-service", "compras-service")
        return fetch_service_logs(self.root, self.project, self.env, *svc_names)

    def parse_service_json_logs(self, service: str) -> list[dict]:
        logs = self.compose("logs", "--no-color", "--no-log-prefix", service, capture=True) or ""
        return parse_json_logs(logs)

    def get_all_secrets(self) -> list[str]:
        secrets = [
            self.admin_password,
            self.events_secret,
            self.purchases_secret,
            self.csrf_secret,
            self.admin_token,
        ]
        tokens = self.state.get("tokens", [])
        secrets.extend(tokens)
        return [s for s in secrets if s]

    def ensure_users(self):
        """Ensure default test users exist and are populated in context state."""
        if "organizer_id" not in self.state:
            org_id, org_tokens = self.register_user("organizer@example.com", "organizador")
            self.enable_organizer(org_id)
            self.state["organizer_id"] = org_id
            self.state["organizer_tokens"] = org_tokens
            self.state.setdefault("tokens", []).extend([org_tokens["access_token"], org_tokens["refresh_token"]])

        if "other_organizer_id" not in self.state:
            other_org_id, other_tokens = self.register_user("other@example.com", "organizador")
            self.enable_organizer(other_org_id)
            self.state["other_organizer_id"] = other_org_id
            self.state["other_tokens"] = other_tokens
            self.state.setdefault("tokens", []).extend([other_tokens["access_token"], other_tokens["refresh_token"]])

        if "customer_id" not in self.state:
            cust_id, cust_tokens = self.register_user("customer@example.com", "cliente")
            self.state["customer_id"] = cust_id
            self.state["customer_tokens"] = cust_tokens
            self.state.setdefault("tokens", []).extend([cust_tokens["access_token"], cust_tokens["refresh_token"]])

        if "other_customer_id" not in self.state:
            other_cust_id, other_cust_tokens = self.register_user("customer2@example.com", "cliente")
            self.state["other_customer_id"] = other_cust_id
            self.state["other_customer_tokens"] = other_cust_tokens
            self.state.setdefault("tokens", []).extend(
                [other_cust_tokens["access_token"], other_cust_tokens["refresh_token"]]
            )

    @staticmethod
    def build_event_payload(cupo: int = 100) -> dict:
        """Payload válido de evento con una modalidad general."""
        return {
            "nombre": "Integration event",
            "venue": "Test venue",
            "fecha": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "modalidades": [
                {
                    "nombre": "General",
                    "tipo": "general",
                    "precio": "1500.00",
                    "cupo": cupo,
                }
            ],
        }

    def create_event(self, cupo: int = 100, correlation_id: str | None = None) -> dict:
        """Crea un evento nuevo con el organizador por defecto."""
        self.ensure_users()
        headers = {"X-Correlation-Id": correlation_id} if correlation_id else None
        return self.request(
            "events",
            "POST",
            "/eventos",
            self.build_event_payload(cupo),
            token=self.state["organizer_tokens"]["access_token"],
            headers=headers,
            expected=201,
        )

    def ensure_event(self) -> dict:
        """Ensure an active event exists in context state for purchase testing."""
        self.ensure_users()
        if "event" not in self.state:
            event_corr = str(uuid.uuid4())
            self.state["event"] = self.create_event(correlation_id=event_corr)
            self.state["event_payload"] = self.build_event_payload()
            self.state["event_correlation"] = event_corr
        return self.state["event"]

    def ensure_purchase(self) -> dict:
        """Ensure a confirmed purchase exists in context state for conflict/isolation testing."""
        event = self.ensure_event()
        if "purchase" not in self.state:
            body = {
                "evento_id": event["id"],
                "modalidad_id": event["modalidades"][0]["id"],
            }
            key = {"Idempotency-Key": f"integration-key-{uuid.uuid4().hex[:8]}"}
            purchase_corr = str(uuid.uuid4())
            purchase = self.request(
                "purchases",
                "POST",
                "/compras",
                body,
                token=self.state["customer_tokens"]["access_token"],
                headers={**key, "X-Correlation-Id": purchase_corr},
                expected=201,
            )
            self.state["purchase"] = purchase
            self.state["purchase_body"] = body
            self.state["purchase_key"] = key
            self.state["purchase_correlation"] = purchase_corr
        return self.state["purchase"]
