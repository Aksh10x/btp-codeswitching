# Code-Switching & Gender Agreement in Bengali-Hindi Bilinguals

**B.Tech Project (BTP)**  
**Student:** Akshath  
**Institution:** Indian Institute of Technology Kharagpur (IIT KGP)  
**Supervisor:** Prof. Dripta Piplai  

## Overview
This project investigates sociolinguistic code-switching and morphological transfer patterns in campus staff at IIT Kharagpur. All speakers are first-language Bengali adults who acquired Hindi naturalistically in workplace settings.

### Key Research Questions
1. **Code-Switching Dynamics**: Characterizing where Bengali enters Hindi discourse and categorizing switch typologies (tag-switching, inter-sentential switching, intra-sentential switching).
2. **Grammatical Gender Agreement Transfer**: Tracking gender agreement marking on Hindi adjectives and past-tense verbs (particularly split-ergative perfective constructions with *-ne*, where the verb agrees with the direct object rather than the subject).

## Repository Structure
- `scripts/`: Audio extraction, signal analysis, transcription, and linguistic analysis pipelines.
- `transcripts/`: Verbatim unnormalized transcripts with word-level timestamps and speaker turns.
- `analysis/`: Companion linguistic reports, candidate switch points, and agreement site tallies.
- `docs/`: Progress reports and presentation materials.

## Running the Pipeline

```bash
# 1. Place recordings in a data folder (e.g., ~/Desktop/BTP/) with subfolders:
#    "BTP videos/", "BTP videos 2/", "BTP videos 3/"

# 2. Run the full pipeline:
bash scripts/run_pipeline.sh ~/Desktop/BTP

# Or run steps individually:
bash scripts/01_extract_audio.sh ~/Desktop/BTP
python3 scripts/02_transcribe_all.py ~/Desktop/BTP/extracted_audio ~/Desktop/BTP/transcripts
python3 scripts/03_linguistic_analysis.py ~/Desktop/BTP/transcripts ~/Desktop/BTP/analysis
```

### Requirements
- Python 3.8+
- ffmpeg / ffprobe
- `pip install openai-whisper faster-whisper numpy`
