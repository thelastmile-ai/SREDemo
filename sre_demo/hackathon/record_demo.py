"""
Automated SREDemo recording script.
Records a full feature walkthrough and saves an MP4.

Usage:
    python3.14 record_demo.py

Requires:
    pip install playwright
    playwright install chromium
    ffmpeg (brew install ffmpeg)

The SREDemo must be running on http://localhost:3000 before executing.
"""
import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3000"
OUT_DIR   = Path(__file__).parent
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
WEBM_PATH = OUT_DIR / f"{TIMESTAMP}-SREDemo-Recording.webm"
MP4_PATH  = OUT_DIR / f"{TIMESTAMP}-SREDemo-Recording.mp4"

VIEWPORT = {"width": 1440, "height": 900}

# ── Timing constants (seconds) ─────────────────────────────────────────────────
T_PAUSE_SHORT  = 1.5   # brief beat between actions
T_PAUSE_MED    = 2.5   # let the user read something
T_PAUSE_LONG   = 4.0   # linger on a key moment
T_PAUSE_XLONG  = 6.0   # major feature reveal

# Polling timeout for UI elements
TIMEOUT_MS = 45_000


async def record() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            slow_mo=80,
            args=["--window-size=1440,900", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(OUT_DIR),
            record_video_size=VIEWPORT,
        )
        page = await ctx.new_page()

        # ── 1. Login ──────────────────────────────────────────────────────────
        print("→ Navigating to SREDemo …")
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(T_PAUSE_MED)

        print("→ Logging in …")
        await page.fill('input[placeholder="sre-operator"]', "demo")
        await asyncio.sleep(0.5)
        await page.fill('input[type="password"]', "demo")
        await asyncio.sleep(0.5)
        await page.click('button[type="submit"]')

        # ── 2. Idle state — show plan history panel ───────────────────────────
        print("→ Waiting for idle dashboard …")
        await page.wait_for_selector("text=Plan History", timeout=TIMEOUT_MS)
        await asyncio.sleep(T_PAUSE_XLONG)   # linger: show plan history panel

        # ── 3. Click K8s Crashloop chip → fills textarea ──────────────────────
        print("→ Clicking K8s Crashloop chip …")
        await page.click("text=☸ K8s Crashloop")
        await asyncio.sleep(T_PAUSE_MED)     # show filled incident text

        # ── 4. Submit incident (Ctrl+Enter on the incident textarea) ──────────
        print("→ Submitting incident …")
        await page.click('textarea[placeholder*="Describe an incident"]')
        await asyncio.sleep(0.3)
        await page.keyboard.press('Control+Enter')
        await asyncio.sleep(T_PAUSE_SHORT)

        # ── 5. Clarification modal ────────────────────────────────────────────
        print("→ Waiting for clarification …")
        await page.wait_for_selector("text=Agent needs clarification", timeout=TIMEOUT_MS)
        await asyncio.sleep(T_PAUSE_MED)     # show the question

        await page.fill('textarea[placeholder="Type your answer…"]',
                        "They are continuously crashlooping — all 3 replicas are in CrashLoopBackOff state right now")
        await asyncio.sleep(T_PAUSE_MED)     # show typed answer
        await page.keyboard.press('Control+Enter')

        # ── 5. Agent running — show activity feed + few-shot badge ────────────
        print("→ Agent running — waiting for few-shot badge …")
        await page.wait_for_selector("text=Few-shot used by agent", timeout=TIMEOUT_MS)
        await asyncio.sleep(T_PAUSE_XLONG)   # ** KEY MOMENT ** linger on the badge

        # ── 6. HITL approval modal ────────────────────────────────────────────
        print("→ Waiting for HITL plan …")
        await page.wait_for_selector("text=Approve & Execute", timeout=TIMEOUT_MS)
        await asyncio.sleep(T_PAUSE_XLONG)   # show the plan steps

        print("→ Approving plan …")
        await page.click("text=Approve & Execute")

        # ── 7. Execution — budget gauge going amber → red → compaction ────────
        print("→ Watching execution + budget gauge …")
        # Wait for first step result
        await page.wait_for_selector("text=COMPLETED", timeout=TIMEOUT_MS)
        await asyncio.sleep(T_PAUSE_MED)

        # Wait for warning banner (amber/red)
        try:
            await page.wait_for_selector("text=Context budget", timeout=20_000)
            await asyncio.sleep(T_PAUSE_MED)
        except Exception:
            pass  # banner timing varies — keep going

        # Wait for compaction banner
        try:
            await page.wait_for_selector("text=compacted", timeout=20_000)
            await asyncio.sleep(T_PAUSE_MED)
        except Exception:
            try:
                await page.wait_for_selector("text=Compacted", timeout=5_000)
                await asyncio.sleep(T_PAUSE_MED)
            except Exception:
                pass

        # ── 8. Report ─────────────────────────────────────────────────────────
        print("→ Waiting for incident report …")
        await page.wait_for_selector("text=ROOT CAUSE", timeout=TIMEOUT_MS)
        await asyncio.sleep(T_PAUSE_XLONG)   # show root cause analysis

        # Scroll the report into view if needed
        report_el = page.locator("text=FOLLOW-UP").first
        if await report_el.count() > 0:
            await report_el.scroll_into_view_if_needed()
            await asyncio.sleep(T_PAUSE_MED)

        # ── 9. Final beat — plan history now has new entry ────────────────────
        await asyncio.sleep(T_PAUSE_LONG)
        print("→ Recording complete.")

        # Save video
        await ctx.close()
        await browser.close()

    # ── Convert WebM → MP4 ────────────────────────────────────────────────────
    # Playwright saves to a timestamped file in OUT_DIR; find the newest .webm
    webm_files = sorted(OUT_DIR.glob("*.webm"), key=lambda f: f.stat().st_mtime)
    if not webm_files:
        print("❌  No .webm file found — recording may have failed")
        return

    src = webm_files[-1]
    print(f"→ Converting {src.name} → {MP4_PATH.name} …")
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(src),
            "-vf", "scale=1440:900",
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(MP4_PATH),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌  ffmpeg failed:\n{result.stderr}")
        return

    src.unlink()   # remove the .webm after conversion
    size_mb = MP4_PATH.stat().st_size / 1_048_576
    print(f"✅  Saved: {MP4_PATH}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(record())
