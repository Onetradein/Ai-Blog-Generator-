import os
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("LLM_API_URL", "https://api.example-llm.com/v1/generate")
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

OUT_DIR = Path("outputs")
OUT_DIR.mkdir(exist_ok=True)

# load prompts
with open("prompts.txt", "r", encoding="utf-8") as f:
    PROMPTS_RAW = f.read().strip().split("\n---\n\n")

def call_llm(prompt, max_tokens=600, temperature=0.2):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "max_tokens": max_tokens, "temperature": temperature}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    text = data.get("text") or data.get("output") or data.get("choices", [{}])[0].get("text", "")
    return text

def run_pipeline(topic, word_count=900, tone="professional"):
    # 1) refine
    prompt1 = PROMPTS_RAW[0].replace("{user_topic}", topic)
    refined = call_llm(prompt1)

    # 2) title & meta
    prompt2 = PROMPTS_RAW[1].replace("{refined}", refined)
    titles = call_llm(prompt2)
    chosen_title = titles.splitlines()[0] if titles else topic

    # 3) outline
    prompt3 = PROMPTS_RAW[2].replace("{chosen_title}", chosen_title).replace("{word_count}", str(word_count))
    outline = call_llm(prompt3)

    # 4) sections (simple)
    sections = []
    outline_lines = [l.strip() for l in outline.splitlines() if l.strip()]
    headings = outline_lines[:5]
    for h in headings:
        s_prompt = PROMPTS_RAW[3].replace("{section_title}", h[:120]).replace("{tone}", tone).replace("{approx_words}", "150")
        sec_text = call_llm(s_prompt)
        sections.append((h, sec_text))

    # 5) combine and fix
    full_draft = f"# {chosen_title}\n\n"
    for h, t in sections:
        full_draft += f"## {h}\n\n{t}\n\n"

    fixer_prompt = PROMPTS_RAW[4].replace("{full_draft}", full_draft)
    seo_fix = call_llm(fixer_prompt)

    out_file = OUT_DIR / (chosen_title.replace(' ', '_')[:50] + ".md")
    with open(out_file, "w", encoding="utf-8") as fh:
        fh.write(full_draft)
        fh.write("\n\n<!-- SEO Fixes & Captions -->\n")
        fh.write(seo_fix)
    print(f"Saved output to: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--words", type=int, default=900)
    args = parser.parse_args()
    run_pipeline(args.topic, word_count=args.words)
