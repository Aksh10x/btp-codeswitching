# BTP Progress Report — November 6, 2026

**Student:** Akshath  
**Supervisor:** Prof. Dripta Piplai  
**Project:** Code-Switching and Gender Agreement in Hindi-Bengali Bilingual Speech  
**Institution:** IIT Kharagpur

---

## 1. What We Have

### Dataset
- **7 speakers** (IIT KGP campus staff): 6 Bengali L1, 1 Hindi L1 (UP, comparison case)
- **8 substantive recordings** totaling ~37.5 minutes of speech
  - 7 video interviews (HEVC 4K) + 1 audio-only (participant declined video)
- **4 discarded clips** (false starts / camera checks, <30s each)

### Audio Quality Assessment (completed)
| Quality Tier | Files | Total Duration |
|---|---|---|
| Excellent (SNR > 17 dB) | 3 files (S2, S3, S7) | ~16 min |
| Clean (SNR 13-15 dB) | 3 files (S1, S5, S6) | ~17 min |
| Usable with caution (SNR ~8 dB) | 1 file (S4) | ~5.5 min |

All files: zero clipping, 48 kHz AAC source, speech activity 22-50%.

### Technical Infrastructure (completed)
- GitHub repository: private, with .gitignore protecting participant privacy
- Full acoustic inventory with per-file technical metadata (JSON)
- Automated pipeline scripts ready to run:
  1. Audio extraction (ffmpeg, 16 kHz mono WAV)
  2. Transcription (faster-whisper large-v3, word-level timestamps)
  3. Linguistic analysis (agreement site extraction, code-switching detection)

---

## 2. What the Transcription Pipeline Does

### Whisper Configuration
- **Model:** faster-whisper large-v3 (int8 quantized for CPU)
- **Language:** Hindi primary, with Bengali code-switching expected
- **Features:** Word-level timestamps, VAD filtering, beam search (5)
- **Prompt engineering:** Explicit instruction to preserve hesitations, false starts,
  and not normalize dialect forms

### Linguistic Analysis (automated, post-transcription)
For each transcript, the pipeline extracts:

1. **Low-confidence segments** — where Whisper's language model struggles, flagging
   possible Bengali stretches or unclear speech
2. **Past-tense verbs** — with gender marking (masculine -aa/-e, feminine -ii)
3. **Adjective-noun pairs** — gendered adjectives matched against known lexicon
4. **Ergative "ne" constructions** — the hardest agreement case (verb agrees with
   object, not subject; Bengali has no equivalent)
5. **Per-speaker summary** — word counts, Bengali candidate words, switch points,
   total agreement sites

### Critical Limitation (documented in all outputs)
> Whisper predicts the most likely sentence. It will silently "correct" agreement
> errors (e.g., "kitab gira" → "kitab giri") and convert Bengali words to
> similar-sounding Hindi. These are exactly what this study measures. Every
> transcript is marked as UNVERIFIED and requires human verification against
> the audio.

---

## 3. Preliminary Observations (from acoustic analysis)

- The Bengali L1 speakers show **high silence fractions** (50-78%), suggesting
  interview-style responses with pauses — consistent with L2 speech production
- **S4** (elevated noise floor) may need segment-level quality checks during
  human verification
- Speaker **S7** (audio-only, who declined video) has excellent audio quality
  (SNR 17.7 dB) — this person's data is fully usable

---

## 4. What Happens Next

### Immediate (this week)
- [ ] Re-upload recordings to cloud session
- [ ] Run full pipeline end-to-end (~1-2 hours on CPU)
- [ ] Inspect first transcript output; verify against audio for one speaker

### Short-term (Nov 7-15)
- [ ] Human verification of all 8 transcripts against audio
  - Priority: mark Bengali stretches Whisper converted to Hindi
  - Priority: check agreement sites for Whisper's silent corrections
- [ ] Produce verified counts: actual Bengali words, actual agreement errors
- [ ] Identify the Hindi L1 speaker (comparison case) and separate their data

### Medium-term (Nov 15-30)
- [ ] Categorize code-switching types per speaker:
  - Tag switches (single Bengali word in Hindi frame)
  - Intra-sentential (Bengali clause within Hindi sentence)
  - Inter-sentential (full sentence in Bengali)
- [ ] Categorize agreement errors by type:
  - Adjective-noun gender disagreement
  - Past-tense verb gender disagreement
  - Ergative "ne" construction errors
- [ ] Compare Bengali L1 speakers vs Hindi L1 speaker on error rates

### Writing (December)
- [ ] Literature review: Poplack (1980) typology, Myers-Scotton MLF model,
  Muysken (2000) on insertion/alternation/congruent lexicalization
- [ ] Results chapter with tables and examples
- [ ] Discussion: does the pattern fit insertional or alternational switching?

---

## 5. Honest Assessment

### Data sufficiency
- **~37.5 minutes across 7 speakers** is enough for a **descriptive/qualitative
  case study** with illustrative examples
- It is **marginal for quantitative comparison** across speakers — depends on
  how many agreement sites and switch points survive human verification
- If the verified count of agreement sites is < 20 total, recommend framing
  as a pilot study or collecting 2-3 more interviews

### Main risks
1. **Whisper normalization** — the biggest risk. The tool corrects the very
   errors we want to count. Human verification is non-negotiable.
2. **Bengali detection** — many words exist in both Hindi and Bengali. Some
   switches will only be detectable by prosody/phonology, not text alone.
3. **Sample size** — 7 speakers is a small N for cross-speaker generalizations.
   Framing matters: this is a detailed case study, not a population survey.

### What I need from you (Prof. Piplai)
- Guidance on whether to frame as pilot study or full study given the N
- Whether to pursue IndicWhisper (AI4Bharat) as a second transcription pass
  for Bengali detection
- Suggestions on additional literature for Hindi-Bengali contact phenomena
