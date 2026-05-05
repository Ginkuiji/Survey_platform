from rest_framework import serializers


ENCODING_CHOICES = (
    "numeric",
    "binary",
    "ordinal",
    "one_hot",
    "rank",
    "matrix_ordinal",
    "matrix_multi_binary",
)

MEASURE_CHOICES = (
    "nominal",
    "ordinal",
    "interval",
    "ratio",
    "binary",
)


class AdvancedVariableSer(serializers.Serializer):
    question_id = serializers.IntegerField()
    encoding = serializers.ChoiceField(choices=ENCODING_CHOICES)
    measure = serializers.ChoiceField(choices=MEASURE_CHOICES)


class CorrelationAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=("pearson", "spearman", "kendall"), default="pearson")
    variables = AdvancedVariableSer(many=True, allow_empty=False)

    def validate_variables(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Correlation requires at least two variables.")
        return value


class CrosstabAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    row = AdvancedVariableSer()
    column = AdvancedVariableSer()


class ChiSquareAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    row = AdvancedVariableSer()
    column = AdvancedVariableSer()


class RegressionAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    target = AdvancedVariableSer()
    features = AdvancedVariableSer(many=True, allow_empty=False)
    include_intercept = serializers.BooleanField(default=True)

    def validate_features(self, value):
        if len(value) < 1:
            raise serializers.ValidationError("Regression requires at least one feature.")
        return value


class FactorAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    variables = AdvancedVariableSer(many=True, allow_empty=False)
    n_factors = serializers.IntegerField(min_value=1, required=False, default=2)
    rotation = serializers.ChoiceField(choices=("none", "varimax"), required=False, default="varimax")
    standardize = serializers.BooleanField(default=True)
    include_factor_scores = serializers.BooleanField(default=False)

    def validate_variables(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Factor analysis requires at least three variables.")
        return value

    def validate(self, attrs):
        variables = attrs.get("variables", [])
        n_factors = attrs.get("n_factors", 2)
        if n_factors >= len(variables):
            raise serializers.ValidationError("n_factors must be less than number of variables.")
        return attrs


class ClusterAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    variables = AdvancedVariableSer(many=True, allow_empty=False)
    profile_variables = AdvancedVariableSer(many=True, required=False, allow_empty=True)
    n_clusters = serializers.IntegerField(min_value=2, max_value=10, required=False, default=3)
    standardize = serializers.BooleanField(default=True)
    max_iter = serializers.IntegerField(min_value=10, max_value=1000, required=False, default=300)
    max_profile_features = serializers.IntegerField(min_value=1, max_value=20, required=False, default=5)

    def validate_variables(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Cluster analysis requires at least two variables.")
        return value


class GroupComparisonSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    group = AdvancedVariableSer()
    value = AdvancedVariableSer()
    method = serializers.ChoiceField(
        choices=("t_test", "anova", "mann_whitney", "kruskal_wallis"),
        default="anova",
    )
    alpha = serializers.FloatField(default=0.05, min_value=0.001, max_value=0.2)
    post_hoc = serializers.BooleanField(default=False)
    post_hoc_method = serializers.ChoiceField(
        choices=("auto", "pairwise_t_test", "pairwise_mann_whitney", "tukey_hsd"),
        default="auto",
        required=False,
    )
    p_adjust = serializers.ChoiceField(
        choices=("bonferroni", "holm"),
        default="bonferroni",
        required=False,
    )

    def validate(self, attrs):
        if attrs["group"]["question_id"] == attrs["value"]["question_id"]:
            raise serializers.ValidationError("Group and value variables must be different questions.")
        method = attrs.get("method")
        post_hoc_method = attrs.get("post_hoc_method", "auto")
        if not attrs.get("post_hoc", False):
            return attrs
        if post_hoc_method == "tukey_hsd" and method != "anova":
            raise serializers.ValidationError("Tukey HSD can be used only with ANOVA.")
        if post_hoc_method == "pairwise_t_test" and method != "anova":
            raise serializers.ValidationError("Pairwise t-tests can be used only with ANOVA.")
        if post_hoc_method == "pairwise_mann_whitney" and method != "kruskal_wallis":
            raise serializers.ValidationError("Pairwise Mann-Whitney tests can be used only with Kruskal-Wallis.")
        return attrs


class TimeAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    group_by = AdvancedVariableSer(required=False, allow_null=True)
    include_active = serializers.BooleanField(default=False)
    bucket_size_seconds = serializers.IntegerField(
        min_value=10,
        max_value=3600,
        required=False,
        default=60,
    )
    max_buckets = serializers.IntegerField(
        min_value=5,
        max_value=100,
        required=False,
        default=30,
    )

    def validate_group_by(self, value):
        if not value:
            return value
        if value.get("encoding") not in ("binary", "ordinal"):
            raise serializers.ValidationError(
                "Time analysis group_by supports only binary or ordinal categorical variables."
            )
        return value


class ReliabilityAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    variables = AdvancedVariableSer(many=True, allow_empty=False)
    standardize = serializers.BooleanField(default=False)

    def validate_variables(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Cronbach's alpha requires at least two variables.")
        return value


class CorrespondenceAnalysisSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    row = AdvancedVariableSer()
    column = AdvancedVariableSer()
    n_dimensions = serializers.IntegerField(min_value=1, max_value=5, required=False, default=2)

    def validate(self, attrs):
        if attrs["row"]["question_id"] == attrs["column"]["question_id"]:
            raise serializers.ValidationError("Row and column variables must be different questions.")
        return attrs


class LogisticRegressionSer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    target = AdvancedVariableSer()
    features = AdvancedVariableSer(many=True, allow_empty=False)
    include_intercept = serializers.BooleanField(default=True)
    threshold = serializers.FloatField(default=0.5, min_value=0.01, max_value=0.99)
    max_iter = serializers.IntegerField(default=1000, min_value=50, max_value=10000)
    learning_rate = serializers.FloatField(default=0.1, min_value=0.0001, max_value=1.0)
    regularization = serializers.ChoiceField(
        choices=("none", "l2"),
        default="l2",
        required=False,
    )
    lambda_ = serializers.FloatField(default=0.01, min_value=0.0, max_value=10.0, required=False)

    def validate_features(self, value):
        if len(value) < 1:
            raise serializers.ValidationError("Logistic regression requires at least one feature.")
        return value

    def validate(self, attrs):
        target_question_id = attrs["target"]["question_id"]
        feature_question_ids = [item["question_id"] for item in attrs["features"]]
        if target_question_id in feature_question_ids:
            raise serializers.ValidationError("Target question must not be used as a feature.")
        return attrs
