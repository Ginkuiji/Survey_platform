from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def _crosstab_shape(result):
    crosstab = result.get("crosstab") or {}
    rows = crosstab.get("rows") or []
    columns = rows[0].get("columns") or [] if rows else []
    return len(rows), len(columns), [
        column.get("count", 0)
        for row in rows
        for column in row.get("columns") or []
    ]


def build_applicability_warnings(analysis_type, result, payload=None, dataset=None, data_quality=None):
    quality = data_quality or {}
    dataset_quality = quality.get("dataset") or {}
    variables = quality.get("variables") or {}
    time_quality = quality.get("time") or {}
    checks = (quality.get("method_checks") or {}).get("method_specific") or {}
    warnings = []

    if dataset_quality.get("analysis_n") is not None and dataset_quality["analysis_n"] < 30:
        warnings.append("Размер выборки меньше 30 наблюдений, результаты следует интерпретировать осторожно.")
    if dataset_quality.get("missing_rate") is not None and dataset_quality["missing_rate"] >= HIGH_MISSING_RATE:
        warnings.append("В анализ не вошла значительная часть наблюдений из-за пропусков.")
    if variables.get("zero_variance_variables_count", 0) > 0:
        warnings.append("В одной или нескольких выбранных переменных нет вариативности; такие переменные могут искажать или блокировать расчет.")
    if variables.get("high_missing_variables_count", 0) > 0:
        warnings.append("В одной или нескольких выбранных переменных высокий уровень пропусков.")
    if (time_quality.get("too_fast_responses_count") or 0) > 0:
        warnings.append("Обнаружены слишком быстрые прохождения; они могут снижать качество данных.")

    if analysis_type == "correlation":
        variables_count = len(result.get("variables") or [])
        n_matrix = result.get("n_matrix") or []
        p_values = result.get("p_values") or []
        pair_ns = [
            n_matrix[row_index][column_index]
            for row_index in range(len(n_matrix))
            for column_index in range(row_index + 1, len(n_matrix[row_index]))
            if n_matrix[row_index][column_index] is not None
        ]
        pair_p_values = [
            p_values[row_index][column_index]
            for row_index in range(len(p_values))
            for column_index in range(row_index + 1, len(p_values[row_index]))
        ]
        if variables_count < 2:
            warnings.append("Для корреляционного анализа требуется не менее двух переменных.")
        if any(value < 3 for value in pair_ns):
            warnings.append("Для части пар переменных недостаточно полных наблюдений для надежной оценки корреляции.")
        if any(3 <= value < 30 for value in pair_ns):
            warnings.append("Для части пар переменных меньше 30 совместных наблюдений; оценки корреляции могут быть нестабильными.")
        if any(value is None for value in pair_p_values):
            warnings.append("Для части корреляций p-value недоступен.")
        if any(
            row_index < len(n_matrix[row_index])
            and any(
                n_matrix[row_index][column_index] < min(n_matrix[row_index][row_index], n_matrix[column_index][column_index])
                for column_index in range(row_index + 1, len(n_matrix[row_index]))
            )
            for row_index in range(len(n_matrix))
        ):
            warnings.append("Для части пар применено попарное исключение наблюдений с пропусками; значения n различаются между корреляциями.")
    elif analysis_type == "crosstab":
        rows, columns, counts = _crosstab_shape(result)
        if rows < 2 or columns < 2:
            warnings.append("Таблица имеет менее двух строк или двух столбцов, анализ связи между категориями невозможен.")
        if any(count < 5 for count in counts):
            warnings.append("Таблица сопряженности содержит малые частоты в ячейках; интерпретация распределения требует осторожности.")
    elif analysis_type == "chi_square":
        if checks.get("expected_below_5_count", 0) > 0:
            warnings.append("Для χ²-критерия часть ожидаемых частот меньше 5; результат следует интерпретировать осторожно.")
        if checks.get("expected_below_5_rate", 0) > 20:
            warnings.append("Более 20% ожидаемых частот меньше 5; χ²-критерий может быть ненадежен.")
        if checks.get("expected_below_1_count", 0) > 0:
            warnings.append("В таблице есть ожидаемые частоты меньше 1; χ²-критерий может быть неприменим.")
        rows, columns, _ = _crosstab_shape(result)
        if rows == 2 and columns == 2 and checks.get("expected_below_5_count", 0):
            warnings.append("Для таблицы 2x2 при малых частотах рекомендуется использовать точный критерий Фишера.")
    elif analysis_type == "correspondence_analysis":
        if (result.get("n_rows") or 0) < 2 or (result.get("n_columns") or 0) < 2:
            warnings.append("Анализ соответствий требует таблицу сопряженности размером не менее 2x2.")
        masses = [
            item.get("mass")
            for item in [*(result.get("row_coordinates") or []), *(result.get("column_coordinates") or [])]
            if item.get("mass") is not None
        ]
        if any(mass < 0.05 for mass in masses):
            warnings.append("Часть категорий имеет очень малую массу, координаты таких категорий могут быть нестабильными.")
    elif analysis_type in ("regression", "logistic_regression"):
        if checks.get("cases_per_feature") is not None and checks["cases_per_feature"] < 10:
            warnings.append("Для регрессии мало наблюдений относительно числа предикторов.")
        if checks.get("high_vif_variables"):
            warnings.append("Обнаружена мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
        diagnostics = result.get("diagnostics") or {}
        multicollinearity = diagnostics.get("multicollinearity") or {}
        if multicollinearity.get("high_vif_variables"):
            warnings.append("Обнаружена возможная мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
        if analysis_type == "regression":
            residual_summary = diagnostics.get("residual_summary") or {}
            if (result.get("r2") is not None and result["r2"] < 0.1):
                warnings.append("R² низкий; модель объясняет небольшую долю вариации целевой переменной.")
            if (residual_summary.get("outliers_rate") or 0) >= 5:
                warnings.append("Обнаружены выбросы по остаткам; отдельные наблюдения могут заметно влиять на модель.")
            if (diagnostics.get("heteroscedasticity") or {}).get("warning"):
                warnings.append("Обнаружены признаки неоднородности дисперсии остатков; стандартные ошибки и p-value могут быть нестабильными.")
            if (diagnostics.get("normality") or {}).get("likely_normal") is False:
                warnings.append("Остатки модели могут отличаться от нормального распределения; p-value коэффициентов следует интерпретировать осторожно.")
            influential = diagnostics.get("influential_points") or {}
            if (influential.get("high_leverage_count") or 0) or (influential.get("large_cooks_distance_count") or 0):
                warnings.append("Обнаружены потенциально влияющие наблюдения; рекомендуется проверить выбросы и качество ответов.")
        if analysis_type == "logistic_regression":
            if checks.get("minority_class_rate") is not None and checks["minority_class_rate"] < 10:
                warnings.append("Целевая переменная сильно несбалансирована; метрики accuracy могут быть малоинформативны.")
            if checks.get("events_per_variable") is not None and checks["events_per_variable"] < 10:
                warnings.append("Для логистической регрессии мало событий на один предиктор; коэффициенты могут быть нестабильными.")
            metrics = result.get("metrics") or {}
            if metrics.get("roc_auc") is not None and metrics["roc_auc"] < 0.7:
                warnings.append("ROC-AUC низкий; модель слабо различает классы.")
            if (metrics.get("precision") is not None and metrics["precision"] < 0.5) or (metrics.get("recall") is not None and metrics["recall"] < 0.5):
                warnings.append("Precision или recall низкие; модель может плохо находить один из классов.")
    elif analysis_type == "factor_analysis":
        if (checks.get("n_variables") or 0) < 3:
            warnings.append("Для факторного анализа выбрано менее трех переменных.")
        if checks.get("cases_per_variable") is not None and checks["cases_per_variable"] < 5:
            warnings.append("Размер выборки мал относительно числа переменных; факторное решение может быть нестабильным.")
        if checks.get("kmo_overall") is not None and checks["kmo_overall"] < 0.6:
            warnings.append("KMO ниже 0.6, данные могут быть плохо пригодны для факторного анализа.")
        if checks.get("bartlett_p_value") is not None and checks["bartlett_p_value"] >= 0.05:
            warnings.append("Критерий Бартлетта незначим, факторный анализ может быть неинформативен.")
        if checks.get("low_kmo_variables"):
            warnings.append("У отдельных переменных низкий KMO; они могут плохо согласовываться с общей факторной структурой.")
        if checks.get("low_communality_variables"):
            warnings.append("Некоторые переменные имеют низкую communality; они плохо объясняются выделенными факторами.")
        if checks.get("cross_loading_variables"):
            warnings.append("Некоторые переменные имеют высокие нагрузки сразу на несколько факторов; их интерпретация может быть неоднозначной.")
        if checks.get("weak_variables"):
            warnings.append("Некоторые переменные не имеют существенных нагрузок ни на один фактор.")
        if checks.get("cumulative_explained_variance") is not None and checks["cumulative_explained_variance"] < 0.5:
            warnings.append("Выбранные факторы объясняют небольшую долю дисперсии; факторное решение может быть слабым.")
    elif analysis_type == "cluster_analysis":
        if checks.get("silhouette_score") is not None and checks["silhouette_score"] < 0.25:
            warnings.append("Silhouette score низкий, кластеры могут быть плохо разделены.")
        if checks.get("min_cluster_size") is not None and checks["min_cluster_size"] < 5:
            warnings.append("Один или несколько кластеров содержат мало респондентов.")
        if checks.get("n_clusters") and result.get("n") is not None and result["n"] < checks["n_clusters"] * 10:
            warnings.append("Количество кластеров слишком велико для доступного числа наблюдений.")
        if checks.get("cluster_size_ratio") is not None and checks["cluster_size_ratio"] >= 10:
            warnings.append("Размеры кластеров сильно различаются; сегментацию следует интерпретировать осторожно.")
        if checks.get("largest_cluster_rate") is not None and checks["largest_cluster_rate"] > 70:
            warnings.append("Один кластер содержит большую часть выборки, поэтому структура сегментов может быть слабой.")
        if checks.get("weak_profile_clusters"):
            warnings.append("Профили некоторых кластеров выражены слабо; отличающие признаки почти не выделяются.")
    elif analysis_type == "group_comparison":
        if checks.get("min_group_size") is not None and checks["min_group_size"] < 5:
            warnings.append("В одной или нескольких группах меньше 5 наблюдений; сравнение групп может быть ненадежным.")
        if checks.get("min_group_size") and checks.get("max_group_size", 0) / checks["min_group_size"] >= 3:
            warnings.append("Размеры групп сильно различаются; результаты следует интерпретировать осторожно.")
        if (result.get("post_hoc") or {}).get("enabled"):
            warnings.append("Для множественных сравнений важно учитывать поправку p-value.")
    elif analysis_type == "time_analysis":
        summary = result.get("summary") or {}
        minimum = summary.get("min_completion_time_seconds")
        maximum = summary.get("max_completion_time_seconds")
        median_value = summary.get("median_completion_time_seconds")
        if minimum is not None and minimum < TOO_FAST_THRESHOLD_SECONDS:
            warnings.append("Обнаружены слишком быстрые прохождения; возможно, часть ответов была дана невнимательно.")
        if maximum is not None and median_value and maximum > max(3600, median_value * 5):
            warnings.append("Обнаружены аномально длинные прохождения; они могут быть связаны с перерывами при заполнении анкеты.")
    elif analysis_type == "reliability_analysis":
        if (result.get("n_items") or 0) < 3:
            warnings.append("Для оценки надежности шкалы желательно использовать не менее трех пунктов.")
        if result.get("alpha") is not None and result["alpha"] < 0.7:
            warnings.append("Cronbach’s alpha ниже 0.7, внутренняя согласованность шкалы может быть недостаточной.")
        if any((item.get("item_total_correlation") or 0) < 0.3 for item in result.get("item_statistics") or []):
            warnings.append("Некоторые пункты слабо связаны с общей шкалой.")
        if any(item.get("improves_alpha") for item in result.get("alpha_if_item_deleted") or []):
            warnings.append("Удаление одного или нескольких пунктов может повысить Cronbach’s alpha; эти пункты стоит проверить содержательно.")
    elif analysis_type == "scale_index":
        if (result.get("n_items") or 0) < 3:
            warnings.append("Индекс шкалы построен по малому числу пунктов; интерпретация может быть ограниченной.")
        if any(item.get("reverse") and (item.get("min_value") is None or item.get("max_value") is None) for item in result.get("items") or []):
            warnings.append("Для обратного кодирования необходимо корректно задать минимальное и максимальное значения шкалы.")
        reliability = result.get("reliability") or {}
        if reliability.get("alpha") is not None and reliability["alpha"] < 0.7:
            warnings.append("Надежность пунктов индекса ограничена; интерпретируйте composite score с осторожностью.")
    elif analysis_type == "missing_analysis":
        if result.get("low_visibility_questions"):
            warnings.append("В опросе используется ветвление, поэтому вопросы, не показанные респонденту, не следует трактовать как обычные пропуски.")
        if result.get("top_skipped_questions"):
            warnings.append("Обнаружены вопросы с высоким уровнем пропусков среди тех, кому они были показаны.")
        if not (payload or {}).get("include_screened_out", False):
            warnings.append("Отсеченные респонденты не включены в анализ пропусков.")
    return warnings


def deduplicate_warnings(warnings):
    result = []
    seen = set()
    for warning in warnings:
        normalized = str(warning).strip() if warning is not None else ""
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
