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
        self.current_process_time: float | None = None
        self.due_date = due_date
        self.idx = idx
        self.delay: float | None = None
        self.done: bool = False
        self.family = family
        self.completion_time: float | None = None
        self.time_in_system: float | None = None
        self.is_late: bool = False
        self.completion_callback = completion_callback
        self.earliness: float | None = None
        self.tardiness: float | None = None
        self.in_system: bool = False # for the PSP version, to know if the job has been released in the system

    def main(self) -> Generator[Request | Process, Any, None]:
        start_time_in_system = self.env.now
        self.in_system = True
        for i in range(len(self.routing)):
            server = self.routing[i]
            process_time = self.process_times[i]
            with server.request(self) as request:
                queue_entry_time = self.env.now
                self.current_process_time = process_time

                yield request

                queue_exit_time = self.env.now
                self.delay = queue_exit_time - queue_entry_time

                yield self.env.process(server.process_job(self))

        self.done = True
        self.completion_time = self.env.now
        if self.completion_time > self.due_date:
            self.is_late = True

        self.time_in_system = self.completion_time - start_time_in_system
        self.tardiness = max(0.0, self.completion_time - self.due_date)
        self.earliness = - min(0.0, self.completion_time - self.due_date)
        self.completion_callback(self)