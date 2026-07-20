{{/* Chart name + version label */}}
{{- define "temporal-video-translator.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Common labels */}}
{{- define "temporal-video-translator.labels" -}}
helm.sh/chart: {{ include "temporal-video-translator.chart" . }}
{{ include "temporal-video-translator.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Selector labels */}}
{{- define "temporal-video-translator.selectorLabels" -}}
app: {{ .Values.app.name }}
{{- end }}

{{/* Plain env vars from .Values.env for the worker */}}
{{- define "temporal-video-translator.env" -}}
{{- range $key, $value := .Values.env }}
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
{{- end }}
