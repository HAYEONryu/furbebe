"""Synthetic relational data for read contracts; never used against DEV."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import insert

from backend.app.db.models import Animal, AnimalImage, AnimalTag, Shelter, SyncRun, Tag

TODAY = date(2026, 9, 16)
NOW = datetime(2026, 9, 16, 3, tzinfo=UTC)
KST_START = datetime(2026, 9, 15, 15, tzinfo=UTC)
SENTINEL = "PRIVATE_RAW_ONLY_FIXTURE"
WEIGHTS = [0, 5, "5.01", 10, "10.01", 20, "20.01", None]
YEARS = [2026, 2025, 2024, 2022, 2021, 2018, 2016, None]


def seed(connection):
    shelters = [
        {
            "id": UUID(int=1000),
            "source": "national_animal_api",
            "source_id": "shelter-a",
            "name": "달빛_보호소",
            "organization": "보호소 주소는 동물 지역이 아님",
        },
        {
            "id": UUID(int=1001),
            "source": "national_animal_api",
            "source_id": "shelter-b",
            "name": "햇빛 보호소",
            "organization": "다른 관할",
        },
    ]
    connection.execute(insert(Shelter), shelters)
    animals, images, tags = [], [], []
    for i in range(40):
        index = i % 8
        org = "서울특별시 강남구" if i % 2 == 0 else "경기도 수원시"
        if i == 2:
            org = "세종특별자치시"
        if i == 7:
            org = "미확인 지역 원문"
        seen = KST_START - timedelta(days=1)
        if i == 0:
            seen = KST_START
        elif i == 1:
            seen = KST_START - timedelta(microseconds=1)
        elif i == 2:
            seen = KST_START + timedelta(days=1)
        raw = {"orgNm": org, "extra_secret": SENTINEL}
        if i == 0:
            raw.update(
                adptnTitle="합성 입양 안내",
                adptnSDate="20260910",
                adptnImg="https://example.invalid/adoption.jpg",
            )
        animals.append(
            {
                "id": UUID(int=i + 1),
                "source": "national_animal_api",
                "source_id": f"fixture-{i}",
                "raw_payload": raw,
                "notice_no": f"test-{i}",
                "species": "dog",
                "breed": "100% 친구" if i == 0 else "말티즈" if i % 2 == 0 else "믹스견",
                "breed_full": "[개] 합성",
                "sex": "female" if i % 2 == 0 else "male",
                "neutered": "yes" if i % 3 == 0 else "unknown",
                "birth_year": YEARS[index],
                "age_text": None if YEARS[index] is None else f"{YEARS[index]}(년생)",
                "weight_kg": None if WEIGHTS[index] is None else Decimal(str(WEIGHTS[index])),
                "weight_text": None if WEIGHTS[index] is None else f"{WEIGHTS[index]}(Kg)",
                "color_text": "흰색",
                "found_date": TODAY - timedelta(days=i // 4),
                "notice_start": TODAY - timedelta(days=10 if i % 2 == 0 else 9),
                "notice_end": None if i == 7 else TODAY + timedelta(days=i % 3),
                "process_state": "종료(반환)"
                if i == 5
                else "신규 원문 상태"
                if i == 6
                else "보호중",
                "shelter_id": None if i == 7 else UUID(int=1000 + i % 2),
                "special_mark": None,
                "social_text": "관찰 원문" if i == 0 else None,
                "health_text": None,
                "first_seen_at": seen,
                "last_seen_at": max(seen, NOW),
                "source_updated_at": None if i % 2 else NOW - timedelta(hours=i),
            }
        )
        if i != 7:
            for n in range(2):
                images.append(
                    {
                        "id": UUID(int=2000 + i * 2 + n),
                        "animal_id": UUID(int=i + 1),
                        "image_url": f"https://example.invalid/{i}-{n}.jpg",
                        "sort_order": n,
                        "image_type": "source",
                    }
                )
        tags.append(
            {
                "id": UUID(int=3000 + i),
                "animal_id": UUID(int=i + 1),
                "tag_key": "white",
                "confidence": Decimal("1"),
                "generator": "rules",
                "generator_version": "1.0",
                "evidence": "흰색",
                "created_at": NOW,
            }
        )
        if i < 2 or i == 6:
            tags.append(
                {
                    "id": UUID(int=4000 + i),
                    "animal_id": UUID(int=i + 1),
                    "tag_key": "puppy",
                    "confidence": Decimal("1"),
                    "generator": "rules",
                    "generator_version": "1.0",
                    "evidence": "관측 연도 근거",
                    "created_at": NOW,
                }
            )
    # An animal with absent values must serialize nulls, not invented replacements.
    animals[7].update(
        sex=None, neutered=None, breed=None, breed_full=None, color_text=None, notice_no=None
    )
    connection.execute(insert(Animal), animals)
    connection.execute(insert(AnimalImage), images)
    connection.execute(
        insert(Tag),
        [
            {"key": "white", "type": "fact", "label": "흰색", "is_active": True},
            {"key": "puppy", "type": "fact", "label": "추정 1세 이하", "is_active": True},
            {"key": "manual", "type": "trait", "label": "수동 확인", "is_active": True},
            {"key": "inactive", "type": "vibe", "label": "비활성", "is_active": False},
        ],
    )
    tags.extend(
        [
            {
                "id": UUID(int=5000),
                "animal_id": UUID(int=1),
                "tag_key": "white",
                "confidence": Decimal("0.8"),
                "generator": "manual",
                "generator_version": "1",
                "evidence": "최신 수동 근거",
                "created_at": NOW + timedelta(seconds=1),
            },
            {
                "id": UUID(int=5001),
                "animal_id": UUID(int=1),
                "tag_key": "inactive",
                "confidence": Decimal("1"),
                "generator": "manual",
                "generator_version": "1",
                "evidence": "미노출",
                "created_at": NOW,
            },
        ]
    )
    connection.execute(insert(AnimalTag), tags)
    connection.execute(
        insert(SyncRun),
        [
            {
                "id": UUID(int=6000),
                "source": "national_animal_api",
                "status": "success",
                "started_at": NOW - timedelta(minutes=2),
                "finished_at": NOW - timedelta(minutes=1),
            },
            {
                "id": UUID(int=6001),
                "source": "national_animal_api",
                "status": "failed",
                "started_at": NOW - timedelta(seconds=2),
                "finished_at": NOW,
            },
        ],
    )
    return animals
