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
    n_clusters = serializers.IntegerField(min_value=2, max_value=10, required=False, default=3)
    standardize = serializers.BooleanField(default=True)
    max_iter = serializers.IntegerField(min_value=10, max_value=1000, required=False, default=300)

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

    def validate(self, attrs):
        if attrs["group"]["question_id"] == attrs["value"]["question_id"]:
            raise serializers.ValidationError("Group and value variables must be different questions.")
        return attrs
