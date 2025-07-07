from __future__ import annotations

from collections.abc import Generator, Callable
from typing import Any, NoReturn

import simpy
from simpy import Process
from simpy.resources.resource import Request

class Job:
    def __init__(
        self,
        env : simpy.Environment,
        routing: list['Server'],
        arrival_time: float,
        process_times: list[float],
        due_date: float,
        idx: int,
        family: str,
        completion_callback: Callable[[Job], None]
    ) -> None:
        self.env = env
        self.routing = routing
        self.arrival_time = arrival_time
        self.process_times = process_times
        self.current_step_index: int = 0
        self.current_process_start_time: float | None = None
        self.current_process_time: float | None = None
        self.due_date = due_date
        self.idx = idx
        self.delay: float | None = None
        self.done: bool = False
        self.family = family
        self.completion_time: float | None = None
        self.time_in_system: float | None = None
        self.completion_callback = completion_callback
        self.earliness: float | None = None
        self.tardiness: float | None = None
        self.in_system: bool = False # for the PSP version, to know if the job has been released in the system

    @property
    def total_processing_time(self) -> float:
        return sum(self.process_times)

    @property
    def remaining_processing_time(self) -> float:
        if self.done:
            return 0.0

        remaining = sum(self.process_times[self.current_step_index:])

        if self.current_process_start_time is not None and self.current_step_index < len(self.process_times):
            time_spent_in_current_step = self.env.now - self.current_process_start_time
            remaining -= time_spent_in_current_step

        return max(0.0, remaining)

    def main(self) -> Generator[Request | Process, Any, None]:
        start_time_in_system = self.env.now
        self.in_system = True
        for i in range(len(self.routing)):
            self.current_step_index = i
            server = self.routing[i]
            self.current_process_time = self.process_times[i]

            with server.request(self) as request:
                queue_entry_time = self.env.now

                yield request

                queue_exit_time = self.env.now
                self.delay = queue_exit_time - queue_entry_time

                self.current_process_start_time = self.env.now
                yield self.env.process(server.process_job(self))

                self.current_process_start_time = None

        self.done = True
        self.in_system = False
        self.completion_time = self.env.now

        self.time_in_system = self.completion_time - start_time_in_system
        self.tardiness = max(0.0, self.completion_time - self.due_date)
        self.earliness = - min(0.0, self.completion_time - self.due_date)
        self.completion_callback(self)