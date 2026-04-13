import time

from src.worker.batcher import Batcher


class TestBatcher:
    def test_should_flush_on_size(self):
        batcher = Batcher(max_size=3, max_linger_seconds=10.0)
        batcher.add("a")
        batcher.add("b")
        assert not batcher.should_flush()
        batcher.add("c")
        assert batcher.should_flush()

    def test_should_flush_on_linger(self):
        batcher = Batcher(max_size=100, max_linger_seconds=0.05)
        batcher.add("a")
        assert not batcher.should_flush()
        time.sleep(0.07)
        assert batcher.should_flush()

    def test_empty_batcher_does_not_flush(self):
        batcher = Batcher(max_size=10, max_linger_seconds=0.001)
        time.sleep(0.01)
        assert not batcher.should_flush()

    def test_drain_returns_items_and_resets(self):
        batcher = Batcher(max_size=3, max_linger_seconds=10.0)
        batcher.add("a")
        batcher.add("b")
        items = batcher.drain()
        assert items == ["a", "b"]
        assert not batcher.should_flush()
        assert batcher.drain() == []

    def test_drain_resets_linger_timer(self):
        batcher = Batcher(max_size=100, max_linger_seconds=0.05)
        batcher.add("a")
        time.sleep(0.07)
        assert batcher.should_flush()
        batcher.drain()
        batcher.add("b")
        # Timer should restart from this add().
        assert not batcher.should_flush()
