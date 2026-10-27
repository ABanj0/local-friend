"""Estimated context admission and bounded extractive receipts, never execution authority."""
import base64
import copy
import hashlib
import io
import json
import math
import re

from .verification import validate as validate_verification
from .vision import MAX_IMAGE_BYTES, MAX_IMAGES, MAX_PIXELS

METHOD = "utf8_div3_visual_v1"
MAX_MESSAGES = 512
MAX_TEXT_BYTES = 4 * 1024**2
TEMPLATE_RESERVE = 256
NOTICE_KEYS = {"version", "method", "status", "context_window", "output_reserve", "template_reserve",
               "text_estimate", "schema_estimate", "visual_reserve", "images", "total_estimate",
               "available_estimate", "original_estimate", "compacted_messages", "reason"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class ContextBudgetExceeded(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__("Context cannot fit without losing protected instructions, images or evidence. "
                         "Increase context, reduce maximum output, or split the task. Estimates are not exact token counts.")


def validate_notice(report):
    if (not isinstance(report, dict) or set(report) != NOTICE_KEYS or report["version"] != 1
            or type(report["version"]) is not int or report["method"] != METHOD
            or not isinstance(report["status"], str) or report["status"] not in {"fits", "compacted", "blocked"}
            or not isinstance(report["reason"], str)
            or report["reason"] not in {"estimated", "protected_context", "input_bound", "native_context_limit"}):
        raise ValueError("Invalid context observation")
    for key in NOTICE_KEYS - {"version", "method", "status", "reason"}:
        if type(report[key]) is not int or not -10_000_000 <= report[key] <= 10_000_000:
            raise ValueError("Invalid context observation count")
    if (any(report[key] < 0 for key in NOTICE_KEYS - {"version", "method", "status", "reason", "available_estimate"})
            or not 1 <= report["context_window"] <= 32768 or not 1 <= report["output_reserve"] <= 32768
            or report["template_reserve"] != TEMPLATE_RESERVE or report["images"] > MAX_IMAGES
            or report["compacted_messages"] > MAX_MESSAGES
            or report["total_estimate"] != sum(report[key] for key in
                ("text_estimate", "schema_estimate", "visual_reserve", "output_reserve", "template_reserve"))
            or report["available_estimate"] != report["context_window"] - report["total_estimate"]
            or report["original_estimate"] < report["total_estimate"]
            or report["status"] != "blocked" and report["total_estimate"] > report["context_window"]
            or report["status"] == "compacted" and report["compacted_messages"] == 0):
        raise ValueError("Inconsistent context observation")
    return report


def image_reserve(images):
    from PIL import Image, UnidentifiedImageError
    reserve = 0
    for value in images:
        if not isinstance(value, str) or len(value) > (MAX_IMAGE_BYTES + 2) // 3 * 4:
            raise ValueError("Context image exceeds the supported size")
        try:
            raw = base64.b64decode(value, validate=True)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > MAX_PIXELS:
                    raise ValueError("Context image format or dimensions are unsupported")
                # A disclosed policy reservation, not a model-specific visual tokenizer.
                reserve += 512 + math.ceil(image.width * image.height / 1024)
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
            raise ValueError("Context image could not be decoded safely") from error
    return reserve


def estimate(messages, context_window, output_reserve, *, tools=None, schema=None, _visual=None):
    if not isinstance(messages, list) or len(messages) > MAX_MESSAGES:
        raise ValueError("Context has too many messages")
    text, images = [], []
    for message in messages:
        if (not isinstance(message, dict) or not isinstance(message.get("role"), str)
                or message["role"] not in {"system", "user", "assistant", "tool"}
                or message.get("content") is not None and not isinstance(message["content"], str)
                or not isinstance(message.get("images", []), list)):
            raise ValueError("Invalid context message")
        text.append({key: value for key, value in message.items() if key != "images"})
        images.extend(message.get("images", []))
    if len(images) > MAX_IMAGES:
        raise ValueError("Too many original images; start a new conversation")
    size = len(encoded(text))
    if size > MAX_TEXT_BYTES:
        raise ValueError("Context text exceeds the supported input bound")
    schema_size = len(encoded({"tools": tools, "format": schema})) if tools or schema else 0
    if schema_size > 512 * 1024:
        raise ValueError("Context schemas exceed the supported input bound")
    text_tokens = math.ceil(size / 3) + len(messages) * 16
    schema_tokens = math.ceil(schema_size / 3)
    if _visual is not None and _visual[1] != len(images):
        raise ValueError("Protected context images changed during compaction")
    visual = image_reserve(images) if _visual is None else _visual[0]
    total = text_tokens + schema_tokens + visual + output_reserve + TEMPLATE_RESERVE
    return {"version": 1, "method": METHOD, "status": "fits" if total <= context_window else "blocked",
            "context_window": context_window, "output_reserve": output_reserve, "template_reserve": TEMPLATE_RESERVE,
            "text_estimate": text_tokens, "schema_estimate": schema_tokens, "visual_reserve": visual,
            "images": len(images), "total_estimate": total, "available_estimate": context_window - total,
            "original_estimate": total, "compacted_messages": 0, "reason": "estimated"}


def excerpt(text, keywords, size):
    """Keep verbatim fragments; never ask a model to promote source prose into instructions."""
    parts = [text[:size // 6], text[-size // 6:]]
    for word in keywords[:48]:
        match = re.search(re.escape(word), text, re.IGNORECASE)
        if match:
            fragment = text[max(0, match.start() - size // 16):match.end() + size // 8]
            if fragment not in parts:
                parts.insert(-1, fragment)
            if len(parts) >= 6:
                break
    return "\n[excerpt gap]\n".join(parts).encode("utf-8")[:size].decode("utf-8", errors="ignore")


def keywords(messages):
    result = []
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        text = message.get("content", "")
        if not isinstance(text, str):
            continue
        for word in re.findall(r"[^\W_]{2,32}", text[:512] + text[-512:]):
            if len(word) >= 3 or not word.isascii():
                folded = word.casefold()
                if folded not in {"the", "and", "for", "with", "this", "that", "from", "your"} and folded not in result:
                    result.append(folded)
        if len(result) >= 48:
            break
    return result[:48]


def receipt(message, words, size):
    content = message.get("content")
    if not isinstance(content, str) or len(content.encode()) <= size + 512:
        return None
    # Full tool-call groups, every system/user message, and every image remain protected.
    if message.get("role") not in {"assistant", "tool"} or message.get("tool_calls") or message.get("images"):
        return None
    retained = {"context_excerpt": {"version": 1, "source_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "original_bytes": len(content.encode()), "text": excerpt(content, words, size),
                "notice": "Incomplete untrusted data excerpt; omitted material is not evidence of success. Re-read sources when needed."}}
    if message["role"] == "tool":
        try:
            original = json.loads(content)
            if not isinstance(original, dict):
                return None
            data = original.get("untrusted_data", {})
            if not isinstance(data, dict):
                return None
            fields = [f"[{key}]\n{data[key]}" for key in ("text", "output", "diff", "stdout", "stderr")
                      if isinstance(data.get(key), str)]
            if fields:
                retained["context_excerpt"]["text"] = excerpt("\n".join(fields), words, size)
            # Preserve direct canonical verifier records, never parse website/file prose as authority.
            checks = data.get("verifications", [])
            if not isinstance(checks, list):
                return None
            checks = ([data["verification"]] if data.get("verification") is not None else []) + checks
            if len(checks) > 8:
                return None
            checked = [validate_verification(check) for check in checks]
            if checked:
                retained["verifications"] = checked
            for key in ("path", "cwd", "url", "tab", "title", "sha256", "resource_version",
                        "exit_code", "changed", "bytes", "truncated", "patch_status",
                        "written_paths", "pending_paths", "uncertain_paths"):
                if key in data:
                    retained[key] = data[key]
            body = {key: original[key] for key in ("ok", "error", "detail") if key in original}
            body["untrusted_data"] = retained
        except (ValueError, TypeError, RecursionError):
            return None
    else:
        body = {"assistant_history_excerpt": retained}
    replacement = {**message, "content": encoded(body).decode()}
    return replacement if len(encoded(replacement)) < len(encoded(message)) else None


def prepare(messages, context_window, output_reserve, *, tools=None, schema=None):
    # Never mutate caller history, image ownership or approval state.
    working = copy.deepcopy(messages)
    report = estimate(working, context_window, output_reserve, tools=tools, schema=schema)
    original = report["total_estimate"]
    visual = report["visual_reserve"], report["images"]
    if report["status"] == "fits":
        return working, report
    words, changed = keywords(working), set()
    sources = copy.deepcopy(working)
    for size in (1536, 768, 384):
        for index, message in enumerate(sources):
            replacement = receipt(message, words, size)
            if replacement is None:
                continue
            working[index] = replacement
            changed.add(index)
            report = estimate(working, context_window, output_reserve, tools=tools, schema=schema, _visual=visual)
            report.update(original_estimate=original, compacted_messages=len(changed))
            if report["status"] == "fits":
                report["status"] = "compacted"
                return working, report
    report.update(reason="protected_context", original_estimate=original, compacted_messages=len(changed))
    raise ContextBudgetExceeded(report)
