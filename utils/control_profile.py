from grok import setting_grok_profile


def open_profile(provider: str):

    if not provider:
        return

    p = provider.strip().lower()

    if p in ["grok", "grok (x-ai)", "x-ai", "xai"]:
        setting_grok_profile()
        return

    print(f"Provider not supported: {provider}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python control_profile.py <provider>")
    else:
        open_profile(sys.argv[1])