import re
from typing import Optional

from telegram_max_bot.core.models import Topic


TOPIC_CLASSIFIER_VERSION = "2026-05-29-2"

TOPICS: tuple[Topic, ...] = (
    Topic(
        code="rs",
        title="Жизнь рядом с РС",
        description="Болезнь, инвалидность, семья и жизнь рядом с хроническим диагнозом.",
        keywords=(
            "рассеянн",
            "склероз",
            "рс",
            "инвалид",
            "болезн",
            "диагноз",
            "обострен",
            "трость",
            "коляск",
            "мсэ",
            "невролог",
            "лекарств",
            "муж бол",
        ),
    ),
    Topic(
        code="family",
        title="Брак и семья",
        description="Реальная семья, брак, супруги, быт, любовь, усталость и ответственность.",
        keywords=(
            "брак",
            "семь",
            "муж",
            "жена",
            "супруг",
            "развод",
            "любов",
            "отношен",
            "родител",
            "дом",
            "быт",
            "свекров",
            "тещ",
        ),
    ),
    Topic(
        code="children",
        title="Дети и воспитание",
        description="Дети, подростки, школа, образование, сыновья и родительский опыт.",
        keywords=(
            "дет",
            "ребен",
            "сын",
            "доч",
            "подрост",
            "школ",
            "учител",
            "урок",
            "образован",
            "воспитан",
            "родител",
            "егэ",
            "домашн",
        ),
    ),
    Topic(
        code="women",
        title="Женская роль и границы",
        description="Женская нагрузка, самопожертвование, феминизм, границы и право на себя.",
        keywords=(
            "женщин",
            "матушк",
            "мать",
            "мама",
            "феминизм",
            "феминист",
            "границ",
            "самопожертв",
            "терпеть",
            "удобн",
            "должна",
            "жертв",
            "насили",
        ),
    ),
    Topic(
        code="psychology",
        title="Психология",
        description="Эмоции, травма, вина, стыд, созависимость и психологическая зрелость.",
        keywords=(
            "психолог",
            "травм",
            "эмоци",
            "чувств",
            "созавис",
            "нарцисс",
            "алекситим",
            "вина",
            "стыд",
            "страх",
            "депресс",
            "тревог",
            "границ",
            "принят",
        ),
    ),
    Topic(
        code="faith",
        title="Вера без насилия",
        description="Православие, вера, церковь, священство и разговор без давления.",
        keywords=(
            "бог",
            "вера",
            "православ",
            "церков",
            "храм",
            "священ",
            "батюшк",
            "приход",
            "молитв",
            "грех",
            "смирен",
            "духовн",
            "христиан",
        ),
    ),
    Topic(
        code="daily",
        title="Быт и повседневность",
        description="Обычная жизнь, работа, деньги, усталость, дом и маленькие решения.",
        keywords=(
            "деньги",
            "работ",
            "устал",
            "магазин",
            "кухн",
            "готов",
            "квартир",
            "уборк",
            "покупк",
            "зарплат",
            "быт",
            "дом",
            "повседнев",
        ),
    ),
    Topic(
        code="culture",
        title="Москва и культура",
        description="Город, книги, фильмы, культура, прогулки, места и впечатления.",
        keywords=(
            "москв",
            "город",
            "музе",
            "театр",
            "книг",
            "фильм",
            "сериал",
            "литератур",
            "искусств",
            "культур",
            "прогулк",
            "парк",
            "выставк",
        ),
    ),
)

TOPICS_BY_CODE = {topic.code: topic for topic in TOPICS}


def get_topic_by_code(code: str) -> Optional[Topic]:
    return TOPICS_BY_CODE.get(code.strip().lower())


def classify_topics(
    *,
    title: str,
    summary: str,
    content_text: str,
    categories: str,
) -> list[tuple[Topic, int]]:
    title_text = _normalize(title)
    body_text = _normalize(" ".join([summary, content_text, categories]))
    matches: list[tuple[Topic, int]] = []

    for topic in TOPICS:
        score = 0
        for keyword in topic.keywords:
            normalized_keyword = _normalize(keyword)
            score += _keyword_count(title_text, normalized_keyword) * 3
            score += _keyword_count(body_text, normalized_keyword)

        if score > 0:
            matches.append((topic, score))

    return sorted(matches, key=lambda item: (-item[1], item[0].title))


def _normalize(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def _keyword_count(text: str, keyword: str) -> int:
    if " " in keyword:
        return text.count(keyword)

    pattern = rf"(?<![0-9a-zа-я]){re.escape(keyword)}[0-9a-zа-я]*"
    return len(re.findall(pattern, text))
