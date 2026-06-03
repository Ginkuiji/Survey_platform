from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
def _mean(values):
    return sum(values) / len(values) if values else None


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    return ordered[middle] if n % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _percent(part, whole):
    return (part / whole * 100) if whole else 0


def _duration_seconds(start, end):
    if not start or not end:
        return None
    return (end - start).total_seconds()


def _duration_percentile(values, percentile):
    if not values:
        return None
    if np is not None:
        return float(np.percentile(values, percentile))
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * percentile / 100
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def _describe_durations(values):
    if not values:
        return {
            "count": 0,
            "average": None,
            "median": None,
            "min": None,
            "max": None,
            "p25": None,
            "p75": None,
            "iqr": None,
            "std": None,
        }
    p25 = _duration_percentile(values, 25)
    p75 = _duration_percentile(values, 75)
    return {
        "count": len(values),
        "average": float(_mean(values)),
        "median": float(_median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
        "p25": p25,
        "p75": p75,
        "iqr": float(p75 - p25) if p25 is not None and p75 is not None else None,
        "std": float(np.std(values, ddof=1)) if np is not None and len(values) > 1 else None,
    }


def _duration_distribution(values, bucket_size_seconds=60, max_buckets=30):
    if not values:
        return [], None
    bucket_counts = Counter(int(value // bucket_size_seconds) for value in values)
    max_bucket = max(bucket_counts)
    truncated = max_bucket + 1 > max_buckets
    buckets = []
    total = len(values)
    limit = max_buckets - 1 if truncated else max_bucket + 1
    for bucket in range(limit):
        start = bucket * bucket_size_seconds
        end = start + bucket_size_seconds
        count = bucket_counts.get(bucket, 0)
        buckets.append({
            "bucket_start_seconds": start,
            "bucket_end_seconds": end,
            "label": f"{start}-{end} сек.",
            "count": count,
            "percent": _percent(count, total),
        })
    if truncated:
        start = (max_buckets - 1) * bucket_size_seconds
        count = sum(count for bucket, count in bucket_counts.items() if bucket >= max_buckets - 1)
        buckets.append({
            "bucket_start_seconds": start,
            "bucket_end_seconds": None,
            "label": f"{start}+ сек.",
            "count": count,
            "percent": _percent(count, total),
        })
    return buckets, ("Распределение длительности сокращено до максимального числа интервалов." if truncated else None)


def _time_group_label(value, value_labels):
    if not value_labels:
        return str(value)
    if value in value_labels:
        return value_labels[value]
    try:
        int_value = int(float(value))
        if int_value in value_labels:
            return value_labels[int_value]
        if str(int_value) in value_labels:
            return value_labels[str(int_value)]
    except (TypeError, ValueError):
        pass
    return str(value)


def _time_analysis_group_test(group_breakdown, warnings):
    completion_groups = [
        item["_completion_values"]
        for item in group_breakdown
        if len(item.get("_completion_values") or []) >= 2
    ]
    if len(completion_groups) < 2:
        if group_breakdown:
            warnings.append("Недостаточно данных о времени завершения для проверки различий между группами.")
        return None
    if stats is None:
        warnings.append("Пакет scipy не установлен; проверка значимости различий времени между группами недоступна.")
        return {
            "method": None,
            "statistic": None,
            "p_value": None,
            "significant": None,
            "interpretation": "p-value недоступен; невозможно оценить различия между группами.",
        }
    if len(completion_groups) == 2:
        result = stats.mannwhitneyu(completion_groups[0], completion_groups[1], alternative="two-sided")
        method = "Mann-Whitney U"
    else:
        result = stats.kruskal(*completion_groups)
        method = "Kruskal-Wallis"
    statistic = _finite_or_none(result.statistic)
    p_value = _finite_or_none(result.pvalue)
    significant = bool(p_value is not None and p_value < 0.05)
    return {
        "method": method,
        "statistic": statistic,
        "p_value": p_value,
        "significant": significant,
        "interpretation": "Время прохождения статистически различается между группами." if significant else "Статистически значимых различий времени между группами не выявлено.",
    }


def compute_time_analysis(
    response_items,
    group_rows=None,
    group_variable=None,
    bucket_size_seconds=60,
    max_buckets=30,
    page_items=None,
    include_quality_flags=True,
    include_page_dropout=True,
    include_flow=True,
    too_fast_threshold_seconds=None,
) -> dict:
    warnings = []
    total_started = len(response_items)
    total_finished = 0
    total_completed = 0
    total_screened_out = 0
    total_active_unfinished = 0
    completion_durations = []
    screenout_durations = []
    screenout_reason_values = defaultdict(list)
    response_metrics = {}
    invalid_duration_count = 0

    for item in response_items:
        response_id = item.get("response_id")
        started_at = item.get("started_at")
        finished_at = item.get("finished_at")
        screened_out = bool(item.get("screened_out"))
        is_complete = bool(item.get("is_complete"))
        complete_reason = item.get("complete_reason")
        duration = _duration_seconds(started_at, finished_at)
        invalid_duration = duration is not None and duration <= 0
        if duration is not None and duration <= 0:
            warnings.append("Обнаружены неположительные длительности прохождения; они исключены из статистики.")
            invalid_duration_count += 1
            duration = None
        if finished_at:
            total_finished += 1
        elif not is_complete:
            total_active_unfinished += 1

        completion_duration = None
        if is_complete and not screened_out and complete_reason == "completed":
            total_completed += 1
            completion_duration = duration
            if completion_duration is not None:
                completion_durations.append(completion_duration)

        screenout_duration = None
        if screened_out:
            total_screened_out += 1
            screenout_duration = _duration_seconds(started_at, item.get("screened_out_at")) or duration
            if screenout_duration is not None and screenout_duration <= 0:
                warnings.append("Обнаружены неположительные длительности до screenout; они исключены из статистики.")
                screenout_duration = None
            if screenout_duration is not None:
                screenout_durations.append(screenout_duration)
                reason = (item.get("screened_out_reason") or "").strip() or "Без указания причины"
                screenout_reason_values[reason].append(screenout_duration)

        response_metrics[response_id] = {
            "finished": bool(finished_at),
            "completed": bool(completion_duration is not None or (is_complete and not screened_out and complete_reason == "completed")),
            "screened_out": screened_out,
            "completion_duration": completion_duration,
            "screenout_duration": screenout_duration,
            "answered_question_ids": set(item.get("answered_question_ids") or []),
            "invalid_duration": invalid_duration,
        }

    completion_distribution, completion_warning = _duration_distribution(completion_durations, bucket_size_seconds, max_buckets)
    screenout_distribution, screenout_warning = _duration_distribution(screenout_durations, bucket_size_seconds, max_buckets)
    if completion_warning:
        warnings.append(completion_warning)
    if screenout_warning:
        warnings.append(screenout_warning)

    screenout_reasons = [
        {
            "reason": reason,
            "count": len(values),
            "percent_screened_out": _percent(len(values), total_screened_out),
            "average_time_to_screenout_seconds": _mean(values),
        }
        for reason, values in sorted(screenout_reason_values.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    ]

    group_breakdown = []
    if group_rows is not None and group_variable is not None:
        grouped = defaultdict(list)
        for row in group_rows:
            response_id = row.get("response_id")
            value = row.get(group_variable.code)
            if response_id in response_metrics and not _is_missing(value):
                grouped[value].append(response_id)
        for group_value in _sort_values(grouped.keys()):
            ids = grouped[group_value]
            metrics = [response_metrics[response_id] for response_id in ids]
            completion_values = [item["completion_duration"] for item in metrics if item.get("completion_duration") is not None]
            screenout_values = [item["screenout_duration"] for item in metrics if item.get("screenout_duration") is not None]
            completed = sum(1 for item in metrics if item.get("completed"))
            screened = sum(1 for item in metrics if item.get("screened_out"))
            finished = sum(1 for item in metrics if item.get("finished"))
            group_breakdown.append({
                "group": group_value,
                "group_label": _time_group_label(group_value, group_variable.value_labels),
                "total_started": len(ids),
                "total_finished": finished,
                "total_completed": completed,
                "total_screened_out": screened,
                "completion_rate": _percent(completed, len(ids)),
                "screenout_rate": _percent(screened, len(ids)),
                "completion_time": _describe_durations(completion_values),
                "screenout_time": _describe_durations(screenout_values),
                "_completion_values": completion_values,
            })

    group_time_test = _time_analysis_group_test(group_breakdown, warnings) if group_breakdown else None
    completion_stats = _describe_durations(completion_durations)
    screenout_stats = _describe_durations(screenout_durations)
    p25 = completion_stats["p25"]
    p75 = completion_stats["p75"]
    iqr = completion_stats["iqr"]
    lower_fence = max(0, p25 - 1.5 * iqr) if p25 is not None and iqr is not None else None
    upper_fence = p75 + 1.5 * iqr if p75 is not None and iqr is not None else None
    median = completion_stats["median"]
    fast_threshold = float(too_fast_threshold_seconds) if too_fast_threshold_seconds is not None else max(30, (median or 0) * 0.25)
    short_outliers = [value for value in completion_durations if lower_fence is not None and value < lower_fence]
    long_outliers = [value for value in completion_durations if upper_fence is not None and value > upper_fence]
    too_fast_ids = {
        response_id for response_id, metrics in response_metrics.items()
        if metrics.get("completion_duration") is not None and metrics["completion_duration"] < fast_threshold
    }
    too_long_ids = {
        response_id for response_id, metrics in response_metrics.items()
        if metrics.get("completion_duration") is not None and upper_fence is not None and metrics["completion_duration"] > upper_fence
    }
    response_flags = []
    if include_quality_flags:
        for response_id, metrics in response_metrics.items():
            flags = []
            duration = metrics.get("completion_duration") or metrics.get("screenout_duration")
            if response_id in too_fast_ids:
                flags.append("too_fast")
            if response_id in too_long_ids:
                flags.append("too_long")
            if metrics.get("invalid_duration"):
                flags.append("invalid_duration")
            if metrics.get("screened_out"):
                flags.append("screened_out")
            if not metrics.get("finished"):
                flags.append("unfinished")
            if flags:
                response_flags.append({"response_id": response_id, "duration_seconds": duration, "flags": flags, "possibly_low_quality": bool({"too_fast", "too_long"} & set(flags)), "reason": "Прохождение требует проверки с учетом длительности и итогового статуса."})
    page_items = page_items or []
    dropout_by_page = []
    funnel_steps = [{"step": 0, "label": "Начали опрос", "count": total_started, "percent_of_started": 100.0}]
    if include_page_dropout:
        previous_entered = total_started
        for index, page in enumerate(page_items, start=1):
            question_ids = set(page.get("question_ids") or [])
            entered = sum(bool(metrics["answered_question_ids"] & question_ids) for metrics in response_metrics.values())
            dropout = max(0, previous_entered - entered)
            dropout_by_page.append({"page_id": page.get("page_id"), "page_title": page.get("page_title"), "page_order": page.get("page_order", index), "entered_count": previous_entered, "completed_page_count": entered, "dropout_count": dropout, "dropout_rate": _percent(dropout, previous_entered)})
            funnel_steps.append({"step": index, "page_id": page.get("page_id"), "label": page.get("page_title"), "count": entered, "percent_of_started": _percent(entered, total_started)})
            previous_entered = entered
    funnel_steps.append({"step": 999, "label": "Завершили", "count": total_completed, "percent_of_started": _percent(total_completed, total_started)})
    highest_dropout = max(dropout_by_page, key=lambda item: item["dropout_rate"], default=None)
    flow_nodes = [{"id": "start", "label": "Начали"}, *[{"id": f"page_{item.get('page_id')}", "label": item.get("page_title")} for item in page_items], {"id": "completed", "label": "Завершили"}, {"id": "screenout", "label": "Отсечены"}, {"id": "unfinished", "label": "Не завершили"}]
    flow_links = []
    if include_flow:
        previous = "start"
        for step in funnel_steps[1:-1]:
            current = f"page_{step.get('page_id')}"
            flow_links.append({"source": previous, "target": current, "value": step["count"]})
            previous = current
        flow_links.extend([{"source": previous, "target": "completed", "value": total_completed}, {"source": previous, "target": "screenout", "value": total_screened_out}, {"source": previous, "target": "unfinished", "value": total_active_unfinished}])
    duration_outliers = {"method": "iqr", "lower_fence_seconds": lower_fence, "upper_fence_seconds": upper_fence, "short_outliers_count": len(short_outliers), "long_outliers_count": len(long_outliers), "outliers_count": len(short_outliers) + len(long_outliers), "outliers_rate": _percent(len(short_outliers) + len(long_outliers), len(completion_durations))}
    quality_flags = {"too_fast": {"threshold_seconds": fast_threshold, "count": len(too_fast_ids), "rate": _percent(len(too_fast_ids), len(completion_durations)), "interpretation": "Слишком быстрое прохождение может указывать на невнимательное заполнение, но не является доказательством низкого качества ответа."}, "too_long": {"threshold_seconds": upper_fence, "count": len(too_long_ids), "rate": _percent(len(too_long_ids), len(completion_durations))}, "possibly_low_quality_count": len(too_fast_ids | too_long_ids), "possibly_low_quality_rate": _percent(len(too_fast_ids | too_long_ids), len(completion_durations))}
    if quality_flags["too_fast"]["rate"] >= 5:
        warnings.append("Обнаружены слишком быстрые прохождения; они требуют проверки перед содержательной интерпретацией.")
    if long_outliers:
        warnings.append("Обнаружены аномально длинные прохождения; они могут быть связаны с перерывами при заполнении анкеты.")
    if highest_dropout and highest_dropout["dropout_rate"] >= 20:
        warnings.append("На отдельных страницах наблюдается повышенный dropout; страница может требовать содержательной проверки.")
    if _percent(total_screened_out, total_started) >= 30:
        warnings.append("Доля screenout заметна; следует проверить условия скрининга.")
    duration_summary = {"count": completion_stats["count"], "average_seconds": completion_stats["average"], "median_seconds": median, "min_seconds": completion_stats["min"], "max_seconds": completion_stats["max"], "p25_seconds": p25, "p75_seconds": p75, "iqr_seconds": iqr, "std_seconds": completion_stats["std"], "invalid_duration_count": invalid_duration_count}
    screenout_block = {"total_screened_out": total_screened_out, "screenout_rate": _percent(total_screened_out, total_started), "reasons": [{**item, "percent_of_screened_out": item["percent_screened_out"], "percent_of_started": _percent(item["count"], total_started)} for item in screenout_reasons], "top_reason": screenout_reasons[0] if screenout_reasons else None}
    group_comparison = {"enabled": bool(group_breakdown), "group_variable": {"code": getattr(group_variable, "code", None), "label": getattr(group_variable, "label", None)} if group_variable else None, "groups": [{"group_value": item["group"], "group_label": item["group_label"], "n": item["total_started"], "median_seconds": item["completion_time"]["median"], "average_seconds": item["completion_time"]["average"], "p25_seconds": item["completion_time"]["p25"], "p75_seconds": item["completion_time"]["p75"], "iqr_seconds": item["completion_time"]["iqr"], "too_fast_count": sum(value < fast_threshold for value in item["_completion_values"]), "too_fast_rate": _percent(sum(value < fast_threshold for value in item["_completion_values"]), len(item["_completion_values"]))} for item in group_breakdown], "test": group_time_test, "warnings": []}
    for item in group_breakdown:
        item.pop("_completion_values", None)
    notes = []
    if include_page_dropout:
        notes.append("Dropout по страницам рассчитан приближенно на основе наличия ответов на вопросы страниц.")
    if len(response_flags) > 500:
        notes.append("Список флагов респондентов ограничен первыми 500 записями.")
    notes.append("Straight-lining и повторяющиеся паттерны ответов следует проверять отдельными методами контроля качества.")
    return {
        "method": "time_and_dropout_analysis",
        "n": total_started,
        "summary": {
            "total_started": total_started,
            "total_finished": total_finished,
            "total_completed": total_completed,
            "total_screened_out": total_screened_out,
            "total_active_unfinished": total_active_unfinished,
            "completion_rate": _percent(total_completed, total_started),
            "screenout_rate": _percent(total_screened_out, total_started),
            "finish_rate": _percent(total_finished, total_started),
            "active_unfinished_rate": _percent(total_active_unfinished, total_started),
            "average_completion_time_seconds": completion_stats["average"],
            "median_completion_time_seconds": completion_stats["median"],
            "min_completion_time_seconds": completion_stats["min"],
            "max_completion_time_seconds": completion_stats["max"],
            "average_screenout_time_seconds": screenout_stats["average"],
            "median_screenout_time_seconds": screenout_stats["median"],
            "min_screenout_time_seconds": screenout_stats["min"],
            "max_screenout_time_seconds": screenout_stats["max"],
        },
        "completion_time_distribution": completion_distribution,
        "duration_distribution": completion_distribution,
        "duration_summary": duration_summary,
        "duration_outliers": duration_outliers,
        "quality_flags": quality_flags,
        "response_flags": response_flags[:500],
        "dropout": {"by_page": dropout_by_page, "highest_dropout_page": highest_dropout},
        "page_funnel": {"steps": funnel_steps},
        "retention_curve": {"unit": "page", "points": [{"step": item["step"], "label": item["label"], "retained_count": item["count"], "retention_rate": item["percent_of_started"]} for item in funnel_steps]},
        "screenout": screenout_block,
        "group_comparison": group_comparison,
        "flow": {"nodes": flow_nodes if include_flow else [], "links": flow_links, "notes": ["Flow diagram построен приближенно по достижению страниц и итоговым статусам прохождения."] if include_flow else []},
        "screenout_time_distribution": screenout_distribution,
        "screenout_reasons": screenout_reasons,
        "group_breakdown": group_breakdown,
        "group_time_test": group_time_test,
        "warnings": warnings,
        "recommendations": ["Проверьте слишком быстрые прохождения перед использованием данных в сложном анализе.", "Если dropout концентрируется на конкретной странице, проверьте длину, сложность и обязательность вопросов на этой странице."],
        "notes": notes,
    }


