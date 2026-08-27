"""進捗状況の監視および通知を行うライブラリモジュール。"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Callable, Iterable, Iterator, Mapping

__all__ = [
	'NullProgressReporter',
	'ProgressEvent',
	'ProgressEventHandler',
	'ProgressReporter',
	'ProgressSession',
]

@dataclass(frozen=True, slots=True)
class ProgressEvent:
	"""進捗セッションから発行されるイベント。

	Attributes:
		session_id: イベントを発生させたセッションのID。
		current: イベント発生時点の進捗値。
		n: 更新された進捗値。
		total: 総ステップ数。
		data: タスク固有の通知データ。
	"""
	session_id: int
	current: int
	n: int = 0
	total: int | None = None
	data: Mapping[str, Any] = field(default_factory=dict)

ProgressEventHandler = Callable[[ProgressEvent], None]

class ProgressReporter(ABC):
	"""進捗イベントの通知方法を定義する基底クラス。"""
	
	def __init__(self: Any) -> None:
		"""ProgressReporter のインスタンスを初期化する。
		"""
		self._session_ids = count(1)
	
	def watch(
			self,
			iterable: Iterable[Any] | None = None,
			*,
			total: int | None = None,
			**data: Any,
	) -> ProgressSession:
		"""進捗セッションを作成する。

		Args:
			iterable: 反復対象。
			total: 総ステップ数。
			**data: セッション開始時の付加情報。

		Returns:
			新しい進捗セッション。
		"""
		if total is None and iterable is not None:
			try:
				total = len(iterable)  # type: ignore[arg-type]
			except TypeError:
				pass
		
		session = ProgressSession(
			session_id=next(self._session_ids),
			iterable=iterable,
			total=total,
			start_callback=self.on_start,
			update_callback=self.on_update,
			close_callback=self.on_close,
			**data,
		)
		
		return session
	
	@abstractmethod
	def on_start(self, event: ProgressEvent) -> None:
		"""セッション開始時の処理。

		Args:
			event: 発行された進捗イベント。
		"""
	
	@abstractmethod
	def on_update(self, event: ProgressEvent) -> None:
		"""セッション更新時の処理。

		Args:
			event: 発行された進捗イベント。
		"""
	
	@abstractmethod
	def on_close(self, event: ProgressEvent) -> None:
		"""セッション終了時の処理。

		Args:
			event: 発行された進捗イベント。
		"""

class ProgressSession:
	"""一回分の進捗状態を管理するセッション。"""
	
	def __init__(
			self,
			*,
			session_id: int,
			iterable: Iterable[Any] | None,
			total: int | None,
			start_callback: ProgressEventHandler,
			update_callback: ProgressEventHandler,
			close_callback: ProgressEventHandler,
			**start_data: Any,
	) -> None:
		"""ProgressSession のインスタンスを初期化する。

		Args:
			session_id: セッションID。
			iterable: 反復対象のオブジェクト。
			total: 総ステップ数。
			start_callback: セッション開始時のコールバック関数。
			update_callback: セッション更新時のコールバック関数。
			close_callback: セッション終了時のコールバック関数。
			**start_data: 開始イベントに付与する情報。
		"""
		self._session_id = session_id
		self._iterable = iterable
		self._total = total
		self.start_callback = start_callback
		self.update_callback = update_callback
		self.close_callback = close_callback
		
		self._current = 0
		self._started = False
		self._closed = False
		
		# コールバックやプロパティ取得が同一セッションの状態へ再入することが
		# あるため、通常の Lock では再入時にデッドロックする可能性がある。
		# 状態の更新と参照を安全に保つには、再入可能なロックが適切。
		self._lock = threading.RLock()
		
		self.start(**start_data)
	
	@property
	def session_id(self) -> int:
		"""セッション識別子を取得する。"""
		return self._session_id
	
	@property
	def current(self) -> int:
		"""現在の進捗値を取得する。"""
		with self._lock:
			return self._current
	
	@property
	def total(self) -> int | None:
		"""総ステップ数を取得する。"""
		with self._lock:
			return self._total
	
	def start(self, **data: Any) -> None:
		"""セッションを開始する。

		Args:
			**data: 開始イベントに付与する情報。
		"""
		with self._lock:
			if self._started:
				return
			
			self._started = True
			current_val = self._current
			total_val = self._total
		
		self.start_callback(
			ProgressEvent(
				session_id=self._session_id,
				current=current_val,
				total=total_val,
				data=data,
			)
		)
	
	def update(
			self,
			n: int = 1,
			*,
			total: int | None = None,
			**data: Any,
	) -> None:
		"""進捗を更新する。

		Args:
			n: 増分ステップ数。
			total: 変更後の総ステップ数。
			**data: この更新イベントに付与する情報。

		Raises:
			ValueError: nが負の値の場合。
			RuntimeError: セッションが未開始またはすでに終了している場合。
		"""
		with self._lock:
			self._ensure_active()
			
			if n < 0:
				raise ValueError("n must be 0 or greater.")
			
			if total is not None:
				self._total = total
			
			self._current += n
			
			current_val = self._current
			total_val = self._total
		
		self.update_callback(
			ProgressEvent(
				session_id=self._session_id,
				current=current_val,
				n=n,
				total=total_val,
				data=data,
			)
		)
	
	def close(self, **data: Any) -> None:
		"""セッションを終了する。

		Args:
			**data: 終了イベントに付加する情報。
		"""
		with self._lock:
			if self._closed:
				return
			
			self._closed = True
			current_val = self._current
			total_val = self._total
		
		self.close_callback(
			ProgressEvent(
				session_id=self._session_id,
				current=current_val,
				total=total_val,
				data=data,
			)
		)
	
	def __enter__(self) -> ProgressSession:
		"""コンテキストマネージャーを開始する。

		Returns:
			自分自身のインスタンス。

		Raises:
			RuntimeError: セッションが未開始またはすでに終了している場合。
		"""
		with self._lock:
			self._ensure_active()
		return self
	
	def __exit__(
			self,
			exc_type: type[BaseException] | None,
			exc_value: BaseException | None,
			traceback: Any,
	) -> None:
		"""コンテキストマネージャーを終了し、セッションを閉じる。"""
		self.close()
	
	def __iter__(self) -> Iterator[Any]:
		"""反復処理を実行し、要素ごとに進捗を自動更新する。

		Yields:
			反復対象の要素。

		Raises:
			TypeError: iterableが指定されていない場合。
			RuntimeError: セッションが未開始またはすでに終了している場合。
		"""
		if self._iterable is None:
			raise TypeError("This progress session has no iterable.")
		
		with self._lock:
			self._ensure_active()
		
		try:
			for item in self._iterable:
				yield item
				self.update()
		finally:
			self.close()
	
	def _ensure_active(self) -> None:
		"""セッションがアクティブ状態であることを確認する。
		
		呼び出し元で排他制御が行われていることを前提とする。

		Raises:
			RuntimeError: セッションが未開始またはすでに終了している場合。
		"""
		if not self._started:
			raise RuntimeError("Progress session has not been started.")
		
		if self._closed:
			raise RuntimeError("Progress session is already closed.")

class NullProgressReporter(ProgressReporter):
	"""進捗イベントとして何も処理しない実装。"""
	
	def on_start(self, event: ProgressEvent) -> None:
		"""セッション開始時イベント。何もしない。

		Args:
			event: 発行された進捗イベント。
		"""
	
	def on_update(self, event: ProgressEvent) -> None:
		"""進捗更新時イベント。何もしない。

		Args:
			event: 発行された進捗イベント。
		"""
	
	def on_close(self, event: ProgressEvent) -> None:
		"""セッション終了時イベント。何もしない。

		Args:
			event: 発行された進捗イベント。
		"""
