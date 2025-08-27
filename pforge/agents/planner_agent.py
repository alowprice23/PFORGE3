from __future__ import annotations
import logging
import uuid

from pforge.agents.base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType
from pforge.messaging.amp import AMPMessage
from pforge.messaging.redis_stream import stream_read_group, stream_ack

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    name = "planner_agent"
    group_name = "planner_group"

    def _calculate_priority(self, event_payload: dict) -> float:
        """
        Calculates the priority of a fix task based on a formula.
        P = (Impact * Frequency) / (Effort * Risk)
        """
        # These values would be determined by other agents or analysis.
        # For now, we use dummy values.
        impact = event_payload.get("impact", 5) # Scale of 1-10
        frequency = event_payload.get("frequency", 3) # Scale of 1-10
        effort = event_payload.get("effort", 2) # Scale of 1-10
        risk = event_payload.get("risk", 2) # Scale of 1-10

        if effort * risk == 0:
            return float('inf') # Avoid division by zero

        priority = (impact * frequency) / (effort * risk)
        return priority

    async def on_tick(self):
        """
        Listens for OBS.TICK events and dispatches FixTasks based on priority.
        """
        messages = await stream_read_group(
            self.redis_client,
            self.group_name,
            self.name,
            {"pforge:amp:global:events": ">"}
        )

        for stream, msg_id, amp_message in messages:
            if amp_message.type == MsgType.OBS_TICK.value:
                logger.info("PlannerAgent consumed OBS.TICK event.")

                priority = self._calculate_priority(amp_message.payload)
                logger.info(f"Calculated priority: {priority}")

                fix_task_payload = {
                    "file_path": amp_message.payload.get("file_path", "example/buggy_file.py"),
                    "description": amp_message.payload.get("description", "A placeholder bug description."),
                    "priority": priority,
                }

                fix_task_message = AMPMessage(
                    type=MsgType.FIX_TASK.value,
                    actor=self.name,
                    snap_sha=amp_message.snap_sha,
                    payload=fix_task_payload,
                    op_id=str(uuid.uuid4())
                )

                logger.info(f"PlannerAgent dispatching FIX_TASK with payload: {fix_task_payload}")
                await self.send_amp_event(
                    event_type=fix_task_message.type,
                    payload=fix_task_message.payload,
                    snap_sha=fix_task_message.snap_sha,
                )
                logger.info(f"PlannerAgent dispatched a FixTask for file: {fix_task_payload.get('file_path')}")

            await stream_ack(self.redis_client, stream, self.group_name, msg_id)
