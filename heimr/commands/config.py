# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import os
import yaml


def normalize_config(config: dict) -> dict:
    """
    Normalize legacy/alias keys to the canonical config schema.

    Canonical keys:
      - llm_url, llm_model, disable_llm
      - prometheus, loki, tempo, prompt_template, output, compare_*

    Legacy/aliases supported:
      - explain: false => disable_llm: true
      - no_llm: true => disable_llm: true
      - llm_url without /v1 => append /v1 for Ollama/OpenAI-compatible servers
    """
    if not isinstance(config, dict):
        return {}

    normalized = dict(config)

    if normalized.get("disable_llm") is None:
        if normalized.get("no_llm") is True:
            normalized["disable_llm"] = True
        elif normalized.get("explain") is False:
            normalized["disable_llm"] = True
        else:
            normalized["disable_llm"] = False

    llm_url = normalized.get("llm_url")
    if isinstance(llm_url, str) and llm_url.startswith("http"):
        if not llm_url.rstrip("/").endswith("/v1"):
            normalized["llm_url"] = llm_url.rstrip("/") + "/v1"

    return normalized


def load_config(config_path: str) -> dict:
    """
    Load configuration from a YAML file.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    return normalize_config(config)


def merge_config_with_args(args, config: dict):
    """
    Merge config file settings with command line arguments.
    CLI arguments take precedence over config file.
    """
    key_mapping = {
        'prometheus': 'prometheus',
        'prometheus_url': 'prometheus',
        'prometheus_file': 'prometheus',
        'loki': 'loki',
        'loki_url': 'loki',
        'loki_file': 'loki',
        'tempo': 'tempo',
        'tempo_url': 'tempo',
        'tempo_file': 'tempo',
        'llm_url': 'llm_url',
        'llm_model': 'llm_model',
        'disable_llm': 'no_llm',
        'no_llm': 'no_llm',
        'prompt_template': 'prompt_template',
        'output': 'output',
        'compare_baseline': 'compare_baseline',
        'compare_prometheus': 'compare_prometheus',
        'compare_loki': 'compare_loki',
        'compare_tempo': 'compare_tempo',
        'detector_mode': 'detector_mode',
        'trend_threshold': 'trend_threshold',
        'cpu_threshold': 'cpu_threshold',
        'mem_growth_threshold': 'mem_growth_threshold',
        'anomaly_threshold': 'anomaly_threshold',
        'error_rate_threshold': 'error_rate_threshold',
        'llm_timeout_sec': 'llm_timeout_sec',
        'llm_max_retries': 'llm_max_retries',
        'log_level': 'log_level',
        'grafana_url': 'grafana_url',
        'grafana_dashboard_uid': 'grafana_dashboard_uid',
    }

    for config_key, arg_key in key_mapping.items():
        if config_key in config:
            current_value = getattr(args, arg_key, None)
            if current_value is None or (isinstance(current_value, bool) and not current_value):
                setattr(args, arg_key, config[config_key])

    return args
