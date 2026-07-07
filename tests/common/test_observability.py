from __future__ import annotations

from common.observability import timed_operation


class TestTimedOperation:
    def test_logs_on_success(self) -> None:
        @timed_operation("test_stage")
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    def test_logs_on_failure(self) -> None:
        @timed_operation("failing_stage")
        def my_func() -> None:
            msg = "something went wrong"
            raise ValueError(msg)

        import pytest

        with pytest.raises(ValueError, match="something went wrong"):
            my_func()

    def test_preserves_args_kwargs(self) -> None:
        @timed_operation("add")
        def add(a: int, b: int) -> int:
            return a + b

        assert add(1, 2) == 3
        assert add(a=10, b=20) == 30

    def test_preserves_function_metadata(self) -> None:
        @timed_operation("named")
        def my_function() -> None:
            pass

        assert my_function.__name__ == "my_function"

    def test_nested_stages(self) -> None:
        call_order: list[str] = []

        @timed_operation("outer")
        def outer() -> None:
            call_order.append("outer_start")
            inner()
            call_order.append("outer_end")

        @timed_operation("inner")
        def inner() -> None:
            call_order.append("inner_ran")

        outer()
        assert call_order == ["outer_start", "inner_ran", "outer_end"]

    def test_exception_preserves_traceback(self) -> None:
        @timed_operation("fail")
        def fail() -> None:
            raise RuntimeError("boom")

        import pytest

        with pytest.raises(RuntimeError) as exc:
            fail()
        assert str(exc.value) == "boom"
