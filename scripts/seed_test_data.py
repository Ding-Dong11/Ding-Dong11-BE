"""
테스트 데이터 시드 스크립트 — raw SQL INSERT 버전
대전 유성구 어은동·봉명동 (충남대 앞 상권) 기준
  - sale_stores       : 30개
  - sale_store_hours  : 각 7일치
  - sale_products     : 각 24개 (합계 720개)
  - coupons           : 50개

실행: .venv/bin/python scripts/seed_test_data.py
      (또는 uv run python scripts/seed_test_data.py)
"""
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core.database import get_engine

KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=KST)

DEADLINES = {
    "soon":  NOW + timedelta(hours=3),
    "today": NOW + timedelta(hours=12),
    "week":  NOW + timedelta(days=7),
    "two":   NOW + timedelta(days=14),
}

# ── 중심 좌표: 대전 유성구 대학로 76 (충남대 정문 앞) ─────────────────────────
BASE_LAT = 36.3703
BASE_LON = 127.3453

# ── 30개 상점 (이름, Δlat, Δlon, 유형) ────────────────────────────────────────
STORES_DEF: list[tuple[str, float, float, str]] = [
    # 편의점 (5)
    ("CU 충남대점",              0.000,  0.001, "편의점"),
    ("GS25 어은동점",            0.002,  0.000, "편의점"),
    ("세븐일레븐 충남대앞점",   -0.001,  0.002, "편의점"),
    ("이마트24 봉명점",          0.003, -0.001, "편의점"),
    ("미니스톱 어은점",         -0.002,  0.003, "편의점"),
    # 빵집 (5)
    ("파리바게뜨 충남대점",      0.001,  0.004, "빵집"),
    ("뚜레쥬르 어은동점",        0.004,  0.001, "빵집"),
    ("성심당 어은분점",         -0.003,  0.001, "빵집"),
    ("리치몬드 과자점 어은점",   0.002,  0.005, "빵집"),
    ("봄봄 베이커리",            0.005,  0.000, "빵집"),
    # 카페 (5)
    ("스타벅스 충남대점",        0.000,  0.005, "카페"),
    ("이디야커피 어은점",       -0.004,  0.002, "카페"),
    ("투썸플레이스 충남대점",    0.003,  0.004, "카페"),
    ("메가MGC커피 어은점",       0.001, -0.003, "카페"),
    ("할리스 봉명점",           -0.002, -0.002, "카페"),
    # 분식·한식 (5)
    ("김밥천국 충남대점",        0.004, -0.003, "분식"),
    ("이삭토스트 어은점",       -0.003,  0.004, "분식"),
    ("봄날떡볶이 어은동점",      0.005,  0.003, "분식"),
    ("어은동 순대국밥",         -0.001, -0.004, "분식"),
    ("충대앞 반찬가게",          0.002, -0.005, "분식"),
    # 치킨 (5)
    ("BBQ 충남대점",            -0.005,  0.001, "치킨"),
    ("교촌치킨 어은점",          0.000, -0.004, "치킨"),
    ("굽네치킨 봉명점",         -0.004, -0.002, "치킨"),
    ("자담치킨 어은동점",        0.003, -0.005, "치킨"),
    ("60계치킨 충남대점",       -0.003, -0.003, "치킨"),
    # 마트·과일 (5)
    ("하나로마트 어은점",        0.005, -0.004, "마트"),
    ("어은동 청과물 가게",      -0.005, -0.001, "마트"),
    ("봄내음 반찬 마트",         0.001,  0.006, "마트"),
    ("어은동 정육점",           -0.002,  0.005, "마트"),
    ("충남대 앞 수산가게",       0.006,  0.002, "마트"),
]

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
OPEN_T  = time(9, 0)
CLOSE_T = time(22, 0)

# ── 상품 템플릿 (유형 → 24개) : (상품명, 정가, 할인가, 재고, 마감키) ─────────
PRODUCTS: dict[str, list[tuple[str, int, int, int, str]]] = {
    "편의점": [
        ("코카콜라 1.5L",       2500, 1800, 40, "week"),
        ("펩시콜라 1.5L",       2300, 1600, 35, "week"),
        ("새우깡 90g",          1500,  900, 60, "today"),
        ("꼬깔콘 72g",          1600,  950, 50, "today"),
        ("불닭볶음면 5개입",    7500, 5000, 30, "week"),
        ("신라면 5개입",        5500, 3800, 30, "week"),
        ("삼각김밥 참치마요",   1500,  900, 80, "today"),
        ("삼각김밥 불고기",     1500,  850, 70, "today"),
        ("핫바 70g",            1500,  800, 60, "soon"),
        ("치킨마요 도시락",     5000, 3200, 20, "soon"),
        ("비빔밥 도시락",       5500, 3500, 20, "soon"),
        ("메로나 6개입",        5000, 3500, 25, "week"),
        ("설레임 1개",          1800, 1100, 40, "week"),
        ("포카리스웨트 500ml",  1800, 1200, 50, "week"),
        ("게토레이 600ml",      2000, 1300, 45, "week"),
        ("레드불 250ml",        3000, 2200, 30, "week"),
        ("바나나우유 240ml",    1800, 1100, 50, "today"),
        ("초코우유 200ml",      1500,  900, 50, "today"),
        ("허니버터칩 55g",      1800, 1200, 45, "week"),
        ("꼬북칩 65g",          1800, 1200, 45, "week"),
        ("스팸 클래식 200g",    6500, 4500, 20, "two"),
        ("참치캔 150g×3",       9000, 6200, 15, "two"),
        ("비요뜨 딸기",         2000, 1300, 35, "today"),
        ("오레오 쿠키 100g",    3000, 2100, 40, "week"),
    ],
    "빵집": [
        ("크로아상",            3500, 2500, 30, "today"),
        ("단팥빵",              2500, 1500, 40, "today"),
        ("소보루빵",            2500, 1500, 40, "today"),
        ("슈크림빵",            3000, 2000, 35, "today"),
        ("치즈케이크 1조각",    5500, 3500, 20, "today"),
        ("티라미수 1조각",      6000, 4000, 15, "today"),
        ("딸기케이크 홀",      35000,24000,  5, "today"),
        ("생크림케이크 홀",    30000,20000,  5, "today"),
        ("식빵 1봉",            5000, 3200, 25, "today"),
        ("마늘바게트",          6000, 4000, 20, "today"),
        ("모카번",              3500, 2200, 30, "today"),
        ("플레인 베이글",       3000, 2000, 25, "today"),
        ("크림치즈 베이글",     4000, 2600, 20, "today"),
        ("초코 머핀",           3500, 2000, 30, "today"),
        ("블루베리 머핀",       3500, 2000, 30, "today"),
        ("글레이즈 도넛",       2000, 1200, 35, "today"),
        ("초코 도넛",           2500, 1500, 30, "today"),
        ("사과 파이",           4000, 2500, 20, "today"),
        ("쿠키 6개 세트",       8000, 5500, 15, "today"),
        ("아메리카노 (R)",      4500, 3000, 50, "today"),
        ("카페라떼 (R)",        5000, 3500, 40, "today"),
        ("아이스티",            4000, 2800, 35, "today"),
        ("딸기 스무디",         6000, 4200, 20, "today"),
        ("레몬 에이드",         5500, 3800, 25, "today"),
    ],
    "카페": [
        ("아메리카노 (R)",      4500, 3200, 60, "today"),
        ("아메리카노 (L)",      5000, 3600, 50, "today"),
        ("카페라떼 (R)",        5000, 3500, 50, "today"),
        ("바닐라라떼 (R)",      5500, 3800, 40, "today"),
        ("카푸치노 (R)",        5000, 3500, 40, "today"),
        ("카라멜마키아토 (R)",  6000, 4200, 35, "today"),
        ("에스프레소 더블",     3500, 2400, 30, "today"),
        ("콜드브루 (R)",        5500, 3800, 30, "today"),
        ("플랫화이트",          5500, 3800, 25, "today"),
        ("말차라떼 (R)",        5500, 3800, 35, "today"),
        ("초코라떼 (R)",        5500, 3800, 35, "today"),
        ("딸기라떼 (R)",        6000, 4200, 30, "today"),
        ("레몬에이드 (R)",      5500, 3800, 40, "today"),
        ("자몽에이드 (R)",      5500, 3800, 40, "today"),
        ("복숭아아이스티 (R)",  5000, 3500, 45, "today"),
        ("치즈케이크 1조각",    7000, 5000, 15, "today"),
        ("티라미수 1조각",      7500, 5200, 12, "today"),
        ("스콘",                4000, 2800, 20, "today"),
        ("크로플",              5000, 3500, 18, "today"),
        ("BLT 샌드위치",        7000, 4800, 15, "today"),
        ("소세지롤",            4500, 3000, 20, "today"),
        ("와플",                6000, 4200, 15, "today"),
        ("바나나케이크 1조각",  6500, 4500, 12, "today"),
        ("쿠키 2개",            3000, 2000, 30, "today"),
    ],
    "분식": [
        ("떡볶이 1인분",        4000, 2800, 50, "today"),
        ("떡볶이 2인분",        7000, 5000, 30, "today"),
        ("순대 1인분",          4000, 2800, 40, "today"),
        ("어묵 1인분",          3500, 2500, 40, "today"),
        ("튀김 5개 모둠",       4000, 2800, 45, "today"),
        ("라볶이 1인분",        5000, 3500, 30, "today"),
        ("참치마요 김밥 1줄",   3500, 2200, 60, "today"),
        ("소고기 김밥 1줄",     4000, 2500, 50, "today"),
        ("충무김밥 1인분",      5000, 3500, 30, "today"),
        ("에그치즈 토스트",     3500, 2500, 40, "soon"),
        ("햄치즈 토스트",       3500, 2500, 40, "soon"),
        ("불고기 토스트",       4000, 2800, 35, "soon"),
        ("순대국밥 1그릇",      8000, 5500, 20, "today"),
        ("설렁탕 1그릇",        9000, 6500, 15, "today"),
        ("콩나물국밥 1그릇",    7000, 5000, 20, "today"),
        ("제육덮밥 1인분",      8500, 6000, 18, "today"),
        ("돈까스 1인분",       10000, 7000, 15, "today"),
        ("비빔밥 1인분",        8000, 5500, 18, "today"),
        ("된장찌개 1인분",      7000, 5000, 20, "today"),
        ("부대찌개 1인분",      9000, 6500, 12, "today"),
        ("반찬 모둠 3종",       5000, 3500, 25, "two"),
        ("깍두기 500g",         3000, 2000, 30, "two"),
        ("배추김치 500g",       5000, 3500, 25, "two"),
        ("멸치볶음 200g",       4000, 2800, 20, "two"),
    ],
    "치킨": [
        ("후라이드 치킨 한마리",18000,13000, 15, "today"),
        ("양념 치킨 한마리",   19000,14000, 12, "today"),
        ("반반 치킨",          19000,14000, 12, "today"),
        ("파닭 한마리",        20000,14000, 10, "today"),
        ("갈릭 치킨 한마리",   20000,14500, 10, "today"),
        ("핫 스파이시 한마리", 18000,13000, 12, "today"),
        ("간장 치킨 한마리",   19000,14000, 12, "today"),
        ("후라이드 반마리",    10000, 7000, 20, "today"),
        ("양념 반마리",        10500, 7500, 18, "today"),
        ("순살 치킨 300g",     13000, 9000, 15, "today"),
        ("뿌링클 한마리",      19000,14000, 12, "today"),
        ("올리브 치킨 한마리", 22000,16000,  8, "today"),
        ("닭다리 5개",          9000, 6200, 20, "today"),
        ("닭날개 10개",        12000, 8500, 15, "today"),
        ("닭강정 대",          15000,10500, 12, "today"),
        ("치킨 스낵 박스",      8000, 5500, 18, "today"),
        ("감자튀김 L",          4000, 2800, 25, "today"),
        ("치즈볼 8개",          5000, 3500, 20, "today"),
        ("웨지감자 L",          4500, 3000, 22, "today"),
        ("코울슬로",            3000, 1800, 25, "today"),
        ("치킨무 3개",          2000, 1200, 30, "today"),
        ("탄산음료 1.5L",       3000, 1800, 30, "week"),
        ("치킨+콜라 세트",     22000,16000,  8, "today"),
        ("땡초 치킨 한마리",   20000,14500, 10, "today"),
    ],
    "마트": [
        ("사과 5개 봉지",       8000, 5500, 30, "week"),
        ("배 3개 봉지",         9000, 6500, 20, "week"),
        ("딸기 500g 팩",        8000, 5500, 25, "today"),
        ("포도 1송이",          6000, 4000, 20, "today"),
        ("바나나 1송이",        3500, 2400, 30, "week"),
        ("방울토마토 500g",     5000, 3500, 25, "today"),
        ("오이 5개",            3000, 2000, 30, "week"),
        ("호박 1개",            2500, 1600, 25, "week"),
        ("양배추 1통",          4000, 2800, 20, "week"),
        ("감자 1kg",            4000, 2800, 25, "week"),
        ("고구마 1kg",          5000, 3500, 20, "week"),
        ("양파 1.5kg",          4500, 3000, 20, "week"),
        ("삼겹살 300g",        12000, 8500, 15, "today"),
        ("목살 300g",          11000, 7800, 15, "today"),
        ("소고기 불고기 300g", 18000,13000, 10, "today"),
        ("닭가슴살 200g×2",     8000, 5500, 20, "today"),
        ("고등어 2마리",        6000, 4200, 15, "today"),
        ("갈치 2마리",          9000, 6500, 12, "today"),
        ("꽃게 500g",          12000, 8500, 10, "today"),
        ("냉동새우 500g",      10000, 7000, 12, "week"),
        ("달걀 30개 특란",      8500, 6000, 20, "week"),
        ("두부 300g×2",         4000, 2800, 25, "week"),
        ("콩나물 300g",         2000, 1300, 30, "today"),
        ("우유 1L",             3000, 2100, 30, "week"),
    ],
}

# ── 쿠폰 50개 ─────────────────────────────────────────────────────────────────
_PH = "https://placehold.co/400x300"
COUPONS_DEF: list[tuple[str, int, str, str]] = [
    # 스타벅스 (5)
    ("스타벅스 아메리카노 R 1잔",      4500, "스타벅스 아메리카노 R사이즈 교환권",      f"{_PH}/006241/white?text=STARBUCKS"),
    ("스타벅스 카페라떼 R 1잔",        5000, "스타벅스 카페라떼 R사이즈 교환권",        f"{_PH}/006241/white?text=STARBUCKS"),
    ("스타벅스 케이크 1조각",          6500, "스타벅스 케이크류 1조각 교환권",          f"{_PH}/006241/white?text=STARBUCKS"),
    ("스타벅스 프라푸치노 R 1잔",      7500, "스타벅스 프라푸치노 R사이즈 교환권",      f"{_PH}/006241/white?text=STARBUCKS"),
    ("스타벅스 1만원 상품권",         10000, "스타벅스 1만원권 교환권",                  f"{_PH}/006241/white?text=STARBUCKS"),
    # 이디야 (3)
    ("이디야 아메리카노 M 1잔",        2500, "이디야커피 아메리카노 M사이즈 교환권",     f"{_PH}/003087/white?text=EDIYA"),
    ("이디야 카페라떼 M 1잔",          3000, "이디야커피 카페라떼 M사이즈 교환권",       f"{_PH}/003087/white?text=EDIYA"),
    ("이디야 5천원 상품권",            5000, "이디야커피 5천원권 교환권",                f"{_PH}/003087/white?text=EDIYA"),
    # 투썸 (3)
    ("투썸 아메리카노 R 1잔",          4500, "투썸플레이스 아메리카노 R 교환권",         f"{_PH}/8B1A1A/white?text=TWOSOME"),
    ("투썸 딸기케이크 1조각",          7000, "투썸플레이스 딸기케이크 1조각 교환권",     f"{_PH}/8B1A1A/white?text=TWOSOME"),
    ("투썸 1만원 상품권",             10000, "투썸플레이스 1만원권 교환권",              f"{_PH}/8B1A1A/white?text=TWOSOME"),
    # 메가MGC (2)
    ("메가커피 아메리카노 L 1잔",      2000, "메가MGC커피 아메리카노 L 교환권",          f"{_PH}/F5A623/black?text=MEGA"),
    ("메가커피 카페라떼 L 1잔",        2500, "메가MGC커피 카페라떼 L 교환권",            f"{_PH}/F5A623/black?text=MEGA"),
    # 배스킨라빈스 (3)
    ("배스킨 패인트컵 1개",            7000, "배스킨라빈스 패인트컵 교환권",             f"{_PH}/FF69B4/white?text=BASKIN"),
    ("배스킨 쿼터컵 1개",              6000, "배스킨라빈스 쿼터컵 교환권",               f"{_PH}/FF69B4/white?text=BASKIN"),
    ("배스킨 아이스크림 케이크",      25000, "배스킨라빈스 아이스크림 케이크 교환권",    f"{_PH}/FF69B4/white?text=BASKIN"),
    # 파리바게뜨 (3)
    ("파리바게뜨 케이크 1조각",        5000, "파리바게뜨 케이크 1조각 교환권",           f"{_PH}/C41230/white?text=PB"),
    ("파리바게뜨 샌드위치",            5500, "파리바게뜨 샌드위치류 교환권",             f"{_PH}/C41230/white?text=PB"),
    ("파리바게뜨 1만원 상품권",       10000, "파리바게뜨 1만원권 교환권",                f"{_PH}/C41230/white?text=PB"),
    # 맥도날드 (3)
    ("맥도날드 빅맥 단품",             5200, "맥도날드 빅맥 단품 교환권",                f"{_PH}/FFC72C/black?text=McDo"),
    ("맥도날드 빅맥세트",              7500, "맥도날드 빅맥 세트 교환권",                f"{_PH}/FFC72C/black?text=McDo"),
    ("맥도날드 맥카페 아메리카노",     3000, "맥도날드 맥카페 아메리카노 교환권",        f"{_PH}/FFC72C/black?text=McDo"),
    # 버거킹 (3)
    ("버거킹 와퍼 단품",               6000, "버거킹 와퍼 단품 교환권",                  f"{_PH}/D62300/white?text=BK"),
    ("버거킹 와퍼세트",                9000, "버거킹 와퍼 세트 교환권",                  f"{_PH}/D62300/white?text=BK"),
    ("버거킹 치킨버거 세트",           8000, "버거킹 치킨버거 세트 교환권",              f"{_PH}/D62300/white?text=BK"),
    # 롯데리아 (2)
    ("롯데리아 한우버거 단품",         5500, "롯데리아 한우불고기버거 단품 교환권",       f"{_PH}/E60026/white?text=Lotteria"),
    ("롯데리아 세트",                  8000, "롯데리아 세트 교환권",                      f"{_PH}/E60026/white?text=Lotteria"),
    # 교촌 (3)
    ("교촌 레드 오리지날 한마리",     20000, "교촌치킨 레드 오리지날 한마리 교환권",     f"{_PH}/8B4513/white?text=KYOCHON"),
    ("교촌 허니 콤보",                22000, "교촌치킨 허니 콤보 교환권",                f"{_PH}/8B4513/white?text=KYOCHON"),
    ("교촌 반반 한마리",              20000, "교촌치킨 반반 한마리 교환권",              f"{_PH}/8B4513/white?text=KYOCHON"),
    # BBQ (3)
    ("BBQ 황금올리브 한마리",         22000, "BBQ 황금올리브치킨 한마리 교환권",         f"{_PH}/FF6600/white?text=BBQ"),
    ("BBQ 후라이드 한마리",           18000, "BBQ 후라이드치킨 한마리 교환권",           f"{_PH}/FF6600/white?text=BBQ"),
    ("BBQ 양념치킨 한마리",           19000, "BBQ 양념치킨 한마리 교환권",               f"{_PH}/FF6600/white?text=BBQ"),
    # CU (3)
    ("CU 5천원 상품권",                5000, "CU편의점 5천원 상품권",                    f"{_PH}/007BBE/white?text=CU"),
    ("CU 1만원 상품권",               10000, "CU편의점 1만원 상품권",                    f"{_PH}/007BBE/white?text=CU"),
    ("CU 2만원 상품권",               20000, "CU편의점 2만원 상품권",                    f"{_PH}/007BBE/white?text=CU"),
    # GS25 (3)
    ("GS25 5천원 상품권",              5000, "GS25 편의점 5천원 상품권",                 f"{_PH}/0047AB/white?text=GS25"),
    ("GS25 1만원 상품권",             10000, "GS25 편의점 1만원 상품권",                 f"{_PH}/0047AB/white?text=GS25"),
    ("GS25 2만원 상품권",             20000, "GS25 편의점 2만원 상품권",                 f"{_PH}/0047AB/white?text=GS25"),
    # 올리브영 (2)
    ("올리브영 1만원 상품권",         10000, "올리브영 1만원 상품권",                    f"{_PH}/00A550/white?text=OliveYoung"),
    ("올리브영 3만원 상품권",         30000, "올리브영 3만원 상품권",                    f"{_PH}/00A550/white?text=OliveYoung"),
    # 신세계·이마트 (2)
    ("신세계 1만원 상품권",           10000, "신세계백화점 1만원 상품권",                f"{_PH}/1C1C1C/white?text=Shinsegae"),
    ("이마트 1만원 상품권",           10000, "이마트 1만원 상품권",                      f"{_PH}/1C1C1C/white?text=Emart"),
    # 다이소 (2)
    ("다이소 5천원 상품권",            5000, "다이소 5천원 상품권",                      f"{_PH}/E60026/white?text=Daiso"),
    ("다이소 1만원 상품권",           10000, "다이소 1만원 상품권",                      f"{_PH}/E60026/white?text=Daiso"),
    # 넷플릭스·왓챠 (2)
    ("넷플릭스 1개월 이용권",         17000, "넷플릭스 스탠다드 1개월 교환권",           f"{_PH}/E50914/white?text=Netflix"),
    ("왓챠 1개월 이용권",              7900, "왓챠 1개월 이용권 교환권",                 f"{_PH}/FF0558/white?text=Watcha"),
    # T머니 (2)
    ("T머니 충전 5천원",               5000, "T머니 교통카드 충전 5천원권",              f"{_PH}/00AEEF/white?text=Tmoney"),
    ("T머니 충전 1만원",              10000, "T머니 교통카드 충전 1만원권",              f"{_PH}/00AEEF/white?text=Tmoney"),
    # GS칼텍스 (2)
    ("GS칼텍스 주유권 1만원",         10000, "GS칼텍스 주유권 1만원",                   f"{_PH}/0047AB/white?text=GS+Caltex"),
    ("GS칼텍스 주유권 3만원",         30000, "GS칼텍스 주유권 3만원",                   f"{_PH}/0047AB/white?text=GS+Caltex"),
]


def seed() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        # ── 기존 시드 데이터 정리 ────────────────────────────────────────────
        print("▶ 기존 시드 데이터 삭제 중...")
        conn.execute(text("""
            DELETE FROM sale_products
             WHERE sale_store_id IN (
               SELECT sale_store_id FROM sale_stores
                WHERE name ~ '충남대|어은|봉명|성심당|봄봄|하나로마트|봄내음'
             )
        """))
        conn.execute(text("""
            DELETE FROM sale_store_hours
             WHERE sale_store_id IN (
               SELECT sale_store_id FROM sale_stores
                WHERE name ~ '충남대|어은|봉명|성심당|봄봄|하나로마트|봄내음'
             )
        """))
        conn.execute(text("""
            DELETE FROM sale_stores
             WHERE name ~ '충남대|어은|봉명|성심당|봄봄|하나로마트|봄내음'
        """))
        conn.execute(text("""
            DELETE FROM coupons
             WHERE name ~ '^(스타벅스|이디야|투썸|메가커피|배스킨|파리바게뜨|맥도날드|버거킹|롯데리아|교촌|BBQ|CU|GS25|올리브영|신세계|이마트|다이소|넷플릭스|왓챠|T머니|GS칼텍스)'
        """))

        # ── sale_stores + hours + products ──────────────────────────────────
        print("▶ sale_stores 30개 + 영업시간 + 할인상품 적재 중...")
        store_count = 0
        product_count = 0

        for store_name, dlat, dlon, store_type in STORES_DEF:
            lat = round(BASE_LAT + dlat, 7)
            lon = round(BASE_LON + dlon, 7)

            row = conn.execute(
                text("""
                    INSERT INTO sale_stores (store_id, name, adong_code, longitude, latitude)
                    VALUES (NULL, :name, NULL, :lon, :lat)
                    RETURNING sale_store_id
                """),
                {"name": store_name, "lon": lon, "lat": lat},
            ).fetchone()
            sid = row[0]

            # 영업시간 7일
            for day in DAYS:
                conn.execute(
                    text("""
                        INSERT INTO sale_store_hours (sale_store_id, day_of_week, open_time, close_time)
                        VALUES (:sid, :day, :open, :close)
                    """),
                    {"sid": sid, "day": day, "open": OPEN_T, "close": CLOSE_T},
                )

            # 할인상품 24개
            for prod_name, orig, sale, stock, dl_key in PRODUCTS[store_type]:
                conn.execute(
                    text("""
                        INSERT INTO sale_products
                            (sale_store_id, small_code, name, original_price, sale_price,
                             stock_quantity, image_url, sale_deadline, status)
                        VALUES
                            (:sid, NULL, :name, :orig, :sale,
                             :stock, NULL, :deadline, 'ON_SALE')
                    """),
                    {
                        "sid": sid,
                        "name": prod_name,
                        "orig": orig,
                        "sale": sale,
                        "stock": stock,
                        "deadline": DEADLINES[dl_key],
                    },
                )
                product_count += 1

            store_count += 1

        print(f"   상점 {store_count}개 / 상품 {product_count}개 완료")

        # ── coupons ──────────────────────────────────────────────────────────
        print("▶ coupons 50개 적재 중...")
        for coupon_name, point_price, desc, img_url in COUPONS_DEF:
            conn.execute(
                text("""
                    INSERT INTO coupons (name, image_url, point_price, description, is_active)
                    VALUES (:name, :img, :price, :desc, true)
                """),
                {"name": coupon_name, "img": img_url, "price": point_price, "desc": desc},
            )

        print(f"   쿠폰 {len(COUPONS_DEF)}개 완료")

    print("✅ 시드 데이터 적재 완료")


if __name__ == "__main__":
    seed()
