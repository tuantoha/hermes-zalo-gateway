"""
Zalo Personal Account Platform Adapter for Hermes Gateway.

Uses openzca CLI (https://github.com/darkamenosa/openzca) to connect
to Zalo personal accounts. Supports DM and group messaging.

Requirements:
    - openzca installed: npm install -g openzca@latest
    - Logged in: openzca auth login
"""

import asyncio
import json
import logging
import os
import re
import shutil
import time
from typing import Optional

logger = logging.getLogger(__name__)

from gateway.platforms.base import (
    BasePlatformAdapter,
    SendResult,
    MessageEvent,
    MessageType,
)
from gateway.config import Platform, PlatformConfig

OPENZCA = shutil.which("openzca") or os.environ.get("OPENZCA_BINARY", "openzca")
PROFILE = os.environ.get("OPENZCA_PROFILE", "default")
MAX_MESSAGE_LENGTH = 2000


class ZaloAdapter(BasePlatformAdapter):
    """Hermes gateway adapter for Zalo personal accounts via openzca."""

    def __init__(self, config, **kwargs):
        platform = Platform("zalo")
        super().__init__(config=config, platform=platform)
        self._listener_process: Optional[asyncio.subprocess.Process] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False
        self._me_id: Optional[str] = None

    # ---- Required methods ----

    async def connect(self) -> bool:
        """Connect to Zalo by spawning openzca listen subprocess."""
        if self._running:
            return True

        # Verify openzca is available and logged in
        try:
            proc = await asyncio.create_subprocess_exec(
                OPENZCA, "--profile", PROFILE, "me", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode != 0:
                logger.error(f"[Zalo] Not logged in: {stderr.decode().strip()}")
                return False
            # openzca outputs JS-like object, not pure JSON. Fix it.
            raw = stdout.decode().strip()
            # Replace single-quoted values with double-quoted  
            raw = re.sub(r": '([^']*)'", r': "\1"', raw)
            # Quote all unquoted keys (word followed by colon, not inside quotes)
            raw = re.sub(r'(?<=[\s\{,])([a-zA-Z_]\w*):', r'"\1":', raw)
            # Remove trailing commas
            raw = re.sub(r',\s*}', '}', raw)
            raw = re.sub(r',\s*]', ']', raw)
            me_data = json.loads(raw)
            self._me_id = me_data.get("userId", "")
            logger.info(f"[Zalo] Connected as {me_data.get('displayName', '?')} ({self._me_id})")
        except Exception as e:
            logger.error(f"[Zalo] Failed to verify login: {e}")
            return False

        # Start listener subprocess
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        return True

    async def disconnect(self):
        """Stop listener and cleanup."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._listener_process and self._listener_process.returncode is None:
            self._listener_process.kill()
            await self._listener_process.wait()
            self._listener_process = None

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        **kwargs,
    ) -> SendResult:
        """Send a text message via openzca."""
        text = content
        # Always use --group since we only poll groups right now
        cmd = [OPENZCA, "--profile", PROFILE, "msg", "send", "--group", chat_id, text]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode == 0:
                raw = stdout.decode().strip()
                # Parse JS-like object output
                raw = re.sub(r": '([^']*)'", r': "\1"', raw)
                raw = re.sub(r'(?<=[\s\{,])([a-zA-Z_]\w*):', r'"\1":', raw)
                raw = re.sub(r',\s*}', '}', raw)
                try:
                    result = json.loads(raw)
                    msg_id = str(result.get("message", {}).get("msgId", ""))
                    return SendResult(success=True, message_id=msg_id)
                except json.JSONDecodeError:
                    return SendResult(success=True, message_id="")
            else:
                return SendResult(success=False, error=stderr.decode().strip())
        except asyncio.TimeoutError:
            return SendResult(success=False, error="Timeout")
        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def send_typing(self, chat_id: str):
        """Zalo doesn't support typing indicator via openzca."""
        pass

    async def send_image(self, chat_id: str, image_url: str, caption: str = "", **kwargs) -> SendResult:
        """Send an image via openzca."""
        cmd = [OPENZCA, "--profile", PROFILE, "msg", "image", chat_id, image_url]
        if kwargs.get("is_group"):
            cmd.insert(4, "--group")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode == 0:
                return SendResult(success=True)
            return SendResult(success=False, error=stderr.decode().strip())
        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def get_chat_info(self, chat_id: str) -> dict:
        """Get info about a chat (user or group)."""
        return {"name": chat_id, "type": "dm", "chat_id": chat_id}

    # ---- Internal ----

    async def _listen_loop(self):
        """Poll Zalo messages via openzca DB instead of listen subprocess."""
        import time
        self._last_msg_id = None
        logger.info("[Zalo] DB poller started (interval=5s)")

        while self._running:
            try:
                # Sync DB first to get latest messages
                sync_proc = await asyncio.create_subprocess_exec(
                    OPENZCA, "--profile", PROFILE,
                    "db", "sync", "group", "2747350517158961481",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(sync_proc.communicate(), timeout=30)

                # Then poll for new messages
                new_messages = []
                proc = await asyncio.create_subprocess_exec(
                    OPENZCA, "--profile", PROFILE,
                    "db", "group", "messages", "2747350517158961481", "--json", "--limit", "10",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
                if proc.returncode != 0:
                    await asyncio.sleep(5)
                    continue

                try:
                    raw = stdout.decode().strip()
                    # Fix JS-object to JSON
                    raw = re.sub(r": '([^']*)'", r': "\1"', raw)
                    raw = re.sub(r'(?<=[\s\{,])([a-zA-Z_]\w*):', r'"\1":', raw)
                    raw = re.sub(r',\s*}', '}', raw)
                    raw = re.sub(r',\s*]', ']', raw)
                    data = json.loads(raw)
                    messages = data.get("messages", [])
                except Exception:
                    await asyncio.sleep(5)
                    continue

                for msg in reversed(messages):
                    msg_id = str(msg.get("msgId", ""))
                    if self._last_msg_id and msg_id <= self._last_msg_id:
                        continue

                    sender_id = str(msg.get("senderId", ""))
                    content = msg.get("content", "")
                    thread_id = str(msg.get("threadId", ""))
                    is_group = bool(msg.get("groupId"))

                    if sender_id == self._me_id:
                        continue
                    if not content or not isinstance(content, str):
                        continue

                    self._last_msg_id = msg_id
                    chat_id = thread_id or sender_id

                    source = self.build_source(
                        chat_id=chat_id,
                        user_id=sender_id,
                        message_id=msg_id,
                        chat_type="group" if is_group else "dm",
                    )

                    event = MessageEvent(
                        message_type=MessageType.TEXT,
                        text=content,
                        source=source,
                        message_id=msg_id,
                    )

                    logger.info(f"[Zalo] inbound: {sender_id} -> {content[:50]}...")
                    await self.handle_message(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Zalo] Poll error: {e}")

            await asyncio.sleep(5)

        logger.info("[Zalo] DB poller stopped")

    async def _handle_raw_message(self, raw: str):
        """Parse a raw JSON message from openzca and dispatch to gateway."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.debug(f"[Zalo] Non-JSON line: {raw[:100]}")
            return

        # Extract message info
        msg_type = data.get("type", data.get("msgType", ""))
        content = data.get("content", data.get("message", ""))
        sender_id = data.get("senderId", data.get("fromId", ""))
        thread_id = data.get("threadId", data.get("groupId", data.get("toId", "")))
        msg_id = str(data.get("msgId", data.get("cliMsgId", "")))
        is_group = bool(data.get("groupId") or data.get("isGroup"))

        # Skip self messages
        if sender_id == self._me_id:
            return

        # Skip non-text messages for now
        if msg_type not in ("webchat", "chat", "text", "1", ""):
            logger.debug(f"[Zalo] Skipping non-text msg type: {msg_type}")
            return

        if not content or not isinstance(content, str):
            return

        chat_id = thread_id or sender_id

        # Build source
        source = self.build_source(
            platform_name="zalo",
            chat_id=chat_id,
            user_id=sender_id,
            message_id=msg_id,
            chat_type="group" if is_group else "dm",
        )

        # Dispatch to gateway
        event = MessageEvent(
            type=MessageType.TEXT,
            text=content,
            source=source,
            message_id=msg_id,
            reply_to_message_id=None,
        )

        logger.info(f"[Zalo] inbound: {sender_id} -> {content[:50]}...")
        await self.handle_message(event)

    # ---- Plugin registration ----

    @staticmethod
    def check_requirements() -> bool:
        """Check if openzca is installed and logged in."""
        return shutil.which("openzca") is not None


def register(ctx):
    """Plugin entry point — register with Hermes gateway."""
    ctx.register_platform(
        platform_name="zalo",
        adapter_class=ZaloAdapter,
        check_requirements=ZaloAdapter.check_requirements,
        env_enablement_fn=_env_enablement,
    )


def _env_enablement() -> Optional[dict]:
    """Enable Zalo platform if openzca is available and logged in."""
    if not shutil.which("openzca"):
        return None
    # Check if logged in
    try:
        import subprocess, json
        r = subprocess.run(
            [OPENZCA, "--profile", PROFILE, "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return {
                "enabled": True,
                "extra": {"profile": PROFILE},
            }
    except Exception:
        pass
    return None
