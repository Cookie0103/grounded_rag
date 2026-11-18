"""在本机读取问答 SSE，可在指定序号断开并续推。"""

import argparse
import json
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from http import HTTPStatus
from http.client import HTTPConnection, HTTPResponse
from typing import Any


@dataclass(frozen=True)
class Event:
    id: int
    name: str
    payload: dict[str, Any]


@dataclass
class StreamResult:
    response_id: str
    text: str = ""
    last_id: int = 0
    first_delta_ms: float | None = None
    total_ms: float = 0.0
    retractions: list[tuple[str, ...]] = field(default_factory=list)
    answer: dict[str, Any] | None = None

    def receive(self, event: Event, elapsed_ms: float) -> None:
        if event.id <= self.last_id:
            return
        if event.id != self.last_id + 1 or event.payload["response_id"] != self.response_id:
            raise RuntimeError("SSE 响应 ID 或事件序号不连续")
        self.last_id = event.id
        if event.name == "delta":
            if self.first_delta_ms is None:
                self.first_delta_ms = elapsed_ms
            self.text += event.payload["text"]
        elif event.name == "retract":
            self.text = event.payload["replacement"]
            self.retractions.append(tuple(event.payload["reasons"]))
        elif event.name == "answer":
            self.answer = event.payload
            self.total_ms = elapsed_ms
            if self.text != self.answer_text():
                raise RuntimeError("SSE 拼接结果与最终答案不同")
        elif event.name == "error":
            raise RuntimeError(f"{event.payload['code']}：{event.payload['message']}")

    def answer_text(self) -> str:
        return str(self.answer["answer"]) if self.answer is not None else ""


def _events(response: HTTPResponse) -> Iterator[Event]:
    fields: dict[str, str] = {}
    for raw in response:
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line:
            if fields:
                yield Event(int(fields["id"]), fields["event"], json.loads(fields["data"]))
                fields.clear()
            continue
        name, _, value = line.partition(":")
        if name:
            fields[name] = value.lstrip()


def _consume(response: HTTPResponse, result: StreamResult, started: float, cutoff: int) -> None:
    for event in _events(response):
        result.receive(event, (time.perf_counter() - started) * 1000)
        if event.id == cutoff or result.answer is not None:
            return


def _check_response(response: HTTPResponse) -> None:
    if response.status != HTTPStatus.OK:
        raise RuntimeError(f"问答服务返回 HTTP {response.status}")


def ask_stream(port: int, body: dict[str, object], *, disconnect_after: int = 0) -> StreamResult:
    started = time.perf_counter()
    connection = HTTPConnection("127.0.0.1", port, timeout=100)
    try:
        connection.request(
            "POST",
            "/chat",
            body=json.dumps({**body, "stream": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with connection.getresponse() as response:
            _check_response(response)
            response_id = response.getheader("X-Response-Id")
            if response_id is None:
                raise RuntimeError("服务器没有返回流式响应 ID")
            result = StreamResult(response_id)
            _consume(response, result, started, disconnect_after)
    finally:
        connection.close()

    if result.answer is None and disconnect_after:
        _resume(port, result, started)
    if result.answer is None:
        raise RuntimeError("连接关闭前没有收到最终答案")
    return result


def _resume(port: int, result: StreamResult, started: float) -> None:
    connection = HTTPConnection("127.0.0.1", port, timeout=100)
    try:
        connection.request(
            "GET",
            f"/chat/stream/{result.response_id}",
            headers={"Last-Event-ID": str(result.last_id)},
        )
        with connection.getresponse() as response:
            _check_response(response)
            _consume(response, result, started, 0)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="要发送的日文问题")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--channel", choices=("agent", "customer"), default="customer")
    parser.add_argument("--agent-id")
    parser.add_argument("--customer-id")
    parser.add_argument("--disconnect-after", type=int, default=0, help="该序号后断开再续推")
    args = parser.parse_args()
    body: dict[str, object] = {"question": args.question, "channel": args.channel}
    if args.channel == "agent":
        body.update(agent_id=args.agent_id, customer_id=args.customer_id)
    result = ask_stream(args.port, body, disconnect_after=args.disconnect_after)
    sys.stdout.write(result.text + "\n")


if __name__ == "__main__":
    main()
