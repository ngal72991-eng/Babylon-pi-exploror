import hashlib
from pathlib import Path
from flask import Flask, render_template_string, request
import mpmath as mp

app = Flask(__name__)

CACHE_FILE = Path(__file__).with_name("pi_digits_cache.txt")
INITIAL_DIGITS = 50_000
MAX_DIGITS = 250_000

BABEL_ALPHABET = "abcdefghijklmnopqrstuvwxyz .,!"
BABEL_BASE = len(BABEL_ALPHABET)
BABEL_CHAR_TO_VAL = {ch: idx for idx, ch in enumerate(BABEL_ALPHABET)}
PAGES_PER_VOLUME = 100
VOLUMES_PER_SHELF = 100


def load_or_expand_pi(min_digits: int) -> str:
    """Return at least `min_digits` decimal digits of pi, caching on disk."""
    target_digits = min(max(min_digits, INITIAL_DIGITS), MAX_DIGITS)

    existing = ""
    if CACHE_FILE.exists():
        existing = CACHE_FILE.read_text(encoding="utf-8").strip()

    if len(existing) < target_digits:
        mp.mp.dps = target_digits + 20
        pi_str = str(mp.mp.pi).replace(".", "")
        decimals = pi_str[1 : target_digits + 1]
        CACHE_FILE.write_text(decimals, encoding="utf-8")
        return decimals

    return existing[:target_digits]


def encode_text(text: str) -> str:
    """Encode any text into 4-digit Unicode code points."""
    return "".join(f"{ord(ch):04d}" for ch in text)


def find_longest_prefix_match(pi_decimals: str, target_digits: str) -> dict | None:
    """Find the longest prefix of `target_digits` present in `pi_decimals`."""
    if not target_digits:
        return None
    for length in range(min(len(target_digits), 12), 0, -1):
        prefix = target_digits[:length]
        idx = pi_decimals.find(prefix)
        if idx != -1:
            return {
                "prefix": prefix,
                "length": length,
                "total_length": len(target_digits),
                "index": idx,
            }
    return None


def babel_address_to_text(shelf: int, volume: int, page: int) -> str:
    """Decode (shelf, volume, page) back into text."""
    value = (shelf * VOLUMES_PER_SHELF + volume) * PAGES_PER_VOLUME + page
    radix = BABEL_BASE + 1
    digits = []
    while value > 0:
        digits.append(value % radix)
        value //= radix
    digits.reverse()
    if not digits:
        return ""
    length = digits[0]
    payload = digits[1:]
    if len(payload) != length or any(d >= BABEL_BASE for d in payload):
        return "<invalid payload>"
    return "".join(BABEL_ALPHABET[d] for d in payload)


def text_to_babel_address(text: str) -> dict | None:
    """Invertibly encode supported text into (shelf, volume, page)."""
    normalized = text.lower()
    if not normalized or any(ch not in BABEL_CHAR_TO_VAL for ch in normalized):
        return None

    radix = BABEL_BASE + 1
    digits = [len(normalized)] + [BABEL_CHAR_TO_VAL[ch] for ch in normalized]
    value = 0
    for d in digits:
        value = value * radix + d

    page = value % PAGES_PER_VOLUME
    rem = value // PAGES_PER_VOLUME
    volume = rem % VOLUMES_PER_SHELF
    shelf = rem // VOLUMES_PER_SHELF

    return {
        "shelf": shelf,
        "volume": volume,
        "page": page,
        "decoded_check": babel_address_to_text(shelf, volume, page),
    }


def search_in_pi(digits_str: str, search_depth: int) -> dict:
    pi_decimals = load_or_expand_pi(search_depth)
    pos = pi_decimals.find(digits_str)
    n = len(digits_str)
    expected_odds = f"1 in {10 ** n:,}" if n <= 12 else f"1 in 10^{n}"
    partial = None if pos != -1 else find_longest_prefix_match(pi_decimals, digits_str)
    cached_total = (
        len(CACHE_FILE.read_text(encoding="utf-8").strip())
        if CACHE_FILE.exists()
        else len(pi_decimals)
    )

    return {
        "found": pos != -1,
        "index_after_decimal": pos,
        "searched_digits": len(pi_decimals),
        "cached_total": cached_total,
        "expected_odds_per_pos": expected_odds,
        "partial": partial,
    }


def make_catalog_card(raw_query: str, encoded_digits: str, search_result: dict) -> dict:
    digest = hashlib.sha256(encoded_digits.encode("utf-8")).hexdigest()
    shelf = int(digest[:4], 16) % 999 + 1
    volume = int(digest[4:8], 16) % 999 + 1
    return {
        "shelf": f"S-{shelf:03d}",
        "volume": f"V-{volume:04d}",
        "coord_hash": f"π#{digest[:16]}",
        "char_count": len(raw_query),
        "digit_count": len(encoded_digits),
        "preview_digits": encoded_digits[:64] + ("..." if len(encoded_digits) > 64 else ""),
        "found": search_result["found"],
        "position": search_result["index_after_decimal"],
        "odds": search_result["expected_odds_per_pos"],
        "partial": search_result["partial"],
        "babel": text_to_babel_address(raw_query),
    }


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Babylon Pi Explorer</title>
  <style>
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      margin: 0;
      padding: 2rem;
    }
    .container {
      max-width: 780px;
      margin: 0 auto;
    }
    h1 { margin-bottom: 0.25rem; color: #f8fafc; }
    .sub { color: #94a3b8; margin-top: 0; margin-bottom: 1.5rem; }
    form {
      background: #1e293b;
      padding: 1.25rem;
      border-radius: 12px;
      display: grid;
      gap: 1rem;
      border: 1px solid #334155;
    }
    label { font-size: 0.9rem; color: #cbd5e1; display: grid; gap: 0.35rem; }
    input, select, button {
      padding: 0.65rem 0.8rem;
      border-radius: 8px;
      border: 1px solid #475569;
      background: #0f172a;
      color: #f8fafc;
      font-size: 1rem;
    }
    button {
      background: #2563eb;
      border: none;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover { background: #1d4ed8; }
    .card {
      margin-top: 1.5rem;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 1.25rem;
    }
    .badge-hit { color: #4ade80; font-weight: 700; }
    .badge-miss { color: #fbbf24; font-weight: 700; }
    code {
      background: #0f172a;
      padding: 0.2rem 0.4rem;
      border-radius: 6px;
      word-break: break-all;
      color: #93c5fd;
    }
    .meta { color: #94a3b8; font-size: 0.9rem; margin-top: 0.75rem; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Babylon Pi Explorer</h1>
    <p class="sub">Encode text or digits, search cached decimal places of π, inspect partial matches, and compute invertible Library coordinates.</p>

    <form method="post">
      <label>
        Text or digits to search (e.g., <code>hi</code>, <code>27032009</code>, or <code>hello!</code>)
        <input type="text" name="query" value="{{ query }}" required>
      </label>

      <label>
        Input mode
        <select name="mode">
          <option value="text" {% if mode == "text" %}selected{% endif %}>Text (4-digit Unicode encoding)</option>
          <option value="raw_digits" {% if mode == "raw_digits" %}selected{% endif %}>Raw Digits (search digits directly)</option>
        </select>
      </label>

      <label>
        Search depth in decimal digits of π
        <select name="depth">
          <option value="50000" {% if depth == 50000 %}selected{% endif %}>50,000 digits</option>
          <option value="100000" {% if depth == 100000 %}selected{% endif %}>100,000 digits</option>
          <option value="250000" {% if depth == 250000 %}selected{% endif %}>250,000 digits</option>
        </select>
      </label>

      <button type="submit">Search π & Generate Library Card</button>
    </form>

    {% if result %}
    <div class="card">
      <div>
        {% if result.found %}
          <span class="badge-hit">FOUND in first {{ "{:,}".format(searched_digits) }} decimal digits of π!</span>
          <p>Starting index after decimal point: <code>{{ result.position }}</code></p>
        {% else %}
          <span class="badge-miss">Not found in first {{ "{:,}".format(searched_digits) }} decimal digits of π.</span>
          <p>Odds per position: <code>{{ result.odds }}</code> for a {{ result.digit_count }}-digit string.</p>
          {% if result.partial %}
            <p>Closest prefix match: <code>{{ result.partial.prefix }}</code> ({{ result.partial.length }}/{{ result.partial.total_length }} digits) at index <code>{{ result.partial.index }}</code>.</p>
          {% endif %}
        {% endif %}
      </div>

      <p><strong>Catalog Hash Stub:</strong> Shelf <code>{{ result.shelf }}</code> · Volume <code>{{ result.volume }}</code> · Stub <code>{{ result.coord_hash }}</code></p>
      {% if result.babel %}
        <p><strong>Invertible Babel Address:</strong> Shelf <code>{{ result.babel.shelf }}</code> · Volume <code>{{ result.babel.volume }}</code> · Page <code>{{ result.babel.page }}</code> (decodes back to <code>{{ result.babel.decoded_check }}</code>)</p>
      {% endif %}
      <p><strong>Encoded Digits ({{ result.digit_count }} digits):</strong> <code>{{ result.preview_digits }}</code></p>
      <p class="meta">Local cache file size: {{ "{:,}".format(cached_total) }} decimal digits stored on disk.</p>
    </div>
    {% endif %}
  </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    query = ""
    mode = "text"
    depth = INITIAL_DIGITS
    result = None
    searched_digits = INITIAL_DIGITS
    cached_total = (
        len(CACHE_FILE.read_text(encoding="utf-8").strip()) if CACHE_FILE.exists() else 0
    )

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        mode = request.form.get("mode", "text")
        depth = int(request.form.get("depth", INITIAL_DIGITS))

        if query:
            if mode == "raw_digits":
                cleaned = "".join(ch for ch in query if ch.isdigit())
                encoded = cleaned if cleaned else encode_text(query)
            else:
                encoded = encode_text(query)

            search_res = search_in_pi(encoded, depth)
            result = make_catalog_card(query, encoded, search_res)
            searched_digits = search_res["searched_digits"]
            cached_total = search_res["cached_total"]

    return render_template_string(
        HTML_TEMPLATE,
        query=query,
        mode=mode,
        depth=depth,
        result=result,
        searched_digits=searched_digits,
        cached_total=cached_total,
    )


if __name__ == "__main__":
    load_or_expand_pi(INITIAL_DIGITS)
    app.run(debug=True)
