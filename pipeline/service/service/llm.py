from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LLMConfig:
    mode: str  # "off" | "mock" | "openai"
    base_url: str
    api_key: str
    model: str
    timeout_sec: float


def llm_config_from_env() -> LLMConfig:
    return LLMConfig(
        mode=str(os.environ.get("APP_LLM_MODE", "mock")).strip().lower(),
        base_url=str(os.environ.get("APP_LLM_BASE_URL", "https://api.openai.com/v1")).strip(),
        api_key=str(os.environ.get("APP_LLM_API_KEY", "")).strip(),
        model=str(os.environ.get("APP_LLM_MODEL", "gpt-4o-mini")).strip(),
        timeout_sec=float(os.environ.get("APP_LLM_TIMEOUT_SEC", "12")),
    )


_JSON_EXTRACT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_loose(text: str) -> Optional[Dict[str, Any]]:
    s = (text or "").strip()
    if not s:
        return None
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else None
    except Exception:
        pass
    m = _JSON_EXTRACT_RE.search(s)
    if not m:
        return None
    try:
        v = json.loads(m.group(0))
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def _mock_analysis(pred_class: str, *, severity: str, prob: float, evidence: Dict[str, Any]) -> Dict[str, Any]:
    pred = (pred_class or "").lower()
    templates = list(evidence.get("top_templates") or [])[:5]
    examples = list(evidence.get("error_examples") or [])[:3]

    if "dhcp" in pred:
        suspected = ["DHCP Agent/网络命名空间异常", "Neutron 侧服务不可用或延迟", "实例网卡绑定/OVS/bridge 配置不一致"]
        steps = [
            "检查 Neutron DHCP agent 是否存活、是否在对应主机上调度",
            "检查实例所在计算节点与网络节点连通性（MTU、VLAN/VXLAN、iptables）",
            "从 nova-compute / neutron-server 日志中按 request_id 追踪失败链路",
        ]
        impact = "实例可能无法获取 IP，启动后不可达"
    elif "destroy" in pred or "undefine" in pred:
        suspected = ["libvirt domain 状态异常导致 destroy/undefine 失败", "nova-compute 与 libvirtd 通信异常", "实例状态机与资源回收不同步"]
        steps = [
            "在计算节点检查 libvirtd 状态与 domain 列表，确认实例是否残留",
            "检查 nova-compute 日志中是否存在 libvirtError / timeout",
            "必要时执行手工清理：virsh undefine（谨慎）并核对 Nova DB 状态",
        ]
        impact = "实例生命周期异常，可能导致资源泄漏/残留"
    else:
        suspected = ["Nova/Neutron/Placement 组件间调用失败", "后端存储或网络抖动", "短时间错误突发导致窗口内 ERROR 比例升高"]
        steps = [
            "按 entity_key/window_end 定位窗口内 ERROR 原文，提取 request_id 进行链路追踪",
            "检查对应时间段的服务健康（nova-api/nova-compute/neutron）与资源使用",
            "若告警重复出现，适当调高阈值或延长 dedup TTL 以避免刷屏",
        ]
        impact = "可能导致实例创建/删除失败或性能下降"

    return {
        "summary": f"检测到疑似故障：{pred_class}（{severity}，置信度 {prob:.3f}）。",
        "suspected_causes": suspected,
        "next_steps": steps,
        "impact": impact,
        "confidence": float(prob),
        "evidence_used": {"top_templates": templates, "error_examples": examples},
        "mode": "mock",
    }


def _openai_chat(cfg: LLMConfig, *, prompt: str) -> Optional[str]:
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg.model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "You are an AIOps assistant for OpenStack Nova. Reply ONLY with valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    req = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError:
        return None
    except Exception:
        return None

    try:
        obj = json.loads(raw)
        content = obj["choices"][0]["message"]["content"]
        return str(content)
    except Exception:
        return None


def generate_llm_analysis(
    cfg: LLMConfig,
    *,
    alert_id: str,
    entity_key: str,
    window_start: str,
    window_end: str,
    pred_class: str,
    severity: str,
    prob: float,
    evidence: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    mode = (cfg.mode or "off").lower()
    if mode in ("off", "disabled", "0", "false", "no"):
        return None

    if mode == "mock" or not cfg.api_key:
        return _mock_analysis(pred_class, severity=severity, prob=prob, evidence=evidence)

    prompt = (
        "请基于以下 OpenStack Nova 告警证据，输出严格 JSON（不要 Markdown/不要多余文本），字段：\n"
        "- summary: string（50~120字）\n"
        "- suspected_causes: string[]（3~5条）\n"
        "- next_steps: string[]（3~6条，尽量可操作）\n"
        "- impact: string\n"
        "- confidence: number（0~1）\n"
        "- evidence_used: object（可包含 top_templates、error_examples 摘要）\n\n"
        f"alert_id={alert_id}\n"
        f"entity_key={entity_key}\n"
        f"window={window_start} ~ {window_end}\n"
        f"pred_class={pred_class}\n"
        f"severity={severity}\n"
        f"prob={prob:.6f}\n\n"
        f"evidence={json.dumps(evidence, ensure_ascii=False)}\n"
    )

    content = _openai_chat(cfg, prompt=prompt)
    parsed = _parse_json_loose(content or "")
    if not parsed:
        return None
    parsed["mode"] = "openai"
    return parsed

