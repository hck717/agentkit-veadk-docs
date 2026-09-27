# AI Movie Generator — Project Plan

呢個 project 係一個多 Agent 嘅 AI 電影生成系統，用晒 **BytePlus / Volcengine 全套產品**。
User 輸入 idea + reference movies，Agent 透過 A2A 串連，自動完成：
research → 劇本 → 角色視覺生成 → 分鏡 → 影片生成（含音訊）→ 配音 → 合併，
最終產出一套完整短片。

---

## 整體流程

```
[User Input: Idea + Reference Movies]
   │
   ▼
Agent1 — Research Agent           上網搵 reference movie 資料、風格分析
   │                              模型：Seed 2.0 Lite + web_search
   │ A2A
   ▼
Agent2 — Script Agent             創作完整故事、對白、角色設定
   │                              模型：Seed 2.0 Lite
   │ A2A
   ▼
Agent3 — Storyboard + Image Gen   拆 script 做 N 個 scene + 生成角色參考圖
   │                              模型：Seed 2.0 Mini + Seedream 5.0 Lite（Image Gen）
   │ A2A (parallel)
   ▼
┌───────────────────────────────────────────────────────────┐
│ Agent4a           Agent4b           Agent4c    Agent4N    │
│ (Scene 1)         (Scene 2)         (Scene 3)  (Scene N)  │
│   │                 │                 │           │       │
│ Seedance 2.0     Seedance 2.0     Seedance   Seedance     │
│ Fast (480p)      Fast (480p)      Fast (480p) Fast (480p) │
│   │                 │                 │           │       │
└──┼─────────────────┼─────────────────┼───────────┼───────┘
   ▼                 ▼                 ▼           ▼
  clip1.mp4+au    clip2.mp4+au    clip3.mp4+au  clipN.mp4+au
   │                 │                 │           │
   └─────────────────┴─────────────────┴───────────┘
   │ A2A
   ▼
Agent5 — Audio/Merge Agent        Seed Speech TTS 配音 + FFmpeg 合併
   │                              + Omnihuman digital human（可選）
   │                              + DreamActor motion control（可選）
   ▼
[Final Movie: final_movie.mp4]
```

---

## Agent Plan Medium 適用性

呢個 plan 係基於 **Agent Plan Medium (¥200/月, 100,000 AFP)** 做設計，所有模型選擇都以 Medium Plan 支援為前提：

| 產品 | Medium Plan 版本 | AFP/次 | Upgrade Path |
|------|-----------------|--------|-------------|
| Seed LLM | Seed 2.0 Lite / Mini (極速模型 1×) | ~1-5 | → Seed 2.0 Pro (3×) |
| Seedream | **5.0 Lite** | ~100/img | → 5.0 Pro (Large↑) |
| Seedance | **2.0 Fast** 480-720p | ~2,000/clip | → 2.0 標準版 (Large↑) |
| Harness | 聯網搜索 150次/月 | 1/request | → 400次 (Large) |
| Omnihuman/DreamActor | ❌ 唔包 | — | → Large Plan |

### 每月產能估算

```
100,000 AFP / 月
  ├── 1 個 movie project: ~25,370 AFP (25%)
  ├── 2 個 movie project: ~50,740 AFP (51%)
  ├── 3 個 movie project: ~76,110 AFP (76%)  ← 建議上限
  └── 剩餘 ~23,890 AFP → 其他 LLM 任務
```

---

## Agent 角色詳情

### Agent1：Research Agent

| 項目 | 細節 |
|------|------|
| **角色** | 根據 user idea + reference movies 上網 research |
| **模型** | **Seed 2.0 Lite** (極速模型 1× AFP) — 輕量 research 夠用 |
| **工具** | `web_search`（VeADK built-in, 150次/月 Medium Plan Harness） |
| **功能** | 分析 reference movie 風格、視覺語言、角色 archetype；搜集相關參考資料、市場數據 |
| **輸出** | `research.md` — story genre、tone、visual style reference、similar works analysis |
| **A2A** | 完成後 call Agent2 endpoint，傳 research.md |
| **Eval** | Research completeness、source citation accuracy |
| **AFP/project** | ~50 AFP |
| **日後升級** | 換 `seed-2-0-pro-260324`（標準模型 3× AFP）提升 research depth |

```python
# research_agent.py — 概念
from veadk import Agent
from veadk.tools.builtin_tools.web_search import web_search

agent = Agent(
    name="film_researcher",
    model_name="seed-2-0-lite-260228",  # 極速模型 1× AFP
    instruction="""Research the reference movies provided by the user.
    Analyze their visual style, narrative structure, and key elements.
    Use web_search to find relevant information.""",
    tools=[web_search],
)
```

### Agent2：Script Agent

| 項目 | 細節 |
|------|------|
| **角色** | 基於 research 創作完整故事、對白、角色設定 |
| **模型** | **Seed 2.0 Lite** (極速模型 1× AFP) — 長文本用 Lite 已夠，Mini context window 可能唔夠 |
| **輸入** | `research.md`（Agent1 output） |
| **輸出** | `plot.md`（故事大綱）、`script.md`（完整劇本，按 scene 劃分）、`characters.json`（角色設定，含 visual description 俾 Seedream 生圖用） |
| **Eval** | 評估創意 coherence、user idea 吻合度 |
| **AFP/project** | ~80 AFP |
| **日後升級** | 換 `seed-2-0-pro-260324`（標準模型 3× AFP）提升 script 質素 |

```python
# script_agent.py — 概念
agent = Agent(
    name="scriptwriter",
    model_name="seed-2-0-lite-260228",  # 極速模型 1× AFP
    instruction="""Based on the research, create:
    1. plot.md — Story outline with 3-act structure
    2. script.md — Full screenplay divided into scenes (max 15s each)
    3. characters.json — Each character with name, personality, visual description
       (visual description will be used by Seedream to generate character reference images)
    
    Each scene should be max 15 seconds when performed.""",
)
```

### Agent3：Storyboard Agent

| 項目 | 細節 |
|------|------|
| **角色** | 將 script 拆成 N 個 15s scene segment + 用 **Seedream 5.0 Lite** 生成角色/場景參考圖 |
| **模型** | **Seed 2.0 Mini** (極速模型 1× AFP) 拆 scene + **Seedream 5.0 Lite** (生圖類，AFP消耗較高) |
| **輸入** | `script.md` + `characters.json` |
| **輸出** | `storyboard.json` — `List[Scene]`，每個 scene 有 `scene_id`, `prompt_for_seedance`（俾 Seedance 用）, `duration` (<=15s), `visual_style`, `transition_type`, `narrative_summary`, `reference_images[]`（Seedream 生成嘅角色/場景圖 key） |
| **關鍵設計** | Seedance 2.0 Fast max 15s；Seedream 5.0 Lite 生成角色參考圖俾 Seedance 做 `@Image` reference；Medium Plan 包含 Seedream 5.0 Lite |
| **Eval** | Scene duration 準確度、prompt 質素、Seedream 圖像 consistency |
| **AFP/project** | ~1,220 AFP（LLM ~20 + Seedream 12張×~100） |

```python
# storyboard_agent.py — 概念
from veadk import Agent
from tools.seedream_tool import seedream_generate_image

agent = Agent(
    name="storyboarder",
    model_name="seed-2-0-mini-260428",     # 極速模型 1× AFP
    tools=[seedream_generate_image],        # Seedream 5.0 Lite (Medium Plan 包含)
    instruction="""Break the script into 15-second scenes.
    For each scene, generate a Seedream reference image of the character/environment.
    Each scene must have a detailed visual prompt suitable for Seedance Fast video generation.
    Include transition instructions between scenes.
    Output as JSON array of Scene objects with reference image URLs.""",
)
```

### Agent4：Video Generation Agent（Seedance 2.0 Fast + Parallel）

| 項目 | 細節 |
|------|------|
| **角色** | 每個 scene 獨立 call **Seedance 2.0 Fast** 生成 15s clip（含原生音訊） |
| **模型** | **Seedance 2.0 Fast** (低延遲版, 720p, AFP 消耗 ~⅓ of 標準版) |
| **工具** | `seedance_generate()` — 自訂 Python tool |
| **輸入** | 一個 `Scene` object（prompt, style, duration, reference_images[]） |
| **輸出** | `.mp4` file + 同步音訊（Seedance 原生支援 `generate_audio=true`） |
| **關鍵** | **Parallel execution** — N 個 scene 同時 gen；Seedance 支援 `@Image` reference 保持角色一致；Medium Plan 包含 Seedance 2.0 系列 |
| **Scaling** | 可以 deploy 多個 instance 同時處理，或用多個 scene 塞同一 prompt 做 multi-shot |
| **Eval** | Seedance Fast output visual quality、prompt adherence、角色 consistency |
| **AFP/project (12 scenes)** | ~24,000 AFP（Fast ~2,000/clip vs 標準 ~6,000/clip） |
| **日後升級** | 換 `dreamina-seedance-2-0-260128`（標準版）提升畫質 |

```python
# tools/seedance.py — 概念
import httpx
import asyncio
from typing import Optional

class SeedanceClient:
    """Seedance 2.0 Fast API 客戶端（via BytePlus ModelArk — Agent Plan Medium）"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.byteplus.com"):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def generate_video(
        self,
        prompt: str,
        duration: int = 15,
        style: str = "cinematic",
        reference_images: Optional[list[str]] = None,
        generate_audio: bool = True,
        resolution: str = "480p",            # Downgrade 480p 省 AFP
    ) -> str:
        """Call Seedance 2.0 Fast to generate video
        
        因應 Agent Plan Medium 限制，用 Seedance 2.0 Fast + 480p：
        - AFP 消耗約 ~2,000/clip（標準版 ~6,000）
        - 支援 @Image1 reference 保持角色一致
        - 原生 audio sync
        
        Args:
            prompt: Scene visual description
            duration: 影片時長（秒），4-15
            style: cinematic / anime / realistic
            reference_images: Seedream 5.0 Lite 生成嘅角色參考圖
            generate_audio: 同步音訊
            resolution: 480p / 720p（Fast 最高 720p）
        """
        payload = {
            "model": "dreamina-seedance-2-0-fast-260128",  # Fast 版
            "prompt": prompt,
            "duration": duration,
            "style": style,
            "generate_audio": generate_audio,
            "resolution": resolution,
        }
        if reference_images:
            payload["reference_images"] = reference_images
        
        task = await self.client.post("/ark/vision/generation", json=payload)
        task_id = task.json()["task_id"]
        
        while True:
            status = await self.client.get(f"/ark/vision/generation/{task_id}")
            data = status.json()
            if data["status"] == "completed":
                return data["video_url"]
            elif data["status"] == "failed":
                raise Exception(f"Seedance gen failed: {data.get('error')}")
            await asyncio.sleep(3)
```

```python
# video_gen_agent.py — 概念
from veadk import Agent
from tools.seedance import seedance_generate

agent = Agent(
    name="video_generator",
    tools=[seedance_generate],
    instruction="""Generate a 15-second video clip using Seedance 2.0.
    Each scene gets its own clip with synchronized audio.
    Use @Image1, @Image2 syntax in prompts to reference character images.
    Set generate_audio=true for native audio sync.""",
)
```

### Agent5：Audio/Merge Agent

| 項目 | 細節 |
|------|------|
| **角色** | 用 **Seed Speech TTS** 加角色配音/旁白 + FFmpeg 合併所有 clip + 加 transition + BGM |
| **工具** | FFmpeg + **Seed Speech TTS 2.0**（BytePlus 語音合成）+ **Omnihuman 1.5**（可選 digital human）+ **DreamActor M2.0**（可選 motion control） |
| **模型** | **Seed 2.0 Mini** (極速模型 1× AFP) 決定 transition 參數 + **Seed Speech TTS 2.0** |
| **輸入** | `storyboard.json` + `List[clip_path]` + `script.md`（對白 text） |
| **輸出** | `final_movie.mp4` |
| **Eval** | Transition 流暢度、TTS 自然度、A/V sync、總時長準確 |

```python
# tools/seed_speech.py — Seed Speech TTS 概念
import httpx

class SeedSpeechClient:
    """Seed Speech TTS 2.0 — BytePlus 語音合成"""
    
    def __init__(self, api_key: str):
        self.client = httpx.Client(
            base_url="https://api.byteplus.com",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    def synthesize(
        self,
        text: str,
        voice: str = "zh_female_1",  # 多種聲線可選
        speed: float = 1.0,
        pitch: float = 1.0,
        format: str = "mp3",
    ) -> str:
        """將文字轉成語音
        
        Args:
            text: 對白內容
            voice: 聲線類型（zh_female_1 / zh_male_1 / en_female_1 ...）
            speed: 語速 (0.5-2.0)
            pitch: 音調 (0.5-2.0)
        
        Returns:
            audio_url: 生成嘅語音檔案 URL
        """
        resp = self.client.post("/speech/tts/v1", json={
            "text": text,
            "voice": voice,
            "speed": speed,
            "pitch": pitch,
            "format": format,
        })
        return resp.json()["audio_url"]
```

```python
# tools/ffmpeg_tool.py — 概念
import subprocess

def merge_video_clips(
    clip_paths: list[str],
    transitions: list[str],
    output_path: str = "final_movie.mp4",
    bgm_path: str | None = None,
    subtitle_path: str | None = None,
) -> str:
    """Merge multiple video clips using FFmpeg
    
    Args:
        clip_paths: 按順序排列嘅 clip 路徑（已含 Seedance 原生音訊）
        transitions: 每個 transition 類型（fade/cut/dissolve）
        output_path: 最終輸出 path
        bgm_path: 背景音樂（可選）
        subtitle_path: 字幕文件（可選）
    
    Returns:
        output_path
    """
    # 1. Build FFmpeg filter complex
    # 2. Run FFmpeg with concat + transitions
    # 3. Optionally overlay TTS audio tracks
    # 4. Return output path
    pass
```

### 可選延伸：Omnihuman Digital Human + DreamActor

| 產品 | 用途 | 技術 |
|------|------|------|
| **Omnihuman 1.5** | 生成 virtual human 做影片角色表演 | `omnihuman.generate_video(script="...", avatar="...")` |
| **DreamActor M2.0** | 精細 motion control — 動作、表情、手勢 | `dreamactor.drive_character(motion_ref="...", target="...")` |

> ⚠️ Agent Plan Medium **唔包** Omnihuman 同 DreamActor。需要 **Large (¥500)** 以上或者獨立 API 計費。
> 如果 upgrade 咗，可以將 Agent4（Seedance Fast）部分 scene 改為 Omnihuman 生成真人表演片段。

```python
# omni_human_tool.py — 概念
def omnihuman_generate(
    script: str,
    avatar_image: str,
    voice: str = "zh_female_1",
) -> str:
    """Omnihuman 1.5 — 生成 virtual human 影片
    
    Args:
        script: 人物嘅對白/動作描述
        avatar_image: 頭像圖片 URL
        voice: TTS 聲線
    
    Returns:
        video_url: 生成嘅人物影片 URL
    """
    pass
```

---

## A2A 通訊設計

### Flow-based Chain

```python
# 每個 Agent 係獨立 A2A service，順序 call
# Agent1 → Agent2 → Agent3 → Agent4 (parallel) → Agent5

# Agent1 完成 research → auto-invoke Agent2
@a2a_research.agent_executor(name="research_agent")
async def research_flow(idea: dict) -> dict:
    research_doc = await research_agent.run_async(messages=idea)
    script = await call_a2a_agent("script-agent", research_doc)
    return script
```

### Parallel Video Generation

Agent3 輸出 storyboard（N 個 scene）後，Agent4 可以 parallel invoke：

```python
# storyboard 完成後，每個 scene 獨立 call Agent4
# 可以用 asyncio.gather() 或 A2A parallel invoke

storyboard = await storyboard_agent.run_async(messages=script)

# Parallel video generation
tasks = [
    call_a2a_agent(f"video-gen-agent-{i % NUM_INSTANCES}", scene)
    for i, scene in enumerate(storyboard["scenes"])
]
clip_results = await asyncio.gather(*tasks)
```

---

## BytePlus API Integration

### Seedream 5.0 Lite — Image Generation（Agent3 用）

Agent3 用 Seedream 5.0 Lite（Agent Plan Medium 包含）生成角色參考圖同 mood board：

```python
# tools/seedream_tool.py — 概念
import httpx

def seedream_generate_image(
    prompt: str,
    style: str = "anime",
    aspect_ratio: str = "16:9",
) -> str:
    """用 Seedream 5.0 Lite 生成角色/場景參考圖
    
    Agent Plan Medium 已包含 Seedream 5.0 Lite。
    如升級到 Large/Max 可用 Seedream 5.0 Pro（細節更好）。
    
    Args:
        prompt: 角色視覺描述
        style: anime / photorealistic / cinematic / 3d
        aspect_ratio: 16:9 / 9:16 / 1:1 / 4:3
    
    Returns:
        image_url: 生成圖片 URL，可以傳俾 Seedance Fast 做 @Image reference
    """
    pass
```

### Seedance 2.0 — Video Generation（Agent4 用）

見 Agent4 上面嘅 `tools/seedance.py`。

### Seed Speech TTS 2.0（Agent5 用）

見 Agent5 上面嘅 `tools/seed_speech.py`。

### Omnihuman + DreamActor（可選，需 Large Plan ↑）

> ⚠️ Medium Plan 唔包。見 Agent5 上面嘅可選延伸 section。

### BytePlus ModelArk 統一 API 入口

所有產品都可以透過 **BytePlus ModelArk** 同一 API 平台調用：

```python
# ModelArk 統一客戶端概念
from byteplus import ModelArkClient

client = ModelArkClient(api_key="<key>", region="ap-southeast-1")

# Seed LLM (Agent Plan Medium — 極速模型 1× AFP)
llm_resp = client.chat(model="seed-2-0-lite-260228", messages=[...])

# Seedream Image (Agent Plan Medium — 5.0 Lite)
img_resp = client.vision.generate_image(model="seedream-5-0-lite-260228", prompt="...")

# Seedance Video (Agent Plan Medium — Fast 版 省 AFP)
vid_resp = client.vision.generate_video(model="dreamina-seedance-2-0-fast-260128", prompt="...")

# Seed Speech TTS
tts_resp = client.speech.synthesize(model="tts-2", text="...", voice="zh_female_1")
```

---

## Deployment 策略

所有 Agent 用 **BytePlus ModelArk** 或 **AgentKit CLI** 獨立 deploy：

```bash
# 每個 Agent 獨立 deploy
ak deploy research-agent --app-name movie-research
ak deploy script-agent --app-name movie-script
ak deploy storyboard-agent --app-name movie-storyboard

# Agent4 可以多 instance 做 horizontal scaling
ak deploy video-gen-agent --app-name movie-videogen-0
ak deploy video-gen-agent --app-name movie-videogen-1

ak deploy audio-merge-agent --app-name movie-merge

# Model 配置（全部 within Agent Plan Medium）
ak config set --app-name movie-research MODEL_AGENT_NAME="seed-2-0-lite-260228"
ak config set --app-name movie-script MODEL_AGENT_NAME="seed-2-0-lite-260228"
ak config set --app-name movie-storyboard MODEL_AGENT_NAME="seed-2-0-mini-260428"
ak config set --app-name movie-storyboard SEEDREAM_MODEL="seedream-5-0-lite-260228"
ak config set --app-name movie-videogen-0 SEEDANCE_MODEL="dreamina-seedance-2-0-fast-260128"
ak config set --app-name movie-merge MODEL_AGENT_NAME="seed-2-0-mini-260428"
ak config set --app-name movie-merge TTS_MODEL="tts-2"

# 日後升級 path：逐個 agent 換 model name
# ak config set --app-name movie-videogen-0 SEEDANCE_MODEL="dreamina-seedance-2-0-260128"
# ak config set --app-name movie-storyboard SEEDREAM_MODEL="seedream-5-0-pro-260708"
```

---

## Evaluation 策略

| Agent | Eval Dataset | 主要指標 |
|-------|-------------|---------|
| **Research** | 10 個 sample movie ideas + expected research topics | Completeness (key topics coverage)、Citation accuracy |
| **Script** | 10 ideas with expected plot structure | Coherence score、User idea alignment |
| **Storyboard** | 5 scripts → expected scene breakdown + Seedream image quality | Duration accuracy、Prompt quality、Image consistency |
| **Video Gen** | 20 prompts → generated clips by Seedance 2.0 | Visual quality、Prompt adherence、角色 consistency、Audio sync |
| **Audio/Merge** | 5 sets of test clips + TTS output | Transition smoothness、TTS naturalness (MOS)、A/V sync |

### BytePlus ModelArk Evaluation 工具

BytePlus ModelArk 內置 **evaluation** 功能，可以用嚟統一做 eval：

```bash
# 用 ModelArk eval 功能
ak eval create --app-name movie-videogen-0 --test-set eval/test_data/test_prompts.json
ak eval run --eval-id <id>
ak eval results --eval-id <id>
```

---

## Production Infrastructure

### 1. Database — 每層用咩 Backend

| Component | Backend | 用途 |
|-----------|---------|------|
| **STM (Session)** | PostgreSQL / SQLite（開發） | 存每個 movie project 嘅 session 狀態、生成進度 |
| **LTM (長期記憶)** | **VikingDB** / **OpenViking** | 跨 project 記 user 風格偏好、之前用過成功嘅 prompt |
| **KnowledgeBase** | **VikingDB** | reference movie 知識庫、角色設定庫、視覺風格參考 |
| **Artifacts** | **TOS** | Seedance 生成影片、Seedream 角色圖、最終 movie 檔案 |
| **Metadata** | PostgreSQL | Project config、eval results、generation logs |
| **Cache** | Redis | Seedance / Seedream result cache（同一 prompt 唔使 gen 兩次） |

```yaml
# configs/videogen.yaml — Agent4 Database 配置
short_term_memory:
  backend: postgresql
  db_url: postgresql://user:pass@pg-internal.vpc:5432/movie_stm
  session_ttl_hours: 168        # movie project 可能做幾日

long_term_memory:
  backend: viking
  app_name: movie_ltm
  index: user_style_preferences
  host: vikingdb-internal.vpc
  port: 8080

knowledge_base:
  backend: viking
  index: movie_references

storage:
  backend: tos
  bucket: movie-assets
  region: ap-southeast-1
  internal_endpoint: true
```

### 2. ShortTermMemory — Session 管理

每個 movie project 係一個 session：

```python
from veadk.memory.short_term_memory import ShortTermMemory

stm = ShortTermMemory(
    backend="postgresql",
    db_url="postgresql://user:pass@pg-internal.vpc:5432/movie_stm",
    session_ttl_hours=168,        # 7 日 — movie project 需時較長
    cleanup_interval_minutes=60,
)

# Session 記錄 project progression
session = await stm.create_session(
    app_name="movie_generator",
    user_id="user-42",
    session_id="project-summer-blockbuster-001",
    metadata={
        "idea": "A heist movie set in space",
        "num_scenes": 12,
        "status": "research_complete",
        "current_agent": "agent2",
    },
)
```

Session expiry：

```yaml
session_policy:
  ttl: 168h                       # 7 日
  extended_if_active: true
  cleanup_cron: "0 3 * * *"      # 每日凌晨 3 點清
  max_sessions_per_user: 20       # 每人最多 20 個 project
```

### 3. LongTermMemory — 跨 Project 學習

記住 user 嘅風格偏好，下次直接套用：

```python
from veadk.memory.long_term_memory import LongTermMemory

ltm = LongTermMemory(
    backend="viking",
    app_name="movie_ltm",
    embedding_model="seed-2-0-lite-260228",
)

# Project 完成後記住 user 偏好
await ltm.save_memory(
    user_id="user-42",
    memory_type="style_preference",
    content={
        "genre": "sci-fi",
        "visual_style": "cinematic",
        "preferred_actors": ["realistic"],
        "music_taste": "orchestral",
        "duration_preference": "2-3 min",
    },
)

# 新 project 開始時 load 偏好
prefs = await ltm.search_memory(
    user_id="user-42",
    query="user style preferences",
    memory_type="style_preference",
    top_k=1,
)
```

LTM policy：

```yaml
ltm_policy:
  retention_days: 730              # 保留兩年（movie 項目可以參考返舊作）
  min_confidence: 0.6
  dedup_threshold: 0.9
  auto_archive: true
```

### 4. Context Management — Session 上限同壓縮

Movie project 嘅 context 比 invoice 複雜（research doc + script + storyboard can be long)：

```python
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models.lite_llm import LiteLlm

summarizer = LlmEventSummarizer(
    llm=LiteLlm(model="seed-2-0-lite-260228"),
    prompt_template="Summarize the movie project progress so far...",
)

app = App(
    name="script_agent",
    root_agent=agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,        # 每 3 輪壓縮一次（尤其 research iterates fast）
        overlap_size=2,
        compactor=summarizer,          # LLM 摘要壓縮
    ),
    max_session_messages=200,
)

context_policy:
  max_input_tokens: 16000          # movie context 較長
  max_output_tokens: 8000
  window_strategy: summary         # summary 保留關鍵資訊
  window_size: 30
  summary_model: seed-2-0-lite
```

### 5. Security

| 層面 | 措施 |
|------|------|
| **A2A Internal** | A2A 端點行 internal VPC + mTLS |
| **API Keys** | 用 **Volcengine IAM** 管理 Seedance/Seedream API key |
| **User Identity** | `AuthRequestProcessor` 驗證 user 身份 |
| **Generated Assets** | TOS pre-signed URL + auto-expiry（24h） |
| **ModelArk API** | API key 限 IP whitelist |
| **審計日誌** | 所有 generation 動作寫 audit log |

```yaml
# security.yaml
security:
  a2a_auth:
    type: mTLS
    cert_path: /etc/certs/a2a-client.pem
    key_path: /etc/certs/a2a-key.pem
    ca_path: /etc/certs/ca.pem
  
  api_key_management:
    provider: iam
    rotation_days: 90
  
  asset_url_expiry:
    default_hours: 24            # generated video URL auto-expire
    max_hours: 168               # max 7 日
  
  auth_processor:
    enabled: true
    provider: ve_identity
```

### 6. Access Control

```yaml
rbac:
  roles:
    - name: creator
      permissions: [create_project, view_own_project, generate_video]
    - name: reviewer
      permissions: [view_all_projects, review_generations]
    - name: admin
      permissions: [all, manage_quota, view_audit_log]
  
  rate_limiting:
    generation: "10/hour per user"       # Seedance 有限制
    tts: "100/hour per user"
    research: "50/hour per user"
  
  quota:
    max_duration_seconds: 300             # 每人每次最多 5 min 影片
    max_projects: 10                       # 每人最多 10 個 active projects
```

### 7. Network Architecture

```
                      ┌──────────────────────┐
                      │   Internet / User     │
                      │   (Idea Upload)       │
                      └──────────┬───────────┘
                                 │
┌────────────────────────────────┼────────────────────────────┐
│                     VPC (Internal)                         │
│                                                             │
│  ┌──────────┐   A2A (mTLS)   ┌──────────┐    ┌──────────┐  │
│  │ Agent1   │◄──────────────►│ Agent2   │... │ Agent5   │  │
│  │(Research)│                │ (Script) │    │(Merge)   │  │
│  └────┬─────┘                └────┬─────┘    └────┬─────┘  │
│       │                          │                │         │
│       ▼                          ▼                ▼         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Internal Services                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ TOS      │  │ VikingDB │  │ PostgreSQL│          │   │
│  │  │ (Assets) │  │(Vector)  │  │ (Meta)   │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Egress Only                             │   │
│  │  ModelArk API ───► api.byteplus.com (whitelisted)   │   │
│  │  Seedance     ───► seedance.api.byteplus.com        │   │
│  │  Seedream     ───► seedream.api.byteplus.com        │   │
│  │  Seed Speech  ───► tts.api.byteplus.com             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

Firewall：

```
inbound:
  - from: vpc_cidr (10.0.0.0/16)
    to: agents (port 8080-8090)
    protocol: tcp
  - from: load_balancer
    to: ingress (port 443)
    protocol: tcp

outbound:
  - to: api.byteplus.com (port 443)
  - to: seedance.api.byteplus.com (port 443)
  - to: seedream.api.byteplus.com (port 443)
  - to: tts.api.byteplus.com (port 443)
  - to: tos-ap-southeast-1.volces.com (port 443)
  - all_other_egress: denied
```

### 8. Evaluation Infrastructure

```yaml
eval_pipeline:
  ci:
    trigger: on_push / nightly
    scope: [research_eval, script_eval, storyboard_eval]
    test_data: eval/test_data/
    threshold:
      research_completeness: 0.8
      script_coherence: 0.75
  
  # 全面 eval — 需要實際 call Seedance/Seedream API
  offline:
    trigger: weekly
    scope: [all]
    test_data:
      - eval/test_data/sample_ideas.json
      - eval/test_data/regression/
    cost_budget: "$50/week"            # API call 成本上限
  
  # 生產監控
  monitoring:
    type: shadow_eval
    sample_rate: 0.05                  # 5% 流量做 eval
    metrics:
      - generation_success_rate        # Seedance API 成功率
      - visual_quality_score
      - user_satisfaction              # post-generation survey
      - generation_latency

# Ground truth
ground_truth:
  storage: TOS bucket (gt-movie-data)
  format: |
    {
      "idea": "a heist movie in space",
      "expected_research_topics": ["heist genre tropes", "sci-fi visual style"],
      "expected_num_scenes": 8,
      "quality_benchmarks": { "visual": 0.8, "audio_sync": 0.9 }
    }
```

### 9. OpenTelemetry — Distributed Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer("movie-generator")

@a2a_research.agent_executor(name="research_agent")
async def research_flow(idea: dict, ctx: dict) -> dict:
    with tracer.start_as_current_span("movie_research") as span:
        span.set_attribute("project_id", ctx.get("project_id"))
        result = await runner.run(messages=idea)
        ctx["trace_id"] = trace.get_current_span().get_span_context().trace_id
        return await call_a2a_agent("script-agent", result, ctx)
```

```yaml
opentelemetry:
  exporter: otlp
  endpoint: http://otel-collector:4318
  service_name: movie-generator
  sampling_rate: 1.0
  baggage:
    - environment: production
    - region: ap-southeast-1
  exporters:
    - type: jaeger
      endpoint: http://jaeger:14250
    - type: cloudwatch
      log_group: /opentelemetry/movie-traces
```

### 10. Full Auditing

```yaml
audit:
  store:
    type: dual_write
    primary: postgresql
    archive: tos
    archive_cron: "0 0 * * 0"
  retention:
    online_days: 90
    archive_years: 3                    # Movie IP maybe 3 years
  immutability:
    chain_hash: true
    signing_key: /etc/keys/audit-signing.pem
  record_structure:
    audit_id, timestamp, agent, action, actor, resource
    input_hash, output_hash, trace_id, decision
    compliance_metadata:
      data_residency: ap-southeast-1
      copyright_checked: true
```

### 11. Error Handling

```yaml
error_handling:
  retry:
    max_attempts: 3
    backoff: exponential
    retryable_errors: [timeout, rate_limit, service_unavailable]
    non_retryable: [invalid_input, auth_failed, copyright_violation]

  circuit_breaker:
    failure_threshold: 5
    reset_timeout_seconds: 30
    half_open_max_requests: 3

  dlq:
    store: tos
    bucket: movie-dlq
    alert_on_enqueue: true
    manual_replay_endpoint: /admin/dlq/replay

  partial_failure:
    strategy: skip_failed_scenes           # Scene gen 失敗 skip 唔好停成個 project
    max_failure_rate: 0.3
```

```python
@circuit_breaker(name="seedance_api", failure_threshold=5)
@retry(max_attempts=3, backoff="exponential")
async def generate_video_with_seedance(scene: dict) -> str:
    return await seedance_client.generate(scene)
```

### 12. Secrets Management

```yaml
secrets:
  provider: vault
  auth_method: kubernetes
  rotation:
    default: 90d
    high_risk: 30d
    auto_rotate: true
  paths:
    seedance_api_key: vault://projects/movie/seedance/api_key
    seedream_api_key: vault://projects/movie/seedream/api_key
    tts_api_key: vault://projects/movie/tts/api_key
    tos_credentials: vault://shared/tos/credentials
    postgresql_url: vault://shared/postgresql/movie_url
```

### 13. PII / Copyright Detection

Movie project — 主要係版權風險，唔係 PII：

```python
from byteplus.content_detector import ContentDetector

detector = ContentDetector(api_key="<key>")

async def check_generation_safety(prompt: str) -> dict:
    result = detector.check(
        text=prompt,
        rules=[
            "COPYRIGHTED_CHARACTER",        # Mickey Mouse, Harry Potter...
            "REAL_CELEBRITY",               # Taylor Swift, Elon Musk...
            "BRAND_LOGO",                   # Nike, Apple logo...
            "TRADEMARKED_PHRASE",           # "Just do it"...
        ],
    )
    return result
```

```yaml
content_safety:
  scan_points:
    - user_input                          # User idea 入嚟就 check
    - before_seedance                     # 每個 scene prompt 送出前
    - before_seedream                     # Image gen prompt
  actions:
    high_risk: [block_project, notify_admin]
    medium_risk: [rewrite_prompt, log]
    low_risk: [log_only]
```

### 14. Prompt Filtering & Shield

```yaml
prompt_shield:
  provider: byteplus_modelark_shield
  pre_filter:
    enabled: true
    categories: [prompt_injection, jailbreak, toxicity, sensitive_topics]
    action: block
  post_filter:
    enabled: true
    categories: [hallucinated_pii, harmful_content]
    action: mask_or_block
  movie_rules:
    - pattern: REAL_CELEBRITY_NAME
      action: rewrite_character          # 改做原創角色
    - pattern: COPYRIGHTED_CHARACTER
      action: block
    - pattern: BRAND_LOGO
      action: block
```

### 15. Cost Management

```yaml
agent_plan: medium                         # ¥200/月，100,000 AFP
# Agent Plan Medium 關鍵限制：
# - Seedance 2.0 Fast + 480p：~2,000 AFP/clip（標準版 ~6,000）
# - Seedream 5.0 Lite：~100 AFP/image（Pro 版 ~200）
# - 極速模型 (Mini/Lite)：1× AFP
# - 聯網搜索：150次/月
# - 唔包 Seedance 標準版同 Seedream Pro（Large 先有）

cost_management:
  tracking:
    provider: byteplus_billing_api (Agent Plan AFP)
    dimensions: [agent_name, model_name, project_id, user_id]
  budget:
    monthly_limit: "¥200 (Medium Plan)"
    per_project_alert: "¥50"                # ~25,000 AFP
    alert_channels: [feishu, email]
  monthly_afp_forecast:
    total_available: 100,000 AFP
    per_project: ~25,370 AFP                 # 1 project ≈ 25%
    max_projects_per_month: ~3               # 76% 用盡
  optimization:
    cache_strategy:
      identical_prompt_cache: true
      cache_store: redis
      cache_ttl_hours: 24
    seedance_resolution_tier:
      draft: 480p                             # Agent Plan Medium 最佳化
      final: 720p                              # Fast 最高 720p
    parallel_cost_cap: "24,000 AFP/run"       # 12 scenes Fast 版
```

### 16. Logging

```yaml
logging:
  format:
    type: json
    fields: [timestamp, level, service, trace_id, span_id, user_id, project_id, message, duration_ms]
  levels:
    default: info
    pii: warn
    error: error
  sinks:
    - type: stdout
    - type: file
      path: /var/log/movie-generator/
      rotation: 100MB
      retention: 30d
    - type: elasticsearch
      endpoint: https://es-internal.vpc:9200
      index_pattern: "logs-movie-{YYYY-MM-DD}"
```

### 17. CI/CD Pipeline

```yaml
# .github/workflows/movie-generator.yml
name: Movie Generator CI/CD
on:
  push:
    branches: [main, develop]
    paths: ['agents/**', 'tools/**', 'eval/**']
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubicloud
    steps:
      - uses: actions/checkout@v4
      - name: Unit tests
        run: pytest tests/unit/ --cov=agents/ --cov-fail-under=85
      - name: Integration tests
        run: docker compose up -d && pytest tests/integration/
      - name: CI eval
        run: |
          python eval/research_eval.py --ci --threshold 0.8
          python eval/script_eval.py --ci --threshold 0.75
          python eval/storyboard_eval.py --ci --threshold 0.8
      - name: Security scan
        run: trivy image --severity HIGH,CRITICAL --exit-code 1 && snyk test --all-projects

  visual_qa:
    needs: [test]
    steps:
      - run: python scripts/generate_preview.py --output preview.mp4
      - run: python eval/visual_qa.py --video preview.mp4
      - uses: actions/upload-artifact@v4
        with: { name: preview, path: preview.mp4 }

  deploy-staging:
    needs: [test]
    if: github.ref == 'refs/heads/develop'
    steps:
      - run: |
          ak deploy research-agent --app-name movie-research-staging
          ak deploy script-agent --app-name movie-script-staging

  deploy-production:
    needs: [test, visual_qa]
    if: github.ref == 'refs/heads/main'
    steps:
      - run: ak deploy video-gen-agent --app-name movie-videogen-canary --canary 0.1
      - name: Health check
        run: ak health --app movie-videogen-canary --timeout 30s && ak eval run --app movie-videogen-canary --test-set eval/test_data/smoke.json
      - name: Full rollout
        run: ak deploy video-gen-agent --app-name movie-videogen && ...

  cost-track:
    schedule: "0 6 * * 1"
    steps:
      - run: python scripts/check_budget.py --project movie
```

### Updated 檔案結構

---

## 技術棧總結 — 完整 BytePlus / Volcengine Stack

| 層面 | 採用技術 |
|------|---------|
| **Agent Framework** | VeADK (`veadk-python`) |
| **A2A Communication** | AgentKit SDK (`agentkit-sdk-python[a2a]` → `AgentkitA2aApp`) |
| **Deployment** | **ModelArk** Managed Agents / AgentKit CLI (`ak deploy`) |
| **API Layer** | **BytePlus ModelArk**（統一 API 入口） |
| **Subscription** | **Agent Plan Medium** (¥200/月, 100,000 AFP) |
| **LLM (default)** | **Seed 2.0 Lite** (極速 1× AFP, research/script) |
| **LLM (lightweight)** | **Seed 2.0 Mini** (極速 1× AFP, storyboard/merge) |
| **Image Generation** | **Seedream 5.0 Lite** (Medium Plan 已包, ~100 AFP/img) |
| **Video Generation** | **Seedance 2.0 Fast** (Medium Plan 已包, ~2,000 AFP/clip) |
| **Speech** | **Seed Speech TTS 2.0** |
| **Digital Human** | **Omnihuman 1.5**（可選 — 需 Large Plan 或獨立計費） |
| **Motion Control** | **DreamActor M2.0**（可選 — 需 Large Plan 或獨立計費） |
| **Web Research** | VeADK `web_search` built-in tool |
| **Video Processing** | FFmpeg |
| **Object Storage** | **TOS** |
| **Vector DB** | **VikingDB** / **OpenViking** |
| **Relational DB** | PostgreSQL（STM session / metadata） |
| **Cache** | Redis |
| **Security** | VeADK `AuthRequestProcessor` + **Volcengine IAM** + mTLS A2A + Service Mesh (Istio) |
| **Network** | VPC internal + egress-only to BytePlus API |
| **Identity** | **Volcengine Identity** (ve_identity) |
| **Observability** | **OpenTelemetry** (Jaeger + CloudWatch) |
| **Logging** | Structured JSON logging → Elasticsearch / Loki |
| **Audit** | Dual-write (PostgreSQL + TOS), chain-hash immutable |
| **Secrets** | **HashiCorp Vault** + auto-rotation |
| **Content Safety** | **BytePlus Content Detector** (copyright/celebrity/brand) |
| **Prompt Shield** | **BytePlus ModelArk Shield** (pre + post filter) |
| **Cost** | BytePlus billing API + budgets + caching + resolution tiers |
| **Eval** | CI eval pipeline + shadow eval + ground truth versioning + visual QA |
| **Testing** | Unit (pytest, 85% cov) + Integration + Visual QA + Chaos |
