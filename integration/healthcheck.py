import json
import sys
import urllib.error
import urllib.request


def check_lab(port, expected):
    url = f"http://127.0.0.1:{port}/api/account?id=1"
    request = urllib.request.Request(
        url,
        headers={"X-Demo-User": "bob"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    return status == expected


def check_ollama():
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/tags",
            timeout=3
        ) as response:
            if response.status != 200:
                return False

            data = json.load(response)
            return any(
                item.get("name") == "qwen2.5-coder:3b"
                for item in data.get("models", [])
            )
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ):
        return False


def check_all():
    return {
        "vulnerable_lab": check_lab(3002, 200),
        "safe_lab": check_lab(3003, 403),
        "ollama": check_ollama(),
    }


def main():
    results = check_all()
    for name, success in results.items():
        print(f"{name}: {'OK' if success else 'FAILED'}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
