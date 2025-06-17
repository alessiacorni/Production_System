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

class Job:
    def __init__(
        self,
        env : simpy.Environment,
        routing: list['Server'],
        arrival_time: float,
        process_time: float,
        idx: int,
        family: str
    ) -> None:
        self.env = env
        self.routing = routing
        self.arrival_time = arrival_time
        self.process_time = process_time
        self.idx = idx
        self.delay: float | None = None
        self.done: bool = False
        self.family = family

    def main(self) -> Generator[Request | Process, Any, None]:
        for server in self.routing:
            with server.request() as request:
                queue_entry_time = self.env.now

                print("PRODUCT {} of family {}: Waiting for the machine {} to become available".format(self.idx, self.family, server.name))
                yield request
                print("PRODUCT {} of family {}: Machine {} ready".format(self.idx, self.family, server.name))

                queue_exit_time = self.env.now
                self.delay = queue_exit_time - queue_entry_time

                print("PRODUCT {} of family {}: starting to be processed by the machine {}".format(self.idx, self.family, server.name))
                yield self.env.process(server.process_job(self))
                print("PRODUCT {} of family {}: Machine {} process finished".format(self.idx, self.family, server.name))
                self.done = True