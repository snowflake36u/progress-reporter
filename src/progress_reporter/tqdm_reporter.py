"""tqdm を利用した進捗表示を行う Reporter モジュール。"""

from __future__ import annotations

import threading
from typing import Any

from tqdm import tqdm

from progress_reporter import ProgressEvent, ProgressReporter

class TqdmProgressReporter(ProgressReporter):
	"""単一の tqdm プログレスバーを表示する Reporter。

	1つの Reporter につき、同時に1つの ProgressSession のみを扱う。
	複数の進捗バーやネストした進捗バーが必要な場合は、
	:class:`NestedTqdmProgressReporter` を使用する。
	"""
	
	def __init__(self, **config: Any) -> None:
		"""TqdmProgressReporter のインスタンスを初期化する。

		Args:
			**config: tqdm に引き渡す標準オプション。
		"""
		super().__init__()
		self._config = config
		self._pbar: tqdm | None = None
		self._lock = threading.RLock()
	
	def on_start(self, event: ProgressEvent) -> None:
		"""進捗バーを生成する。

		Args:
			 event: 発行された進捗イベント。

		Raises:
			 RuntimeError: 既に別の進捗セッションが実行中の場合。
		"""
		with self._lock:
			if self._pbar is not None:
				raise RuntimeError(
					"TqdmProgressReporter supports only one active progress session."
				)
			
			self._pbar = tqdm(total=event.total, **self._config)
	
	def on_update(self, event: ProgressEvent) -> None:
		"""進捗バーの表示を更新する。

		Args:
			 event: 発行された進捗イベント。
		"""
		with self._lock:
			if self._pbar is None:
				return
			
			if self._pbar.total != event.total:
				self._pbar.total = event.total
			
			if event.n:
				self._pbar.update(event.n)
			else:
				self._pbar.refresh()
	
	def on_close(self, event: ProgressEvent) -> None:
		"""進捗バーを閉じる。

		Args:
			 event: 発行された進捗イベント。
		"""
		with self._lock:
			if self._pbar is None:
				return
			
			self._pbar.close()
			self._pbar = None
	
	@property
	def pbar(self) -> tqdm | None:
		"""現在使用中の tqdm プログレスバーを取得する。"""
		with self._lock:
			return self._pbar

class NestedTqdmProgressReporter(ProgressReporter):
	"""ネストした複数の tqdm プログレスバーを表示する Reporter。

	ProgressSession の開始順に表示位置を割り当てるため、外側のセッションが
	内側のセッションを開始するようなネスト構造をそのまま tqdm の複数バーとして
	表示できる。
	"""
	
	def __init__(self, **config: Any) -> None:
		"""NestedTqdmProgressReporter のインスタンスを初期化する。

		Args:
			 **config: tqdm に引き渡す標準オプション。
				  ``position`` は Reporter が管理するため指定しないことを推奨する。
		"""
		super().__init__()
		self._config = config
		self._pbars: dict[int, tqdm] = { }
		self._levels: dict[int, int] = { }
		self._lock = threading.RLock()
	
	def on_start(self, event: ProgressEvent) -> None:
		"""新しい tqdm プログレスバーを生成する。"""
		with self._lock:
			position = len(self._pbars)
			self._levels[event.session_id] = position
			config = { **self._config, "position": position }
			self._pbars[event.session_id] = tqdm(total=event.total, **config)
	
	def on_update(self, event: ProgressEvent) -> None:
		"""対応する tqdm プログレスバーの表示を更新する。"""
		with self._lock:
			bar = self._pbars.get(event.session_id)
			if bar is None:
				return
			
			if bar.total != event.total:
				bar.total = event.total
			
			if event.n:
				bar.update(event.n)
			else:
				bar.refresh()
	
	def on_close(self, event: ProgressEvent) -> None:
		"""対応する tqdm プログレスバーを閉じる。"""
		with self._lock:
			bar = self._pbars.pop(event.session_id, None)
			self._levels.pop(event.session_id, None)
			if bar is not None:
				bar.close()
	
	def pbar(self, event: ProgressEvent) -> tqdm | None:
		"""イベントに対応する tqdm プログレスバーを取得する。"""
		with self._lock:
			return self._pbars.get(event.session_id)
	
	def level(self, event: ProgressEvent) -> int | None:
		"""イベントに対応する階層（position）を取得する。"""
		with self._lock:
			return self._levels.get(event.session_id)

__all__ = [
	"TqdmProgressReporter",
	"NestedTqdmProgressReporter",
]
