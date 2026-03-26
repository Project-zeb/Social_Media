
### Phase 1: Architectural Foundations & Setup

**1. The Core Philosophy: Human-in-the-Loop (HITL) Architecture**
SurgeGuard AI is not a fully autonomous decision-maker; it is a high-speed filtration engine. The system is built on the premise that AI handles the volume (triage), but humans handle the final truth (verification). The architecture enforces this by mathematically capping AI confidence and requiring cryptographic/session-based human sign-offs for final alerts.

**2. The Asynchronous ASGI Foundation**
Traditional Django uses WSGI, which processes requests synchronously. Because SurgeGuard processes heavy ML models and live social media streams, it is rebuilt on **ASGI (Asynchronous Server Gateway Interface)**. The `sg_intel/asgi.py` file replaces WSGI, allowing the system to handle WebSockets and long-polling real-time dashboard updates without freezing the server.

**3. Daphne Server Integration**
To serve the ASGI application, the system uses Daphne. Daphne is placed at the absolute top of the `INSTALLED_APPS` list in `settings.py`. To run the primary web and WebSocket server, the command is:
`daphne -b 0.0.0.0 -p 8000 sg_intel.asgi:application`
This exposes the server on all local interfaces on port 8000.

**4. Redis and Channels Configuration**
Real-time communication requires a message broker. SurgeGuard uses Redis (or Dragonfly as a drop-in replacement). In `settings.py`, the `CHANNEL_LAYERS` dictionary is configured to use `channels_redis.core.RedisChannelLayer` pointing to `127.0.0.1:6379`. This allows Django views, Celery background tasks, and WebSocket consumers to broadcast JSON data to the frontend simultaneously.

**5. Distributed Task Queues (Celery)**
AI processing (like running OpenAI CLIP) can take 2-5 seconds per post. If done on the main thread, the website would crash under load. Celery is integrated (`sg_intel/celery.py`) to offload this. The broker and result backend are both set to `redis://127.0.0.1:6379/0`. The worker must be booted in a separate terminal using:
`celery -A sg_intel worker --loglevel=info`

---

### Phase 2: Database Schema & State Management

**6. The DisasterEvent Model (The Source of Truth)**
Located in `core/models.py`, this is the parent record for any incident. It stores critical spatial data (`grid_lat`, `grid_lon` with `db_index=True` for fast radius queries), numerical confidence metrics (`ai_triage_score`, `truth_score`), and string descriptors (`event_type`, `district`). 

**7. The "Intel Tier" Hierarchy**
The database utilizes an integer-based `intel_tier` field to define systemic trust:
* **Tier 3:** Officer Verified (Absolute Truth).
* **Tier 2:** AI High Priority (Machine Trusted).
* **Tier 1:** Pending / Flagged (Machine Skeptical).
* **Tier 0:** Fake (Dismissed).

**8. Model-Level Status Synchronization**
To prevent a scenario where a database record says "VERIFIED" but the tier is 1, a custom `save()` method is overridden in the `DisasterEvent` model. Whenever `event.save()` is called, the system forcefully checks the `status` string and hardcodes the `intel_tier` integer to match. This guarantees database integrity regardless of how the data was modified.

**9. The SocialPost Relational Model**
A `DisasterEvent` is a cluster of individual reports. The `SocialPost` model acts as the child, linked via a `ForeignKey` to the event. It stores the `raw_text`, `image_url`, `user_handle`, and a unique `post_id`. The unique `post_id` prevents the mock feed from double-counting the exact same tweet.

**10. Database Indexing Strategy**
Because the dashboard constantly queries the top incidents, `Meta.indexes` are heavily utilized in `models.py`. The database creates B-Tree indexes for `-created_at`, `truth_score`, `ai_triage_score`, `intel_tier`, and a composite index for `['grid_lat', 'grid_lon']`. This drops query times from O(N) to O(log N) during massive regional crises.

---

### Phase 3: The Multimodal AI Pipeline

**11. Multilingual Ingestion via Helsinki-NLP**
India's linguistic diversity requires translation before AI analysis. In `core/triage.py`, the system loads `Helsinki-NLP/opus-mt-hi-en` via HuggingFace's `MarianMTModel`. Every non-English post is converted into English tensor tokens, translated, and decoded back into a text string. This translated string is saved to the `event.summary` field.

**12. Vision-Language Modeling (OpenAI CLIP)**
SurgeGuard uses `openai/clip-vit-base-patch32`. This model maps both text and images into the exact same vector space. The system feeds the translated English text and the raw image (downloaded via `requests.get` to `io.BytesIO`) into the `clip_processor`.

**13. The Cosine Similarity Mathematical Formula**
The core validation is mathematical. The model outputs a logit representing the distance between the image vector ($B$) and text vector ($A$). The cosine similarity is calculated as:
$$Score = \cos(\theta) = \frac{A \cdot B}{\|A\| \|B\|}$$
This proves if the photo visually depicts the text being claimed (e.g., stopping someone from uploading a photo of a concert and claiming it's a riot).

**14. The 22.0 AI Threshold Filter**
Through testing, a CLIP logit score of **22.0** was determined as the threshold for "High Confidence" matches. If the mathematical output is $> 22.0$, the event's status is promoted to `HIGH_PRIORITY` and `intel_tier` becomes 2. If it is $\le 22.0$, it is quarantined as `FLAGGED` (`intel_tier` 1).

**15. Failsafe Image Handling**
The triage script contains a specific `try/except` block to handle both live internet URLs (`http...`) and local file paths (e.g., `test_viva.jpg` for offline viva demonstrations). If image parsing fails, the AI score defaults to 0.0, automatically flagging the post for human review rather than crashing the Celery worker.

---

### Phase 4: Data Processing & Scoring Algorithms

**16. The Mini-NLP Status Generator**
In `core/utils/processor.py`, the `get_3_word_status` function uses keyword mapping to create dense operational summaries. It scans the raw text for intensity markers (e.g., "massive", "critical" = "Critical") and trend markers (e.g., "rising", "spreading" = "Escalating"). It outputs a high-density string like "Critical Flood: Escalating".

**17. Source Credibility Weightage System**
Not all users have equal voting power. The `get_source_weight` function hardcodes trust values:
* **Weight 15.0:** Official agencies (`ndrfhq`, `indiametdept`, `uppolice`).
* **Weight 7.0:** News agencies (`ani`, `ndtv`).
* **Weight 1.0:** Standard civilian accounts.
These weights dictate how much the `truth_score` increases per post.

**18. The Momentum Multiplier (Hashtag Logic)**
To detect viral, rapidly escalating emergencies, the system extracts hashtags using regex `r"#(\w+)"`. It then queries the database for posts using that hashtag in the last 30 minutes. If **5 or more distinct user_handles** used the tag, a multiplier of **1.5x** is applied to the calculated score boost.

**19. Live Weather Integration Data**
The `get_live_weather_score` function supplements social intel. If someone reports a flood, the system uses the grid coordinates to check external weather APIs. If heavy rainfall is actively occurring at that latitude/longitude, a base weather score is immediately injected into the `truth_score`.

**20. Automated Base Verification Triggers**
If the accumulating `truth_score` (Base Weight $\times$ Multiplier $+$ Weather) naturally crosses **20.0**, the system automatically upgrades the status label in the situational summary to "VERIFIED", acknowledging the overwhelming consensus of the crowd before an officer even looks at it.

---

### Phase 5: Spatial Intelligence & Geography

**21. Coordinate Mapping (The Grid System)**
Raw text contains district names, not GPS coordinates. The `get_coords_from_district` function uses an internal lookup (likely referencing `coordinate_districts_v3.csv`) to map string names (e.g., "Delhi") to exact floating-point latitude and longitude values for the database.

**22. Spatial Event Clustering (The 4-Hour Rule)**
When a new post arrives, the system queries for any active `DisasterEvent` with the same `event_type`, at the exact same `grid_lat` and `grid_lon`, updated within the last **4 hours**. If found, the post is merged into the existing event, incrementing `total_votes` and stacking the `truth_score`, preventing dashboard duplication.

**23. Regional Spread Detection Logic**
The system identifies macro-disasters. `detect_regional_spread` searches for similar events (score > 10.0, last 6 hours) within a **0.6-degree radius** (approx 60-65 kilometers in North India) by comparing absolute differences in lat/lon. 

**24. Macro-Crisis Alerting**
If the regional spread condition is met, the system prepends a critical alert to the summary: `"⚠️ REGIONAL CRISIS: Linked with [Neighboring District] sector."` This tells the human commander that this is a multi-district incident requiring higher-level resource allocation.

**25. Missing Data Rejection**
If the NLP processor cannot extract a valid location name, or if the geo-mapper cannot find the coordinates for that location in the North India grid, the system explicitly returns `"❌ Location not in North India grid"` and drops the processing to maintain database purity.

---

### Phase 6: The Temporal Decay Engine (Lifecycle Management)

**26. The Philosophy of Obsolescence**
A flood report from 3 days ago is irrelevant today. SurgeGuard AI treats truth as a decaying variable. The system features two layers of decay: backend database decay and frontend visual decay.

**27. Backend Database Decay (The Cron Job)**
In `core/utils/decay_logic.py`, the `apply_global_decay` function is designed to run periodically (e.g., via the `python manage.py apply_decay` command). It queries all events with a score $> 0.5$ and multiplies their `truth_score` by **0.90** (a 10% reduction). If it drops below 1.0, the event is functionally dead.

**28. Frontend Visual Decay (The Dashboard Multiplier)**
The `dashboard` view in `core/views.py` calculates real-time decay down to the second without writing to the database. It calculates the `hours_passed` since `updated_at`. The formula applied is:
$$DisplayScore = TruthScore \times (0.92^{hours\_passed})$$
This results in an 8% drop in visibility score for every hour it sits inactive on the dashboard.

**29. The "Ghosting" Threshold (0.1)**
During the view rendering process, the system checks the `display_score`. If the dynamically calculated score drops to **0.1 or lower**, the event is excluded from the `processed_alerts` list for the Live Feed, automatically clearing the screen of resolved or dead incidents.

**30. Data Ingestion Simulation Engine**
To feed the system during development or presentations, the `python manage.py run_mock_feed` command continuously reads sample data and fires it into the `process_social_intel` function. The speed of this feed is controlled by the `INGESTION_INTERVAL` variable in the `.env` file.

---

### Phase 7: UI/UX, Access Control, and Administrative Authority

**31. Strict Segment Segregation (The Views)**
The dashboard view dynamically alters its query based on the URL parameter (`segment`).
* `/verified/`: Filters strictly for `intel_tier=3`.
* `/ai-pass/`: Filters strictly for `intel_tier=2`.
* `/flagged/`: Filters for Tier 1 anomalies (The Review Queue).
If no segment is provided, it defaults to the Public Live Feed, combining Tier 2 and Tier 3.

**32. The 99% AI Cap (Psychological UI Design)**
To prevent human officers from blindly trusting the machine, the `dashboard` view intercepts Tier 1 and Tier 2 events before rendering. It uses `min(round(decayed_score, 1), 99.0)`. No matter how confident the AI is, the UI will never display a score higher than 99.0% unless an officer has manually stamped it.

**33. Supreme Officer Authentication & The Audit Trail**
The `update_event_status` view requires the `@login_required` decorator. When an officer clicks "Verify", the following occurs:
1. Status changes to `VERIFIED`.
2. `intel_tier` is locked to 3.
3. `truth_score` is forcefully set to 100.0 (overriding decay and AI limits).
4. **Audit:** `event.verified_by = request.user` logs the exact admin account that took responsibility for the decision.
5. A Django `messages.success` notification fires, documenting the action on the UI.