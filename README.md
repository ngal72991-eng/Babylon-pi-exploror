# Babylon Pi Explorer

An open-source Flask web app that explores **$\pi$ digit searching**, **local digit caching**, **probability odds ($10^{-N}$)**, **closest partial matches**, and **invertible Library of Babel coordinates**.

## Features
- **Search $\pi$ with Disk Caching:** Computes decimal digits of $\pi$ with `mpmath` and caches them locally in `pi_digits_cache.txt` (ignored by Git).
- **Text & Raw Digit Modes:** Encode text into 4-digit Unicode code points or search raw numbers directly (such as dates or sequences).
- **Closest Partial Match:** When a sequence isn't found in the current $\pi$ slice, shows the longest matching prefix found and where it appears.
- **Invertible Library Address:** Converts short text (`a-z`, space, `.`, `,`, `!`) into a reversible `(Shelf, Volume, Page)` coordinate and decodes it back.

## Run Locally
```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## License
GNU General Public License v3.0 — see `LICENSE`.
