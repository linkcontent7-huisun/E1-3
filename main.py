"""Mini NPU 시뮬레이터: 그림(숫자 칸)과 필터를 겹쳐 곱하고 더하는 MAC 연산으로 패턴을 판별한다.

실행: python main.py   (Python 3.8 이상, 외부 라이브러리 없음)
"""
import json
import re
import sys
import time
from pathlib import Path

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


# ============================================================
# 4. MAC 연산: 같은 칸끼리 곱하고 전부 더한다 (반복문으로 직접 구현)
# ============================================================
def mac(pattern, filt):
    """pattern과 filt의 같은 위치 값을 곱해서 모두 더한 점수(float)를 돌려준다."""
    score = 0.0
    for r in range(filt.size):
        for c in range(filt.size):
            score += pattern.get(r, c) * filt.get(r, c)
    return score


def judge(score_a, score_b):
    """두 점수를 비교해 'A', 'B', 'UNDECIDED'(동점) 중 하나를 돌려준다. 허용오차 EPSILON을 쓴다."""
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return "A" if score_a > score_b else "B"


def measure_ms(func, repeat=REPEAT):
    """func를 repeat번 실행하고 1회 평균 시간(ms)을 돌려준다. 입출력은 포함하지 않는다."""
    start = time.perf_counter()
    for _ in range(repeat):
        func()
    return (time.perf_counter() - start) * 1000.0 / repeat


# ============================================================
# 5. 라벨 정규화: 여러 표기를 표준 라벨 Cross / X 로 통일한다
# ============================================================
CROSS, X_LABEL, UNDECIDED = "Cross", "X", "UNDECIDED"


def normalize_label(text):
    """'+', 'cross' → Cross, 'x' → X. 그 밖의 값은 ValueError."""
    key = str(text).strip().lower()
    if key in ("+", "cross"):
        return CROSS
    if key == "x":
        return X_LABEL
    raise ValueError("알 수 없는 라벨: {!r}".format(text))


# ============================================================
# 6. 모드 1: 사용자 입력 (3×3)
# ============================================================
def read_row(name, row_index, size):
    """한 줄을 읽어 size개의 숫자로 바꾼다. 틀리면 안내하고 같은 줄을 다시 묻는다."""
    while True:
        text = read_line("{} {}행: ".format(name, row_index + 1))
        parts = text.split()
        if len(parts) != size:
            print("입력 형식 오류: 각 줄에 {}개의 숫자를 공백으로 구분해 입력하세요.".format(size))
            continue
        try:
            return [float(p) for p in parts]
        except ValueError:
            print("입력 형식 오류: 숫자만 입력하세요. (예: 0 1 0)")


def read_grid(name, size=3):
    """size줄을 차례로 받아 Grid를 만든다."""
    print("{} ({}줄 입력, 공백 구분)".format(name, size))
    rows = [read_row(name, r, size) for r in range(size)]
    return Grid.from_rows(rows)


def print_perf_table(sizes):
    """크기별 평균 시간과 연산 횟수(N²)를 표로 보여준다."""
    print("크기     평균 시간(ms)   연산 횟수")
    print("-" * 37)
    for n in sizes:
        pattern = Grid(n, 1.0)
        filt = Grid(n, 1.0)
        avg = measure_ms(lambda: mac(pattern, filt))
        print("{0:<8} {1:<15.4f} {2}".format("{0}×{0}".format(n), avg, n * n))


def run_user_mode():
    """필터 A·B와 패턴을 입력받고, 두 점수로 판정한 뒤 3×3 성능을 보여준다."""
    print()
    print("#----------------------------------------")
    print("# [1] 필터 입력")
    print("#----------------------------------------")
    filter_a = read_grid("필터 A")
    filter_b = read_grid("필터 B")
    print()
    print("#----------------------------------------")
    print("# [2] 패턴 입력")
    print("#----------------------------------------")
    pattern = read_grid("패턴")

    score_a = mac(pattern, filter_a)
    score_b = mac(pattern, filter_b)
    avg_a = measure_ms(lambda: mac(pattern, filter_a))
    avg_b = measure_ms(lambda: mac(pattern, filter_b))
    verdict = judge(score_a, score_b)
    verdict_text = {"A": "A", "B": "B", "UNDECIDED": "판정 불가 (|A-B| < 1e-9)"}[verdict]

    print()
    print("#----------------------------------------")
    print("# [3] MAC 결과")
    print("#----------------------------------------")
    print("A 점수: {}".format(score_a))
    print("B 점수: {}".format(score_b))
    print("연산 시간(평균/{}회): {:.4f} ms (A), {:.4f} ms (B)".format(REPEAT, avg_a, avg_b))
    print("판정: {}".format(verdict_text))
    print()
    print("#----------------------------------------")
    print("# [4] 성능 분석 (3×3)")
    print("#----------------------------------------")
    print_perf_table([3])


# ============================================================
# 7. 모드 2: data.json 분석
# ============================================================
DATA_PATH = Path(__file__).resolve().parent / "data.json"
PERF_SIZES = [3, 5, 13, 25]


def load_data(path):
    """data.json을 읽는다. 파일이 없거나 JSON이 깨졌으면 (None, 안내 문구)를 돌려준다."""
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file), None
    except FileNotFoundError:
        return None, "data.json 파일을 찾을 수 없습니다: {}".format(path)
    except (OSError, ValueError) as error:
        return None, "data.json을 읽을 수 없습니다: {}".format(error)


def grid_from_json(rows):
    """JSON의 2차원 리스트를 Grid로 바꾼다. 형식이 틀리면 ValueError."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("2차원 배열이 아닙니다.")
    return Grid.from_rows(rows)


def check_case(key, case, filters):
    """패턴 한 개를 판정한다. 문제가 생기면 이유(string)를 담은 FAIL 결과를 돌려준다.

    반환: dict(key, n, cross, x, verdict, expected, passed, reason)
    """
    result = {"key": key, "n": None, "cross": None, "x": None,
              "verdict": None, "expected": None, "passed": False, "reason": ""}
    match = re.match(r"^size_(\d+)_\d+$", key)
    if not match:
        result["reason"] = "키 형식 오류: 'size_N_번호' 형태가 아닙니다."
        return result
    n = int(match.group(1))
    result["n"] = n
    try:
        expected = normalize_label(case["expected"])
        result["expected"] = expected
        pattern = grid_from_json(case["input"])
    except (KeyError, ValueError, TypeError) as error:
        result["reason"] = "데이터 오류: {}".format(error)
        return result
    filter_set = filters.get("size_{}".format(n))
    if filter_set is None:
        result["reason"] = "필터 없음: size_{} 필터가 data.json에 없습니다.".format(n)
        return result
    try:
        cross_filter = grid_from_json(filter_set["cross"])
        x_filter = grid_from_json(filter_set["x"])
    except (KeyError, ValueError, TypeError) as error:
        result["reason"] = "필터 오류: {}".format(error)
        return result
    if pattern.size != n or cross_filter.size != n or x_filter.size != n:
        result["reason"] = "크기 불일치: 키는 {0}×{0}인데 패턴 {1}×{1}, 필터 {2}×{2}".format(
            n, pattern.size, cross_filter.size)
        return result

    cross_score = mac(pattern, cross_filter)
    x_score = mac(pattern, x_filter)
    verdict = judge(cross_score, x_score)
    result["cross"], result["x"] = cross_score, x_score
    result["verdict"] = verdict
    if verdict == UNDECIDED:
        result["reason"] = "동점(UNDECIDED)이라 판정할 수 없습니다."
        return result
    verdict_label = CROSS if verdict == "A" else X_LABEL
    result["passed"] = verdict_label == expected
    if not result["passed"]:
        result["reason"] = "판정 {}, 기대값 {}".format(verdict_label, expected)
    return result


def print_case(result):
    """케이스 한 개를 명세 예시 형식으로 출력한다."""
    print("- -- {} ---".format(result["key"]))
    if result["cross"] is None:
        print("FAIL: {}".format(result["reason"]))
        return
    print("Cross 점수: {}".format(result["cross"]))
    print("X 점수: {}".format(result["x"]))
    status = "PASS" if result["passed"] else "FAIL"
    tail = "" if result["passed"] else " ({})".format(result["reason"])
    print("판정: {} | expected: {} | {}{}".format(
        result["verdict"] if result["verdict"] == UNDECIDED else (CROSS if result["verdict"] == "A" else X_LABEL),
        result["expected"], status, tail))


def run_json_mode():
    """data.json을 읽어 모든 패턴을 판정하고, 성능과 결과 요약을 보여준다."""
    data, problem = load_data(DATA_PATH)
    if problem:
        print("⚠️ {}".format(problem))
        return
    filters = data.get("filters", {})
    patterns = data.get("patterns", {})
    print()
    print("#---------------------------------------")
    print("# [1] 필터 로드")
    print("#---------------------------------------")
    for name in sorted(filters):
        print("✓ {} 필터 로드 완료 (Cross, X)".format(name))
    print()
    print("#---------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#---------------------------------------")
    results = [check_case(key, patterns[key], filters) for key in sorted(patterns)]
    for result in results:
        print_case(result)
    print()
    print("#---------------------------------------")
    print("# [3] 성능 분석 (평균/{}회)".format(REPEAT))
    print("#---------------------------------------")
    print_perf_table(PERF_SIZES)
    print()
    print("#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    passed = sum(1 for r in results if r["passed"])
    failed = [r for r in results if not r["passed"]]
    print("총 테스트: {}개".format(len(results)))
    print("통과: {}개".format(passed))
    print("실패: {}개".format(len(failed)))
    if failed:
        print("실패 케이스:")
        for r in failed:
            print("- {}: {}".format(r["key"], r["reason"]))
    print()
    print("#---------------------------------------")
    print("# [5] 보너스: 2차원 vs 1차원 배열 비교 (평균/{}회)".format(REPEAT))
    print("#---------------------------------------")
    print_optimization_table(PERF_SIZES)


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
    print("3. 패턴 생성기 (보너스)")
    while True:
        choice = read_line("선택: ")
        if choice in ("1", "2", "3"):
            return int(choice)
        print("⚠️ 잘못된 입력입니다. 1, 2, 3 중에서 입력하세요.")


# ============================================================
# 8. 보너스 1: 2차원 배열 → 1차원 배열(길이 N²) 최적화 전후 비교
# ============================================================
def flatten(grid):
    """n×n 칸을 한 줄(길이 n²)로 펼친다. 행 순서대로 이어 붙인다."""
    return [value for row in grid.rows for value in row]


def mac_flat(pattern_flat, filter_flat):
    """1차원 배열끼리 같은 위치의 값을 곱해 모두 더한다. 결과는 mac()과 같아야 한다."""
    score = 0.0
    for i in range(len(pattern_flat)):
        score += pattern_flat[i] * filter_flat[i]
    return score


def print_optimization_table(sizes):
    """같은 입력, 같은 반복 횟수로 2차원과 1차원 방식을 재고 점수가 같은지도 확인한다."""
    print("크기     2차원(ms)     1차원(ms)     빨라진 비율  점수 일치")
    print("-" * 66)
    for n in sizes:
        pattern = make_cross(n)
        filt = make_x(n)
        pattern_flat = flatten(pattern)   # 펼치는 준비 작업은 시간 측정에서 뺀다
        filter_flat = flatten(filt)
        avg_2d = measure_ms(lambda: mac(pattern, filt))
        avg_1d = measure_ms(lambda: mac_flat(pattern_flat, filter_flat))
        same = mac(pattern, filt) == mac_flat(pattern_flat, filter_flat)
        ratio = avg_2d / avg_1d if avg_1d > 0 else float("inf")
        print("{0:<8} {1:<13.4f} {2:<13.4f} {3:<12.2f} {4}".format(
            "{0}×{0}".format(n), avg_2d, avg_1d, ratio, "예" if same else "아니오"))


# ============================================================
# 9. 보너스 2: 패턴 생성기 (N×N 십자가 · X 자동 생성)
# ============================================================
def make_cross(n):
    """가운데 행과 가운데 열을 1로 채운 십자가 패턴. n은 홀수 권장."""
    grid = Grid(n, 0.0)
    mid = n // 2
    for r in range(n):
        for c in range(n):
            if r == mid or c == mid:
                grid.set(r, c, 1.0)
    return grid


def make_x(n):
    """두 대각선을 1로 채운 X 패턴."""
    grid = Grid(n, 0.0)
    for r in range(n):
        for c in range(n):
            if r == c or r + c == n - 1:
                grid.set(r, c, 1.0)
    return grid


def show_grid(grid):
    """패턴을 ■(1) □(0) 모양으로 보여준다. 사람이 눈으로 확인하기 쉽게."""
    for r in range(grid.size):
        print(" ".join("■" if grid.get(r, c) == 1.0 else "□" for c in range(grid.size)))


def run_generator_mode():
    """홀수 N(3~25)을 받아 십자가와 X 패턴을 만들고, 두 필터와의 MAC 점수를 보여준다."""
    print()
    while True:
        text = read_line("패턴 크기 N (홀수, 3~25): ")
        if text.isdigit() and 3 <= int(text) <= 25 and int(text) % 2 == 1:
            n = int(text)
            break
        print("⚠️ 잘못된 입력입니다. 3~25 사이의 홀수를 입력하세요.")
    cross = make_cross(n)
    x_shape = make_x(n)
    print()
    print("[십자가 패턴 {0}×{0}]".format(n))
    show_grid(cross)
    print()
    print("[X 패턴 {0}×{0}]".format(n))
    show_grid(x_shape)
    print()
    print("십자가 패턴 vs 십자가 필터: {}".format(mac(cross, make_cross(n))))
    print("십자가 패턴 vs X 필터: {}".format(mac(cross, x_shape)))
    print()
    print("#----------------------------------------")
    print("# 이 크기의 MAC 연산 시간 (평균/{}회)".format(REPEAT))
    print("#----------------------------------------")
    print_perf_table([n])


def main():
    use_utf8_io()
    try:
        mode = choose_mode()
        if mode == 1:
            run_user_mode()
        elif mode == 2:
            run_json_mode()
        else:
            run_generator_mode()
    except ExitRequested:
        print("⚠️ 입력이 중단되어 안전하게 종료합니다.")


if __name__ == "__main__":
    main()
