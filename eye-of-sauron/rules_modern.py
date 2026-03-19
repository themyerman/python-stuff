"""Modern multi-language rules for eye-of-sauron."""

COMMON_SECRET_RULES = [
    {
        "id": "HARDCODED_PASSWORD",
        "pattern": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]",
        "description": "Potential hardcoded password.",
        "remediation": "Move credentials to secret manager or environment variables.",
        "tags": ["secrets", "auth"],
        "cwe": "CWE-798",
        "confidence": "medium",
    },
    {
        "id": "PRIVATE_KEY_MATERIAL",
        "pattern": r"-----BEGIN (RSA|EC|OPENSSH|DSA)? ?PRIVATE KEY-----",
        "description": "Private key material in source file.",
        "remediation": "Remove key from source control and rotate compromised key.",
        "tags": ["secrets", "crypto"],
        "cwe": "CWE-321",
        "confidence": "high",
    },
    {
        "id": "GENERIC_API_KEY",
        "pattern": r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        "description": "Potential hardcoded API token/key.",
        "remediation": "Use runtime secret injection.",
        "tags": ["secrets"],
        "cwe": "CWE-798",
        "confidence": "medium",
    },
]

MODERN_RULES = {
    "extensions": [".py", ".ts", ".tsx", ".java", ".go", ".rb", ".sh", ".yml", ".yaml", ".tf"],
    "rule_set": {
        ".py": {
            "specific": {},
            "general": {
                "high": COMMON_SECRET_RULES
                + [
                    {
                        "id": "PY_EVAL_EXEC",
                        "pattern": r"\b(eval|exec)\(",
                        "description": "Dynamic execution in Python.",
                        "remediation": "Avoid eval/exec on untrusted input.",
                        "tags": ["injection", "rce"],
                        "cwe": "CWE-95",
                        "confidence": "high",
                    },
                    {
                        "id": "PY_SUBPROCESS_SHELL_TRUE",
                        "pattern": r"subprocess\.(run|Popen|call|check_call|check_output)\(.*shell\s*=\s*True",
                        "description": "subprocess with shell=True can enable command injection.",
                        "remediation": "Pass argument arrays and keep shell=False.",
                        "tags": ["injection", "command"],
                        "cwe": "CWE-78",
                        "confidence": "high",
                    },
                    {
                        "id": "PY_INSECURE_TLS_VERIFY_FALSE",
                        "pattern": r"verify\s*=\s*False",
                        "description": "TLS certificate verification disabled.",
                        "remediation": "Enable certificate validation.",
                        "tags": ["tls", "transport"],
                        "cwe": "CWE-295",
                        "confidence": "medium",
                    },
                ],
                "medium": [
                    {"id": "PY_PICKLE_LOADS", "pattern": r"pickle\.loads?\(", "description": "Unsafe deserialization via pickle."},
                    {"id": "PY_YAML_LOAD", "pattern": r"yaml\.load\(", "description": "Potential unsafe YAML loading."},
                ],
                "low": [],
            },
        },
        ".ts": {
            "specific": {},
            "general": {
                "high": COMMON_SECRET_RULES
                + [
                    {"id": "TS_EVAL", "pattern": r"\beval\(", "description": "Dynamic eval in TS/JS."},
                    {"id": "TS_NEW_FUNCTION", "pattern": r"new\s+Function\(", "description": "Dynamic function construction."},
                    {"id": "TS_CHILD_PROCESS_EXEC", "pattern": r"child_process\.(exec|spawn)\(", "description": "Command execution API used."},
                ],
                "medium": [
                    {"id": "TS_INSECURE_TLS", "pattern": r"rejectUnauthorized\s*:\s*false", "description": "TLS verification disabled."}
                ],
                "low": [],
            },
        },
        ".tsx": {
            "specific": {},
            "general": {
                "high": COMMON_SECRET_RULES + [{"id": "TSX_EVAL", "pattern": r"\beval\(", "description": "Dynamic eval in TSX."}],
                "medium": [],
                "low": [],
            },
        },
        ".java": {
            "specific": {},
            "general": {
                "high": COMMON_SECRET_RULES
                + [
                    {"id": "JAVA_RUNTIME_EXEC", "pattern": r"Runtime\.getRuntime\(\)\.exec\(", "description": "Command execution sink."},
                    {"id": "JAVA_OBJECT_INPUT_STREAM", "pattern": r"ObjectInputStream\s*\(", "description": "Potential unsafe deserialization."},
                ],
                "medium": [{"id": "JAVA_WEAK_HASH", "pattern": r"MessageDigest\.getInstance\(\"(MD5|SHA-1)\"\)", "description": "Weak hashing algorithm."}],
                "low": [],
            },
        },
        ".go": {
            "specific": {},
            "general": {
                "high": COMMON_SECRET_RULES
                + [
                    {"id": "GO_OS_EXEC", "pattern": r"\bexec\.Command\(", "description": "Command execution sink."},
                    {"id": "GO_INSECURE_SKIP_VERIFY", "pattern": r"InsecureSkipVerify\s*:\s*true", "description": "TLS verification disabled."},
                ],
                "medium": [],
                "low": [],
            },
        },
        ".rb": {
            "specific": {},
            "general": {
                "high": COMMON_SECRET_RULES
                + [
                    {"id": "RB_EVAL", "pattern": r"\beval\(", "description": "Dynamic eval in Ruby."},
                    {"id": "RB_OPEN3", "pattern": r"Open3\.(popen|capture)", "description": "Shell/process execution path."},
                ],
                "medium": [],
                "low": [],
            },
        },
        ".sh": {
            "specific": {},
            "general": {
                "high": [
                    {"id": "SH_CURL_PIPE_SHELL", "pattern": r"curl\s+.*\|\s*(sh|bash)", "description": "Piping remote scripts to shell."},
                    {"id": "SH_WGET_PIPE_SHELL", "pattern": r"wget\s+.*\|\s*(sh|bash)", "description": "Piping remote scripts to shell."},
                ],
                "medium": [{"id": "SH_RM_RF_VAR", "pattern": r"rm\s+-rf\s+\$[{(]?[A-Za-z_]", "description": "Potential dangerous recursive delete with variable."}],
                "low": [],
            },
        },
        ".yml": {
            "specific": {},
            "general": {"high": COMMON_SECRET_RULES, "medium": [], "low": []},
        },
        ".yaml": {
            "specific": {},
            "general": {"high": COMMON_SECRET_RULES, "medium": [], "low": []},
        },
        ".tf": {
            "specific": {},
            "general": {
                "high": COMMON_SECRET_RULES
                + [
                    {"id": "TF_PUBLIC_0_0_0_0", "pattern": r"0\.0\.0\.0/0", "description": "Open CIDR found in Terraform config."}
                ],
                "medium": [],
                "low": [],
            },
        },
    },
}
