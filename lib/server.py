from __future__ import annotations

import random
import statistics
from collections import defaultdict
from collections.abc import Generator, Iterable
from typing import Any, NoReturn

import matplotlib.pyplot as plt
import simpy
from simpy import Process
from simpy.events import Timeout
from simpy.resources.resource import Release, Request


class Server(simpy.Resource):
    def __init__(self, env: simpy.Environment, capacity: int, name: str) -> None:
        super().__init__(env, capacity)
        self.env = env
        self.name = name
        self.queue_history: dict[int, float] = defaultdict(float)
        self.qt: list[tuple[float, int]] = []
        self.ut: list[tuple[float, int]] = [(0, 0)]

        self.last_queue_level: int = 0
        self.last_queue_level_timestamp: float = 0

        self.worked_time: float = 0
        self.job_on_machine: 'Job' | None = None
        self.job_start_time: float = 0.0

    @property
    def average_queue_length(self) -> float:
        return (
                sum(
                    queue_length * time for queue_length, time in self.queue_history.items()
                )
                / self.env.now
        )

    @property
    def utilization_rate(self) -> float:
        return self.worked_time / self.env.now

    def _update_qt(self) -> None:
        self.qt.append((self.env.now, len(self.queue)))

    def _update_ut(self) -> None:
        status = int(self.count == 1 or len(self.queue) > 0)
        if self.ut and self.ut[-1][1] == status:  # we update ut only if something has changed
            return
        self.ut.append((self.env.now, status))

    def _update_queue_history(self, _) -> None:
        self.queue_history[self.last_queue_level] += (
                self.env.now - self.last_queue_level_timestamp
        )
        self.last_queue_level_timestamp = self.env.now
        self.last_queue_level = len(self.queue)
        self._update_qt()

    def request(self, job: 'Job') -> Request:
        request = super().request()
        request.associated_job = job

        self._update_queue_history(None)

        request.callbacks.append(self._update_queue_history)
        return request

    def release(self, request: Request) -> Release:
        release = super().release(request)
        self._update_qt()
        return release

    def process_job(self, job: 'Job') -> Generator[Timeout, None, None]:
        self.job_on_machine = job
        self.job_start_time = self.env.now

        yield self.env.timeout(job.process_time)

        self.job_on_machine = None
        self.job_start_time = 0.0
        self.worked_time += job.process_time

    def plot_qt(self) -> None:
        x, y = zip(*self.qt)
        plt.step(x, y, where="pre")
        plt.fill_between(x, y, step="pre", alpha=1.0)
        plt.title("Q(t): Queue length over time")
        plt.xlabel("Simulation Time")
        plt.ylabel("Queue Length")
        plt.show()

    def plot_ut(self) -> None:
        ut = self.ut + [(self.env.now, self.ut[-1][1])]
        x, y = zip(*ut)
        plt.step(x, y, where="post")
        plt.fill_between(x, y, step="post", alpha=1.0)
        plt.title("U(t): Machine Center utilization over time")
        plt.xlabel("Simulation Time")
        plt.ylabel("Utilization rate")
        plt.show()