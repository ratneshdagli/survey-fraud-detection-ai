/**
 * Z-AUDIT — Record Detail Slide-Out Panel (v2 — Explainable Analysis)
 * Shows full details of a single audit record with per-section analysis,
 * evidence citations, and detailed score breakdowns.
 */

import { useState, useEffect, useRef } from 'react';
import { api } from '../api';

const FRAUD_COLORS = {
  fake_form: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', bar: 'bg-red-500' },
  mimicry: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', bar: 'bg-orange-500' },
  force_survey: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', bar: 'bg-amber-500' },
  clean: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', bar: 'bg-emerald-500' },
};

const FRAUD_LABELS = {
  fake_form: 'Fake Form',
  mimicry: 'Mimicry',
  force_survey: 'Force Survey',
  clean: 'Clean',
};

const FRAUD_EMOJI = {
  fake_form: '👻',
  mimicry: '🎭',
  force_survey: '💪',
  clean: '✅',
};

const SECTION_ICONS = {
  'Voice & Speaker Analysis': '🎙️',
  'Script Compliance': '📋',
  'Data Integrity': '🔍',
  'Questioning Technique': '❓',
  'Response Authenticity': '🛡️',
};

const SEVERITY_STYLES = {
  critical: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-200', dot: 'bg-red-500', label: '🔴 Critical' },
  warning: { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-200', dot: 'bg-amber-500', label: '🟡 Warning' },
  info: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', dot: 'bg-blue-500', label: '🔵 Info' },
};

const VERDICT_STYLES = {
  pass: { bg: 'bg-emerald-100', text: 'text-emerald-800', label: '✅ Pass' },
  partial: { bg: 'bg-amber-100', text: 'text-amber-800', label: '⚠️ Partial' },
  fail: { bg: 'bg-red-100', text: 'text-red-800', label: '❌ Fail' },
};


function ScoreBar({ label, score, color }) {
  const percentage = (score / 10) * 100;
  const getBarColor = () => {
    if (score >= 7) return 'bg-emerald-500';
    if (score >= 5) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-gray-600">{label}</span>
        <span className="text-sm font-bold text-gray-800">{score?.toFixed(1) ?? '—'}/10</span>
      </div>
      <div className="progress-bar">
        <div className={`progress-fill ${color || getBarColor()}`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}


function SectionCard({ section, onPlayClip, uid }) {
  const [expanded, setExpanded] = useState(false);

  const icon = SECTION_ICONS[section.section] || '📊';
  const verdictStyle = VERDICT_STYLES[section.verdict] || VERDICT_STYLES.partial;
  const scoreColor = section.score >= 7 ? 'text-emerald-600' : section.score >= 5 ? 'text-amber-600' : 'text-red-600';
  const scoreBarColor = section.score >= 7 ? 'bg-emerald-500' : section.score >= 5 ? 'bg-amber-500' : 'bg-red-500';
  const scorePercent = (section.score / 10) * 100;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden transition-all duration-200 hover:shadow-md">
      {/* Section Header — always visible, clickable */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3.5 flex items-center gap-3 bg-white hover:bg-gray-50 transition-colors text-left"
      >
        <span className="text-lg flex-shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-sm text-gray-900 truncate">{section.section}</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${verdictStyle.bg} ${verdictStyle.text}`}>
              {verdictStyle.label}
            </span>
          </div>
          {/* Mini score bar */}
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-500 ${scoreBarColor}`} style={{ width: `${scorePercent}%` }} />
            </div>
            <span className={`text-xs font-bold ${scoreColor}`}>{section.score?.toFixed(1)}</span>
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-gray-100 bg-gray-50/50 space-y-3">
          {/* Findings */}
          {section.findings && section.findings.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Findings</p>
              <ul className="space-y-1.5">
                {section.findings.map((finding, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0" />
                    <span className="text-sm text-gray-700 leading-relaxed">{finding}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Evidence */}
          {section.evidence && section.evidence.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Evidence</p>
              <div className="space-y-2">
                {section.evidence.map((ev, idx) => {
                  const sev = SEVERITY_STYLES[ev.severity] || SEVERITY_STYLES.info;
                  return (
                    <div key={idx} className={`${sev.bg} ${sev.border} border rounded-lg p-3`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] font-bold ${sev.text} uppercase`}>{sev.label}</span>
                        <span className="text-[10px] text-gray-500 font-medium">
                          [{ev.type || 'observation'}]
                        </span>
                        {ev.timestamp_start != null && (
                          <span className="text-[10px] text-gray-400 ml-auto">
                            {Math.floor(ev.timestamp_start / 60)}:{String(Math.floor(ev.timestamp_start % 60)).padStart(2, '0')}
                            {ev.timestamp_end != null && ` — ${Math.floor(ev.timestamp_end / 60)}:${String(Math.floor(ev.timestamp_end % 60)).padStart(2, '0')}`}
                          </span>
                        )}
                      </div>
                      <p className={`text-sm ${sev.text} leading-relaxed`}>{ev.text}</p>
                      {ev.timestamp_start != null && uid ? (
                        <div className="mt-3 overflow-hidden rounded-lg border border-gray-200 bg-gray-50/50 shadow-sm">
                          <div className="bg-gray-100/80 px-3 py-2 border-b border-gray-200 flex justify-between items-center">
                            <div className="flex items-center gap-1.5">
                              <span className="text-lg">🎧</span>
                              <span className="text-xs uppercase font-bold text-gray-500 tracking-wider">
                                Evidence Audio
                              </span>
                            </div>
                            <span className="text-[10px] font-mono font-medium text-gray-500 bg-white px-2 py-0.5 rounded border border-gray-200">
                              {Math.floor(ev.timestamp_start / 60)}:{String(Math.floor(ev.timestamp_start % 60)).padStart(2, '0')} - {Math.floor((ev.timestamp_end || ev.timestamp_start + 10) / 60)}:{String(Math.floor((ev.timestamp_end || ev.timestamp_start + 10) % 60)).padStart(2, '0')}
                            </span>
                          </div>
                          <div className="px-3 py-2">
                            <audio 
                              controls 
                              className="w-full h-8 outline-none" 
                              src={`/api/audio/${uid}#t=${ev.timestamp_start},${ev.timestamp_end || ev.timestamp_start + 10}`} 
                              preload="metadata"
                            />
                          </div>
                        </div>
                      ) : ev.timestamp_start != null && onPlayClip && (
                        <button
                          onClick={() => onPlayClip(ev.timestamp_start, ev.timestamp_end)}
                          className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/80 hover:bg-white border border-gray-200 rounded-lg text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-all shadow-sm hover:shadow"
                        >
                          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                          ▶ Play Clip ({Math.round((ev.timestamp_end || ev.timestamp_start + 10) - ev.timestamp_start)}s)
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


function SpeakerTimelineBar({ speakerData, onPlayClip }) {
  if (!speakerData?.timeline?.length || !speakerData?.total_duration) return null;

  const { timeline, total_duration } = speakerData;
  const speakerColors = {
    'SPEAKER_00': '#3b82f6',  // blue
    'SPEAKER_01': '#10b981',  // green
    'SPEAKER_02': '#a855f7',  // purple
    'SPEAKER_03': '#f59e0b',  // amber
  };

  return (
    <div className="mt-4">
      <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Conversation Timeline</p>
      <div
        className="relative h-8 bg-gray-200 rounded-lg overflow-hidden cursor-pointer"
        onClick={(e) => {
          if (!onPlayClip) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const pct = (e.clientX - rect.left) / rect.width;
          const time = pct * total_duration;
          onPlayClip(time, Math.min(time + 10, total_duration));
        }}
        title="Click to play from that point"
      >
        {timeline.map((turn, idx) => {
          const left = (turn.start / total_duration) * 100;
          const width = ((turn.end - turn.start) / total_duration) * 100;
          const color = speakerColors[turn.speaker] || '#94a3b8';
          return (
            <div
              key={idx}
              className="absolute top-0 h-full opacity-85 hover:opacity-100 transition-opacity"
              style={{ left: `${left}%`, width: `${Math.max(width, 0.3)}%`, backgroundColor: color }}
              title={`${turn.speaker}: ${turn.start.toFixed(1)}s — ${turn.end.toFixed(1)}s`}
            />
          );
        })}
      </div>
      {/* Legend */}
      <div className="flex items-center gap-3 mt-2">
        {Object.entries(speakerColors).slice(0, Object.keys(speakerData.speakers || {}).length).map(([label, color], idx) => (
          <div key={label} className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
            <span className="text-[10px] text-gray-500 font-medium">
              {['Surveyor', 'Respondent', 'Speaker 3', 'Speaker 4'][idx] || label}
            </span>
          </div>
        ))}
        <span className="text-[10px] text-gray-400 ml-auto">Click timeline to play</span>
      </div>
    </div>
  );
}


function SpeakerDiarizationCard({ speakerData, onPlayClip }) {
  if (!speakerData || speakerData.error) return null;

  const { num_speakers, speakers, total_duration, speaker_turns, avg_turn_duration } = speakerData;
  const speakerEntries = Object.entries(speakers || {});
  const speakerLabels = ['Surveyor (likely)', 'Respondent (likely)', 'Speaker 3', 'Speaker 4'];

  const statusColor = num_speakers === 1
    ? 'bg-red-100 border-red-200 text-red-800'
    : num_speakers === 2
    ? 'bg-emerald-100 border-emerald-200 text-emerald-800'
    : 'bg-blue-100 border-blue-200 text-blue-800';

  const statusIcon = num_speakers === 1 ? '🔴' : num_speakers === 2 ? '✅' : 'ℹ️';
  const statusText = num_speakers === 1
    ? 'Only 1 speaker — strong indicator of mimicry/fake'
    : num_speakers === 2
    ? '2 speakers detected — consistent with real interview'
    : `${num_speakers} speakers detected`;

  return (
    <div className="bg-violet-50 border border-violet-200 rounded-xl p-5">
      <h3 className="text-xs font-semibold text-violet-600 uppercase tracking-wider mb-3 flex items-center gap-2">
        🔊 AI Speaker Diarization
        <span className="text-[10px] font-normal text-violet-400">(pyannote)</span>
      </h3>

      {/* Status Banner */}
      <div className={`${statusColor} border rounded-lg px-3 py-2 mb-4 flex items-center gap-2`}>
        <span>{statusIcon}</span>
        <span className="text-sm font-semibold">{statusText}</span>
      </div>

      {/* Speaker bars */}
      <div className="space-y-3 mb-4">
        {speakerEntries.map(([label, data], idx) => {
          const barColor = idx === 0 ? 'bg-blue-500' : idx === 1 ? 'bg-emerald-500' : 'bg-purple-500';
          return (
            <div key={label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-gray-700">
                  {speakerLabels[idx] || label}
                </span>
                <span className="text-xs text-gray-500">
                  {data.total_time}s ({data.percentage}%)
                </span>
              </div>
              <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${barColor}`}
                  style={{ width: `${data.percentage}%` }}
                />
              </div>
              <p className="text-[10px] text-gray-400 mt-0.5">{data.segments} segments</p>
            </div>
          );
        })}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-white rounded-lg border border-violet-100 p-2 text-center">
          <p className="text-lg font-bold text-violet-700">{num_speakers}</p>
          <p className="text-[9px] text-gray-500 font-semibold uppercase">Speakers</p>
        </div>
        <div className="bg-white rounded-lg border border-violet-100 p-2 text-center">
          <p className="text-lg font-bold text-violet-700">{speaker_turns}</p>
          <p className="text-[9px] text-gray-500 font-semibold uppercase">Turns</p>
        </div>
        <div className="bg-white rounded-lg border border-violet-100 p-2 text-center">
          <p className="text-lg font-bold text-violet-700">{avg_turn_duration}s</p>
          <p className="text-[9px] text-gray-500 font-semibold uppercase">Avg Turn</p>
        </div>
      </div>

      {/* Speaker Timeline Visualization */}
      <SpeakerTimelineBar speakerData={speakerData} onPlayClip={onPlayClip} />
    </div>
  );
}


function KeyFlagsBadges({ flags }) {
  if (!flags || flags.length === 0) return null;

  const flagColors = {
    single_voice: 'bg-red-100 text-red-700',
    gender_mismatch: 'bg-purple-100 text-purple-700',
    no_natural_pauses: 'bg-orange-100 text-orange-700',
    short_duration: 'bg-amber-100 text-amber-700',
    proxy_answering: 'bg-red-100 text-red-700',
    questions_skipped: 'bg-yellow-100 text-yellow-700',
    coerced_responses: 'bg-red-100 text-red-700',
    analysis_failed: 'bg-gray-100 text-gray-600',
  };

  return (
    <div className="flex flex-wrap gap-1.5">
      {flags.map((flag, idx) => {
        const colorClass = flagColors[flag] || 'bg-gray-100 text-gray-700';
        const label = flag.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        return (
          <span key={idx} className={`text-[10px] font-bold px-2 py-1 rounded-full ${colorClass}`}>
            {label}
          </span>
        );
      })}
    </div>
  );
}


export default function RecordDetail({ record: initialRecord, onClose, onDelete, onRecordUpdate }) {
  const [record, setRecord] = useState(initialRecord);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [reanalyzeStatus, setReanalyzeStatus] = useState('');
  const [showTranscript, setShowTranscript] = useState(false);
  const [showAnswers, setShowAnswers] = useState(false);
  const audioRef = useRef(null);

  // Sync with parent
  useEffect(() => {
    setRecord(initialRecord);
  }, [initialRecord]);

  // Fetch available models
  useEffect(() => {
    api.getModels().then(data => {
      setModels(data.models || []);
      setSelectedModel(data.default || '');
    }).catch(() => {});
  }, []);

  if (!record) return null;

  const fraudStyle = FRAUD_COLORS[record.fraud_type] || FRAUD_COLORS.clean;

  // Parse raw_json for additional details
  let rawData = null;
  try {
    rawData = typeof record.raw_json === 'string' ? JSON.parse(record.raw_json) : record.raw_json;
  } catch { }

  const audioAnswers = rawData?.audioanswers || [];
  const isRealTranscript = record.transcript && !record.transcript.includes('MOCK TRANSCRIPT');

  // Detailed analysis data
  const analysis = record.detailed_analysis || null;
  const sections = analysis?.section_analysis || [];
  const executiveSummary = analysis?.executive_summary || record.fraud_reason || '';
  const keyFlags = analysis?.key_flags || [];
  // Speaker data: prefer cached from record, fallback to analysis
  const speakerData = record.speaker_data || analysis?.speaker_data || null;

  // Play a specific clip from the audio
  const clipTimeoutRef = useRef(null);

  const clearClipTimeout = () => {
    if (clipTimeoutRef.current) {
      clearTimeout(clipTimeoutRef.current);
      clipTimeoutRef.current = null;
    }
  };

  const playClip = (startSeconds, endSeconds) => {
    const audio = audioRef.current;
    if (!audio) return;
    clearClipTimeout();  // cancel any previous clip timeout
    audio.currentTime = startSeconds;
    audio.play();
    if (endSeconds != null) {
      const duration = (endSeconds - startSeconds) * 1000;
      clipTimeoutRef.current = setTimeout(() => {
        if (audio.currentTime >= endSeconds - 0.5) {
          audio.pause();
        }
        clipTimeoutRef.current = null;
      }, duration + 200);
    }
  };

  const handleReanalyze = async () => {
    if (!selectedModel) return;
    setIsReanalyzing(true);
    setReanalyzeStatus(`🤖 Re-analyzing with ${models.find(m => m.id === selectedModel)?.name || selectedModel}...`);

    try {
      const result = await api.reanalyzeRecord(record.uid, selectedModel);
      setRecord(result.record);
      setReanalyzeStatus(`✅ Done! Scroll down for detailed analysis.`);
      // Notify parent to refresh dashboard
      if (onRecordUpdate) onRecordUpdate(result.record);
    } catch (err) {
      setReanalyzeStatus(`❌ Failed: ${err.message}`);
    } finally {
      setIsReanalyzing(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div className="modal-backdrop" onClick={onClose} />

      {/* Slide Panel */}
      <div className="slide-panel">
        {/* Header */}
        <div className="sticky top-0 bg-white z-10 px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">UID: {record.uid}</h2>
            <p className="text-sm text-gray-500">{record.surveyor_name}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onDelete(record.uid)}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
              title="Delete"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-6">

          {/* ======= FRAUD STATUS + EXECUTIVE SUMMARY ======= */}
          <div className={`${fraudStyle.bg} ${fraudStyle.border} border rounded-xl p-4`}>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">{FRAUD_EMOJI[record.fraud_type]}</span>
              <div>
                <p className={`font-bold text-lg ${fraudStyle.text}`}>
                  {record.fraud_detected ? 'Fraud Detected' : 'No Fraud'}
                </p>
                <p className={`text-sm font-semibold ${fraudStyle.text} opacity-80`}>
                  Type: {FRAUD_LABELS[record.fraud_type]}
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed mt-3">{executiveSummary}</p>

            {/* Key Flags */}
            {keyFlags.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200/50">
                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Key Flags</p>
                <KeyFlagsBadges flags={keyFlags} />
              </div>
            )}
          </div>


          {/* ======= RE-ANALYZE SECTION ======= */}
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
            <h3 className="text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-3">
              🔄 Re-Analyze with Different Model
            </h3>
            <p className="text-xs text-gray-500 mb-3">
              Re-runs speaker diarization + LLM fraud analysis with detailed per-section scoring.
            </p>
            <div className="flex items-center gap-2">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="flex-1 text-sm border border-indigo-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={isReanalyzing}
              >
                {models.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
              <button
                onClick={handleReanalyze}
                disabled={isReanalyzing}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {isReanalyzing ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    Analyzing...
                  </span>
                ) : 'Re-Analyze'}
              </button>
            </div>
            {reanalyzeStatus && (
              <p className="text-sm mt-3 font-medium text-gray-700">{reanalyzeStatus}</p>
            )}
          </div>


          {/* ======= AUDIO PLAYER ======= */}
          <div className="bg-gray-50 rounded-xl p-5">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">🎙️ Audio Recording</h3>
            <audio
              ref={audioRef}
              controls
              className="w-full"
              src={`/api/audio/${record.uid}`}
              onSeeking={clearClipTimeout}
              onPlay={() => { /* don't clear on play from playClip */ }}
            >
              Your browser does not support audio playback.
            </audio>
            <p className="text-xs text-gray-400 mt-2">UID: {record.uid} | Duration: {record.time_difference_seconds ? `${Math.floor(record.time_difference_seconds / 60)}m ${record.time_difference_seconds % 60}s` : 'Unknown'}</p>
          </div>


          {/* ======= SPEAKER DIARIZATION ======= */}
          <SpeakerDiarizationCard speakerData={speakerData} onPlayClip={playClip} />


          {/* ======= SCORE OVERVIEW (compact bars) ======= */}
          <div className="bg-gray-50 rounded-xl p-5 space-y-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Score Overview</h3>
            <ScoreBar label="Quality Score" score={record.quality_score} />
            <ScoreBar label="Completeness" score={record.completeness_score} />
            <ScoreBar label="Fraud Risk" score={record.fraud_risk_score} color="bg-red-500" />
            <ScoreBar label="Technique" score={record.technique_score} />
          </div>


          {/* ======= DETAILED SECTION ANALYSIS ======= */}
          {sections.length > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  📊 Detailed Analysis ({sections.length} Sections)
                </h3>
                <span className="text-[10px] text-gray-400">Click sections to expand</span>
              </div>
              <div className="space-y-2">
                {sections.map((section, idx) => (
                  <SectionCard key={idx} section={section} onPlayClip={playClip} uid={record.uid} />
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-center">
              <p className="text-sm text-yellow-700 font-medium">
                ⚠️ No detailed analysis available for this record.
              </p>
              <p className="text-xs text-yellow-600 mt-1">
                Click "Re-Analyze" above to generate a full per-section breakdown with evidence.
              </p>
            </div>
          )}


          {/* ======= TRANSCRIPT INFO ======= */}
          <div className="bg-gray-50 rounded-xl p-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">📝 Transcript Info</h3>
            <div className="flex items-center gap-3">
              <span className={`text-xs font-bold px-2 py-1 rounded-full ${isRealTranscript ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                {isRealTranscript ? '✅ Real Whisper' : '📋 Mock (from Q&A)'}
              </span>
              <span className="text-xs text-gray-500">{record.transcript ? record.transcript.length : 0} characters</span>
            </div>
          </div>


          {/* ======= SURVEY DETAILS ======= */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Survey Details</h3>
            <div className="grid grid-cols-2 gap-3">
              <InfoItem label="Date" value={record.survey_date} />
              <InfoItem label="Time" value={record.survey_time} />
              <InfoItem label="Duration" value={record.time_difference_seconds ? `${Math.floor(record.time_difference_seconds / 60)}m ${record.time_difference_seconds % 60}s` : '—'} />
              <InfoItem label="Gender" value={record.respondent_gender} />
              <InfoItem label="DOB" value={record.respondent_dob} />
              <InfoItem label="Area" value={record.respondent_area} />
              <InfoItem label="Occupation" value={record.respondent_occupation} />
              <InfoItem label="Surveyor ID" value={record.surveyor_id} />
            </div>
          </div>

          {/* Address */}
          {record.actual_address && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Location</h3>
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
                <p className="text-sm text-gray-700 flex items-start gap-2">
                  <svg className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {record.actual_address}
                </p>
              </div>
            </div>
          )}


          {/* ======= RECORDED ANSWERS (collapsible) ======= */}
          {audioAnswers.length > 0 && (
            <div>
              <button
                onClick={() => setShowAnswers(!showAnswers)}
                className="w-full flex items-center justify-between text-left"
              >
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Recorded Answers ({audioAnswers.length})
                </h3>
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${showAnswers ? 'rotate-180' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showAnswers && (
                <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 mt-3">
                  {audioAnswers.map((pair, idx) => {
                    if (!Array.isArray(pair) || pair.length < 2) return null;
                    const answer = pair[0];
                    const question = pair[1];
                    if (!question || String(question).toUpperCase().includes('UPLOAD')) return null;

                    // Extract English portion of question
                    const qParts = String(question).split('/');
                    const qShort = qParts.find(p => /[a-zA-Z]{5,}/.test(p))?.trim() || String(question).slice(0, 120);

                    return (
                      <div key={idx} className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs font-semibold text-blue-600 mb-1">Q{idx + 1}: {qShort.slice(0, 150)}</p>
                        <p className="text-sm text-gray-700">
                          {answer ? String(answer).slice(0, 200) : <span className="text-gray-400 italic">No answer</span>}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}


          {/* ======= FULL TRANSCRIPT (collapsible) ======= */}
          {record.transcript && (
            <div>
              <button
                onClick={() => setShowTranscript(!showTranscript)}
                className="w-full flex items-center justify-between text-left"
              >
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Full Transcript</h3>
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${showTranscript ? 'rotate-180' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showTranscript && (
                <div className="bg-gray-900 rounded-xl p-4 max-h-[300px] overflow-y-auto mt-3">
                  <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap leading-relaxed">
                    {record.transcript}
                  </pre>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </>
  );
}

function InfoItem({ label, value }) {
  return (
    <div className="bg-white rounded-lg border border-gray-100 p-3">
      <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-medium text-gray-800 mt-0.5 truncate">{value || '—'}</p>
    </div>
  );
}
