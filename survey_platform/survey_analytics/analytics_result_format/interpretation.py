from .constants import *  # noqa: F401,F403
from . import helpers as _helpers
from . import main_results as _main_results
from survey_analytics.analytics_data_quality import deduplicate_warnings

globals().update({name: getattr(_helpers, name) for name in dir(_helpers) if not name.startswith("__")})
globals().update({name: getattr(_main_results, name) for name in dir(_main_results) if not name.startswith("__")})

def _build_base_interpretation(analysis_type, result, effect_size):
    if analysis_type == "correlation":
        strongest = _strongest_correlations(result)
        if strongest:
            item = strongest[0]
            summary = (
                f"Наиболее выраженная связь обнаружена между «{item['left_label']}» и «{item['right_label']}»: "
                f"r = {item['coefficient']:.3f}. Направление связи: {correlation_direction(item['coefficient'])}; "
                f"сила связи: {interpret_correlation(item['coefficient'])}."
            )
        else:
            summary = "Для выбранных переменных не удалось выделить парную корреляционную связь."
        return {"summary": summary, "details": [], "limitations": ["Корреляция не доказывает причинно-следственную связь."]}
    if analysis_type == "chi_square":
        main = build_main_results(analysis_type, result)
        summary = (
            "Между выбранными категориальными переменными обнаружена статистически значимая связь."
            if main["significant"]
            else "Статистически значимая связь между выбранными категориальными переменными не выявлена. Следует учитывать размер выборки и распределение частот по ячейкам."
        )
        if effect_size.get("interpretation"):
            summary += f" Сила связи по V Крамера: {effect_size['interpretation']}."
        if ((result.get("chi_square") or {}).get("expected_diagnostics") or {}).get("assumption_warning"):
            summary += " Часть ожидаемых частот мала, поэтому результат χ²-критерия следует интерпретировать осторожно."
        return {
            "summary": summary,
            "details": [
                "χ²-критерий проверяет, отличается ли наблюдаемое распределение от ожидаемого при отсутствии связи между переменными.",
                "V Крамера показывает силу связи между категориальными переменными.",
                "Стандартизированные остатки помогают понять, какие ячейки таблицы сильнее всего отличаются от ожидаемых значений.",
            ],
            "limitations": [
                "Статистическая связь не доказывает причинно-следственную зависимость.",
                "При малых ожидаемых частотах χ²-критерий может быть ненадёжен.",
            ],
        }
    if analysis_type == "time_analysis":
        summary = result.get("summary") or {}
        duration = result.get("duration_summary") or {}
        dropout = (result.get("dropout") or {}).get("highest_dropout_page") or {}
        quality = result.get("quality_flags") or {}
        completion_rate = summary.get("completion_rate")
        text = "Анализ показывает, как респонденты проходят опрос и на каких этапах возникает отсев."
        if completion_rate is not None:
            text += f" Полностью завершили опрос {completion_rate:.2f}% начавших."
        if duration.get("median_seconds") is not None:
            text += f" Медианное время полного прохождения составляет {duration['median_seconds']:.2f} сек."
        if dropout.get("page_title"):
            text += f" Наибольший dropout наблюдается на этапе «{dropout['page_title']}»: {dropout.get('dropout_rate', 0):.2f}%."
        if (quality.get("too_fast") or {}).get("rate", 0) > 0:
            text += f" Доля слишком быстрых прохождений составляет {(quality.get('too_fast') or {}).get('rate'):.2f}%."
        return {
            "summary": text,
            "details": [
                "Медиана и квартильный размах устойчивее среднего времени к аномально длинным прохождениям.",
                "Воронка и retention curve показывают сохранение респондентов по этапам анкеты.",
                "Флаги слишком быстрых и аномально длинных прохождений помогают выделить ответы для дополнительной проверки.",
            ],
            "limitations": [
                "Dropout по страницам рассчитывается приближенно по наличию ответов на вопросы страниц.",
                "Слишком быстрое прохождение является сигналом для проверки, но само по себе не доказывает низкое качество ответа.",
                "Straight-lining и повторяющиеся паттерны ответов требуют отдельных методов контроля качества.",
            ],
        }
    if analysis_type == "crosstab":
        return {
            "summary": "Таблица сопряженности показывает совместное распределение двух категориальных переменных. Она позволяет увидеть, какие сочетания категорий встречаются чаще или реже.",
            "details": ["Для содержательной интерпретации сопоставляйте абсолютные частоты и проценты по строкам."],
            "limitations": ["Сама таблица сопряженности не подтверждает статистическую значимость наблюдаемой ассоциации."],
        }
    if analysis_type == "group_comparison":
        main = build_main_results(analysis_type, result)
        highest = main.get("highest_group") or {}
        lowest = main.get("lowest_group") or {}
        if main.get("significant"):
            if (main.get("groups_count") or 0) == 2:
                summary = f"Между двумя группами обнаружены статистически значимые различия. Среднее значение выше в группе «{highest.get('label')}», ниже в группе «{lowest.get('label')}»."
            else:
                summary = f"Обнаружены статистически значимые различия между группами. Наибольшее среднее значение наблюдается в группе «{highest.get('label')}», наименьшее — в группе «{lowest.get('label')}»."
        else:
            summary = "Статистически значимые различия между группами не выявлены. Следует учитывать размер выборки, разброс внутри групп и размер эффекта."
        if effect_size.get("interpretation"):
            summary += f" Размер эффекта: {effect_size['interpretation']}."
        return {
            "summary": summary,
            "details": [
                "t-test и Mann–Whitney применяются для сравнения двух групп.",
                "ANOVA и Kruskal–Wallis применяются для сравнения трех и более групп.",
                "Размер эффекта показывает, насколько выражены различия между группами.",
                "Post-hoc сравнения помогают определить, между какими именно группами есть различия.",
            ],
            "limitations": [
                "Статистическая значимость не показывает величину различий; для этого используется размер эффекта.",
                "При малых или сильно несбалансированных группах результаты следует интерпретировать осторожно.",
                "Post-hoc сравнения увеличивают риск ложноположительных результатов, поэтому требуется поправка p-value.",
            ],
        }
    if analysis_type == "regression" and effect_size:
        return {
            "summary": f"Модель объясняет {effect_size['value'] * 100:.2f}% вариации целевой переменной. Коэффициенты показывают среднее изменение целевой переменной при изменении предиктора на одну единицу при прочих равных условиях. Регрессионная модель показывает статистическую связь, но сама по себе не доказывает причинное влияние.",
            "details": ["R² показывает долю вариации целевой переменной, объясняемую моделью.", "Adjusted R² учитывает количество предикторов.", "Стандартизированные коэффициенты помогают сравнивать относительную силу предикторов.", "VIF используется для проверки мультиколлинеарности.", "Диагностика остатков помогает оценить применимость линейной модели."],
            "limitations": ["Линейная регрессия предполагает приблизительно линейную связь.", "Регрессионная модель не доказывает причинно-следственную зависимость.", "При мультиколлинеарности коэффициенты могут быть нестабильными.", "При неоднородности дисперсии остатков стандартные ошибки и p-value могут быть ненадежными."],
        }
    if analysis_type == "logistic_regression":
        return {
            "summary": "Логистическая регрессия оценивает связь факторов с вероятностью наступления бинарного события. Odds ratio больше 1 соответствует увеличению шансов события, меньше 1 — уменьшению шансов при прочих равных условиях. Модель не доказывает причинно-следственную зависимость.",
            "details": ["Odds ratio показывает изменение шансов события при увеличении предиктора на одну единицу.", "ROC-AUC оценивает способность модели различать классы.", "Матрица ошибок показывает правильные и ошибочные классификации.", "Калибровка сопоставляет предсказанные вероятности с наблюдаемой частотой события."],
            "limitations": ["Логистическая регрессия показывает статистическую связь, но не доказывает причинность.", "При дисбалансе классов accuracy может быть завышенной.", "При малом числе событий на предиктор коэффициенты могут быть нестабильными."],
        }
    if analysis_type == "factor_analysis":
        kmo = (result.get("kmo") or {}).get("overall")
        bartlett = (result.get("bartlett") or {}).get("significant")
        variance = result.get("cumulative_explained_variance")
        summary = "Факторный анализ указывает на возможную скрытую структуру связей между выбранными переменными."
        if kmo is not None:
            summary += f" Общий KMO равен {kmo:.3f}."
        if bartlett is True:
            summary += " Критерий Бартлетта статистически значим."
        elif bartlett is False:
            summary += " Критерий Бартлетта незначим, поэтому решение следует интерпретировать осторожно."
        if variance is not None:
            summary += f" Выбранные факторы объясняют {variance * 100:.2f}% вариации."
        return {
            "summary": summary,
            "details": [
                "KMO оценивает пригодность данных для факторного анализа.",
                "Критерий Бартлетта проверяет, отличается ли корреляционная матрица от единичной.",
                "Factor loadings показывают связь переменных с факторами.",
                "Communality показывает, насколько хорошо переменная объясняется выделенными факторами.",
                "Parallel analysis сравнивает eigenvalues реальных данных со случайными данными.",
            ],
            "limitations": [
                "Факторный анализ не доказывает существование скрытых причин, а только выявляет структуру связей между переменными.",
                "Названия факторов должны задаваться исследователем на основе смысла вопросов с высокими нагрузками.",
                "При малой выборке или низком KMO факторное решение может быть нестабильным.",
                "Переменные с cross-loading могут затруднять интерпретацию факторов.",
            ],
        }
    if analysis_type == "reliability_analysis":
        alpha = result.get("cronbach_alpha", result.get("alpha"))
        summary = (
            "Шкала демонстрирует приемлемую внутреннюю согласованность. Выбранные пункты в целом могут рассматриваться как элементы одной шкалы."
            if alpha is not None and alpha >= 0.7
            else "Внутренняя согласованность шкалы ограничена. Часть пунктов может требовать reverse coding, уточнения формулировки или содержательной проверки."
        )
        if any(item.get("improves_alpha") for item in result.get("alpha_if_item_deleted") or []):
            summary += " Удаление одного или нескольких пунктов может повысить alpha, поэтому эти пункты стоит проверить содержательно."
        return {
            "summary": summary,
            "details": ["Cronbach’s alpha показывает внутреннюю согласованность пунктов шкалы.", "Item-total correlation показывает, насколько пункт согласуется с суммой остальных пунктов.", "Alpha if item deleted показывает, как изменится alpha при исключении конкретного пункта.", "Межпунктовые корреляции помогают увидеть связи между пунктами."],
            "limitations": ["Cronbach’s alpha не доказывает одномерность шкалы; для проверки структуры можно использовать факторный анализ.", "Высокая alpha не гарантирует содержательную валидность шкалы.", "Решение об удалении пункта должно приниматься не только по статистике, но и по смыслу вопроса."],
        }
    if analysis_type == "scale_index":
        normalized_mean = (result.get("normalized_score_summary") or {}).get("mean")
        summary = "Индекс объединяет выбранные пункты в интегральный показатель."
        if normalized_mean is not None:
            summary += f" Среднее нормированное значение составляет {normalized_mean:.2f} из 100."
        summary += " Содержательная интерпретация зависит от формулировок включенных вопросов и корректности reverse coding."
        return {
            "summary": summary,
            "details": ["Composite score объединяет несколько пунктов анкеты в один интегральный показатель.", "Reverse coding используется для пунктов, направленных противоположно общей шкале.", "Нормировка 0–100 облегчает интерпретацию индекса и сравнение разных шкал."],
            "limitations": ["Индекс имеет смысл только если выбранные пункты содержательно относятся к одному конструкту.", "Reverse coding должен быть задан корректно, иначе направление индекса может быть искажено.", "Нормировка 0–100 в текущей реализации основана на наблюдаемом диапазоне значений."],
        }
    return {
        "summary": ANALYSIS_PURPOSES.get(analysis_type, "Результат метода подготовлен для дальнейшей интерпретации."),
        "details": [],
        "limitations": [],
    }


def extract_primary_p_value(analysis_type, result):
    if analysis_type == "chi_square":
        return (result.get("chi_square") or {}).get("p_value")
    if analysis_type == "group_comparison":
        return (
            result.get("p_value")
            if result.get("p_value") is not None
            else (result.get("test") or {}).get(
                "p_value",
                (result.get("omnibus") or {}).get("p_value"),
            )
        )
    if analysis_type == "correlation":
        strongest = _strongest_correlations(result)
        return strongest[0].get("p_value") if strongest else None
    if analysis_type == "factor_analysis":
        return (result.get("bartlett") or {}).get("p_value")
    return result.get("p_value")


def build_statistical_significance(analysis_type, result, alpha=0.05):
    p_value = extract_primary_p_value(analysis_type, result)
    if p_value is None:
        return {
            "available": False,
            "p_value": None,
            "alpha": alpha,
            "is_significant": None,
            "interpretation": "Для данного результата p-value не найден или не рассчитывается.",
        }
    is_significant = p_value < alpha
    if analysis_type == "factor_analysis":
        interpretation = (
            "Критерий Бартлетта статистически значим: данные содержат основания для применения факторного анализа."
            if is_significant
            else "Критерий Бартлетта не достигает статистической значимости: пригодность данных для факторного анализа ограничена."
        )
    elif is_significant:
        interpretation = "Результат статистически значим при уровне значимости 0,05."
    else:
        interpretation = "Результат не достигает статистической значимости при уровне значимости 0,05."
    return {
        "available": True,
        "p_value": p_value,
        "alpha": alpha,
        "is_significant": is_significant,
        "interpretation": interpretation,
    }


def _effect_strength_level(effect_size):
    text = str((effect_size or {}).get("interpretation") or "").lower()
    if any(marker in text for marker in ("слаб", "низк", "незнач", "огранич")):
        return "weak"
    if any(marker in text for marker in ("умерен", "замет", "достаточ", "приемлем")):
        return "moderate"
    if any(marker in text for marker in ("сильн", "высок", "хорош", "выраж")):
        return "strong"
    value = (effect_size or {}).get("value")
    if isinstance(value, (int, float)):
        if abs(value) < 0.3:
            return "weak"
        if abs(value) < 0.5:
            return "moderate"
        return "strong"
    return "unknown"


def build_effect_interpretation(effect_size):
    effect_size = effect_size or {}
    value = effect_size.get("value")
    if not effect_size.get("name") or value is None:
        return {
            "available": False,
            "interpretation": "Для данного результата размер эффекта не найден или не был рассчитан.",
        }
    strength = effect_size.get("interpretation") or "размер эффекта рассчитан"
    return {
        "available": True,
        "effect_name": effect_size["name"],
        "effect_value": value,
        "strength": strength,
        "strength_level": _effect_strength_level(effect_size),
        "interpretation": f"Размер эффекта указывает на следующий уровень выраженности результата: {strength}.",
    }


def build_practical_significance(statistical_significance, effect_interpretation, data_quality=None):
    if not statistical_significance.get("available") or not effect_interpretation.get("available"):
        return {
            "level": "unclear",
            "interpretation": "Практическую значимость невозможно оценить полностью, так как отсутствуют данные о статистической значимости или размере эффекта.",
        }
    significant = statistical_significance.get("is_significant")
    strength = effect_interpretation.get("strength_level")
    if significant and strength in ("moderate", "strong"):
        return {
            "level": "high" if strength == "strong" else "moderate",
            "interpretation": "Результат статистически значим и имеет выраженный размер эффекта, поэтому он может иметь практическое значение.",
        }
    if significant and strength == "weak":
        return {
            "level": "limited",
            "interpretation": "Результат статистически значим, однако размер эффекта невелик. Практическая значимость результата может быть ограниченной.",
        }
    if not significant and strength in ("moderate", "strong"):
        return {
            "level": "unclear",
            "interpretation": "Размер эффекта выглядит заметным, но статистическая значимость не достигнута. Возможно, выборка недостаточна для устойчивого вывода.",
        }
    return {
        "level": "limited",
        "interpretation": "Статистически значимый и практически выраженный эффект не выявлен; содержательный вывод следует формулировать осторожно.",
    }


def build_result_confidence(data_quality, warnings, statistical_significance, effect_interpretation):
    quality = data_quality or {}
    method_checks = quality.get("method_checks") or {}
    dataset = quality.get("dataset") or {}
    if not quality or (dataset.get("analysis_n") is None and not warnings):
        return {
            "level": "unknown",
            "interpretation": "Недостаточно информации для оценки устойчивости результата.",
        }
    critical_quality_issue = any(
        method_checks.get(key) is False
        for key in ("sample_size_ok", "missing_rate_ok", "zero_variance_ok")
    )
    if critical_quality_issue or len(warnings) >= 4:
        return {
            "level": "low",
            "interpretation": "Надежность вывода ограничена из-за качества данных или условий применимости метода.",
        }
    if (
        not warnings
        and statistical_significance.get("is_significant") is True
        and effect_interpretation.get("strength_level") in ("moderate", "strong")
    ):
        return {
            "level": "high",
            "interpretation": "Результат выглядит достаточно устойчивым: размер выборки приемлемый, качество данных не содержит критичных предупреждений.",
        }
    return {
        "level": "medium",
        "interpretation": "Результат можно использовать как ориентир, но его следует интерпретировать с учетом предупреждений о данных или применимости метода.",
    }


def _build_common_limitations(analysis_type, significance, data_quality, warnings):
    limitations = []
    association_methods = {
        "correlation", "crosstab", "chi_square", "correspondence_analysis",
        "regression", "logistic_regression",
    }
    if analysis_type in ("regression", "logistic_regression"):
        limitations.append("Регрессионная модель показывает статистическую связь между факторами и целевой переменной, но сама по себе не доказывает причинное влияние.")
    elif analysis_type in association_methods:
        limitations.append("Обнаруженная связь не доказывает причинно-следственную зависимость.")
    if significance.get("available"):
        limitations.append("p-value не показывает силу эффекта; для оценки практической значимости следует учитывать размер эффекта.")
    dataset = (data_quality or {}).get("dataset") or {}
    if dataset.get("analysis_n") is not None and dataset["analysis_n"] < 30:
        limitations.append("При малом размере выборки статистические выводы могут быть нестабильными.")
    if dataset.get("missing_rate") is not None and dataset["missing_rate"] >= 30:
        limitations.append("Высокий уровень пропусков может смещать результаты анализа.")
    if analysis_type == "missing_analysis" and any("ветвлен" in warning.lower() for warning in warnings):
        limitations.append("Вопросы, не показанные из-за ветвления, не следует трактовать как обычные пропуски.")
    return limitations


def build_interpretation(analysis_type, result, effect_size=None, data_quality=None, warnings=None):
    base = _build_base_interpretation(analysis_type, result, effect_size or {})
    warnings = warnings or []
    significance = build_statistical_significance(analysis_type, result)
    effect_interpretation = build_effect_interpretation(effect_size)
    practical_significance = build_practical_significance(significance, effect_interpretation, data_quality)
    confidence = build_result_confidence(data_quality, warnings, significance, effect_interpretation)
    details = list(base.get("details") or [])
    details.extend([
        "p-value показывает, насколько наблюдаемый результат совместим с предположением об отсутствии эффекта или связи.",
        "Статистическая значимость не показывает силу эффекта и не доказывает практическую важность результата.",
    ])
    if effect_interpretation.get("available"):
        details.append("Размер эффекта показывает, насколько выражена связь, различие или объясняющая способность модели.")
    limitations = deduplicate_warnings([
        *(base.get("limitations") or []),
        *_build_common_limitations(analysis_type, significance, data_quality, warnings),
    ])
    return {
        **base,
        "statistical_significance": significance,
        "effect_interpretation": effect_interpretation,
        "practical_significance": practical_significance,
        "confidence": confidence,
        "details": deduplicate_warnings(details),
        "limitations": limitations,
    }


def build_common_recommendations(analysis_type, interpretation, warnings):
    significance = interpretation["statistical_significance"]
    effect = interpretation["effect_interpretation"]
    recommendations = []
    if significance.get("available") and not effect.get("available"):
        recommendations.append("Рекомендуется дополнить результат оценкой размера эффекта, чтобы понять практическую значимость результата.")
    if significance.get("is_significant") is True and effect.get("strength_level") == "weak":
        recommendations.append("Рекомендуется не ограничиваться статистической значимостью и оценить, имеет ли слабый эффект содержательный смысл для исследования.")
    if significance.get("is_significant") is False and effect.get("strength_level") in ("moderate", "strong"):
        recommendations.append("Рекомендуется проверить размер выборки: возможно, данных недостаточно для статистически устойчивого вывода.")
    if len(warnings) >= 3:
        recommendations.append("Перед содержательной интерпретацией рекомендуется проверить качество данных: пропуски, слишком быстрые прохождения и переменные без вариативности.")
    if analysis_type in {"correlation", "crosstab", "chi_square", "correspondence_analysis", "regression", "logistic_regression"}:
        recommendations.append("Для содержательного вывода рекомендуется сопоставить статистический результат с исследовательской гипотезой и контекстом вопроса анкеты.")
    return recommendations


def collect_warnings(result):
    warnings = list(result.get("warnings") or [])
    chi_square = result.get("chi_square") or {}
    warnings.extend(chi_square.get("warnings") or [])
    warnings.extend((result.get("kmo") or {}).get("warnings") or [])
    warnings.extend((result.get("bartlett") or {}).get("warnings") or [])
    warnings.extend((result.get("cluster_quality") or {}).get("warnings") or [])
    if "p_value" in chi_square and chi_square.get("p_value") is None:
        warnings.append("Для данного метода не удалось рассчитать p-value.")
    return warnings


def build_visualization_specs(analysis_type):
    specs = []
    for index, item in enumerate(VISUALIZATIONS.get(analysis_type, [])):
        if isinstance(item, dict):
            specs.append({**item, "recommended": item.get("recommended", index == 0)})
        else:
            chart_type, title = item
            specs.append({"type": chart_type, "title": title, "recommended": index == 0})
    return specs

