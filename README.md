# progress-reporters

`progress-reporters` is a lightweight Python library for monitoring long-running tasks while keeping task execution logic separate from presentation and notification logic.

In applications implementations, the code that performs work can be mixed with UI concerns such as progress bars, logging, or status updates. This library introduces a small event-driven model: the task emits progress events, and a reporter decides how those events are displayed or processed.

This makes it easier to keep business logic clean while still supporting progress bars, logs, or custom monitoring implementations.

## Why this exists

A typical pattern is to integrate a progress bar directly into the task loop. For example, calling `tqdm` updates inside the processing code couples the implementation of the work with the formatting of the display.

`progress-reporters` separates these concerns:

- `ProgressSession` tracks the state of a single progress lifecycle
- `ProgressReporter` defines how events are handled
- concrete reporters such as `TqdmProgressReporter` and `NestedTqdmProgressReporter` render progress in a terminal
- `IntervalTrigger` helps suppress excessively frequent update events

## Features

- Thread-safe progress sessions with `start()`, `update()`, and `close()`
- Iterable-driven progress tracking via `watch()`
- Support for custom reporters by subclassing `ProgressReporter`
- `NullProgressReporter` for no-op behavior in tests or non-interactive environments
- `TqdmProgressReporter` for terminal progress bars
- `NestedTqdmProgressReporter` for nested terminal progress bars
- `IntervalTrigger` for throttling updates by step count or elapsed time

## Requirements

- tqdm (Optional, to use `progress_reporters.tqdm_reporter` module)

## Installation

```bash
pip install progress-reporters
```

For local development:

```bash
python -m pip install -U pip
python -m pip install -e .
```

## Quick start for handling tqdm

```python
from progress_reporters.tqdm_reporter import TqdmProgressReporter

# Arguments will be passed to tqdm() internally
reporter = TqdmProgressReporter(desc="Processing items")
source = [1, 2, 3, 6]

# Pattern 1: Session as Iterator
with reporter.watch(source) as progress:
    for item in progress:
        # do the real work here
        print(f"processing {item}")

# Pattern 2: Handling Session Manually
progress = reporter.watch(source)	# or `reporter.watch(total=len(source))`
for item in source:
    # do the real work here
    print(f"processing {item}")

    progress.update()
progress.close()
```

`reporter.watch()` creates a progress session and automatically/manually triggers start, update, and close events. The `TqdmProgressReporter` subscribes to those events and updates the console bar accordingly.

The session supports:

- `start(**data)`
- `update(n=1, total=None, **data)`
- `close(**data)`
- context manager usage with `with ...:`
- iteration-based updates when an iterable has been specified to `reporter.watch()`

If no iterable is specified to `reporter.watch()`, only the manual session management is available.

## Nested tqdm bars

When a task has nested loops or multiple concurrent progress scopes, use `NestedTqdmProgressReporter` to render them as stacked tqdm bars.

```python
from progress_reporters.tqdm_reporter import NestedTqdmProgressReporter

reporter = NestedTqdmProgressReporter(desc="Processing batches")

for batch in reporter.watch(range(2)):
    for item in reporter.watch(range(3)):
        # do the real work here
        ...
```

Each session is assigned its own tqdm position in start order, so the nested bars remain aligned without interfering with one another.

## Custom reporter example

```python
from progress_reporters import ProgressEvent, ProgressReporter

class LoggingReporter(ProgressReporter):
    def on_start(self, event: ProgressEvent) -> None:
        print(f"start session={event.session_id} total={event.total}")

    def on_update(self, event: ProgressEvent) -> None:
        item = event.data.get("item")
        print(
            f"session={event.session_id} "
            f"current={event.current} delta={event.n} "
            f"item={item}"
        )

    def on_close(self, event: ProgressEvent) -> None:
        print(f"close session={event.session_id}")

reporter = LoggingReporter()

array = ["a", "b", "c"]
progress = reporter.watch(total=len(array))
for item in array:
    # do the real work here
    progress.update(1, item=item, status="processed")

progress.close()
```

`ProgressSession.update(..., **data)` stores extra payloads in `event.data`, so a reporter can inspect task-specific metadata without coupling the work loop to the display layer. In the example above, the reporter reads `event.data["item"]` and prints it together with the current progress state.

This is the core philosophy of the library: task logic emits progress events, while the reporter decides how to expose them.

## IntervalTrigger

`IntervalTrigger` is a utility for reducing the frequency of progress events when work produces updates too often to be useful.

It can trigger updates based on either:

- a fixed number of steps (`step_interval`)
- a fixed amount of elapsed time (`time_interval`)

When both are set, the first condition to become true wins.

```python
from progress_reporters.trigger import IntervalTrigger

trigger = IntervalTrigger(step_interval=10)

for step in range(25):
    if trigger.step():
        print(f"Update triggered at step {trigger.steps}")
```

Time-based scheduling is also supported:

```python
from progress_reporters.trigger import IntervalTrigger

trigger = IntervalTrigger(time_interval=0.5)

for _ in range(10):
    if trigger.step():
        print("time-based update fired")
```

This is especially helpful in situations where a task emits many small progress notifications, but only a subset of them need to reach a UI layer such as a progress bar or log sink.

 For iteration-based progress updates with `tqdm`, the built-in `miniters` and `mininterval` options are often sufficient, so `IntervalTrigger` is usually not needed there. It becomes useful when progress is updated at times other than the main iteration loop, such as processing sub-tasks or external events that need throttling.

## License

This project is distributed under the BSD-3-Clause license.
