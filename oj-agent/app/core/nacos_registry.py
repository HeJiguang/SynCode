from dataclasses import dataclass, field
import json
import logging
from threading import Event, Thread

import httpx

from app.core.config import AgentSettings


LOGGER = logging.getLogger(__name__)
NACOS_HTTP_TIMEOUT_SECONDS = 10.0


@dataclass
class NacosRegistry:
    settings: AgentSettings
    _heartbeat_stop: Event = field(default_factory=Event, init=False, repr=False)
    _heartbeat_thread: Thread | None = field(default=None, init=False, repr=False)

    def register(self) -> None:
        if not self.settings.nacos_enabled or not self.settings.nacos_server_addr:
            return
        with httpx.Client(timeout=NACOS_HTTP_TIMEOUT_SECONDS, trust_env=False) as client:
            access_token = self._login(client)
            client.post(
                self._instance_url(),
                params=self._common_params(access_token),
            ).raise_for_status()
        self._start_heartbeat_loop()
        LOGGER.info("Registered oj-agent to Nacos as service=%s", self.settings.nacos_service_name)

    def deregister(self) -> None:
        if not self.settings.nacos_enabled or not self.settings.nacos_server_addr:
            return
        self._stop_heartbeat_loop()
        with httpx.Client(timeout=NACOS_HTTP_TIMEOUT_SECONDS, trust_env=False) as client:
            access_token = self._login(client)
            client.delete(
                self._instance_url(),
                params=self._common_params(access_token),
            ).raise_for_status()
        LOGGER.info("Deregistered oj-agent from Nacos as service=%s", self.settings.nacos_service_name)

    def _instance_url(self) -> str:
        return self.settings.nacos_server_addr.rstrip("/") + "/nacos/v1/ns/instance"

    def _login(self, client: httpx.Client) -> str | None:
        if not self.settings.nacos_username or not self.settings.nacos_password:
            return None
        response = client.post(
            self.settings.nacos_server_addr.rstrip("/") + "/nacos/v1/auth/users/login",
            data={
                "username": self.settings.nacos_username,
                "password": self.settings.nacos_password,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("accessToken")

    def _common_params(self, access_token: str | None) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "serviceName": self.settings.nacos_service_name,
            "ip": self.settings.nacos_ip,
            "port": self.settings.nacos_port,
            "groupName": self.settings.nacos_group,
            "ephemeral": "true",
        }
        if self.settings.nacos_namespace:
            params["namespaceId"] = self.settings.nacos_namespace
        if access_token:
            params["accessToken"] = access_token
        return params

    def _heartbeat_params(self, access_token: str | None) -> dict[str, str | int]:
        params = self._common_params(access_token)
        params["beat"] = json.dumps({
            "ip": self.settings.nacos_ip,
            "port": self.settings.nacos_port,
            "serviceName": self.settings.nacos_service_name,
            "scheduled": True,
            "weight": 1.0,
        })
        return params

    def _beat_url(self) -> str:
        return self.settings.nacos_server_addr.rstrip("/") + "/nacos/v1/ns/instance/beat"

    def _start_heartbeat_loop(self) -> None:
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()
        self._heartbeat_thread = Thread(target=self._heartbeat_loop, name="oj-agent-nacos-heartbeat", daemon=True)
        self._heartbeat_thread.start()

    def _stop_heartbeat_loop(self) -> None:
        self._heartbeat_stop.set()
        thread = self._heartbeat_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        with httpx.Client(timeout=NACOS_HTTP_TIMEOUT_SECONDS, trust_env=False) as client:
            while not self._heartbeat_stop.wait(5.0):
                try:
                    access_token = self._login(client)
                    client.put(
                        self._beat_url(),
                        params=self._heartbeat_params(access_token),
                    ).raise_for_status()
                except Exception:
                    LOGGER.warning("Failed to heartbeat oj-agent instance to Nacos.", exc_info=True)
