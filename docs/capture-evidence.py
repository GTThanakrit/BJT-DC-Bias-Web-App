"""Capture B1-B8 browser evidence from the real Flask app with Chrome/Playwright."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path("docs/captures")
OUT.mkdir(parents=True, exist_ok=True)

SIM_DEFAULTS = {
    "vcc": "12", "r1": "100000", "r2": "22000", "rc": "2200", "re": "1000",
    "rl": "10000", "cin_uf": "10", "cout_uf": "10", "source_peak_v": "0.01",
    "source_freq_hz": "1000", "beta": "100", "vbe": "0.7",
}


def fill(page, values):
    for key, value in values.items():
        loc = page.locator(f'[name="{key}"]')
        if loc.count() == 1:
            loc.fill(value)


def run_sim(page, mode, values, wait_for):
    page.goto(f"{BASE}/simulator", wait_until="load")
    page.select_option("#analysis", mode)
    fill(page, values)
    page.get_by_role("button", name="Run ngspice").click()
    page.locator(".sim-results .value").first.wait_for(timeout=30000)
    text = page.locator(".sim-results").inner_text()
    assert wait_for in text, f"{wait_for!r} not in results: {text[:300]}"
    return text


def summary(page, name, mode=None):
    text = page.locator(".sim-results").inner_text()
    status = "SUCCESS" if "SUCCESS" in text else ("ERROR" if "RUN FAILED" in text or "NOT AVAILABLE" in text else "?")
    values = page.locator(".sim-results .value").all_inner_texts()[:8]
    print(f"{name}: status={status} values={values} svg={page.locator('.plot svg').count()}")


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])

    # B1 - Lab 03 regression at desktop width
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto(f"{BASE}/?mode=divider", wait_until="load")
    fill(page, {"vcc": "12", "r1": "100000", "r2": "22000", "rc": "2200",
                "re": "1000", "beta": "100", "vbe": "0.7"})
    page.get_by_role("button", name="Calculate DC Bias").click()
    page.get_by_text("Forward-Active", exact=False).first.wait_for(timeout=30000)
    print("B1:", page.locator("body").inner_text()[-500:].replace("\n", " | "))
    page.screenshot(path=str(OUT / "lab04-b1-lab03-regression.png"), full_page=True)
    ctx.close()

    # B2-B7 at desktop width
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()

    run_sim(page, "dc", SIM_DEFAULTS, "DC operating point")
    summary(page, "B2")
    page.screenshot(path=str(OUT / "lab04-b2-dc-spice.png"), full_page=True)

    run_sim(page, "dc", {**SIM_DEFAULTS, "re": "2000"}, "DC operating point")
    summary(page, "B3")
    page.screenshot(path=str(OUT / "lab04-b3-re-2000.png"), full_page=True)

    run_sim(page, "ac", {**SIM_DEFAULTS, "re": "2000"}, "AC sweep")
    summary(page, "B4")
    page.screenshot(path=str(OUT / "lab04-b4-ac-bode.png"), full_page=True)

    run_sim(page, "tran", SIM_DEFAULTS, "Vin peak")
    summary(page, "B5")
    page.screenshot(path=str(OUT / "lab04-b5-tran-10mv-1khz.png"), full_page=True)

    run_sim(page, "tran", {**SIM_DEFAULTS, "source_peak_v": "0.05", "source_freq_hz": "2000"}, "Vin peak")
    summary(page, "B6")
    page.screenshot(path=str(OUT / "lab04-b6-tran-50mv-2khz.png"), full_page=True)
    page.screenshot(path=str(OUT / "lab04-b8-desktop-tran.png"), full_page=True)

    page.goto(f"{BASE}/simulator", wait_until="load")
    page.select_option("#analysis", "tran")
    fill(page, {**SIM_DEFAULTS, "re": "0"})
    page.get_by_role("button", name="Run ngspice").click()
    page.locator(".alert-error").first.wait_for(timeout=30000)
    print("B7:", page.locator(".alert").inner_text().replace("\n", " | "),
          "svg=", page.locator(".plot svg").count())
    page.screenshot(path=str(OUT / "lab04-b7-invalid-re.png"), full_page=True)
    ctx.close()

    # B8 - mobile viewport WITH a real TRAN result
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
                              device_scale_factor=1, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    run_sim(page, "tran", SIM_DEFAULTS, "Vin peak")
    summary(page, "B8-mobile")
    print("B8-mobile metrics:", page.evaluate(
        "() => ({innerWidth: window.innerWidth, scrollWidth: document.documentElement.scrollWidth,"
        " overflow: getComputedStyle(document.querySelector('.plot')).overflowX})"))
    page.screenshot(path=str(OUT / "lab04-b8-mobile-tran.png"), full_page=True)
    ctx.close()

    browser.close()
print("CAPTURES_DONE")
