from rest_framework import serializers


ENCODING_CHOICES = (
    "numeric",
    "binary",
    "ordinal",
    "one_hot",
    "rank",
    "matrix_ordinal",
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
    method = serializers.ChoiceField(choices=("pearson", "spearman"), default="pearson")
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
