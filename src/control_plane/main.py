import sys
import logging
import asyncio
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import ClassVar
from llama_agents import ControlPlaneServer, AgentOrchestrator
from llama_index.llms.openai import OpenAI
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_agents.message_queues import SimpleRemoteClientMessageQueue


logger = logging.getLogger(__name__)


class ControlPlaneConfig(BaseSettings):
    llm_provider: ClassVar[str] = "openai"  # Update for other LLM providers later
    llm_model: str = Field(
        default="gpt-3.5-turbo",
        env="MODEL",
    )

    host: str = Field(
        default="localhost",
        env="HOST",
    )
    port: int = Field(
        default=8001,
        env="PORT",
    )

    orchestrator_type: str = Field(
        default="agent",
        env="ORCHESTRATOR_TYPE",
    )

    message_queue_url: str = Field(
        default="http://localhost:8100",
        env="MESSAGE_QUEUE_URL",
        alias="message_queue_url",
    )

    _llm: FunctionCallingLLM = None

    class Config:
        env_prefix = "CONTROL_PLANE_"

    def get_llm(self):
        # TODO: Update for other LLM providers later
        if self._llm is None:
            self._llm = OpenAI(model=self.llm_model)
        return self._llm

    def get_orchestrator(self):
        llm = self.get_llm()

        match self.orchestrator_type:
            case "agent":
                return AgentOrchestrator(llm=self.get_llm())
            case _:
                raise ValueError(f"Unknown orchestrator type: {self.orchestrator_type}")


async def launch_control_plane(config: ControlPlaneConfig):
    message_queue = SimpleRemoteClientMessageQueue(base_url=config.message_queue_url)

    control_plane = ControlPlaneServer(
        message_queue=message_queue,
        orchestrator=config.get_orchestrator(),
        host=config.host,
        port=config.port,
    )

    server = control_plane.launch_server()
    await message_queue.register_consumer(control_plane.as_consumer(remote=True))
    await server


if __name__ == "__main__":
    config = ControlPlaneConfig()
    asyncio.run(launch_control_plane(config=config))