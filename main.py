"""Mini NPU 시뮬레이터: 그림(숫자 칸)과 필터를 겹쳐 곱하고 더하는 MAC 연산으로 패턴을 판별한다.

실행: python main.py   (Python 3.8 이상, 외부 라이브러리 없음)
"""
import sys

EPSILON = 1e-9  # 두 점수의 차이가 이보다 작으면 같은 점수(동점)로 본다
REPEAT = 10     # 성능 측정 반복 횟수


# ============================================================
# 1. 데이터 구조: n×n 칸에 숫자를 저장하고 읽는다
# ============================================================
class Grid:
    """n×n 크기의 2차원 숫자 칸. 필터와 패턴을 이 모양으로 담는다."""

    def __init__(self, size, fill=0.0):
        self.size = size
        self.rows = [[fill for _ in range(size)] for _ in range(size)]

    def get(self, row, col):
        """row행 col열의 값을 읽는다."""
        return self.rows[row][col]

    def set(self, row, col, value):
        """row행 col열에 값을 저장한다."""
        self.rows[row][col] = value

    @classmethod
    def from_rows(cls, rows):
        """2차원 리스트로 Grid를 만든다. 정사각형이 아니면 ValueError."""
        size = len(rows)
        for row in rows:
            if len(row) != size:
                raise ValueError("정사각형(n×n)이 아닙니다: {}행 중 {}개짜리 줄이 있습니다.".format(size, len(row)))
        grid = cls(size)
        for r in range(size):
            for c in range(size):
                grid.set(r, c, float(rows[r][c]))
        return grid


# ============================================================
# 2. 입출력 도우미
# ============================================================
class ExitRequested(Exception):
    """Ctrl+C 또는 입력 끝(EOF)이 들어왔을 때 안전하게 끝내기 위한 신호."""


def read_line(prompt):
    """한 줄을 읽어 앞뒤 공백을 지운다. 중단 입력은 ExitRequested로 바꾼다."""
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        raise ExitRequested


def use_utf8_io():
    """한글 Windows(cp949)에서도 한글·기호가 깨지지 않게 입출력을 UTF-8로 맞춘다."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")


def run_user_mode():
    print("(준비 중: 사용자 입력 모드)")


def run_json_mode():
    print("(준비 중: data.json 분석 모드)")


# ============================================================
# 3. 실행 흐름
# ============================================================
def choose_mode():
    """1(사용자 입력) 또는 2(data.json 분석)를 받을 때까지 묻는다."""
    print("=== Mini NPU Simulator ===")
    print()
    print("[모드 선택]")
    print()
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    while True:
        choice = read_line("선택: ")
        if choice in ("1", "2"):
            return int(choice)
        print("⚠️ 잘못된 입력입니다. 1 또는 2를 입력하세요.")


def main():
    use_utf8_io()
    try:
        mode = choose_mode()
        if mode == 1:
            run_user_mode()
        else:
            run_json_mode()
    except ExitRequested:
        print("⚠️ 입력이 중단되어 안전하게 종료합니다.")


if __name__ == "__main__":
    main()
