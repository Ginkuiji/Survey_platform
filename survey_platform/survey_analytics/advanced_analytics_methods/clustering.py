from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
def _complete_factor_cases_with_ids(rows, variables):
    matrix = []
    response_ids = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if all(_is_numeric(value) for value in values):
            matrix.append([_as_float(value) for value in values])
            response_ids.append(row.get("response_id"))
    return response_ids, matrix


def _complete_kmeans_cases(rows, variables):
    matrix = []
    response_ids = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if any(_is_missing(value) for value in values):
            continue
        if not all(_is_numeric(value) for value in values):
            raise ValueError("Для кластерного анализа все выбранные значения должны быть числовыми.")
        matrix.append([_as_float(value) for value in values])
        response_ids.append(row.get("response_id"))
    return response_ids, matrix


def _run_numpy_kmeans(x_matrix, n_clusters, max_iter, random_state):
    rng = np.random.default_rng(random_state)
    n = x_matrix.shape[0]
    initial_indexes = rng.choice(n, size=n_clusters, replace=False)
    centers = x_matrix[initial_indexes].copy()
    labels = np.zeros(n, dtype=int)

    for _ in range(max_iter):
        distances = np.sum((x_matrix[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        next_labels = np.argmin(distances, axis=1)

        next_centers = centers.copy()
        for cluster_index in range(n_clusters):
            members = x_matrix[next_labels == cluster_index]
            if len(members):
                next_centers[cluster_index] = np.mean(members, axis=0)
            else:
                farthest_index = int(np.argmax(np.min(distances, axis=1)))
                next_centers[cluster_index] = x_matrix[farthest_index]

        if np.array_equal(labels, next_labels) and np.allclose(centers, next_centers):
            labels = next_labels
            centers = next_centers
            break

        labels = next_labels
        centers = next_centers

    inertia = float(np.sum((x_matrix - centers[labels]) ** 2))
    return labels, centers, inertia


def _profile_label_for_value(value, value_labels):
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
    if str(value) in value_labels:
        return value_labels[str(value)]
    return str(value)


def _profile_value_key(value):
    try:
        numeric = float(value)
        if numeric.is_integer():
            return int(numeric)
        return numeric
    except (TypeError, ValueError):
        return value


def _profile_median(values):
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    return ordered[middle] if n % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _numeric_profile_summary(variable, all_values, cluster_values):
    if not all_values or not cluster_values:
        return None
    overall_mean = sum(all_values) / len(all_values)
    cluster_mean = sum(cluster_values) / len(cluster_values)
    overall_std = _sample_std(all_values) if len(all_values) > 1 else None
    cluster_std = _sample_std(cluster_values) if len(cluster_values) > 1 else None
    difference = cluster_mean - overall_mean
    z_difference = difference / overall_std if overall_std and overall_std > 0 else None
    if z_difference is None:
        interpretation = "около среднего"
    elif z_difference >= 0.5:
        interpretation = "выше среднего"
    elif z_difference <= -0.5:
        interpretation = "ниже среднего"
    else:
        interpretation = "около среднего"
    return {
        "variable": variable.code,
        "label": variable.label,
        "encoding": variable.encoding,
        "cluster_mean": float(cluster_mean),
        "cluster_median": float(_profile_median(cluster_values)),
        "cluster_std": float(cluster_std) if cluster_std is not None else None,
        "cluster_min": float(min(cluster_values)),
        "cluster_max": float(max(cluster_values)),
        "overall_mean": float(overall_mean),
        "overall_std": float(overall_std) if overall_std is not None else None,
        "difference": float(difference),
        "z_difference": float(z_difference) if z_difference is not None else None,
        "interpretation": interpretation,
    }


def _binary_profile_summary(variable, all_values, cluster_values):
    if not all_values or not cluster_values:
        return None
    overall_selected = sum(1 for value in all_values if value > 0)
    cluster_selected = sum(1 for value in cluster_values if value > 0)
    overall_percent = overall_selected / len(all_values) * 100
    cluster_percent = cluster_selected / len(cluster_values) * 100
    difference_pp = cluster_percent - overall_percent
    if difference_pp >= 10:
        interpretation = "чаще, чем в среднем"
    elif difference_pp <= -10:
        interpretation = "реже, чем в среднем"
    else:
        interpretation = "примерно как в среднем"
    return {
        "variable": variable.code,
        "label": variable.label,
        "encoding": variable.encoding,
        "cluster_count_selected": int(cluster_selected),
        "cluster_percent_selected": float(cluster_percent),
        "overall_percent_selected": float(overall_percent),
        "difference_pp": float(difference_pp),
        "interpretation": interpretation,
    }


def _categorical_distribution_summary(variable, all_values, cluster_values):
    value_labels = getattr(variable, "value_labels", None)
    if not value_labels or not all_values or not cluster_values:
        return None

    overall_counts = Counter(_profile_value_key(value) for value in all_values)
    cluster_counts = Counter(_profile_value_key(value) for value in cluster_values)
    categories = []
    for value in sorted(overall_counts.keys(), key=lambda item: str(item)):
        cluster_count = cluster_counts.get(value, 0)
        overall_count = overall_counts.get(value, 0)
        cluster_percent = cluster_count / len(cluster_values) * 100 if cluster_values else 0
        overall_percent = overall_count / len(all_values) * 100 if all_values else 0
        categories.append({
            "value": value,
            "label": _profile_label_for_value(value, value_labels),
            "cluster_count": int(cluster_count),
            "cluster_percent": float(cluster_percent),
            "overall_count": int(overall_count),
            "overall_percent": float(overall_percent),
            "difference_pp": float(cluster_percent - overall_percent),
        })

    return {
        "variable": variable.code,
        "label": variable.label,
        "encoding": variable.encoding,
        "categories": categories,
    }


def _cluster_interpretation(top_features):
    if not top_features:
        return "Выраженных отличий от общей выборки не выявлено."

    high = []
    low = []
    more = []
    less = []
    for feature in top_features[:3]:
        label = feature.get("label") or feature.get("variable")
        difference = feature.get("difference") or 0
        if feature.get("type") == "numeric":
            (high if difference > 0 else low).append(label)
        else:
            (more if difference > 0 else less).append(label)

    parts = []
    if high:
        parts.append(f"высокими значениями по признакам: {', '.join(high)}")
    if low:
        parts.append(f"низкими значениями по признакам: {', '.join(low)}")
    if more:
        parts.append(f"чаще встречается: {', '.join(more)}")
    if less:
        parts.append(f"реже встречается: {', '.join(less)}")
    if not parts:
        return "Выраженных отличий от общей выборки не выявлено."
    return f"Кластер характеризуется {'; '.join(parts)}."


def _build_cluster_profiles(profile_rows, profile_variables, assignments, max_profile_features=5):
    if not profile_rows or not profile_variables or not assignments:
        return []

    cluster_by_response_id = {
        assignment.get("response_id"): assignment.get("cluster")
        for assignment in assignments
        if assignment.get("response_id") is not None
    }
    cluster_ids = sorted(set(cluster_by_response_id.values()))
    total_assigned = len(cluster_by_response_id)
    rows_by_cluster = defaultdict(list)
    for row in profile_rows:
        response_id = row.get("response_id")
        cluster = cluster_by_response_id.get(response_id)
        if cluster is not None:
            rows_by_cluster[cluster].append(row)

    profiles = []
    numeric_encodings = {"numeric", "ordinal", "rank", "matrix_ordinal"}
    binary_encodings = {"binary", "one_hot", "matrix_multi_binary"}

    for cluster in cluster_ids:
        cluster_rows = rows_by_cluster.get(cluster, [])
        numeric_summary = []
        binary_summary = []
        categorical_summary = []
        top_features = []

        for variable in profile_variables:
            all_raw_values = [
                row.get(variable.code)
                for row in profile_rows
                if row.get("response_id") in cluster_by_response_id and not _is_missing(row.get(variable.code))
            ]
            cluster_raw_values = [
                row.get(variable.code)
                for row in cluster_rows
                if not _is_missing(row.get(variable.code))
            ]
            if not all_raw_values or not cluster_raw_values:
                continue

            if variable.encoding in numeric_encodings and all(_is_numeric(value) for value in all_raw_values + cluster_raw_values):
                all_values = [_as_float(value) for value in all_raw_values]
                cluster_values = [_as_float(value) for value in cluster_raw_values]
                summary = _numeric_profile_summary(variable, all_values, cluster_values)
                if summary:
                    numeric_summary.append(summary)
                    if not (variable.encoding == "ordinal" and getattr(variable, "value_labels", None)):
                        score = abs(summary["z_difference"]) if summary["z_difference"] is not None else abs(summary["difference"])
                        top_features.append({
                            "variable": variable.code,
                            "label": variable.label,
                            "type": "numeric",
                            "cluster_value": summary["cluster_mean"],
                            "overall_value": summary["overall_mean"],
                            "difference": summary["difference"],
                            "standardized_difference": summary["z_difference"],
                            "score": float(score),
                            "interpretation": summary["interpretation"],
                        })

            if variable.encoding in binary_encodings and all(_is_numeric(value) for value in all_raw_values + cluster_raw_values):
                all_values = [_as_float(value) for value in all_raw_values]
                cluster_values = [_as_float(value) for value in cluster_raw_values]
                summary = _binary_profile_summary(variable, all_values, cluster_values)
                if summary:
                    binary_summary.append(summary)
                    top_features.append({
                        "variable": variable.code,
                        "label": variable.label,
                        "type": "binary",
                        "cluster_value": summary["cluster_percent_selected"],
                        "overall_value": summary["overall_percent_selected"],
                        "difference": summary["difference_pp"],
                        "score": abs(summary["difference_pp"]),
                        "interpretation": summary["interpretation"],
                    })

            if variable.encoding == "ordinal" and getattr(variable, "value_labels", None):
                summary = _categorical_distribution_summary(variable, all_raw_values, cluster_raw_values)
                if summary:
                    categorical_summary.append(summary)
                    categories = summary.get("categories") or []
                    if categories:
                        top_category = max(categories, key=lambda item: abs(item.get("difference_pp") or 0))
                        top_features.append({
                            "variable": variable.code,
                            "label": f"{variable.label}: {top_category.get('label')}",
                            "type": "categorical",
                            "cluster_value": top_category.get("cluster_percent"),
                            "overall_value": top_category.get("overall_percent"),
                            "difference": top_category.get("difference_pp"),
                            "score": abs(top_category.get("difference_pp") or 0),
                            "interpretation": "чаще, чем в среднем" if (top_category.get("difference_pp") or 0) >= 10 else ("реже, чем в среднем" if (top_category.get("difference_pp") or 0) <= -10 else "примерно как в среднем"),
                        })

        top_features = sorted(top_features, key=lambda item: item.get("score") or 0, reverse=True)[:max_profile_features]
        size = len(cluster_rows)
        positive_features = [
            item for item in top_features
            if (item.get("difference") or 0) > 0
        ]
        negative_features = [
            item for item in top_features
            if (item.get("difference") or 0) < 0
        ]
        profiles.append({
            "cluster": cluster,
            "label": f"Кластер {cluster}",
            "size": size,
            "percent": round(size / total_assigned * 100, 2) if total_assigned else 0,
            "numeric_summary": numeric_summary,
            "categorical_summary": categorical_summary,
            "binary_summary": binary_summary,
            "top_distinguishing_features": top_features,
            "top_positive_features": positive_features,
            "top_negative_features": negative_features,
            "profile_values": [
                {
                    "code": item["variable"],
                    "label": item["label"],
                    "cluster_mean": item["cluster_mean"],
                    "overall_mean": item["overall_mean"],
                    "difference": item["difference"],
                    "standardized_difference": item["z_difference"],
                    "interpretation": item["interpretation"],
                }
                for item in numeric_summary
            ],
            "summary": _cluster_interpretation(top_features),
            "interpretation": _cluster_interpretation(top_features),
            "interpretation_hint": "Кластер можно содержательно рассматривать как возможный сегмент респондентов после проверки профиля признаков.",
        })

    return profiles


MAX_CLUSTER_ASSIGNMENTS = 500
MAX_SILHOUETTE_SAMPLES = 500
MAX_CLUSTER_SCATTER_POINTS = 500
MAX_RADAR_FEATURES = 8
DISTINGUISHING_FEATURE_THRESHOLD = 0.3


def _cluster_elbow(x_matrix, include_elbow, min_k, max_k, max_iter, random_state):
    if not include_elbow:
        return {"enabled": False, "points": [], "suggested_k": None, "interpretation": "Elbow plot отключен в настройках отчета."}
    upper = min(max_k, len(x_matrix) - 1)
    lower = max(1, min_k)
    if upper < lower:
        return {"enabled": False, "points": [], "suggested_k": None, "interpretation": "Недостаточно наблюдений для elbow plot."}
    points = []
    for k in range(lower, upper + 1):
        _, _, inertia = _run_numpy_kmeans(x_matrix, k, max_iter, random_state)
        points.append({"k": k, "inertia": inertia})
    suggested = None
    if len(points) >= 3:
        improvements = [points[index - 1]["inertia"] - points[index]["inertia"] for index in range(1, len(points))]
        if improvements and max(improvements) > 0:
            changes = [
                improvements[index - 1] - improvements[index]
                for index in range(1, len(improvements))
            ]
            if changes and max(changes) > 0:
                suggested = points[int(np.argmax(changes)) + 1]["k"]
    interpretation = (
        f"На elbow plot улучшение заметно замедляется после k={suggested}."
        if suggested is not None
        else "Явный локоть не обнаружен; число кластеров следует выбирать с учетом silhouette score и содержательной интерпретации."
    )
    return {"enabled": True, "min_k": lower, "max_k": upper, "points": points, "suggested_k": suggested, "interpretation": interpretation}


def _cluster_dimension_reduction(x_matrix, response_ids, labels, centers, cluster_number_by_label, include_projection):
    if not include_projection or x_matrix.shape[1] < 2:
        return {"method": "pca", "available": False, "points": [], "centroids": [], "explained_variance": [], "reason": "Для двумерной визуализации требуется не менее двух переменных."}
    centered = x_matrix - np.mean(x_matrix, axis=0)
    _, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
    components = vh[:2]
    points = centered @ components.T
    projected_centers = (centers - np.mean(x_matrix, axis=0)) @ components.T
    total_variance = float(np.sum(singular_values ** 2))
    explained = [
        {"component": f"PC{index + 1}", "explained_variance": float(singular_values[index] ** 2 / total_variance) if total_variance else 0}
        for index in range(min(2, len(singular_values)))
    ]
    return {
        "method": "pca",
        "available": True,
        "explained_variance": explained,
        "points": [
            {"response_id": response_id, "x": float(points[index, 0]), "y": float(points[index, 1]), "cluster": cluster_number_by_label[int(label)], "cluster_label": f"Кластер {cluster_number_by_label[int(label)]}"}
            for index, (response_id, label) in enumerate(zip(response_ids, labels))
        ][:MAX_CLUSTER_SCATTER_POINTS],
        "centroids": [
            {"cluster": cluster_number_by_label[label], "cluster_label": f"Кластер {cluster_number_by_label[label]}", "x": float(projected_centers[label, 0]), "y": float(projected_centers[label, 1])}
            for label in sorted(cluster_number_by_label)
        ],
    }


def compute_kmeans_clustering(
    rows,
    variables,
    n_clusters=3,
    standardize=True,
    max_iter=300,
    random_state=42,
    profile_rows=None,
    profile_variables=None,
    max_profile_features=5,
    include_elbow=True,
    elbow_min_k=2,
    elbow_max_k=8,
    include_pca_projection=True,
) -> dict:
    if np is None:
        raise ValueError("Для кластерного анализа требуется установленный пакет numpy.")
    if len(variables) < 2:
        raise ValueError("Для кластерного анализа требуется не менее двух переменных.")
    if n_clusters < 2 or n_clusters > 10:
        raise ValueError("Число кластеров должно быть от 2 до 10.")
    if max_iter < 10 or max_iter > 1000:
        raise ValueError("max_iter должен быть от 10 до 1000.")

    response_ids, complete_cases = _complete_kmeans_cases(rows, variables)
    n = len(complete_cases)
    p = len(variables)
    if n < n_clusters:
        raise ValueError("Для кластерного анализа число полных наблюдений должно быть не меньше числа кластеров.")

    raw_matrix = np.array(complete_cases, dtype=float)
    if not np.all(np.isfinite(raw_matrix)):
        raise ValueError("Данные кластерного анализа содержат некорректные числовые значения.")

    means = np.mean(raw_matrix, axis=0)
    standard_deviations = np.std(raw_matrix, axis=0, ddof=1)
    zero_variance_indexes = np.where(standard_deviations == 0)[0]
    if len(zero_variance_indexes):
        labels = [variables[index].label for index in zero_variance_indexes]
        raise ValueError(f"Cluster analysis cannot use variables with zero variance: {', '.join(labels)}.")

    x_matrix = (raw_matrix - means) / standard_deviations if standardize else raw_matrix
    warnings = []
    method = "numpy_kmeans"

    try:
        from sklearn.cluster import KMeans

        model = KMeans(
            n_clusters=n_clusters,
            max_iter=max_iter,
            random_state=random_state,
            n_init=10,
        )
        labels = model.fit_predict(x_matrix)
        centers = model.cluster_centers_
        inertia = float(model.inertia_)
        method = "sklearn_kmeans"
    except ImportError:
        labels, centers, inertia = _run_numpy_kmeans(x_matrix, n_clusters, max_iter, random_state)
        warnings.append("Пакет sklearn не установлен; использован резервный расчет k-средних на numpy.")

    output_centers = (centers * standard_deviations + means) if standardize else centers
    order = sorted(range(n_clusters), key=lambda index: (-int(np.sum(labels == index)), index))
    cluster_number_by_label = {label: position + 1 for position, label in enumerate(order)}

    clusters = []
    cluster_sizes = []
    cluster_centroids = []
    for label in order:
        size = int(np.sum(labels == label))
        center = output_centers[label]
        standardized_center = centers[label]
        cluster_number = cluster_number_by_label[label]
        clusters.append({
            "cluster": cluster_number,
            "size": size,
            "percent": round(size / n * 100, 2) if n else 0,
            "centroid": {
                variable.code: float(center[index])
                for index, variable in enumerate(variables)
            },
        })
        cluster_sizes.append({"cluster": cluster_number, "label": f"Кластер {cluster_number}", "count": size, "size": size, "percent": round(size / n * 100, 2) if n else 0})
        cluster_centroids.append({
            "cluster": cluster_number,
            "label": f"Кластер {cluster_number}",
            "values": [
                {"code": variable.code, "label": variable.label, "value": float(center[index]), "standardized_value": float(standardized_center[index])}
                for index, variable in enumerate(variables)
            ],
        })

    assigned_distances = np.linalg.norm(x_matrix - centers[labels], axis=1)
    assignments = [
        {
            "response_id": response_id,
            "cluster": cluster_number_by_label[int(label)],
            "cluster_label": f"Кластер {cluster_number_by_label[int(label)]}",
            "distance_to_centroid": float(assigned_distances[index]),
        }
        for index, (response_id, label) in enumerate(zip(response_ids, labels))
    ]
    profile_rows = profile_rows if profile_rows is not None else rows
    profile_variables = profile_variables if profile_variables is not None else variables
    cluster_profiles = _build_cluster_profiles(
        profile_rows,
        profile_variables,
        assignments,
        max_profile_features=max_profile_features,
    )
    distances_summary = []
    for label in order:
        values = assigned_distances[labels == label]
        distances_summary.append({
            "cluster": cluster_number_by_label[label],
            "label": f"Кластер {cluster_number_by_label[label]}",
            "mean_distance_to_centroid": float(np.mean(values)),
            "median_distance_to_centroid": float(np.median(values)),
            "min_distance_to_centroid": float(np.min(values)),
            "max_distance_to_centroid": float(np.max(values)),
            "std_distance_to_centroid": float(np.std(values, ddof=1)) if len(values) > 1 else 0,
        })
    distance_threshold = float(np.mean(assigned_distances) + 2 * np.std(assigned_distances, ddof=1)) if n > 1 else None
    high_distance_count = int(np.sum(assigned_distances > distance_threshold)) if distance_threshold is not None else 0
    cluster_distances = {
        "summary": distances_summary,
        "overall_mean_distance_to_centroid": float(np.mean(assigned_distances)),
        "high_distance_points_count": high_distance_count,
    }

    silhouette_score_value = None
    silhouette_samples_values = None
    try:
        from sklearn.metrics import silhouette_samples, silhouette_score
        if n_clusters < n and len(set(labels)) > 1:
            silhouette_score_value = float(silhouette_score(x_matrix, labels))
            silhouette_samples_values = silhouette_samples(x_matrix, labels)
    except ImportError:
        warnings.append("Пакет sklearn не установлен; silhouette score недоступен.")
    silhouette_summary = []
    silhouette_sample_rows = []
    if silhouette_samples_values is not None:
        silhouette_sample_rows = [
            {"response_id": response_id, "cluster": cluster_number_by_label[int(label)], "silhouette": float(silhouette_samples_values[index])}
            for index, (response_id, label) in enumerate(zip(response_ids, labels))
        ][:MAX_SILHOUETTE_SAMPLES]
        for label in order:
            values = silhouette_samples_values[labels == label]
            negative_count = int(np.sum(values < 0))
            silhouette_summary.append({
                "cluster": cluster_number_by_label[label],
                "label": f"Кластер {cluster_number_by_label[label]}",
                "mean_silhouette": float(np.mean(values)),
                "min_silhouette": float(np.min(values)),
                "negative_silhouette_count": negative_count,
                "negative_silhouette_rate": round(negative_count / len(values) * 100, 2) if len(values) else 0,
            })
    silhouette_interpretation = (
        "кластеры выражены слабо" if silhouette_score_value is not None and silhouette_score_value < 0.25
        else "кластеры разделены умеренно" if silhouette_score_value is not None and silhouette_score_value < 0.5
        else "кластеры хорошо разделены" if silhouette_score_value is not None and silhouette_score_value < 0.7
        else "кластеры очень хорошо разделены" if silhouette_score_value is not None
        else "silhouette score недоступен"
    )
    total_sum_of_squares = float(np.sum((x_matrix - np.mean(x_matrix, axis=0)) ** 2))
    cluster_quality = {"silhouette_score": silhouette_score_value, "silhouette_interpretation": silhouette_interpretation, "inertia": inertia, "within_cluster_sum_of_squares": inertia, "between_cluster_sum_of_squares": total_sum_of_squares - inertia, "warnings": []}
    elbow = _cluster_elbow(x_matrix, include_elbow, elbow_min_k, elbow_max_k, max_iter, random_state)
    dimension_reduction = _cluster_dimension_reduction(x_matrix, response_ids, labels, centers, cluster_number_by_label, include_pca_projection)

    standardized_centers_by_cluster = {cluster_number_by_label[label]: centers[label] for label in order}
    profile_heatmap = {
        "rows": [
            {"cluster": cluster_number, "cluster_label": f"Кластер {cluster_number}", "values": [{"code": variable.code, "label": variable.label, "value": float(output_centers[label, index]), "standardized_value": float(centers[label, index])} for index, variable in enumerate(variables)]}
            for label, cluster_number in [(label, cluster_number_by_label[label]) for label in order]
        ]
    }
    feature_variation = np.std(np.array(list(standardized_centers_by_cluster.values())), axis=0)
    radar_indexes = np.argsort(feature_variation)[::-1][:MAX_RADAR_FEATURES]
    radar_profiles = [
        {"cluster": cluster_number_by_label[label], "cluster_label": f"Кластер {cluster_number_by_label[label]}", "values": [{"axis": variables[index].label, "code": variables[index].code, "value": float(centers[label, index])} for index in radar_indexes]}
        for label in order
    ]
    top_distinguishing_features = []
    weak_profile_clusters = []
    for profile in cluster_profiles:
        distinguishing = [
            item for item in profile.get("top_distinguishing_features", [])
            if abs(item.get("standardized_difference") if item.get("standardized_difference") is not None else item.get("difference") or 0) >= DISTINGUISHING_FEATURE_THRESHOLD
        ]
        if not distinguishing:
            weak_profile_clusters.append(profile["cluster"])
        for item in distinguishing:
            difference = item.get("difference") or 0
            top_distinguishing_features.append({
                "cluster": profile["cluster"], "cluster_label": profile.get("label"), "code": item.get("variable"), "label": item.get("label"),
                "cluster_mean": item.get("cluster_value"), "overall_mean": item.get("overall_value"), "standardized_difference": item.get("standardized_difference", item.get("score")),
                "direction": "higher" if difference > 0 else "lower", "interpretation": item.get("interpretation"),
            })
    notes = ["В текущей реализации для двумерной визуализации кластеров используется PCA-проекция."]
    if len(assignments) > MAX_CLUSTER_ASSIGNMENTS:
        notes.append("Для отображения сохранена ограниченная выборка назначений респондентов к кластерам.")
    if n > MAX_SILHOUETTE_SAMPLES:
        notes.append("Для отображения сохранена ограниченная выборка silhouette-значений.")
    if n > MAX_CLUSTER_SCATTER_POINTS:
        notes.append("Для PCA scatterplot сохранена ограниченная выборка респондентов.")
    sizes = [item["size"] for item in clusters]
    if min(sizes) < 5:
        warnings.append("Один или несколько кластеров содержат мало респондентов; такие кластеры могут быть нестабильными.")
    if min(sizes) and max(sizes) / min(sizes) >= 10:
        warnings.append("Размеры кластеров сильно различаются; сегментацию следует интерпретировать осторожно.")
    if max(sizes) / n > 0.7:
        warnings.append("Один кластер содержит большую часть выборки, поэтому структура сегментов может быть слабой.")
    if silhouette_score_value is not None and silhouette_score_value < 0.25:
        cluster_quality["warnings"].append("Silhouette score низкий, кластеры могут быть плохо разделены.")
    if any(item["negative_silhouette_count"] for item in silhouette_summary):
        warnings.append("В одном или нескольких кластерах есть респонденты с отрицательным silhouette; их принадлежность может быть неустойчивой.")
    if high_distance_count:
        warnings.append("Обнаружены респонденты, находящиеся далеко от центроидов кластеров; они могут быть плохо представлены выбранной структурой.")
    if weak_profile_clusters:
        warnings.append("Профили некоторых кластеров выражены слабо; отличающие признаки почти не выделяются.")

    return {
        "method": method,
        "n": n,
        "n_variables": p,
        "n_clusters": n_clusters,
        "standardize": standardize,
        "max_iter": max_iter,
        "variables": [
            {"code": variable.code, "label": variable.label}
            for variable in variables
        ],
        "clusters": clusters,
        "assignments": assignments,
        "cluster_assignments": assignments[:MAX_CLUSTER_ASSIGNMENTS],
        "cluster_sizes": cluster_sizes,
        "cluster_centroids": cluster_centroids,
        "cluster_distances": cluster_distances,
        "cluster_profiles": cluster_profiles,
        "top_distinguishing_features": top_distinguishing_features,
        "cluster_quality": cluster_quality,
        "silhouette_score": silhouette_score_value,
        "silhouette": {"score": silhouette_score_value, "samples": silhouette_sample_rows, "cluster_summary": silhouette_summary},
        "elbow": elbow,
        "dimension_reduction": dimension_reduction,
        "radar_profiles": radar_profiles,
        "profile_heatmap": profile_heatmap,
        "inertia": inertia,
        "warnings": warnings,
        "notes": notes,
    }


