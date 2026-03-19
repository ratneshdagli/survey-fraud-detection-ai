"""
Z-AUDIT — Speaker Diarization Module
Uses pyannote.audio locally with GPU for real speaker detection.
Detects: number of speakers, speaking time per speaker, speaker turns.
"""

import os
import json
import traceback

# Lazy-load the pipeline (heavy import, only load once)
_pipeline = None


def _get_pipeline():
    """Lazy-load the pyannote speaker diarization pipeline (GPU if available)."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    # Read token at call time (after main.py has called load_dotenv)
    hf_token = os.getenv("HF_TOKEN", "")
    if not hf_token:
        print("[Speaker Analysis] ERROR: HF_TOKEN is empty! Set it in .env")
        return None

    print(f"[Speaker Analysis] Using HF_TOKEN: {hf_token[:8]}...")

    try:
        import torch
        from pyannote.audio import Pipeline

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Speaker Analysis] Loading pyannote pipeline on {device}...")

        _pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        )
        _pipeline = _pipeline.to(device)
        print(f"[Speaker Analysis] Pipeline loaded successfully on {device}")
        return _pipeline

    except Exception as e:
        print(f"[Speaker Analysis] Failed to load pipeline: {e}")
        traceback.print_exc()
        return None


def analyze_speakers(audio_file_path: str) -> dict:
    """
    Run pyannote speaker diarization on an audio file.
    Returns structured speaker analysis data.

    Output format:
    {
        "num_speakers": 2,
        "speakers": {
            "SPEAKER_00": {"total_time": 245.3, "segments": 15, "percentage": 42.1},
            "SPEAKER_01": {"total_time": 337.8, "segments": 14, "percentage": 57.9},
        },
        "total_duration": 583.1,
        "speaker_turns": 29,
        "avg_turn_duration": 20.1,
        "timeline": [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 5.2},
            {"speaker": "SPEAKER_01", "start": 5.5, "end": 12.8},
            ...
        ],
        "analysis_source": "pyannote/speaker-diarization-3.1 (local GPU)",
        "error": null
    }
    """
    if not os.getenv("HF_TOKEN", ""):
        return _fallback_result("No HF_TOKEN configured — set HF_TOKEN in .env")

    if not os.path.exists(audio_file_path):
        return _fallback_result(f"Audio file not found: {audio_file_path}")

    try:
        file_size = os.path.getsize(audio_file_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"[Speaker Analysis] Processing {file_size_mb:.1f}MB audio: {audio_file_path}")

        pipeline = _get_pipeline()
        if pipeline is None:
            return _fallback_result("pyannote pipeline failed to load — check install and HF token")

        # Pre-load audio with soundfile + torch (bypasses broken torchcodec/torchaudio)
        import soundfile as sf
        import torch
        print(f"[Speaker Analysis] Loading audio with soundfile...")
        audio_np, sample_rate = sf.read(audio_file_path, dtype="float32")
        # soundfile returns (samples, channels) — torch needs (channels, samples)
        if audio_np.ndim == 1:
            waveform = torch.from_numpy(audio_np).unsqueeze(0)
        else:
            waveform = torch.from_numpy(audio_np.T)

        # Run diarization with pre-loaded waveform
        print(f"[Speaker Analysis] Running diarization on {waveform.shape[1]/sample_rate:.1f}s audio...")
        diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

        # Parse results
        # pyannote 4.x returns DiarizeOutput, extract the Annotation from it
        if hasattr(diarization, 'speaker_diarization'):
            annotation = diarization.speaker_diarization
        else:
            annotation = diarization  # fallback for older versions

        speakers = {}
        timeline = []
        total_duration = 0.0

        for turn, _, speaker in annotation.itertracks(yield_label=True):
            start = turn.start
            end = turn.end
            duration = end - start

            if duration <= 0:
                continue

            if speaker not in speakers:
                speakers[speaker] = {"total_time": 0.0, "segments": 0}

            speakers[speaker]["total_time"] += duration
            speakers[speaker]["segments"] += 1

            timeline.append({
                "speaker": speaker,
                "start": round(start, 2),
                "end": round(end, 2),
            })

            total_duration = max(total_duration, end)

        # Calculate percentages
        total_speaking_time = sum(s["total_time"] for s in speakers.values())
        for label, data in speakers.items():
            data["total_time"] = round(data["total_time"], 1)
            data["percentage"] = round(
                (data["total_time"] / total_speaking_time * 100) if total_speaking_time > 0 else 0, 1
            )

        num_speakers = len(speakers)
        speaker_turns = len(timeline)
        avg_turn = round(total_speaking_time / speaker_turns, 1) if speaker_turns > 0 else 0

        result = {
            "num_speakers": num_speakers,
            "speakers": speakers,
            "total_duration": round(total_duration, 1),
            "speaker_turns": speaker_turns,
            "avg_turn_duration": avg_turn,
            "timeline": timeline[:50],  # Limit to first 50 for prompt size
            "analysis_source": "pyannote/speaker-diarization-3.1 (local GPU)",
            "error": None,
        }

        print(f"[Speaker Analysis] ✅ Detected {num_speakers} speaker(s), {speaker_turns} turns, {total_duration:.0f}s total")
        for label, data in speakers.items():
            print(f"  {label}: {data['total_time']}s ({data['percentage']}%), {data['segments']} segments")

        return result

    except Exception as e:
        print(f"[Speaker Analysis Error] {e}")
        traceback.print_exc()
        return _fallback_result(str(e))


def format_speaker_data_for_prompt(speaker_data: dict) -> str:
    """
    Format speaker analysis into a readable text block for the LLM prompt.
    This gives the LLM REAL evidence about voices instead of guessing from text.
    """
    if not speaker_data or speaker_data.get("error"):
        return "SPEAKER ANALYSIS: Not available (no audio file or analysis failed)"

    lines = []
    lines.append(f"SPEAKER ANALYSIS (pyannote AI diarization — machine-detected, not guessed):")
    lines.append(f"  Speakers detected: {speaker_data['num_speakers']}")
    lines.append(f"  Total audio duration: {speaker_data['total_duration']}s")
    lines.append(f"  Total speaker turns: {speaker_data['speaker_turns']}")
    lines.append(f"  Average turn duration: {speaker_data['avg_turn_duration']}s")
    lines.append("")

    # Speaker breakdown
    for label, data in speaker_data.get("speakers", {}).items():
        lines.append(f"  {label}: spoke for {data['total_time']}s ({data['percentage']}% of speaking time), {data['segments']} segments")

    # Key observations the LLM should consider
    lines.append("")
    num = speaker_data["num_speakers"]
    if num == 1:
        lines.append("  ⚠️  CRITICAL: Only ONE speaker detected in the entire recording.")
        lines.append("      This is a strong indicator of mimicry or fake form fraud.")
    elif num == 2:
        lines.append("  ✅ TWO speakers detected — consistent with a real surveyor-respondent interview.")
        # Check if one speaker dominates heavily
        percentages = [d["percentage"] for d in speaker_data.get("speakers", {}).values()]
        if percentages and max(percentages) > 85:
            lines.append(f"  ⚠️  BUT one speaker dominates ({max(percentages)}% of speaking time).")
            lines.append("      The respondent may not be actively participating.")
    elif num > 2:
        lines.append(f"  ℹ️  {num} speakers detected — multiple people present during the interview.")

    # First 10 turns of the conversation
    timeline = speaker_data.get("timeline", [])
    if timeline:
        lines.append("")
        lines.append("  First 10 speaker turns:")
        for i, turn in enumerate(timeline[:10]):
            duration = round(turn["end"] - turn["start"], 1)
            lines.append(f"    Turn {i+1}: {turn['speaker']} [{turn['start']}s – {turn['end']}s] ({duration}s)")

    return "\n".join(lines)


def _fallback_result(error_msg: str) -> dict:
    """Return a fallback result when speaker analysis fails."""
    print(f"[Speaker Analysis] Fallback: {error_msg}")
    return {
        "num_speakers": None,
        "speakers": {},
        "total_duration": 0,
        "speaker_turns": 0,
        "avg_turn_duration": 0,
        "timeline": [],
        "analysis_source": "none",
        "error": error_msg,
    }
