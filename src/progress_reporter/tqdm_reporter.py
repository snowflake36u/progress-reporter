"""進捗状況の監視および通知を行うライブラリモジュール。"""

from __future__ import annotations

import threading
from typing import Any

from tqdm import tqdm

from progress_reporter import ProgressReporter, ProgressEvent

class TqdmProgressReporter(ProgressReporter):
	"""tqdmを利用して進捗を表示するReporter。"""
	
	def __init__(self, **config: Any) -> None:
		"""TqdmProgressReporter のインスタンスを初期化する。

		Args:
			**config: tqdm に引き渡す標準オプション。
		"""
		super().__init__(**config)
		self._pbars: dict[int, tqdm] = { }
		
		# 複数のプログレスバー操作が競合しないように保護する
		self._lock = threading.Lock()
	
	def on_start(self, event: ProgressEvent) -> None:
		"""tqdm プログレスバーを生成して保持する。

		Args:
			event: 発行された進捗イベント。
		"""
		with self._lock:
			self._pbars[event.session_id] = tqdm(
				total=event.total,
				**self._config,
			)
	
	def on_update(self, event: ProgressEvent) -> None:
		"""tqdm プログレスバーの表示を更新する。

		Args:
			event: 発行された進捗イベント。
		"""
		with self._lock:
			bar = self.pbar(event)
			if bar is None:
				return
			
			if bar.total != event.total:
				bar.total = event.total
			
			if event.n:
				bar.update(event.n)
			else:
				bar.refresh()
	
	def on_close(self, event: ProgressEvent) -> None:
		"""tqdm プログレスバーを閉じる。

		Args:
			event: 発行された進捗イベント。
		"""
		with self._lock:
			bar = self._pbars.pop(event.session_id, None)
			if bar is not None:
				bar.close()
	
	def pbar(self, event: ProgressEvent) -> tqdm:
		return self._pbars.get(event.session_id)

__all__ = [
	"TqdmProgressReporter",
]
