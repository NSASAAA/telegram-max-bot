import re
from typing import Optional

from telegram_max_bot.core.models import Topic


TOPIC_CLASSIFIER_VERSION = "2026-05-30-soft-v2"

TOPICS: tuple[Topic, ...] = (
    Topic(
        code="rs_basics",
        title="РС: основы и симптомы",
        description="Базовые материалы о рассеянном склерозе, симптомах и состоянии.",
        keywords=(
            "рассеянн",
            "склероз",
            "симптом",
            "что такое рс",
            "болезнь рс",
            "диагноз рс",
            "обострен",
        ),
    ),
    Topic(
        code="rs_treatment",
        title="РС: лечение и медицина",
        description="Терапия, ПИТРС, врачи, анализы, медицина и лечение РС.",
        keywords=(
            "питрс",
            "невролог",
            "мрт",
            "терапи",
            "лечение",
            "лекарств",
            "препарат",
            "капельниц",
            "ремисси",
            "мсэ",
        ),
    ),
    Topic(
        code="rs_daily",
        title="РС: быт и жизнь семьи",
        description="Повседневная жизнь с РС, нагрузка семьи и адаптация.",
        keywords=(
            "инвалидност",
            "коляск",
            "трость",
            "супруг бол",
            "муж бол",
            "быт с рс",
            "семья и рс",
            "как жить с рс",
        ),
    ),
    Topic(
        code="marriage_roles",
        title="Брак: роли и ожидания",
        description="Роли мужа и жены, ожидания в браке и семейные сценарии.",
        keywords=(
            "брак",
            "муж",
            "жена",
            "супруг",
            "роль",
            "семейн",
            "отношен",
            "каким мужем",
            "хранительниц",
        ),
    ),
    Topic(
        code="marriage_conflict",
        title="Брак: конфликты и кризисы",
        description="Сложные периоды брака, конфликты, разводные и пограничные темы.",
        keywords=(
            "конфликт",
            "ссора",
            "развод",
            "кризис",
            "скандал",
            "оставить супруга",
            "смирени",
            "предатель",
            "измена",
        ),
    ),
    Topic(
        code="marriage_support",
        title="Брак: поддержка и близость",
        description="Взаимная поддержка супругов, забота, близость и командность в семье.",
        keywords=(
            "поддерж",
            "забот",
            "любов",
            "вместе",
            "близост",
            "довер",
            "счастлив",
            "благодар",
        ),
    ),
    Topic(
        code="inlaws",
        title="Родня и границы семьи",
        description="Отношения со свекровью, тещей и расширенной семьей.",
        keywords=(
            "свекров",
            "тещ",
            "родств",
            "мама мужа",
            "родня",
            "называю свекровь",
        ),
    ),
    Topic(
        code="parenting_small",
        title="Дети: ранний возраст",
        description="Малыши, дошкольный возраст, детский сад и первые этапы воспитания.",
        keywords=(
            "ребен",
            "малыш",
            "дошколь",
            "детский сад",
            "детсад",
            "маленьк",
            "воспитан",
        ),
    ),
    Topic(
        code="parenting_teens",
        title="Дети: подростки",
        description="Подростковый возраст, взросление, коммуникация с сыновьями и дочерьми.",
        keywords=(
            "подрост",
            "сын",
            "доч",
            "взросле",
            "переходн возраст",
            "подростков",
            "выпускник",
        ),
    ),
    Topic(
        code="education_school",
        title="Образование: школа",
        description="Школа, учителя, уроки, оценки и учебные траектории.",
        keywords=(
            "школ",
            "учител",
            "урок",
            "класс",
            "егэ",
            "оценк",
            "дневник",
            "выпускн",
        ),
    ),
    Topic(
        code="education_home",
        title="Образование: дома",
        description="Домашнее и семейное обучение, альтернативные форматы учебы.",
        keywords=(
            "домашн обуч",
            "семейн обуч",
            "семейн образован",
            "учится дома",
            "на дому",
            "домашняя школа",
            "хоумскул",
        ),
    ),
    Topic(
        code="children_media",
        title="Дети: фильмы и книги",
        description="Контент для семейного просмотра и чтения с детьми.",
        keywords=(
            "смотрим фильм",
            "с детьми",
            "мультфильм",
            "детское кино",
            "читаем с детьми",
            "книга для детей",
            "семейный фильм",
        ),
    ),
    Topic(
        code="women_boundaries",
        title="Женщины: границы",
        description="Личные границы, право на себя и отказ от разрушающих сценариев.",
        keywords=(
            "границ",
            "личное пространство",
            "нельзя терпеть",
            "право на себя",
            "уважение к себе",
            "сказать нет",
        ),
    ),
    Topic(
        code="women_load",
        title="Женщины: нагрузка",
        description="Перегруз, самопожертвование, материнская и бытовая усталость.",
        keywords=(
            "самопожертв",
            "перегруз",
            "устал",
            "должна",
            "тащу все",
            "жертв",
            "выгор",
            "нагрузк",
        ),
    ),
    Topic(
        code="women_feminism",
        title="Женщины: феминизм и роль",
        description="Женская роль, феминизм, социальные ожидания и стереотипы.",
        keywords=(
            "феминизм",
            "феминист",
            "женская роль",
            "патриарх",
            "русской женщине",
            "гендер",
            "с восьмым марта",
        ),
    ),
    Topic(
        code="psy_narcissism",
        title="Психология: нарциссизм",
        description="Нарциссизм, нарциссические сценарии и последствия в отношениях.",
        keywords=(
            "нарцисс",
            "нарциссизм",
            "нарцисст",
            "абьюз",
            "токсич",
            "газлайт",
        ),
    ),
    Topic(
        code="psy_trauma",
        title="Психология: травма",
        description="Психологическая травма, стыд, вина и трудный эмоциональный опыт.",
        keywords=(
            "травм",
            "стыд",
            "вина",
            "боль",
            "потер",
            "ранен",
            "исцел",
        ),
    ),
    Topic(
        code="psy_stress",
        title="Психология: стресс",
        description="Стресс, тревога, выгорание и способы справляться с напряжением.",
        keywords=(
            "стресс",
            "тревог",
            "выгор",
            "устал",
            "нерв",
            "паник",
            "депресс",
        ),
    ),
    Topic(
        code="psy_growth",
        title="Психология: развитие",
        description="Осознанность, рост, принятие, изменения и психологическая зрелость.",
        keywords=(
            "осознан",
            "зрелост",
            "принят",
            "развит",
            "изменил",
            "научил",
            "опыт",
        ),
    ),
    Topic(
        code="faith_church",
        title="Вера: церковная жизнь",
        description="Храм, служба, литургия, молитвенная и церковная практика.",
        keywords=(
            "храм",
            "литурги",
            "молитв",
            "приход",
            "батюшк",
            "исповед",
            "причаст",
            "церков",
        ),
    ),
    Topic(
        code="faith_questions",
        title="Вера: трудные вопросы",
        description="Вопросы о вере, смысле, сомнениях и духовном пути.",
        keywords=(
            "почему бог",
            "веришь в бога",
            "можно ли православным",
            "грех",
            "смирени",
            "духовник",
            "сомнен",
            "вера",
        ),
    ),
    Topic(
        code="faith_holidays",
        title="Вера: праздники и традиции",
        description="Православные праздники, посты и церковные традиции.",
        keywords=(
            "праздник",
            "пасх",
            "рождеств",
            "успени",
            "покров",
            "пост",
            "сочельник",
            "новый год православ",
        ),
    ),
    Topic(
        code="moscow_city",
        title="Москва: город и маршруты",
        description="Городские маршруты, прогулки, места и повседневная Москва.",
        keywords=(
            "москв",
            "город",
            "прогулк",
            "парк",
            "улиц",
            "район",
            "метро",
        ),
    ),
    Topic(
        code="culture_films",
        title="Культура: кино",
        description="Фильмы, семейный просмотр и обсуждение кино.",
        keywords=(
            "фильм",
            "кино",
            "сериал",
            "посмотреть",
            "рекомендация фильма",
            "смотрим кино",
        ),
    ),
    Topic(
        code="culture_books",
        title="Культура: книги",
        description="Книги, чтение и литературные рекомендации.",
        keywords=(
            "книг",
            "чита",
            "литератур",
            "роман",
            "писател",
            "библиотек",
            "что почитать",
        ),
    ),
    Topic(
        code="culture_events",
        title="Культура: события и места",
        description="Музеи, театры, выставки, культурные события и пространства.",
        keywords=(
            "музе",
            "театр",
            "выставк",
            "культур",
            "концерт",
            "экскурси",
            "галере",
        ),
    ),
    Topic(
        code="daily_money",
        title="Быт: деньги и работа",
        description="Доходы, расходы, работа и бытовая финансовая реальность.",
        keywords=(
            "деньг",
            "зарплат",
            "работ",
            "бюджет",
            "покупк",
            "траты",
            "доход",
            "подработ",
        ),
    ),
    Topic(
        code="daily_household",
        title="Быт: дом и рутина",
        description="Домашняя рутина, хозяйство, готовка, уборка и ежедневные задачи.",
        keywords=(
            "быт",
            "дом",
            "кухн",
            "готов",
            "уборк",
            "квартир",
            "магазин",
            "рутин",
        ),
    ),
)

TOPICS_BY_CODE = {topic.code: topic for topic in TOPICS}


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
