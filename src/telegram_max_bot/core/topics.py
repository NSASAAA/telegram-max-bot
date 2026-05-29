import re
from typing import Optional

from telegram_max_bot.core.models import Topic


TOPIC_CLASSIFIER_VERSION = "2026-05-30-soft-v3-16"

TOPICS: tuple[Topic, ...] = (
    Topic(
        code="rs_life",
        title="РС и жизнь",
        description="Жизнь рядом с рассеянным склерозом, семья и повседневная адаптация.",
        keywords=(
            "рассеянн",
            "склероз",
            "рс",
            "инвалидност",
            "обострен",
            "как жить с рс",
            "семья и рс",
            "муж бол",
            "супруг бол",
        ),
    ),
    Topic(
        code="rs_treatment",
        title="Терапия РС",
        description="Лечение, препараты, врачи и медицинские решения по РС.",
        keywords=(
            "питрс",
            "невролог",
            "лечение",
            "терапи",
            "лекарств",
            "препарат",
            "ремисси",
            "мрт",
            "мсэ",
            "капельниц",
        ),
    ),
    Topic(
        code="marriage_support",
        title="Любовь и поддержка",
        description="Поддержка в браке, близость, доверие и семейное партнерство.",
        keywords=(
            "брак",
            "муж",
            "жена",
            "супруг",
            "любов",
            "поддерж",
            "забот",
            "довер",
            "вместе",
            "семья",
        ),
    ),
    Topic(
        code="marriage_crisis",
        title="Кризисы брака",
        description="Конфликты, сложные периоды, границы терпения и кризисы в отношениях.",
        keywords=(
            "развод",
            "конфликт",
            "ссора",
            "кризис",
            "скандал",
            "измена",
            "оставить супруга",
            "смирени",
            "обида",
        ),
    ),
    Topic(
        code="family_inlaws",
        title="Свекровь и родня",
        description="Отношения с родственниками, родней и семейными кругами.",
        keywords=(
            "свекров",
            "тещ",
            "родств",
            "родня",
            "мама мужа",
            "золовк",
            "девер",
        ),
    ),
    Topic(
        code="children_parenting",
        title="Малыши и подростки",
        description="Воспитание детей и подростков, взросление и семейные сценарии.",
        keywords=(
            "ребен",
            "дет",
            "малыш",
            "дошколь",
            "подрост",
            "сын",
            "доч",
            "воспитан",
            "взросле",
        ),
    ),
    Topic(
        code="children_education",
        title="Школа и учеба",
        description="Школа, уроки, домашнее обучение и образовательные траектории.",
        keywords=(
            "школ",
            "учител",
            "урок",
            "класс",
            "егэ",
            "оценк",
            "дневник",
            "выпускн",
            "домашн обуч",
            "учится дома",
            "семейн обуч",
        ),
    ),
    Topic(
        code="children_leisure",
        title="Отдых с детьми",
        description="Совместный отдых, семейные фильмы и книги для родителей с детьми.",
        keywords=(
            "с детьми",
            "семейн фильм",
            "мультфильм",
            "детское кино",
            "смотрим фильм",
            "читаем с детьми",
            "что почитать",
            "прогулк с детьми",
        ),
    ),
    Topic(
        code="women_boundaries",
        title="Личные границы",
        description="Границы, право на себя и внутренние опоры в сложных отношениях.",
        keywords=(
            "границ",
            "личное пространство",
            "право на себя",
            "нельзя терпеть",
            "сказать нет",
            "уважение к себе",
        ),
    ),
    Topic(
        code="women_load",
        title="Женская нагрузка",
        description="Перегруз, самопожертвование, эмоциональная и бытовая усталость.",
        keywords=(
            "самопожертв",
            "перегруз",
            "устал",
            "должна",
            "тащу все",
            "жертв",
            "выгор",
            "нагрузк",
            "феминизм",
            "женская роль",
        ),
    ),
    Topic(
        code="psy_narc_trauma",
        title="Нарциссизм и травма",
        description="Нарциссические сценарии, травматический опыт, вина и стыд.",
        keywords=(
            "нарцисс",
            "нарциссизм",
            "абьюз",
            "газлайт",
            "травм",
            "стыд",
            "вина",
            "боль",
            "ранен",
            "исцел",
        ),
    ),
    Topic(
        code="psy_stress_growth",
        title="Стресс и рост",
        description="Стресс, тревога, выгорание, принятие и личностное взросление.",
        keywords=(
            "стресс",
            "тревог",
            "выгор",
            "депресс",
            "паник",
            "осознан",
            "принят",
            "зрелост",
            "развит",
            "опыт",
            "изменил",
        ),
    ),
    Topic(
        code="faith_questions",
        title="Вопросы веры",
        description="Сомнения, смысл, трудные вопросы о вере и духовном пути.",
        keywords=(
            "вера",
            "бог",
            "почему бог",
            "веришь в бога",
            "грех",
            "сомнен",
            "духовник",
            "смирени",
            "можно ли православным",
        ),
    ),
    Topic(
        code="faith_church",
        title="Церковная жизнь",
        description="Храм, литургия, молитва, посты и церковные праздники.",
        keywords=(
            "храм",
            "литурги",
            "молитв",
            "приход",
            "батюшк",
            "исповед",
            "причаст",
            "церков",
            "праздник",
            "пост",
            "покров",
            "рождеств",
            "пасх",
        ),
    ),
    Topic(
        code="moscow_culture",
        title="Москва и культура",
        description="Город, прогулки, маршруты, музеи, театр, кино и книги.",
        keywords=(
            "москв",
            "город",
            "прогулк",
            "район",
            "парк",
            "музе",
            "театр",
            "выставк",
            "культур",
            "экскурси",
            "фильм",
            "кино",
            "книг",
            "литератур",
            "что почитать",
        ),
    ),
    Topic(
        code="money_daily",
        title="Деньги и быт",
        description="Работа, финансы, расходы и повседневная бытовая реальность семьи.",
        keywords=(
            "деньг",
            "зарплат",
            "работ",
            "доход",
            "траты",
            "бюджет",
            "покупк",
            "подработ",
            "быт",
            "дом",
            "кухн",
            "уборк",
            "магазин",
            "квартир",
            "рутин",
        ),
    ),
)

TOPICS_BY_CODE = {topic.code: topic for topic in TOPICS}

# Order used in Telegram topics UI; nearby items should be visually diverse.
TOPIC_DISPLAY_ORDER_CODES: tuple[str, ...] = (
    "marriage_support",
    "rs_life",
    "moscow_culture",
    "women_load",
    "children_education",
    "faith_questions",
    "money_daily",
    "psy_stress_growth",
    "children_parenting",
    "faith_church",
    "marriage_crisis",
    "women_boundaries",
    "rs_treatment",
    "children_leisure",
    "family_inlaws",
    "psy_narc_trauma",
)


def get_topic_by_code(code: str) -> Optional[Topic]:
    return TOPICS_BY_CODE.get(code.strip().lower())


def get_topic_command(topic_code: str) -> str:
    return f"/topic_{topic_code.strip().lower()}"


def get_topic_code_from_command(command: str) -> Optional[str]:
    command_parts = command.strip().split()
    if not command_parts:
        return None

    normalized_command = command_parts[0].split("@")[0].lower()
    if not normalized_command.startswith("/topic_"):
        return None

    topic_code = normalized_command.removeprefix("/topic_")
    if topic_code in TOPICS_BY_CODE:
        return topic_code

    return None


def get_topics_for_display() -> tuple[Topic, ...]:
    display_topics: list[Topic] = []
    used_codes: set[str] = set()

    for code in TOPIC_DISPLAY_ORDER_CODES:
        topic = TOPICS_BY_CODE.get(code)
        if topic is None:
            continue
        display_topics.append(topic)
        used_codes.add(code)

    for topic in TOPICS:
        if topic.code in used_codes:
            continue
        display_topics.append(topic)

    return tuple(display_topics)


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
            score += _keyword_count(title_text, normalized_keyword) * 4
            score += _keyword_count(body_text, normalized_keyword)

        if score > 0:
            matches.append((topic, score))

    sorted_matches = sorted(matches, key=lambda item: (-item[1], item[0].title))
    if not sorted_matches:
        return []

    # Soft mode: article can be placed in several relevant rubrics,
    # but we cap it to keep navigation usable.
    max_topics_per_post = 3
    absolute_score_floor = 2
    primary_score = sorted_matches[0][1]
    relative_score_floor = max(absolute_score_floor, int(primary_score * 0.4))

    filtered_matches: list[tuple[Topic, int]] = []
    for topic, score in sorted_matches:
        if score < absolute_score_floor:
            continue
        if filtered_matches and score < relative_score_floor:
            continue
        filtered_matches.append((topic, score))
        if len(filtered_matches) >= max_topics_per_post:
            break

    if filtered_matches:
        return filtered_matches

    return [sorted_matches[0]]


def _normalize(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def _keyword_count(text: str, keyword: str) -> int:
    if " " in keyword:
        return text.count(keyword)

    pattern = rf"(?<![0-9a-zа-я]){re.escape(keyword)}[0-9a-zа-я]*"
    return len(re.findall(pattern, text))
