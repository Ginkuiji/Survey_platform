from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_group_comparison_chart(report, config, result, chart_type):
    group_spec = config.get("group") or _single_spec(report.survey_id, config.get("groupQuestionId"), "group_comparison", "group")
    value_spec = config.get("value") or _single_spec(report.survey_id, config.get("valueQuestionId"), "group_comparison", "value")
    dataset = build_analysis_dataset(report.survey_id, [group_spec, value_spec])
    group_variable = _find_variable_by_question(dataset, group_spec["question_id"])
    value_variable = _find_variable_by_question(dataset, value_spec["question_id"])
    grouped = defaultdict(list)
    for row in dataset.rows:
        group_value = row.get(group_variable.code)
        value = _numeric(row.get(value_variable.code))
        if group_value is not None and value is not None:
            grouped[_value_label(group_variable, group_value)].append(value)
    groups = [(label, values) for label, values in grouped.items() if values]
    if len(groups) < 2:
        raise ValueError("Boxplot requires at least two non-empty groups.")
    if chart_type in {"mean_ci", "group_mean_ci_plot"}:
        stats_by_label = {
            str(item.get("label", item.get("group"))): item
            for item in result.get("groups") or []
        }
        labels = [label for label, _ in groups]
        means = [sum(values) / len(values) for _, values in groups]
        intervals = [stats_by_label.get(str(label), {}).get("confidence_interval_95") for label in labels]
        lower_errors = [mean - interval["low"] if interval else 0 for mean, interval in zip(means, intervals)]
        upper_errors = [interval["high"] - mean if interval else 0 for mean, interval in zip(means, intervals)]
        fig, ax = plt.subplots(figsize=(max(7, len(groups) * 1.1), 5))
        ax.bar(range(len(labels)), means, color="#1f77b4", alpha=0.8)
        if any(intervals):
            ax.errorbar(range(len(labels)), means, yerr=[lower_errors, upper_errors], fmt="none", ecolor="#222", capsize=4)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels([_truncate(label, 18) for label in labels], rotation=25, ha="right")
        ax.set_title("Средние значения по группам")
        ax.set_ylabel(_truncate(value_variable.label))
        ax.grid(axis="y", alpha=0.25)
        return figure_to_png(fig)
    if chart_type in {"violin", "group_violin_plot"}:
        fig, ax = plt.subplots(figsize=(max(7, len(groups) * 1.1), 5))
        ax.violinplot([values for _, values in groups], showmedians=True)
        ax.set_xticks(range(1, len(groups) + 1))
        ax.set_xticklabels([_truncate(label, 18) for label, _ in groups], rotation=25, ha="right")
        ax.set_title("Распределения показателя по группам")
        ax.set_ylabel(_truncate(value_variable.label))
        ax.grid(axis="y", alpha=0.25)
        return figure_to_png(fig)
    if chart_type in {"post_hoc", "post_hoc_table"}:
        raise ValueError("Таблица post-hoc сравнений доступна в JSON-результате отчета; отдельный PNG-график для нее не требуется.")
    fig, ax = plt.subplots(figsize=(max(7, len(groups) * 1.1), 5))
    ax.boxplot([values for _, values in groups], labels=[_truncate(label, 18) for label, _ in groups], patch_artist=True)
    ax.set_title("Group comparison boxplot")
    ax.set_ylabel(_truncate(value_variable.label))
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    return figure_to_png(fig)


