# -*- coding: utf-8 -*-
"""
FJS-12 Scoring logic.

Behrend H, Giesinger K, Giesinger JM, Kuster MS (2012).
The "forgotten joint" as the ultimate goal in joint arthroplasty:
validation of a new patient-reported outcome measure.
J Arthroplasty, 27(3): 430-436.

Each item is rated 0-4:
  0 = Never, 1 = Almost never, 2 = Seldom, 3 = Sometimes, 4 = Mostly

Raw sum range: 0-48
FJS-12 = (1 - raw/48) * 100  → 0-100, higher is better.

If <12 items answered, pro-rate using the mean of answered items.
At least 9/12 items must be answered for a valid score.
"""

NUM_ITEMS = 12
MIN_ANSWERED = 9


def calculate_fjs_score(answers):
    """
    Calculate the FJS-12 score from a list of integer answers (0-4 each).

    Args:
        answers: list of int (0-4) or None for skipped. Length up to 12.

    Returns:
        float score 0-100, or None if too few items answered.
    """
    if not answers:
        return None

    valid = [a for a in answers if a is not None and 0 <= a <= 4]
    if len(valid) < MIN_ANSWERED:
        return None

    # Pro-rate to 12 items if some were skipped (per FJS scoring manual)
    mean_item = sum(valid) / len(valid)
    pro_rated_total = mean_item * NUM_ITEMS  # 0-48

    score = (1 - pro_rated_total / 48.0) * 100.0
    return round(score, 1)


def score_label(score, lang='tr'):
    """Optional qualitative interpretation. Not part of the official scoring."""
    if score is None:
        return ''
    labels = {
        'tr': [
            (90, 'Mükemmel — eklem neredeyse hiç fark edilmiyor'),
            (75, 'Çok iyi'),
            (50, 'İyi'),
            (25, 'Orta'),
            (0,  'Zayıf — eklem belirgin şekilde fark ediliyor'),
        ],
        'en': [
            (90, 'Excellent — joint is almost never noticed'),
            (75, 'Very good'),
            (50, 'Good'),
            (25, 'Fair'),
            (0,  'Poor — joint is clearly noticed'),
        ],
        'ar': [
            (90, 'ممتاز — لا يكاد المفصل يُلاحظ'),
            (75, 'جيد جداً'),
            (50, 'جيد'),
            (25, 'متوسط'),
            (0,  'ضعيف — المفصل ملحوظ بوضوح'),
        ],
        'bg': [
            (90, 'Отличен — ставата почти не се усеща'),
            (75, 'Много добър'),
            (50, 'Добър'),
            (25, 'Среден'),
            (0,  'Слаб — ставата се усеща ясно'),
        ],
    }
    table = labels.get(lang, labels['tr'])
    for threshold, label in table:
        if score >= threshold:
            return label
    return table[-1][1]
