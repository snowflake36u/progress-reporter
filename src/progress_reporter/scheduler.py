import time
from typing import Callable

class IntervalScheduler:
	"""ステップ数または時間間隔に基づいて更新タイミングを判定するクラス。

	指定されたステップ数または時間間隔のいずれかが条件を満たしたタイミングで
	トリガーを返します。ログ出力やチェックポイント保存などの頻度制御に使用します。

	Attributes:
		step_interval: 更新判定を行うステップ間隔。
		time_interval: 更新判定を行う時間間隔（秒）。
	"""
	
	def __init__(
			self,
			step_interval: int | None = None,
			time_interval: float | None = None,
			*,
			clock: Callable[[], float] = time.monotonic,
	) -> None:
		"""IntervalScheduler のインスタンスを初期化します。

		Args:
			step_interval: 更新判定を行うステップ数。
			time_interval: 更新判定を行う時間間隔（秒）。
			clock: 現在時刻を取得するための呼び出し可能オブジェクト。

		Raises:
			ValueError: 更新間隔が1つも指定されていない場合、
				または指定された値が0以下の場合。
		"""
		if step_interval is None and time_interval is None:
			raise ValueError("Either step_interval or time_interval must be specified.")
		if step_interval is not None and step_interval <= 0:
			raise ValueError("step_interval must be 1 or greater.")
		if time_interval is not None and time_interval <= 0:
			raise ValueError("time_interval must be greater than 0.")
		
		self.step_interval = step_interval
		self.time_interval = time_interval
		self._clock = clock
		self._steps = 0
		self._next_update_steps: int | None = None
		self._last_update = 0.0
		self.reset()
	
	def add(self, steps: int = 1) -> bool:
		"""指定ステップ数を加算し、更新タイミングに達したかを判定します。

		ステップ間隔と時間間隔の両方を指定した場合は、どちらか一方が
		先に条件を満たした時点で True になります。

		Args:
			steps: 加算するステップ数。

		Returns:
			更新タイミングに達した場合は True、それ以外は False。

		Raises:
			ValueError: steps に負の数が指定された場合。
		"""
		if steps < 0:
			raise ValueError("steps must be 0 or greater.")
		
		self._steps += steps
		
		if self._next_update_steps is not None and self._steps >= self._next_update_steps:
			self.update()
			return True
		
		if self.time_interval is not None:
			now = self._clock()
			if now - self._last_update >= self.time_interval:
				self.update(now=now)
				return True
		
		return False
	
	def update(self, *, now: float | None = None) -> None:
		"""次の更新判定に向けて状態を更新します。

		累積ステップ数は維持されるため、累積値を表示する用途にも使用できます。

		Args:
			now: リセット基準となる現在時刻。指定しない場合は clock から取得します。
		"""
		self._last_update = self._clock() if now is None else now
		
		if self.step_interval is None:
			self._next_update_steps = None
			return
		
		self._next_update_steps = \
			(self._steps // self.step_interval + 1) * self.step_interval
	
	def reset(self, *, now: float | None = None) -> None:
		"""内部状態を完全に初期化します。

		Args:
			now: 初期化基準となる現在時刻。指定しない場合は clock から取得します。
		"""
		self._steps = 0
		self._last_update = self._clock() if now is None else now
		self._next_update_steps = self.step_interval
	
	@property
	def steps(self) -> int:
		"""現在までに加算された累積ステップ数を取得します。

		Returns:
			累積ステップ数。
		"""
		return self._steps

__all__ = [
	"IntervalScheduler",
]
