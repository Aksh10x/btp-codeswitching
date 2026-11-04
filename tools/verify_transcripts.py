#!/usr/bin/env python3
"""
Transcript Verification Server

Serves an interactive UI for verifying Whisper transcripts against audio.
Corrections auto-save to verification/<file>_corrections.json.

Usage:
    python3 tools/verify_transcripts.py

Then open http://localhost:8765 in your browser.
Load audio files when prompted (WAV from extracted_audio/).
"""

import http.server
import json
import os
import sys
import webbrowser
import mimetypes
from pathlib import Path
from urllib.parse import unquote
from datetime import datetime

PORT = 8765
BASE_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
AUDIO_DIR = BASE_DIR / "extracted_audio"
CORRECTIONS_DIR = BASE_DIR / "verification"


def load_transcripts():
    transcripts = {}
    for f in sorted(TRANSCRIPTS_DIR.glob("*_transcript.json")):
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            transcripts[data["file"]] = data
    return transcripts


def get_audio_files():
    files = {}
    if AUDIO_DIR.exists():
        for f in AUDIO_DIR.glob("*.wav"):
            files[f.stem] = str(f)
    return files


HTML_TEMPLATE = r"""
<title>Transcript Verifier</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600&display=swap">
<style>
:root {
    --bg: #f8f7f4;
    --surface: #ffffff;
    --surface-alt: #f0eeea;
    --border: #ddd8d0;
    --fg: #1a1a1a;
    --fg-dim: #6b6560;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --flag-bg: #fef3c7;
    --flag-border: #f59e0b;
    --verified-bg: #ecfdf5;
    --verified-border: #10b981;
    --low-conf: #ef4444;
    --med-conf: #f59e0b;
    --high-conf: #10b981;
    --playing-bg: #eff6ff;
    --playing-border: #3b82f6;
    font-family: 'Inter', system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
        --bg: #111110;
        --surface: #1c1c1a;
        --surface-alt: #252523;
        --border: #3a3935;
        --fg: #e8e6e1;
        --fg-dim: #9b9590;
        --accent: #60a5fa;
        --accent-hover: #93bbfd;
        --flag-bg: #422006;
        --flag-border: #d97706;
        --verified-bg: #052e16;
        --verified-border: #059669;
        --low-conf: #f87171;
        --med-conf: #fbbf24;
        --high-conf: #34d399;
        --playing-bg: #172554;
        --playing-border: #60a5fa;
        color-scheme: dark;
    }
}
:root[data-theme="dark"] {
    --bg: #111110;
    --surface: #1c1c1a;
    --surface-alt: #252523;
    --border: #3a3935;
    --fg: #e8e6e1;
    --fg-dim: #9b9590;
    --accent: #60a5fa;
    --accent-hover: #93bbfd;
    --flag-bg: #422006;
    --flag-border: #d97706;
    --verified-bg: #052e16;
    --verified-border: #059669;
    --low-conf: #f87171;
    --med-conf: #fbbf24;
    --high-conf: #34d399;
    --playing-bg: #172554;
    --playing-border: #60a5fa;
    color-scheme: dark;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: var(--bg);
    color: var(--fg);
    padding-left: max(16px, env(safe-area-inset-left, 0px));
    padding-right: max(16px, env(safe-area-inset-right, 0px));
    padding-block: 0;
    min-height: 100vh;
}

.header {
    position: sticky;
    top: env(safe-area-inset-top, 0px);
    z-index: 10;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
}
.header h1 {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.02em;
    white-space: nowrap;
}
.header select, .header button, .header label {
    font: inherit;
    font-size: 13px;
}
.header select {
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface-alt);
    color: var(--fg);
    cursor: pointer;
}
.btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    background: var(--accent);
    color: #fff;
    font-weight: 500;
    font-size: 13px;
    cursor: pointer;
    white-space: nowrap;
}
.btn:hover { background: var(--accent-hover); }
.btn-outline {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--fg);
}
.btn-outline:hover { background: var(--surface-alt); }

.stats {
    margin-left: auto;
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: var(--fg-dim);
    font-variant-numeric: tabular-nums;
}
.stats span { white-space: nowrap; }
.stats strong { color: var(--fg); }

.audio-bar {
    position: sticky;
    top: calc(env(safe-area-inset-top, 0px) + 55px);
    z-index: 9;
    background: var(--surface-alt);
    border-bottom: 1px solid var(--border);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.audio-bar .play-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: none;
    background: var(--accent);
    color: #fff;
    font-size: 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.audio-bar .play-btn:hover { background: var(--accent-hover); }
.progress-wrap {
    flex: 1;
    min-width: 0;
    height: 28px;
    display: flex;
    align-items: center;
    cursor: pointer;
    position: relative;
}
.progress-track {
    width: 100%;
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    position: relative;
    overflow: hidden;
}
.progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    width: 0%;
    transition: width 0.1s linear;
}
.time-display {
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    color: var(--fg-dim);
    white-space: nowrap;
    min-width: 90px;
    text-align: center;
}
.speed-btn {
    font-size: 12px;
    padding: 4px 8px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--surface);
    color: var(--fg);
    cursor: pointer;
    font-weight: 600;
}
.no-audio {
    text-align: center;
    padding: 16px;
    background: var(--flag-bg);
    border: 1px solid var(--flag-border);
    border-radius: 8px;
    margin: 16px 0;
    font-size: 14px;
}
.no-audio input[type=file] { margin-top: 8px; }

.segments {
    max-width: 900px;
    margin: 0 auto;
    padding: 16px 0 120px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.segment {
    background: var(--surface);
    border: 2px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
}
.segment:hover { border-color: var(--accent); }
.segment.playing {
    background: var(--playing-bg);
    border-color: var(--playing-border);
}
.segment.flagged {
    border-color: var(--flag-border);
    background: var(--flag-bg);
}
.segment.verified {
    border-color: var(--verified-border);
    background: var(--verified-bg);
}

.seg-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
    flex-wrap: wrap;
}
.seg-time {
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    color: var(--fg-dim);
    font-weight: 500;
}
.seg-play {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--fg);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex-shrink: 0;
}
.seg-play:hover { background: var(--accent); color: #fff; border-color: var(--accent); }
.seg-conf {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 500;
}
.conf-high { background: color-mix(in srgb, var(--high-conf) 15%, transparent); color: var(--high-conf); }
.conf-med { background: color-mix(in srgb, var(--med-conf) 15%, transparent); color: var(--med-conf); }
.conf-low { background: color-mix(in srgb, var(--low-conf) 15%, transparent); color: var(--low-conf); }

.seg-text {
    font-family: 'Noto Sans Devanagari', 'Inter', sans-serif;
    font-size: 16px;
    line-height: 1.8;
    margin-bottom: 8px;
    text-wrap: pretty;
}
.seg-text .word {
    padding: 1px 2px;
    border-radius: 3px;
    cursor: help;
    transition: background 0.1s;
}
.seg-text .word:hover { background: color-mix(in srgb, var(--accent) 20%, transparent); }
.seg-text .word.low { background: color-mix(in srgb, var(--low-conf) 15%, transparent); }
.seg-text .word.med { background: color-mix(in srgb, var(--med-conf) 10%, transparent); }

.seg-actions {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
}

.correction-panel {
    margin-top: 10px;
    padding: 12px;
    background: var(--surface-alt);
    border-radius: 6px;
    display: none;
}
.correction-panel.open { display: block; }
.correction-panel label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--fg-dim);
}
.correction-panel textarea {
    width: 100%;
    min-height: 60px;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--fg);
    font-family: 'Noto Sans Devanagari', 'Inter', sans-serif;
    font-size: 14px;
    resize: vertical;
    margin-bottom: 8px;
}
.correction-panel textarea:focus { outline: 2px solid var(--accent); border-color: transparent; }
.error-types {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
}
.error-types label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 400;
    cursor: pointer;
    color: var(--fg);
}
.error-types input[type=radio] { accent-color: var(--accent); }

.shortcuts {
    position: fixed;
    bottom: 16px;
    right: max(16px, env(safe-area-inset-right, 0px));
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 11px;
    color: var(--fg-dim);
    z-index: 20;
    line-height: 1.6;
}
.shortcuts kbd {
    display: inline-block;
    padding: 1px 5px;
    border: 1px solid var(--border);
    border-radius: 3px;
    background: var(--surface-alt);
    font-family: inherit;
    font-size: 11px;
}
@media (max-width: 600px) {
    .shortcuts { display: none; }
    .stats { display: none; }
}
</style>

<div class="header">
    <h1>Verify Transcripts</h1>
    <select id="speaker-select"></select>
    <div id="audio-load-area"></div>
    <div class="stats" id="stats"></div>
</div>

<div class="audio-bar" id="audio-bar" style="display:none">
    <button class="play-btn" id="global-play" title="Space to toggle">&#9654;</button>
    <div class="progress-wrap" id="progress-wrap">
        <div class="progress-track">
            <div class="progress-fill" id="progress-fill"></div>
        </div>
    </div>
    <div class="time-display" id="time-display">0:00 / 0:00</div>
    <button class="speed-btn" id="speed-btn" title="Playback speed">1x</button>
</div>

<div class="segments" id="segments"></div>

<div class="shortcuts">
    <kbd>Space</kbd> play/pause &nbsp;
    <kbd>&larr;</kbd><kbd>&rarr;</kbd> skip 3s &nbsp;
    <kbd>&uarr;</kbd><kbd>&darr;</kbd> prev/next segment &nbsp;
    <kbd>F</kbd> flag current
</div>

<script>
const TRANSCRIPTS = __TRANSCRIPTS_DATA__;
const AUDIO_MAP = __AUDIO_MAP__;
let currentFile = null;
let audio = null;
let corrections = {};
let verifiedSegs = new Set();
let currentSegIdx = -1;
let playingSegId = null;
let speeds = [0.5, 0.75, 1, 1.25, 1.5];
let speedIdx = 2;
let saveTimeout = null;

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

function init() {
    const sel = $('#speaker-select');
    const files = Object.keys(TRANSCRIPTS).sort();
    files.forEach(f => {
        const t = TRANSCRIPTS[f];
        const opt = document.createElement('option');
        opt.value = f;
        opt.textContent = `${t.speaker_code} — ${f} (${t.total_segments} segs, ${Math.round(t.duration_s)}s)`;
        sel.appendChild(opt);
    });
    sel.addEventListener('change', () => loadSpeaker(sel.value));
    if (files.length > 0) loadSpeaker(files[0]);
}

async function loadSpeaker(file) {
    currentFile = file;
    currentSegIdx = -1;
    playingSegId = null;
    const data = TRANSCRIPTS[file];

    // Load existing corrections
    try {
        const resp = await fetch(`/api/corrections/${file}`);
        if (resp.ok) {
            const saved = await resp.json();
            corrections = {};
            (saved.corrections || []).forEach(c => corrections[c.segment_id] = c);
            verifiedSegs = new Set(saved.verified_segments || []);
        } else {
            corrections = {};
            verifiedSegs = new Set();
        }
    } catch(e) {
        corrections = {};
        verifiedSegs = new Set();
    }

    // Audio
    if (audio) { audio.pause(); audio.src = ''; }
    const audioArea = $('#audio-load-area');
    const audioBar = $('#audio-bar');

    if (AUDIO_MAP[file]) {
        loadAudioFromServer(file);
    } else {
        audioBar.style.display = 'none';
        audioArea.innerHTML = `<label class="btn btn-outline" style="cursor:pointer">
            Load Audio (${file}.wav)
            <input type="file" accept=".wav,.mp3,.m4a,.ogg" style="display:none"
                onchange="handleAudioFile(this.files[0])">
        </label>`;
    }

    renderSegments(data);
    updateStats();
}

function loadAudioFromServer(file) {
    audio = new Audio(`/audio/${file}.wav`);
    setupAudio();
}

function handleAudioFile(file) {
    if (!file) return;
    audio = new Audio(URL.createObjectURL(file));
    setupAudio();
}

function setupAudio() {
    const bar = $('#audio-bar');
    bar.style.display = 'flex';
    $('#audio-load-area').innerHTML = '<span style="font-size:12px;color:var(--fg-dim)">Audio loaded</span>';

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', () => {
        updateTimeDisplay();
    });
    audio.addEventListener('ended', () => {
        $('#global-play').innerHTML = '&#9654;';
    });

    $('#global-play').onclick = togglePlay;
    $('#progress-wrap').onclick = e => {
        if (!audio.duration) return;
        const rect = e.currentTarget.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        audio.currentTime = pct * audio.duration;
    };
    $('#speed-btn').onclick = cycleSpeed;
}

function togglePlay() {
    if (!audio) return;
    if (audio.paused) {
        audio.play();
        $('#global-play').innerHTML = '&#9646;&#9646;';
    } else {
        audio.pause();
        $('#global-play').innerHTML = '&#9654;';
    }
}

function cycleSpeed() {
    speedIdx = (speedIdx + 1) % speeds.length;
    audio.playbackRate = speeds[speedIdx];
    $('#speed-btn').textContent = speeds[speedIdx] + 'x';
}

function onTimeUpdate() {
    if (!audio || !audio.duration) return;
    const pct = (audio.currentTime / audio.duration) * 100;
    $('#progress-fill').style.width = pct + '%';
    updateTimeDisplay();

    // Highlight playing segment
    const data = TRANSCRIPTS[currentFile];
    if (!data) return;
    let foundSeg = null;
    data.segments.forEach((seg, i) => {
        if (audio.currentTime >= seg.start && audio.currentTime <= seg.end) {
            foundSeg = seg.id;
            if (currentSegIdx !== i) {
                currentSegIdx = i;
            }
        }
    });

    $$('.segment').forEach(el => {
        el.classList.toggle('playing', el.dataset.segId == foundSeg);
    });
}

function updateTimeDisplay() {
    if (!audio) return;
    const cur = fmtTime(audio.currentTime);
    const dur = fmtTime(audio.duration || 0);
    $('#time-display').textContent = `${cur} / ${dur}`;
}

function fmtTime(s) {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return m + ':' + String(sec).padStart(2, '0');
}

function fmtTimestamp(s) {
    const m = Math.floor(s / 60);
    const sec = (s % 60).toFixed(1);
    return m + ':' + String(sec).padStart(4, '0');
}

function confClass(logprob) {
    if (logprob === null || logprob === undefined) return 'conf-med';
    if (logprob > -0.4) return 'conf-high';
    if (logprob > -0.8) return 'conf-med';
    return 'conf-low';
}

function confLabel(logprob) {
    if (logprob === null || logprob === undefined) return '?';
    if (logprob > -0.4) return 'good';
    if (logprob > -0.8) return 'mid';
    return 'low';
}

function wordConfClass(prob) {
    if (prob >= 0.7) return '';
    if (prob >= 0.4) return 'med';
    return 'low';
}

function renderSegments(data) {
    const container = $('#segments');
    container.innerHTML = '';

    data.segments.forEach((seg, idx) => {
        const div = document.createElement('div');
        div.className = 'segment';
        div.dataset.segId = seg.id;
        div.dataset.idx = idx;

        const isFlagged = corrections[seg.id] !== undefined;
        const isVerified = verifiedSegs.has(seg.id);
        if (isFlagged) div.classList.add('flagged');
        else if (isVerified) div.classList.add('verified');

        const wordsHtml = (seg.words || []).map(w => {
            const cls = wordConfClass(w.probability || 1);
            const title = `${w.word} (${(w.probability * 100).toFixed(0)}% @ ${fmtTimestamp(w.start)})`;
            return `<span class="word ${cls}" title="${title}">${w.word}</span>`;
        }).join(' ');

        const correction = corrections[seg.id];
        const corrText = correction ? correction.correction : '';
        const corrType = correction ? correction.error_type : 'wrong_word';
        const corrNotes = correction ? (correction.notes || '') : '';

        div.innerHTML = `
            <div class="seg-header">
                <button class="seg-play" onclick="playSeg(${seg.start}, ${seg.end}, event)" title="Play segment">&#9654;</button>
                <span class="seg-time">${fmtTimestamp(seg.start)} &rarr; ${fmtTimestamp(seg.end)}</span>
                <span class="seg-conf ${confClass(seg.avg_logprob)}">${confLabel(seg.avg_logprob)}</span>
                <div style="margin-left:auto; display:flex; gap:6px;">
                    <button class="btn btn-outline" style="font-size:11px; padding:3px 10px"
                        onclick="toggleFlag(${seg.id}, this, event)">
                        ${isFlagged ? 'Unflag' : 'Flag'}
                    </button>
                    <button class="btn btn-outline" style="font-size:11px; padding:3px 10px; ${isVerified ? 'border-color:var(--verified-border)' : ''}"
                        onclick="toggleVerify(${seg.id}, this, event)">
                        ${isVerified ? 'Verified' : 'Mark OK'}
                    </button>
                </div>
            </div>
            <div class="seg-text">${wordsHtml || seg.text}</div>
            <div class="correction-panel ${isFlagged ? 'open' : ''}" id="corr-${seg.id}">
                <label>What you actually hear (Hinglish is fine):</label>
                <textarea id="corr-text-${seg.id}" oninput="updateCorrection(${seg.id})"
                    placeholder="Type exactly what you hear...">${corrText}</textarea>
                <div class="error-types">
                    <label><input type="radio" name="errtype-${seg.id}" value="wrong_word"
                        ${corrType === 'wrong_word' ? 'checked' : ''}
                        onchange="updateCorrection(${seg.id})"> Wrong word</label>
                    <label><input type="radio" name="errtype-${seg.id}" value="gender_changed"
                        ${corrType === 'gender_changed' ? 'checked' : ''}
                        onchange="updateCorrection(${seg.id})"> Gender changed</label>
                    <label><input type="radio" name="errtype-${seg.id}" value="missing_bengali"
                        ${corrType === 'missing_bengali' ? 'checked' : ''}
                        onchange="updateCorrection(${seg.id})"> Missing Bengali</label>
                    <label><input type="radio" name="errtype-${seg.id}" value="hallucination"
                        ${corrType === 'hallucination' ? 'checked' : ''}
                        onchange="updateCorrection(${seg.id})"> Hallucination/noise</label>
                    <label><input type="radio" name="errtype-${seg.id}" value="other"
                        ${corrType === 'other' ? 'checked' : ''}
                        onchange="updateCorrection(${seg.id})"> Other</label>
                </div>
                <label>Notes (optional):</label>
                <textarea id="corr-notes-${seg.id}" style="min-height:30px"
                    oninput="updateCorrection(${seg.id})"
                    placeholder="Any extra notes...">${corrNotes}</textarea>
            </div>
        `;

        div.addEventListener('click', (e) => {
            if (e.target.closest('button') || e.target.closest('textarea') || e.target.closest('input') || e.target.closest('.correction-panel')) return;
            playSeg(seg.start, seg.end, e);
        });

        container.appendChild(div);
    });
}

function playSeg(start, end, e) {
    if (e) e.stopPropagation();
    if (!audio) { alert('Load an audio file first'); return; }
    audio.currentTime = start;
    audio.play();
    $('#global-play').innerHTML = '&#9646;&#9646;';

    // Auto-pause at segment end
    const handler = () => {
        if (audio.currentTime >= end) {
            audio.pause();
            $('#global-play').innerHTML = '&#9654;';
            audio.removeEventListener('timeupdate', handler);
        }
    };
    audio.addEventListener('timeupdate', handler);
}

function toggleFlag(segId, btn, e) {
    e.stopPropagation();
    const panel = document.getElementById(`corr-${segId}`);
    const segEl = btn.closest('.segment');

    if (corrections[segId]) {
        delete corrections[segId];
        panel.classList.remove('open');
        segEl.classList.remove('flagged');
        btn.textContent = 'Flag';
    } else {
        const seg = TRANSCRIPTS[currentFile].segments.find(s => s.id === segId);
        corrections[segId] = {
            segment_id: segId,
            start: seg.start,
            end: seg.end,
            whisper_text: seg.text,
            correction: '',
            error_type: 'wrong_word',
            notes: ''
        };
        panel.classList.add('open');
        segEl.classList.add('flagged');
        segEl.classList.remove('verified');
        verifiedSegs.delete(segId);
        btn.textContent = 'Unflag';
        const ta = document.getElementById(`corr-text-${segId}`);
        if (ta) ta.focus();
    }
    scheduleSave();
    updateStats();
}

function toggleVerify(segId, btn, e) {
    e.stopPropagation();
    const segEl = btn.closest('.segment');
    if (verifiedSegs.has(segId)) {
        verifiedSegs.delete(segId);
        segEl.classList.remove('verified');
        btn.textContent = 'Mark OK';
        btn.style.borderColor = '';
    } else {
        verifiedSegs.add(segId);
        segEl.classList.add('verified');
        btn.textContent = 'Verified';
        btn.style.borderColor = 'var(--verified-border)';
        // Remove flag if present
        if (corrections[segId]) {
            delete corrections[segId];
            const panel = document.getElementById(`corr-${segId}`);
            panel.classList.remove('open');
            segEl.classList.remove('flagged');
            const flagBtn = segEl.querySelector('.seg-header .btn-outline');
            if (flagBtn) flagBtn.textContent = 'Flag';
        }
    }
    scheduleSave();
    updateStats();
}

function updateCorrection(segId) {
    if (!corrections[segId]) return;
    const text = document.getElementById(`corr-text-${segId}`);
    const notes = document.getElementById(`corr-notes-${segId}`);
    const typeEl = document.querySelector(`input[name="errtype-${segId}"]:checked`);

    if (text) corrections[segId].correction = text.value;
    if (notes) corrections[segId].notes = notes.value;
    if (typeEl) corrections[segId].error_type = typeEl.value;

    scheduleSave();
}

function scheduleSave() {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveCorrections, 1000);
}

async function saveCorrections() {
    if (!currentFile) return;
    const data = {
        file: currentFile,
        speaker_code: TRANSCRIPTS[currentFile].speaker_code,
        corrections: Object.values(corrections),
        verified_segments: Array.from(verifiedSegs),
        timestamp: new Date().toISOString()
    };

    try {
        const resp = await fetch(`/api/corrections/${currentFile}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data, null, 2)
        });
        if (resp.ok) {
            updateStats('saved');
        }
    } catch(e) {
        console.error('Save failed:', e);
    }
}

function updateStats(saveStatus) {
    if (!currentFile) return;
    const data = TRANSCRIPTS[currentFile];
    const total = data.segments.length;
    const flagged = Object.keys(corrections).length;
    const verified = verifiedSegs.size;
    const remaining = total - flagged - verified;
    const statusText = saveStatus === 'saved' ? ' &middot; saved' : '';

    $('#stats').innerHTML = `
        <span><strong>${flagged}</strong> flagged</span>
        <span><strong>${verified}</strong> OK</span>
        <span><strong>${remaining}</strong> remaining</span>
        <span style="color: var(--high-conf)">${statusText}</span>
    `;
}

// Keyboard shortcuts
document.addEventListener('keydown', e => {
    if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;

    const data = TRANSCRIPTS[currentFile];
    if (!data) return;

    if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
    } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        if (audio) audio.currentTime = Math.max(0, audio.currentTime - 3);
    } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        if (audio) audio.currentTime = Math.min(audio.duration, audio.currentTime + 3);
    } else if (e.code === 'ArrowUp') {
        e.preventDefault();
        if (currentSegIdx > 0) {
            currentSegIdx--;
            const seg = data.segments[currentSegIdx];
            playSeg(seg.start, seg.end, null);
            scrollToSeg(currentSegIdx);
        }
    } else if (e.code === 'ArrowDown') {
        e.preventDefault();
        if (currentSegIdx < data.segments.length - 1) {
            currentSegIdx++;
            const seg = data.segments[currentSegIdx];
            playSeg(seg.start, seg.end, null);
            scrollToSeg(currentSegIdx);
        }
    } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        if (currentSegIdx >= 0) {
            const seg = data.segments[currentSegIdx];
            const segEl = document.querySelector(`.segment[data-idx="${currentSegIdx}"]`);
            if (segEl) {
                const btn = segEl.querySelector('.seg-header .btn-outline');
                if (btn) toggleFlag(seg.id, btn, { stopPropagation: () => {} });
            }
        }
    }
});

function scrollToSeg(idx) {
    const el = document.querySelector(`.segment[data-idx="${idx}"]`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

init();
</script>
"""


class VerifierHandler(http.server.BaseHTTPRequestHandler):
    html_content = ""

    def log_message(self, format, *args):
        pass  # suppress request logs

    def do_GET(self):
        path = unquote(self.path)

        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.html_content.encode("utf-8"))

        elif path.startswith("/audio/"):
            fname = path[7:]
            fpath = AUDIO_DIR / fname
            if not fpath.exists():
                self.send_response(404)
                self.end_headers()
                return
            self._serve_file_with_ranges(fpath, "audio/wav")

        elif path.startswith("/api/corrections/"):
            file_key = path[17:]
            corr_path = CORRECTIONS_DIR / f"{file_key}_corrections.json"
            if corr_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(corr_path.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = unquote(self.path)

        if path.startswith("/api/corrections/"):
            file_key = path[17:]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            corr_path = CORRECTIONS_DIR / f"{file_key}_corrections.json"
            corr_path.write_bytes(body)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file_with_ranges(self, fpath, content_type):
        file_size = fpath.stat().st_size
        range_header = self.headers.get("Range")

        if range_header:
            try:
                range_spec = range_header.replace("bytes=", "")
                start_str, end_str = range_spec.split("-")
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(fpath, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(65536, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except Exception:
                self.send_response(416)
                self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with open(fpath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)


def main():
    CORRECTIONS_DIR.mkdir(exist_ok=True)

    transcripts = load_transcripts()
    audio_files = get_audio_files()

    if not transcripts:
        print(f"No transcript JSONs found in {TRANSCRIPTS_DIR}")
        sys.exit(1)

    print(f"Found {len(transcripts)} transcripts")
    print(f"Found {len(audio_files)} audio files in {AUDIO_DIR}")
    if not audio_files:
        print("  (You can load audio files manually in the browser)")

    html = HTML_TEMPLATE.replace(
        "__TRANSCRIPTS_DATA__",
        json.dumps(transcripts, ensure_ascii=False),
    ).replace(
        "__AUDIO_MAP__",
        json.dumps(audio_files, ensure_ascii=False),
    )

    VerifierHandler.html_content = html

    server = http.server.HTTPServer(("127.0.0.1", PORT), VerifierHandler)
    url = f"http://localhost:{PORT}"
    print(f"\nVerification server running at {url}")
    print("Press Ctrl+C to stop\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
