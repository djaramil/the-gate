# FAU Trussed.ai — Enable & Use Guide

**Audience:** FAU AI Hootcamp students and instructors  
**Sources:** FAU HPC Trussed onboarding email (June 2026), `FAUSampleQuery.ipynb`, Should We Go? Week 3 integration  
**Portal:** https://trussed.hpc.fau.edu  
**API base:** https://fauengtrussed.fau.edu/provider/generic

---

## 1. What is Trussed.ai?

**Trussed.ai** is FAU’s managed LLM access platform. It gives students and instructors **API keys** to call cloud AI models through a **single OpenAI-compatible proxy** — without each student signing up for separate OpenAI/Google accounts.

| Benefit | Detail |
|---------|--------|
| FAU SSO login | No personal API billing setup |
| Per-student budget | Default **$10/month** after key creation |
| Course projects | Models enabled per class/Hootcamp project |
| One endpoint | Works with Python, curl, OpenAI SDK, Continue extension |

Trussed is **not** a chat website you paste into — you use it via **API keys** in your code or IDE.

---

## 2. Hootcamp projects (Summer 2026)

Per FAU HPC setup (June 2026), these projects exist for Hootcamp:

| Project | Provider | Model |
|---------|----------|-------|
| **HootCamp OpenAI** | OpenAI | GPT-5.4 |
| **HootCamp Gemini** | Google | Gemini 2.5 Pro |

Select the project that matches the model you want before requesting a key.

> **Week 3 mini-project note:** The engineering proxy also exposes open-weight models (e.g. `cogito:14b`) used in Should We Go? — see [§7 Models](#7-models--allowlist).

---

## 3. Get your API key

1. Go to **https://trussed.hpc.fau.edu**
2. Log in with **FAU SSO**
3. From **Projects**, select your course project (e.g. *HootCamp OpenAI*)
4. Click **Request API Key**
5. **Copy the key immediately** — it is shown **only once**
6. View keys and expiration under **My Keys**

### Key policies

| Policy | Value |
|--------|-------|
| Key expiration | **4 months** (default) |
| Monthly budget | **$10/student** (default) |
| Lost key | Generate a new one — old key cannot be recovered |

**Store the key in `.env.local`** (or IDE config). Never commit it to GitHub.

```env
TRUSSED_API_KEY=your_key_here
```

---

## 4. API endpoint

All chat completions use the **OpenAI-compatible** path:

```
POST https://fauengtrussed.fau.edu/provider/generic/chat/completions
Authorization: Bearer <TRUSSED_API_KEY>
Content-Type: application/json
```

OpenAI SDK `baseURL` (no `/chat/completions` suffix):

```
https://fauengtrussed.fau.edu/provider/generic
```

---

## 5. Quick test — Python

From `FAUSampleQuery.ipynb`:

```python
import requests

api_key = "YOUR_TRUSSED_API_KEY"  # from .env in real projects
api_url = "https://fauengtrussed.fau.edu/provider/generic/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}

data = {
    "model": "gpt-5.4",  # or model enabled for your project
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in one sentence."},
    ],
    "max_tokens": 100,
    "temperature": 0.5,
}

response = requests.post(api_url, json=data, headers=headers)

if response.status_code == 200:
    print(response.json()["choices"][0]["message"]["content"])
else:
    print(f"Error {response.status_code}: {response.text}")
```

---

## 6. Quick test — curl

```bash
curl https://fauengtrussed.fau.edu/provider/generic/chat/completions \
  -H "Authorization: Bearer $TRUSSED_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5.4",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

---

## 7. Use in a Next.js app (Hootcamp pattern)

Install the OpenAI SDK and point it at Trussed:

```bash
npm install openai
```

`.env.local`:

```env
LLM_PROVIDER=trussed
TRUSSED_API_KEY=your_key_here
TRUSSED_BASE_URL=https://fauengtrussed.fau.edu/provider/generic
LLM_MODEL=cogito:14b
```

```ts
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.TRUSSED_API_KEY,
  baseURL: process.env.TRUSSED_BASE_URL,
});

const response = await client.chat.completions.create({
  model: process.env.LLM_MODEL ?? "cogito:14b",
  messages: [{ role: "user", content: "Hello" }],
  max_tokens: 100,
});
```

**Rules for Gate projects:**

- Call Trussed **only from server** (`src/app/api/`, `src/lib/llm/`)
- Never expose `TRUSSED_API_KEY` to the browser
- Use **structured JSON** for AI features (not a generic chat UI)

Full Week 3 walkthrough: `Projects/Week3/ShouldWeGo/docs/LLM_INTEGRATION.md`

---

## 8. IDE setup — VS Code / Cursor (Continue extension)

FAU HPC tested the **Continue** extension with Trussed. Example config for GPT-5.4:

```yaml
models:
  - name: Trussed GPT 5.4
    provider: openai
    model: gpt-5.4
    apiBase: https://fauengtrussed.fau.edu/provider/generic
    apiKey: "YOUR_TRUSSED_API_KEY"
    useResponsesApi: false
    roles:
      - chat
    defaultCompletionOptions:
      maxTokens: 100
      temperature: 0.5
      stream: false
```

Works similarly for **Gemini 2.5 Pro** — change `model` to the Gemini id enabled in your HootCamp Gemini project.

---

## 9. Models & allowlist

### Hootcamp cloud models (course projects)

| Model | Project | Use case |
|-------|---------|----------|
| `gpt-5.4` | HootCamp OpenAI | General / coding |
| `gemini-2.5-pro` (or project-specific id) | HootCamp Gemini | General / coding |

### Engineering proxy models (Week 3 app testing)

When using the generic engineering endpoint, only **allowlisted** model names work. If you request a model not on the list, Trussed returns **404** with available models.

| Model | Notes |
|-------|-------|
| `cogito:14b` | **Recommended** for structured JSON in Should We Go? |
| `ministral-3:14b` | Alternative 14B |
| `gemma4:26b` | Larger, slower |
| `gpt-4o` | **Not on allowlist** — use `cogito:14b` instead |

### Pricing (how Trussed bills)

Pricing is **per million tokens**, not per API call:

- **Input** — tokens you send (prompt + context)
- **Output** — tokens the model generates

Example from a prior FAU class (170 students, ~1 month): combined OpenAI + Gemini usage was **~$1** total for light app-level use. Heavy dev-tool usage costs more.

---

## 10. Structured JSON (recommend / compare features)

For Gate mini-projects, request JSON output:

```ts
const response = await client.chat.completions.create({
  model: "cogito:14b",
  messages: [
    { role: "system", content: "Return ONLY valid JSON matching the schema." },
    { role: "user", content: "..." },
  ],
  response_format: { type: "json_object" },
  max_tokens: 1200,
  temperature: 0.3,
});
```

Always **validate** LLM output (e.g. with zod) and provide a **fallback** when the model fails.

---

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **401 / 403** | Bad or missing API key | Regenerate key at trussed.hpc.fau.edu; check `.env.local` |
| **404 model** | Model not on project allowlist | Use `cogito:14b` or a model listed in the error response |
| **429** | Rate limit or **$0 billing balance** | Wait and retry; contact instructor if class-wide |
| **Empty response** | Wrong model family | Avoid “thinking” models on local LM Studio; on Trussed use instruct models |
| Key not working after copy | Extra spaces / not saved | Re-copy; restart `npm run dev` after env changes |

### Check usage

- Students: **My Keys** tab on https://trussed.hpc.fau.edu
- Instructors: request usage reports from FAU HPC / TSG (`help@eng.fau.edu`)

---

## 12. Security checklist

- [ ] API key in `.env.local` only (gitignored)
- [ ] No `NEXT_PUBLIC_TRUSSED_API_KEY`
- [ ] Server-side API routes only
- [ ] Trim large payloads before sending (reviews, logs) to control tokens/cost
- [ ] Handle 429 with backoff in production code

---

## 13. Local alternative (LM Studio)

For **free offline dev**, use LM Studio instead of Trussed:

```env
LLM_PROVIDER=openai-compatible
OPENAI_API_KEY=lm-studio
OPENAI_BASE_URL=http://localhost:1234/v1
LLM_MODEL=qwen/qwen2.5-27b-instruct
```

Switch back to Trussed for deploy/demo:

```env
LLM_PROVIDER=trussed
LLM_MODEL=cogito:14b
```

---

## 14. Support contacts

| Resource | Contact |
|----------|---------|
| Trussed portal | https://trussed.hpc.fau.edu |
| FAU Engineering TSG | help@eng.fau.edu |
| TSG website | https://www.fau.edu/engineering/tsg/ |
| Sample notebook | `Trussed-AI/FAUSampleQuery.ipynb` |

---

## 15. Reference — request body fields

| Field | Description |
|-------|-------------|
| `model` | Must match an enabled/allowlisted model id |
| `messages` | Array of `{ role, content }` — `system`, `user`, `assistant` |
| `max_tokens` | Cap on completion length |
| `temperature` | 0–1; lower = more deterministic (use ~0.3 for JSON) |
| `response_format` | `{ "type": "json_object" }` for structured output |

---

*Compiled from FAU HPC Trussed onboarding correspondence (Kathyayani Sasala, TSG) and Hootcamp Week 3 integration work — June 2026.*
