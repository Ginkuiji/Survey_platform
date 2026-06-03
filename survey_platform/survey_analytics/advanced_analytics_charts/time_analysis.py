from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_time_analysis_chart(report, config, result, chart_type):
    if chart_type in {"flow", "flow_diagram"}:
        raise ValueError("Flow diagram доступен в интерактивном отчете как агрегированная таблица.")
    if chart_type in {"funnel", "page_funnel"}:
        rows = (result.get("page_funnel") or {}).get("steps") or []
        if not rows:
            raise ValueError("Воронка прохождения недоступна.")
        return _bar_chart([item.get("label") for item in rows], [_numeric(item.get("count")) or 0 for item in rows], "Воронка прохождения", "Респонденты")
    if chart_type == "retention_curve":
        rows = (result.get("retention_curve") or {}).get("points") or []
        if not rows:
            raise ValueError("Retention curve недоступна.")
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot([item.get("label") for item in rows], [_numeric(item.get("retention_rate")) or 0 for item in rows], marker="o")
        ax.set_title("Retention curve")
        ax.set_ylabel("Retention, %")
        ax.tick_params(axis="x", rotation=30)
        ax.grid(axis="y", alpha=0.25)
        return figure_to_png(fig)
    if chart_type == "dropout_by_page":
        rows = (result.get("dropout") or {}).get("by_page") or []
        if not rows:
            raise ValueError("Dropout по страницам недоступен.")
        return _bar_chart([item.get("page_title") for item in rows], [_numeric(item.get("dropout_rate")) or 0 for item in rows], "Dropout по страницам", "Dropout, %")
    if chart_type == "screenout_reasons":
        rows = (result.get("screenout") or {}).get("reasons") or result.get("screenout_reasons") or []
        if not rows:
            raise ValueError("Причины screenout недоступны.")
        return _bar_chart([item.get("reason") for item in rows], [_numeric(item.get("count")) or 0 for item in rows], "Причины screenout", "Респонденты")
    if chart_type == "boxplot":
        summary = result.get("duration_summary") or {}
        if summary.get("median_seconds") is None:
            raise ValueError("Boxplot-показатели времени недоступны.")
        stats = [{
            "label": "Время прохождения",
            "med": summary.get("median_seconds"),
            "q1": summary.get("p25_seconds"),
            "q3": summary.get("p75_seconds"),
            "whislo": summary.get("min_seconds"),
            "whishi": summary.get("max_seconds"),
            "fliers": [],
        }]
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.bxp(stats, showfliers=False)
        ax.set_title("Boxplot времени прохождения")
        ax.set_ylabel("Секунды")
        ax.grid(axis="y", alpha=0.25)
        return figure_to_png(fig)
    if chart_type == "group_boxplot":
        rows = (result.get("group_comparison") or {}).get("groups") or []
        if not rows:
            raise ValueError("Сравнение времени по группам недоступно.")
        stats = [{
            "label": item.get("group_label"),
            "med": item.get("median_seconds"),
            "q1": item.get("p25_seconds"),
            "q3": item.get("p75_seconds"),
            "whislo": item.get("p25_seconds"),
            "whishi": item.get("p75_seconds"),
            "fliers": [],
        } for item in rows if item.get("median_seconds") is not None]
        if not stats:
            raise ValueError("Сравнение времени по группам недоступно.")
        fig, ax = plt.subplots(figsize=(max(7, len(stats) * 1.2), 5))
        ax.bxp(stats, showfliers=False)
        ax.set_title("Сравнение времени по группам")
        ax.set_ylabel("Секунды")
        ax.tick_params(axis="x", rotation=30)
        ax.grid(axis="y", alpha=0.25)
        return figure_to_png(fig)
    rows = result.get("duration_distribution") or result.get("completion_time_distribution") or []
    if not rows:
        raise ValueError("Распределение времени прохождения недоступно.")
    return _bar_chart([item.get("label") for item in rows], [_numeric(item.get("count")) or 0 for item in rows], "Распределение времени прохождения", "Респонденты")


